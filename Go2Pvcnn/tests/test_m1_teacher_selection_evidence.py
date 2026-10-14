"""Producer-owned preparation selection, before interpolation or actuation."""
import copy
from dataclasses import replace

import pytest
import torch

from test_m1_reference_teacher import api, advance
from test_m1_teacher_reference_commit import near_state, prepared_teacher
from test_m1_teacher_probe_contract import probe, episode, verify_episode, real_video_files


def observed(teacher, s, *, diagnostic=True):
    contexts = getattr(teacher, '_probe_selection_context', {})
    probe().observe_preparation_selection(teacher, s, contexts)
    out = teacher.diagnostic_step(s, active_wheel=0, lift=False) if diagnostic else teacher.step(s)
    return out, contexts


def test_not_ready_can_search_but_cannot_lift(monkeypatch):
    t = api(); s = near_state(); teacher = t.ReferenceTeacher()
    s.com_pos_w[:, :2] = (s.wheel_pos_w[:, 1, :2]+s.wheel_pos_w[:, 2, :2])/2
    assert hasattr(teacher, '_select_preparation_pose'), 'single preparation selection boundary missing'
    original = teacher._select_preparation_pose; calls = []
    def selected(st, i, work, accepted, q, branch):
        assert st is s
        result = original(st, i, work, accepted, q, branch)
        calls.append(result)
        return result
    monkeypatch.setattr(teacher, '_select_preparation_pose', selected)
    out, contexts = observed(teacher, s)
    d = probe().diagnostic_json(out.diagnostic[0].tolist())
    assert len(calls) == 1 and calls[0].valid.item()
    assert d['measured_com_margin_m'] < .010 and out.phase.item() != t.Phase.LIFT
    assert d['candidate_measured_triangle_margin_m'] >= .010
    assert contexts[0]['measured_wheels_w'] == s.wheel_pos_w[0].tolist()
    # Accepted interpolation can remain below the final-target threshold.
    assert d['predicted_com_margin_m'] < .010 and d['reference_valid'] == 1


@pytest.mark.parametrize('phase', ['LIFT', 'PASS', 'RESTORE'])
def test_later_phases_do_not_search_or_claim_selection(phase, monkeypatch):
    t = api(); teacher, s, _ = prepared_teacher()
    teacher._rows[0]['phase'] = getattr(t.Phase, phase)
    monkeypatch.setattr(teacher, '_select_preparation_pose', lambda *_: pytest.fail('later phase selection'))
    out, contexts = observed(teacher, advance(s), diagnostic=False)
    assert not contexts
    assert probe().diagnostic_json(out.diagnostic[0].tolist())['candidate_measured_triangle_margin_m'] is None


def test_selection_evidence_rejects_tampering():
    teacher, s = api().ReferenceTeacher(), near_state(batch=2)
    _, contexts = observed(teacher, s)
    module = probe(); context = contexts[0]; choice = context['choice']
    verify = lambda c, v: module.verify_preparation_selection(c, v, replay_backend='cpu', require_backend_evidence=True)
    assert verify(context, choice) == []
    for mutate in (
        lambda c: c['identity'].update(env_id=1),
        lambda c: c['identity'].update(input_frame=99),
        lambda c: c['measured_wheels_w'][1].__setitem__(0, c['measured_wheels_w'][1][0]+.03),
        lambda c: c.pop('anchor'),
        lambda c: c.pop('producer_backend'),
        lambda c: c['producer_backend'].update(device='cuda:99999'),
    ):
        changed = copy.deepcopy(context); mutate(changed)
        assert verify(changed, choice)
    for mutate in (
        lambda c: c.update(candidate_index=55),
        lambda c: c.update(predicted_margin_m=.99),
        lambda c: c.update(measured_triangle_margin_m=.99),
        lambda c: c.update(candidate_count=0),
        lambda c: c.update(valid=False),
    ):
        changed = copy.deepcopy(choice); mutate(changed)
        assert verify(context, changed)
    # The snapshot owns its tensors, even if the input buffers subsequently move.
    saved = copy.deepcopy(context); s.wheel_pos_w.add_(1.)
    assert context == saved


@pytest.mark.parametrize('unsolved', [False, True])
def test_previous_reference_125_and_no_solution_are_replayable(unsolved):
    from ame_baseline.m1_teacher_pose import BodyPose, PoseReference
    teacher, s, _ = prepared_teacher(diagnostic=True)
    row = teacher._rows[0]; prior = row['accepted']
    # Off-grid accepted body has zero displacement cost only at candidate125.
    row['accepted'] = PoseReference(BodyPose(prior.body.pos_w+torch.tensor([[.003,.002,-.005]]),
        prior.body.quat_w), prior.wheels_w)
    if unsolved:
        s.com_pos_w[:, 0] += 100.
    out, contexts = observed(teacher, advance(s))
    choice = contexts[0]['choice']
    assert choice['candidate_index'] == (-1 if unsolved else 125)
    assert choice['valid'] is (not unsolved)
    assert probe().verify_preparation_selection(contexts[0], choice,
        replay_backend='cpu', require_backend_evidence=True) == []


def test_reset_duplicate_and_new_input_keep_only_owned_context():
    teacher, s = api().ReferenceTeacher(), near_state(batch=2)
    _, contexts = observed(teacher, s); saved = copy.deepcopy(contexts)
    observed(teacher, s)
    assert contexts == saved
    reset = replace(s, reset_mask=torch.tensor([True, False]), episode_id=torch.tensor([1, 0]))
    observed(teacher, reset)
    assert 0 not in contexts and contexts[1] == saved[1]
    failed = advance(reset, reset_mask=torch.zeros(2, dtype=torch.bool), collision=torch.tensor([False, True]))
    observed(teacher, failed)
    assert 1 not in contexts


