"""Authenticate measured actuation and the bounded transaction actually applied."""
from types import SimpleNamespace

import pytest
import torch

from test_m1_teacher_probe_contract import probe,real_video_files


def test_preparation_requires_five_additional_ready_frames():
    hold = probe().PreparationHoldCounter()
    for frame in range(5):
        assert not hold.update(0,input_ready=True,output_ready=True,frame=frame,episode_id=4)
    assert hold.update(0,input_ready=True,output_ready=True,frame=5,episode_id=4)
    assert hold.update(0,input_ready=False,output_ready=False,frame=5,episode_id=4)  # duplicate is idempotent
    assert not hold.update(0,input_ready=True,output_ready=False,frame=6,episode_id=4)
    for frame in range(7,12):
        assert not hold.update(0,input_ready=True,output_ready=True,frame=frame,episode_id=4)
    assert hold.update(0,input_ready=True,output_ready=True,frame=12,episode_id=4)
    assert not hold.update(0,input_ready=True,output_ready=True,frame=14,episode_id=4)
    assert not hold.update(0,input_ready=True,output_ready=True,frame=0,episode_id=5)
    assert not hold.update(1,input_ready=True,output_ready=True,frame=20,episode_id=1)
    hold.reset(0)
    assert not hold.update(1,input_ready=True,output_ready=True,frame=21,episode_id=1)


def test_compensation_evidence_matches_actual_apply():
    from test_m1_teacher_reference_commit import prepared_teacher
    from test_m1_teacher_feedback_transaction import shifted
    from ame_baseline.m1_ame_contract import m1_action_targets
    teacher,s,_=prepared_teacher(diagnostic=True)
    probe().replay_feedback_transaction.cache_clear()
    probe().observe_feedback_transactions(teacher)
    s=shifted(s,[.03,0.,-.015])
    output=teacher.diagnostic_step(s,active_wheel=0,lift=False)
    targets=m1_action_targets(output.action,s.default_joint_pos)[0].tolist()
    sample=dict(teacher_diagnostic=probe().diagnostic_json(output.diagnostic[0].tolist()),
        feedback_context=teacher._probe_feedback_context[0],action_target_dtype='float32',
        teacher_action=output.action[0].tolist(),applied_targets=targets,phase=int(output.phase[0]))
    assert probe().verify_feedback_transaction(sample,teacher.cfg)==[]
    import copy
    for mutation in (
        lambda r:r['teacher_diagnostic'].update(command_attempted_root_z=.9),
        lambda r:r['teacher_diagnostic'].update(nominal_ik_residual_m_0=.123),
        lambda r:r['teacher_diagnostic'].update(ik_residual_m_0=.123),
        lambda r:r['teacher_diagnostic'].update(feedback_integral_committed_z=.009),
        lambda r:r['teacher_diagnostic'].update(feedback_output_committed_x=.04),
        lambda r:r['teacher_diagnostic'].update(accepted_root_z=.9),
        lambda r:r['teacher_action'].__setitem__(0,.01),
        lambda r:r['applied_targets'].__setitem__(0,.01),
        lambda r:r.pop('feedback_context'),
    ):
        changed=copy.deepcopy(sample); mutation(changed)
        assert probe().verify_feedback_transaction(changed,teacher.cfg), 'changed transactional claim must fail'


def test_rejected_attempt_is_not_actual_hold(monkeypatch):
    from dataclasses import replace
    from test_m1_teacher_reference_commit import prepared_teacher
    from test_m1_teacher_feedback_transaction import shifted
    from ame_baseline.m1_ame_contract import m1_action_targets
    import ame_baseline.m1_teacher_pose as pose
    teacher,s,_=prepared_teacher(diagnostic=True)
    probe().replay_feedback_transaction.cache_clear()
    probe().observe_feedback_transactions(teacher)
    real=pose.solve_constrained_ik
    monkeypatch.setattr(pose,'solve_constrained_ik',lambda *a:replace(real(*a),valid=torch.tensor([False])))
    # RESTORE avoids the independent candidate-search refusal before transaction.
    teacher._rows[0]['phase']=4
    out=teacher.diagnostic_step(shifted(s,[.03,0.,-.015]),active_wheel=0,lift=False)
    targets=m1_action_targets(out.action,s.default_joint_pos)[0].tolist()
    sample=dict(teacher_diagnostic=probe().diagnostic_json(out.diagnostic[0].tolist()),
        feedback_context=teacher._probe_feedback_context[0],action_target_dtype='float32',
        teacher_action=out.action[0].tolist(),applied_targets=targets,phase=int(out.phase[0]))
    assert out.executable.item() and sample['teacher_diagnostic']['reference_valid']==0
    assert probe().verify_feedback_transaction(sample,teacher.cfg)==[]
    assert any(sample['teacher_diagnostic'][f'wheel_final_surface_speed_{i}']!=0 for i in range(4))


