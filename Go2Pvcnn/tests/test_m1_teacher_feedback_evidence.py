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
    for frame in range(20,25):
        assert not hold.update(1,input_ready=True,output_ready=True,frame=frame,episode_id=1)
    hold.reset(0)
    assert hold.update(1,input_ready=True,output_ready=True,frame=25,episode_id=1), 'resetting peer must retain five ready frames'


@pytest.mark.parametrize('reset_groups',[((0,),),((0,),(1,)),((0,1),)])
def test_real_teacher_quota_resets_preserve_cached_peer_transaction(reset_groups):
    """Execute the native nested decide function, with real Teacher and receipts."""
    import ast
    import copy
    import inspect
    import textwrap
    from dataclasses import replace
    from types import SimpleNamespace as NS
    from test_m1_reference_teacher import state
    from ame_baseline.m1_ame_contract import m1_action_targets
    from ame_baseline.m1_reference_teacher import ReferenceTeacher,LEG_COLUMNS
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    module=probe(); teacher=ReferenceTeacher(); module.observe_feedback_transactions(teacher)
    tree=ast.parse(textwrap.dedent(inspect.getsource(module.NativeProbe.teacher)))
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='decide')
    scope=dict(vars(module),teacher=teacher,wheel=None,scope='course')
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<native quota decide>','exec'),scope)
    decide=scope['decide']; s=state(batch=3,targets=False)
    defaults=s.default_joint_pos.clone(); clock=NS(current_time=0.)
    asset=NS(joint_names=M1_ASSET_JOINT_NAMES,data=NS(joint_pos_target=defaults.clone(),joint_vel_target=torch.zeros(3,16)))
    term=NS(_joint_names=M1_ASSET_JOINT_NAMES,_asset=asset,
        raw_actions=torch.zeros(3,16),processed_actions=torch.zeros(3,16))
    def process(action):
        term.raw_actions.copy_(action); term.processed_actions.copy_(m1_action_targets(action,defaults))
    def apply():
        asset.data.joint_pos_target.copy_(term.processed_actions)
        asset.data.joint_vel_target.copy_(term.processed_actions)
    term.process_actions=process; term.apply_actions=apply
    receipts=module.ActionEvidence(term,sim_time=lambda:clock.current_time)
    def execute(st,out):
        receipts.begin(st,out,teacher,clock.current_time); term.process_actions(out.action)
        for _ in range(4):
            term.apply_actions(); receipts.observe_write(); receipts.observe_physics(); clock.current_time+=.005
        return [dict(receipts.row(row,clock.current_time),phase=int(out.phase[row]),teacher_valid=bool(out.valid[row])) for row in range(3)]
    first=decide(s); old=execute(s,first)
    s=replace(s,control_step=s.control_step+1,last_applied_leg_target=receipts.read_targets()[:,LEG_COLUMNS])
    peer_context=None
    for group in reset_groups:
        rows=list(group)
        episodes=s.episode_id.clone(); episodes[rows]+=1
        frames=s.control_step.clone(); frames[rows]=-1
        mask=torch.zeros(3,dtype=torch.bool); mask[rows]=True
        quota=replace(s,episode_id=episodes,control_step=frames,reset_mask=mask)
        decide(quota)
        if teacher._probe_feedback_context.get(2) is not None:
            peer_context=copy.deepcopy(teacher._probe_feedback_context[2])
        # A real reset decision has no transaction, even after this row owned one.
        assert all(teacher._probe_feedback_context.get(row) is None for row in rows)
        frames[rows]=0
        s=replace(quota,control_step=frames,reset_mask=torch.zeros(3,dtype=torch.bool))
    assert peer_context is not None
    out=decide(s)  # row2 returns its cached next-frame output; no observer call
    samples=execute(s,out)
    assert samples[2]['feedback_context'] is not None, 'cached live peer must retain its real transaction context'
    assert samples[2]['feedback_context']==peer_context
    assert all(module.verify_feedback_transaction(sample,teacher.cfg)==[] for sample in samples)
    assert old[0]['teacher_input_episode_id']==0 and samples[0]['teacher_input_episode_id']==1
    # Same-frame duplicate must retain the same owned transaction on every row.
    duplicate=decide(s)
    receipts.begin(s,duplicate,teacher,clock.current_time)
    assert receipts.pending[2]['feedback_context']==peer_context
    saved=copy.deepcopy(receipts.pending[2]['feedback_context'])
    # Fresh frame with pretransaction collision cannot inherit old context.
    collision=torch.zeros(3,dtype=torch.bool); collision[2]=True
    failed=replace(s,control_step=s.control_step+1,collision=collision)
    decision=decide(failed)
    assert not decision.valid[2] and teacher._probe_feedback_context.get(2) is None
    assert receipts.pending[2]['feedback_context']==saved
    failed_samples=execute(failed,decision)
    assert failed_samples[2]['feedback_context'] is None
    assert module.verify_feedback_transaction(failed_samples[2],teacher.cfg)==[]
    # A same-frame explicit reset also supersedes that row's prior transaction.
    same_frame_reset=replace(failed,reset_mask=torch.tensor([True,False,False]))
    reset_out=decide(same_frame_reset)
    assert not reset_out.valid[0] and teacher._probe_feedback_context.get(0) is None
    receipts.begin(same_frame_reset,reset_out,teacher,clock.current_time)
    assert receipts.pending[0]['feedback_context'] is None


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
