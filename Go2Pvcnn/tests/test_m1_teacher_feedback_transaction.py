"""Bounded feedback uses physical readiness and atomic decoded execution."""
from dataclasses import replace

import pytest
import torch

from test_m1_reference_teacher import api, advance, state
from test_m1_teacher_reference_commit import prepared_teacher, feedback, near_state
from ame_baseline.m1_ame_contract import m1_action_targets


def shifted(s, xyz):
    delta = s.root_pos_w.new_tensor(xyz)
    return replace(s, root_pos_w=s.root_pos_w+delta, com_pos_w=s.com_pos_w+delta,
                   wheel_pos_w=s.wheel_pos_w+delta)


def field(out, name):
    return out.diagnostic[0, api().TEACHER_DIAGNOSTIC_FIELDS.index(name)]


def run(teacher, s):
    return teacher.diagnostic_step(s, active_wheel=0, lift=False)


def test_tracking_freezes_physical_but_corrects_command():
    raws = []
    for distance in (.03, .09):
        teacher, s, _ = prepared_teacher(diagnostic=True)
        row = teacher._rows[0]; ref = row['accepted']; ages = tuple(row[k] for k in ('age','body_age','lift_age'))
        out = run(teacher, shifted(s, [distance, 0., -.015]))
        decoded = m1_action_targets(out.action, s.default_joint_pos)
        assert (decoded[:, api().WHEEL_COLUMNS] < 0).all(), 'tracking must correct longitudinal drift'
        assert torch.equal(row['accepted'].body.pos_w, ref.body.pos_w)
        assert torch.equal(row['accepted'].wheels_w, ref.wheels_w)
        assert tuple(row[k] for k in ('age','body_age','lift_age')) == ages
        assert row['accepted_command'].body.pos_w[0,2] > ref.body.pos_w[0,2]
        assert out.executable.item() and field(out, 'preparation_ready') == 0
        assert ((decoded[:,api().LEG_COLUMNS]-s.last_applied_leg_target).abs() <= 2.5*s.dt[:,None]).all()
        raws.append(field(out, 'feedback_raw_output_x'))
    assert raws[1] < raws[0] < 0


def test_virtual_ik_never_certifies_readiness():
    teacher, s, _ = prepared_teacher(diagnostic=True)
    out = run(teacher, shifted(s, [0., 0., -.03]))
    assert field(out, 'preparation_ready') == 0
    assert out.phase.item() == api().Phase.BALANCE
    assert field(out, 'ik_residual_m_0') <= .002
    assert field(out, 'nominal_ik_residual_m_0') <= .002


@pytest.mark.parametrize('failure', ['ik','decoder','continuity','wheel'])
def test_rejected_feedback_transaction_is_atomic(monkeypatch, failure):
    import ame_baseline.m1_reference_teacher as t
    import ame_baseline.m1_teacher_pose as p
    teacher, s, _ = prepared_teacher(diagnostic=True)
    row = teacher._rows[0]
    before = (row['accepted'], row.get('accepted_command'), row.get('feedback'), row['age'], row['body_age'])
    if failure == 'ik':
        real = p.solve_constrained_ik
        monkeypatch.setattr(p, 'solve_constrained_ik', lambda *a: replace(real(*a), valid=torch.tensor([False])))
        # Avoid the support candidate search; this is the transaction under test.
        row['phase'] = t.Phase.RESTORE
    elif failure == 'decoder':
        real = t.encode_targets
        monkeypatch.setattr(t, 'encode_targets', lambda *a: (real(*a)[0], torch.tensor([False])))
    elif failure == 'continuity':
        s = replace(s, last_applied_leg_target=s.last_applied_leg_target+.5)
    else:
        teacher.cfg = replace(teacher.cfg, yaw_gain_s_inv=10000.)
        row['phase'] = t.Phase.PASS
        angle = s.root_quat_w.new_tensor(.05)
        s = replace(s, root_quat_w=torch.stack([angle.cos(),angle*0,angle*0,angle.sin()])[None])
    out = run(teacher, shifted(s, [.03,0.,-.02]))
    assert field(out, 'reference_valid') == 0
    assert row['accepted'] is before[0] and row.get('accepted_command') is before[1]
    assert row.get('feedback') is before[2] and (row['age'],row['body_age']) == before[3:]
    if failure in ('decoder','continuity'):
        assert not out.executable.item() and torch.isnan(out.action).all()