def test_schema7_requires_selection_field_and_rejects_schema6():
    module = probe()
    assert module.SCHEMA_VERSION == 7
    assert api().TeacherConfig().fingerprint != ''
    for mutate in (lambda r: r.update(schema_version=6),
                   lambda r: r['samples'][2].pop('selection_context')):
        record = episode(); mutate(record)
        assert verify_episode(record)['errors']


def test_claimed_selection_cannot_omit_context():
    record = episode()
    record['samples'][2]['teacher_diagnostic'].update(candidate_index=125, candidate_count=126,
        candidate_com_margin_m=.02, candidate_measured_triangle_margin_m=.02)
    assert 'preparation selection evidence mismatch' in verify_episode(record)['errors']


def selection_sample():
    from types import SimpleNamespace
    teacher, s = api().ReferenceTeacher(), near_state(batch=2)
    module = probe(); module.observe_feedback_transactions(teacher)
    out, contexts = observed(teacher, s)
    term = SimpleNamespace(_joint_names=api().M1_ASSET_JOINT_NAMES, process_actions=lambda action: None)
    receipts = module.ActionEvidence(term); receipts.begin(s, out, teacher, 0.)
    sample = dict(receipts.pending[0], env_id=0, active_wheel=0, phase=int(out.phase[0]))
    return teacher, s, contexts, sample


def test_selection_sample_binds_peer_frame_and_precontrol_measurement():
    teacher, s, contexts, sample = selection_sample(); module = probe()
    verify = lambda v: module.verify_selection_sample(v, teacher.cfg,
        replay_backend='cpu', require_backend_evidence=True)
    assert verify(sample) == []
    assert sample['selection_context'] == contexts[0]
    for mutate in (
        lambda v: v.update(selection_context=copy.deepcopy(contexts[1])),
        lambda v: v.update(teacher_input_frame=99),
        lambda v: v['preparation_input']['wheels'][1].__setitem__(0, 42.),
        lambda v: v['selection_context']['cfg'].pop('com_margin_m'),
    ):
        changed = copy.deepcopy(sample); mutate(changed)
        assert verify(changed)
    # Matching a rewritten digest is not a substitute for real input binding.
    changed = copy.deepcopy(sample); context = changed['selection_context']
    context['measured_wheels_w'][1][0] += .003
    context['measured']['wheels'] = copy.deepcopy(context['measured_wheels_w'])
    context['choice']['input_digest'] = module.selection_input_digest(context)
    assert verify(changed)
    contexts[0]['com_w'][0] += 1.
    assert verify(sample) == [], 'action receipt must own the producer snapshot'


def test_erasing_candidate_diagnostics_cannot_hide_prepared_balance_search():
    teacher, s, contexts, sample = selection_sample()
    sample['selection_context'] = None
    sample['teacher_diagnostic'].update(candidate_index=-1, candidate_count=-1,
        candidate_com_margin_m=None, candidate_measured_triangle_margin_m=None)
    assert probe().verify_selection_sample(sample, teacher.cfg,
        replay_backend='cpu', require_backend_evidence=True)


def test_drifted_measured_wheels_reach_single_selector_without_moving_ik_anchors(monkeypatch):
    import ame_baseline.m1_reference_teacher as t
    teacher, s, _ = prepared_teacher(diagnostic=True)
    anchors = teacher._rows[0]['wheel_anchor'].clone()
    wheels = s.wheel_pos_w.clone(); wheels[:, 1, 0] += .008
    s = advance(s, wheel_pos_w=wheels)
    original = t.choose_support_pose; calls = []
    def selected(*args, **kwargs):
        assert torch.equal(args[4], anchors)
        assert torch.equal(kwargs['measured_wheels_w'], wheels)
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(t, 'choose_support_pose', selected)
    observed(teacher, s)
    assert calls == [1]
    assert torch.equal(teacher._rows[0]['wheel_anchor'], anchors)


def test_incomplete_configuration_is_not_replayed_using_defaults():
    teacher, s, contexts, sample = selection_sample(); module = probe()
    context = copy.deepcopy(contexts[0]); context['cfg'].pop('com_margin_m')
    context['choice']['input_digest'] = module.selection_input_digest(context)
    assert module.verify_preparation_selection(context, context['choice'],
        replay_backend='cpu', require_backend_evidence=True)


def test_explicit_selection_backend_restores_ambient_device(monkeypatch):
    teacher, s, contexts, sample = selection_sample(); module = probe()
    monkeypatch.setattr(torch, 'set_default_device', lambda *_: pytest.fail('global device change'))
    with torch.device('meta'):
        assert module.verify_preparation_selection(contexts[0], contexts[0]['choice'],
            replay_backend='cpu', require_backend_evidence=True) == []
        assert torch.empty(()).device.type == 'meta'


def test_selection_goal_and_prior_are_bound_to_the_real_transaction():
    teacher, s, contexts, sample = selection_sample(); module = probe()
    for mutate in (
        lambda v: v['teacher_diagnostic'].update(preparation_goal_root_x=42.),
        lambda v: v['feedback_context']['accepted_before']['root'].__setitem__(0, 42.),
        lambda v: v['feedback_context']['branch_q'].__setitem__(0, 42.),
    ):
        changed = copy.deepcopy(sample); mutate(changed)
        assert module.verify_selection_sample(changed, teacher.cfg,
            replay_backend='cpu', require_backend_evidence=True)