def test_second_pass_refusal_never_applies_first_pass(monkeypatch):
    from dataclasses import replace
    from test_m1_teacher_reference_commit import prepared_teacher
    from test_m1_teacher_feedback_transaction import shifted
    from ame_baseline.m1_ame_contract import m1_action_targets
    import ame_baseline.m1_teacher_pose as pose
    teacher,s,_=prepared_teacher(diagnostic=True)
    probe().replay_feedback_transaction.cache_clear()
    teacher._rows[0]['phase']=4
    probe().observe_feedback_transactions(teacher)
    real=pose.solve_constrained_ik; calls=[]
    def alternating(*args):
        result=real(*args); calls.append(1)
        return result if len(calls)<=2 else replace(result,valid=torch.tensor([False]))
    monkeypatch.setattr(pose,'solve_constrained_ik',alternating)
    out=teacher.diagnostic_step(shifted(s,[.03,0.,-.015]),active_wheel=0,lift=False)
    targets=m1_action_targets(out.action,s.default_joint_pos)[0].tolist()
    sample=dict(teacher_diagnostic=probe().diagnostic_json(out.diagnostic[0].tolist()),
        feedback_context=teacher._probe_feedback_context[0],action_target_dtype='float32',
        teacher_action=out.action[0].tolist(),applied_targets=targets,phase=int(out.phase[0]))
    d=sample['teacher_diagnostic']
    assert d['feedback_passes']==2 and d['feedback_first_transaction_valid']==1 and d['reference_valid']==0
    assert len(calls)==18
    calls.clear()
    assert probe().verify_feedback_transaction(sample,teacher.cfg)==[]
    assert len(calls)==18
    d['feedback_integral_committed_z']=d['feedback_integral_candidate_z']
    calls.clear()
    assert probe().verify_feedback_transaction(sample,teacher.cfg)


def test_missing_effort_or_legacy_schema_rejects_acceptance():
    from test_m1_teacher_probe_contract import episode,verify_episode
    for mutate in (lambda r:r.update(schema_version=5),lambda r:r['samples'][2].pop('actuation_evidence',None)):
        record=episode(); mutate(record)
        result=verify_episode(record)
        assert result['errors'] and not result['success'] and not result['student_demonstration_usable']


def test_valid_transaction_cannot_omit_context_or_masquerade_as_pass_zero():
    from test_m1_teacher_probe_contract import episode,verify_episode
    for erase_flags in (False,True):
        record=episode(); sample=record['samples'][2]; sample['feedback_context']=None
        if erase_flags:
            sample['teacher_diagnostic'].update(feedback_passes=0,feedback_first_transaction_valid=0)
            for i in range(4): sample['teacher_diagnostic'][f'nominal_ik_residual_m_{i}']=None
        checked=verify_episode(record)
        assert 'bounded feedback transaction evidence mismatch' in checked['errors']
        assert not checked['success'] and not checked['student_demonstration_usable']


def test_pure_replay_cache_does_not_cache_acceptance_or_cross_configuration():
    from dataclasses import replace
    from test_m1_teacher_probe_contract import episode
    from ame_baseline.m1_reference_teacher import TeacherConfig
    sample=episode()['samples'][2]; module=probe(); module.replay_feedback_transaction.cache_clear()
    cfg=TeacherConfig()
    assert module.verify_feedback_transaction(sample,cfg)==[]
    first=module.replay_feedback_transaction.cache_info()
    assert module.verify_feedback_transaction(sample,replace(cfg,flat_speed_m_s=.31))==[]
    assert module.replay_feedback_transaction.cache_info().misses==first.misses+1
    sample['applied_targets'][0]+=.00001
    assert module.verify_feedback_transaction(sample,cfg), 'fresh receipt validation must override cached expected math'


def test_independent_cpu_roundoff_allows_small_math_change_but_exact_receipt_is_required():
    import copy
    from test_m1_teacher_probe_contract import episode
    from ame_baseline.m1_reference_teacher import TeacherConfig,LEG_COLUMNS
    sample=episode()['samples'][2]; cfg=TeacherConfig()
    changed=copy.deepcopy(sample); changed['teacher_action'][LEG_COLUMNS[0]]+=5e-7
    targets=probe().decoded_request_targets(tuple(changed['teacher_action']),
        tuple(changed['action_default_joint_pos']),changed['action_target_dtype'])
    changed['applied_targets']=list(targets)
    for j,i in enumerate(LEG_COLUMNS): changed['teacher_diagnostic'][f'accepted_q_{j}']=targets[i]
    assert probe().verify_feedback_transaction(changed,cfg)==[]
    changed['applied_targets'][LEG_COLUMNS[0]]+=1e-10
    assert probe().verify_feedback_transaction(changed,cfg), 'real request-to-receipt agreement has no replay tolerance'
    changed=copy.deepcopy(sample); changed['teacher_action'][LEG_COLUMNS[0]]+=.001
    changed['applied_targets']=list(probe().decoded_request_targets(tuple(changed['teacher_action']),
        tuple(changed['action_default_joint_pos']),changed['action_target_dtype']))
    for j,i in enumerate(LEG_COLUMNS): changed['teacher_diagnostic'][f'accepted_q_{j}']=changed['applied_targets'][i]
    assert probe().verify_feedback_transaction(changed,cfg)


def test_local_preparation_holds_five_more_physical_frames(tmp_path,monkeypatch):
    import json
    from test_m1_teacher_probe_contract import diagnostic_runner
    run=diagnostic_runner(tmp_path,monkeypatch,'prepared')
    run.teacher(acceptance=False,diagnostic_steps=8,scope='flat-preparation')
    record=json.loads((tmp_path/'stage0_seed101_env0_episode0.json').read_text())
    assert len(record['samples'])==6, 'first ready needs five additional measured frames'


def test_local_and_aborted_traces_never_become_bc():
    from test_m1_teacher_probe_contract import episode,verify_episode
    for end,scope in (('scope_observed','flat-preparation'),('teacher_nonexecutable','course'),('diagnostic_interrupted','course')):
        record=episode(); record.update(end=end,teacher_scope=scope)
        result=verify_episode(record)
        assert not result['success'] and not result['student_demonstration_usable']