def test_com_failure_does_not_disable_safe_feedback():
    teacher, s, _ = prepared_teacher(diagnostic=True)
    s = shifted(s, [.03,0.,0.])
    com = s.com_pos_w.clone(); com[:,:2] = (s.wheel_pos_w[:,1,:2]+s.wheel_pos_w[:,2,:2])/2
    out = run(teacher, replace(s, com_pos_w=com))
    assert field(out, 'measured_com_margin_m') < .01
    assert field(out, 'feedback_output_committed_x') < 0
    assert field(out, 'preparation_ready') == 0 and out.phase.item() == api().Phase.BALANCE


def test_feedback_lifecycle():
    teacher, s, _ = prepared_teacher(diagnostic=True)
    s = shifted(s, [.03,0.,-.02]); out = run(teacher,s)
    row = teacher._rows[0]; saved = row['feedback']; snapshot = out.diagnostic.clone()
    duplicate = run(teacher,s)
    assert torch.equal(duplicate.action,out.action)
    assert row['feedback'] is saved and torch.allclose(duplicate.diagnostic,snapshot,equal_nan=True)
    next_s = replace(s, control_step=s.control_step+9, last_applied_leg_target=row['last_q'].clone())
    run(teacher,next_s)
    assert (row['feedback'].output-saved.output).abs().amax() <= .0020001
    terminal = out.diagnostic.clone()
    reset = run(teacher, advance(next_s, episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask)))
    assert torch.allclose(out.diagnostic,terminal,equal_nan=True)
    assert not teacher._rows[0]['feedback'].integral.any() and not teacher._rows[0]['feedback'].output.any()
    assert field(reset,'feedback_output_committed_x') == 0


def test_approach_decay_retains_reference_and_blocks_capture():
    from ame_baseline.m1_teacher_feedback import FeedbackState
    teacher, s, _ = prepared_teacher()
    row=teacher._rows[0]; old=row['accepted']
    row.update(phase=api().Phase.APPROACH,prepared=False,target=-1,wheel=-1)
    row['feedback']=FeedbackState(s.root_pos_w.new_tensor([[.01,.005,.005]]),s.root_pos_w.new_tensor([[.02,.005,.005]]))
    from ame_baseline.m1_teacher_pose import feedback_command,world_to_goal_body
    from ame_baseline.m1_teacher_ik import solve_constrained_ik
    row['accepted_command']=feedback_command(old,row['feedback'].output,row['yaw'])
    row['last_q']=solve_constrained_ik(s.leg_pos,world_to_goal_body(row['accepted_command']),row['branch_q'],teacher.ik_cfg).q
    s=replace(s,last_applied_leg_target=row['last_q'].clone(),leg_pos=row['last_q'].clone())
    out=teacher.step(s)
    assert not row['prepared'] and row['phase'] == api().Phase.APPROACH
    assert row['accepted_command'] is not None and row['accepted'] is not None
    assert not row['feedback'].integral.any()
    assert torch.allclose(row['feedback'].output,s.root_pos_w.new_tensor([[.018,.0046,.0046]]),atol=1e-7)
    assert field(out,'feedback_active') == 0 and out.executable.item()


def test_feedback_survives_phase_and_single_row_reset():
    from ame_baseline.m1_teacher_feedback import FeedbackState
    t=api(); teacher=t.ReferenceTeacher(); s=near_state(2)
    for _ in range(3):
        out=teacher.step(s); s=feedback(s,teacher,out)
    teacher._rows[1]['feedback']=FeedbackState(s.root_pos_w.new_tensor([[.001,0.,0.]]),s.root_pos_w.new_tensor([[.001,0.,0.]]))
    teacher._rows[1]['phase']=t.Phase.LIFT
    s=replace(s,reset_mask=torch.tensor([True,False]),episode_id=torch.tensor([1,0]))
    out=teacher.step(s)
    assert not teacher._rows[0]['feedback'].output.any()
    assert teacher._rows[1]['feedback'].integral[0,0] != 0
    assert out.valid[1] and out.executable[1]


def test_wheel_correction_respects_decoder_headroom():
    from ame_baseline.m1_teacher_feedback import FeedbackState
    from ame_baseline.m1_ame_contract import M1_WHEEL_RADIUS_M, M1_WHEEL_SPEED_LIMIT_RAD_S
    teacher,s,_=prepared_teacher(); row=teacher._rows[0]; row.update(phase=api().Phase.PASS,age=20)
    limit=M1_WHEEL_RADIUS_M*M1_WHEEL_SPEED_LIMIT_RAD_S
    teacher.cfg=replace(teacher.cfg,pass_speed_m_s=limit-.001)
    delta=s.root_pos_w.new_tensor([-.03,0.,0.])
    drift=replace(s,root_pos_w=s.root_pos_w+delta,com_pos_w=s.com_pos_w+delta)
    out=teacher.step(drift)
    speed=m1_action_targets(out.action,s.default_joint_pos)[:,api().WHEEL_COLUMNS]*M1_WHEEL_RADIUS_M
    assert out.valid.item() and (speed <= limit+1e-7).all()
    assert field(out,'wheel_headroom_limited') == 1
    assert torch.allclose(speed, speed.new_full((1,4),limit),atol=1e-6)
    row['feedback']=FeedbackState(row['feedback'].integral,speed.new_tensor([[.02,0.,0.]]))
    prior=row['accepted']; s=advance(s,last_applied_leg_target=row['last_q'].clone())
    refused=teacher.step(replace(s,root_pos_w=s.root_pos_w+delta,com_pos_w=s.com_pos_w+delta))
    assert not refused.valid.item() and row['accepted'] is prior


def test_bounded_second_pass(monkeypatch):
    import ame_baseline.m1_teacher_pose as p
    teacher,s,_=prepared_teacher(diagnostic=True); row=teacher._rows[0]; row['phase']=api().Phase.RESTORE
    real=p.solve_constrained_ik; calls=[]
    def counted(*a):
        result=real(*a); calls.append(result)
        # First pass succeeds; fixed-integral second pass always refuses.
        return result if len(calls) <= 2 else replace(result,valid=torch.zeros_like(result.valid))
    monkeypatch.setattr(p,'solve_constrained_ik',counted)
    prior=row['accepted']; out=run(teacher,shifted(s,[.03,0.,0.]))
    assert field(out,'feedback_passes') == 2
    assert field(out,'feedback_first_transaction_valid') == 1
    assert field(out,'feedback_first_backtrack_index') == 0
    assert len(calls) == 18 and len(calls) <= 2*8*2
    assert field(out,'reference_valid') == 0 and row['accepted'] is prior


def test_nominal_invalid_rejects_virtual_valid(monkeypatch):
    import ame_baseline.m1_teacher_pose as p
    teacher,s,_=prepared_teacher(diagnostic=True); teacher._rows[0]['phase']=api().Phase.RESTORE
    real=p.solve_constrained_ik; calls=[]
    def alternating(*a):
        result=real(*a); calls.append(result)
        return replace(result,valid=torch.zeros_like(result.valid)) if len(calls)%2 else result
    monkeypatch.setattr(p,'solve_constrained_ik',alternating)
    out=run(teacher,shifted(s,[.03,0.,0.]))
    assert field(out,'reference_valid') == 0
    assert len(calls) <= 32


def test_nominal_solution_is_not_execution_slew():
    import ame_baseline.m1_teacher_pose as p
    from ame_baseline.m1_teacher_ik import solve_constrained_ik,IKConfig
    teacher,s,_=prepared_teacher(diagnostic=True); ref=teacher._rows[0]['accepted']; q=s.leg_pos
    output=q.new_tensor([[0.,0.,.01]])
    cmd=p.PoseReference(p.BodyPose(ref.body.pos_w+output,ref.body.quat_w),ref.wheels_w)
    actual=solve_constrained_ik(q,p.world_to_goal_body(cmd),q,IKConfig()).q
    assert (actual-q).abs().amax() > .0025
    solved=p.backtrack_feedback_reference(ref,ref,output,output,q.new_zeros(1),q,q,actual,.001,IKConfig(),execution_valid=lambda ik,u:ik.valid)
    assert solved.valid.item() and solved.backtrack_index.item() == 0
    assert ((solved.command_ik.q-actual).abs() <= .0025).all()


def test_restore_finish_clears_integral_and_preserves_exit_output():
    from test_m1_reference_teacher import restoring_teacher
    from ame_baseline.m1_teacher_feedback import FeedbackState
    teacher,s=restoring_teacher(); row=teacher._rows[0]
    row['stable']=4; s.recovered[:,0,0]=True
    row['feedback']=FeedbackState(s.root_pos_w.new_tensor([[.001,0.,0.]]),s.root_pos_w.new_tensor([[.001,0.,0.]]))
    out=teacher.step(s)
    assert out.valid.item() and row['phase'] == api().Phase.APPROACH
    assert not row['feedback'].integral.any()
    assert row['feedback'].output[0,0] == .001 and row['accepted_command'] is not None


def test_unlimited_integral_updates_once_with_one_control_dt():
    teacher,s,_=prepared_teacher(diagnostic=True)
    out=run(teacher,shifted(s,[.001,0.,0.]))
    assert field(out,'feedback_passes') == 1
    assert field(out,'feedback_integral_candidate_x') == pytest.approx(-.001*.2*.02,abs=1e-8)
    assert field(out,'feedback_integral_committed_x') == field(out,'feedback_integral_candidate_x')
    assert field(out,'feedback_slew_limited_x') == 0


def test_heading_channels_preserve_full_quaternion_and_world_wheels():
    import ame_baseline.m1_teacher_pose as p
    from ame_baseline.m1_teacher_ik import IKConfig,body_feet
    from extension.parallelism.kinematics import rpy_to_rotation_matrix
    # Unit quaternion with nonzero roll, pitch and yaw: virtual translation
    # must use captured yaw only, while IK keeps the complete body attitude.
    quat=torch.tensor([[.971018,.069063,-.019214,.227841]])
    quat=quat/quat.norm(dim=-1,keepdim=True)
    rotation=rpy_to_rotation_matrix(api().quaternion_rpy(quat))
    s=state(targets=False); body=p.BodyPose(s.root_pos_w,quat)
    ref=p.PoseReference(body,body.pos_w[:,None]+torch.einsum('bij,bkj->bki',rotation,body_feet(s.leg_pos)))
    yaw=s.dt.new_tensor([.7]); u=s.root_pos_w.new_tensor([[.002,.0004,-.0004]])
    solved=p.backtrack_feedback_reference(ref,ref,torch.zeros_like(u),u,yaw,s.leg_pos,s.leg_pos,
        s.last_applied_leg_target,.02,IKConfig(),execution_valid=lambda ik,o:ik.valid)
    assert solved.valid.item()
    delta=torch.stack((-yaw.sin()*u[:,1],yaw.cos()*u[:,1],u[:,2]),-1)
    assert torch.allclose(solved.command.body.pos_w-ref.body.pos_w,delta,atol=1e-7)
    assert torch.allclose(solved.command.body.quat_w,quat,atol=1e-7)
    assert torch.equal(solved.command.wheels_w,ref.wheels_w)


def test_first_proposal_limit_evidence_is_not_second_pass_evidence():
    teacher,s,_=prepared_teacher(diagnostic=True)
    out=run(teacher,shifted(s,[.09,0.,0.]))
    assert field(out,'feedback_passes') == 2
    assert field(out,'feedback_integral_candidate_x') < 0
    assert field(out,'feedback_integral_selected_x') == 0
    assert field(out,'feedback_integral_committed_x') == 0
    assert field(out,'feedback_raw_output_x') < -.09
    assert field(out,'feedback_amplitude_limited_x') == 1
    assert field(out,'feedback_slew_limited_x') == 1
    assert field(out,'feedback_limited_x') == 1
    assert field(out,'feedback_output_committed_x') == pytest.approx(-.002)
