"""Transactional references: real tensor IK, explicit measured/applied evidence."""
from dataclasses import replace

import pytest
import torch

from test_m1_reference_teacher import api, state, advance


def near_state(batch=1, wheel=0):
    s = state(batch)
    s.required_wheels.zero_()
    s.required_wheels[:, 0, wheel] = True
    s.centers_top[:, 0, 0] = s.wheel_pos_w[:, wheel, 0]+.05+.11915+.06
    # A synthetic full-body COM known inside the support triangle. This is
    # explicit evidence supplied by this fixture, never a production fallback.
    support = [j for j in range(4) if j != wheel]
    s.com_pos_w[:, :2] = s.wheel_pos_w[:, support, :2].mean(1)
    return s


def test_same_decision_readiness_is_not_capture_or_predicted_margin():
    from types import SimpleNamespace
    from test_m1_teacher_probe_contract import probe
    t=api(); s=near_state(); teacher=t.ReferenceTeacher()
    s.com_pos_w[:,:2]=(s.wheel_pos_w[:,1,:2]+s.wheel_pos_w[:,2,:2])/2
    out=teacher.diagnostic_step(s,active_wheel=0,lift=False)
    assert teacher._rows[0]['prepared'] is True
    names=t.TEACHER_DIAGNOSTIC_FIELDS
    assert out.diagnostic[0,names.index('reference_valid')]==1
    assert out.diagnostic[0,names.index('measured_com_margin_m')]<.01
    assert out.diagnostic[0,names.index('candidate_com_margin_m')]>=.01
    term=SimpleNamespace(_joint_names=t.M1_ASSET_JOINT_NAMES,process_actions=lambda action:None)
    evidence=probe().ActionEvidence(term); evidence.begin(s,out,teacher,0.)
    assert not evidence.pending[0].get('local_prepare_complete',False)
    assert out.diagnostic[0,names.index('preparation_ready')]==0


def test_measured_ready_is_same_decision_and_cleared_after_refusal_or_reset():
    t=api(); s=near_state(); teacher=t.ReferenceTeacher()
    for _ in range(16):
        out=teacher.diagnostic_step(s,active_wheel=0,lift=False)
        if out.diagnostic[0,t.TEACHER_DIAGNOSTIC_FIELDS.index('preparation_ready')]==1: break
        s=feedback(s,teacher,replace(out,valid=torch.ones_like(out.valid)))
    else: raise AssertionError('ideal measured fixture never became ready')
    assert not out.valid.item() and not out.failure_locked.item()
    q=s.leg_pos.clone(); q[:,0]=3.
    invalid=teacher.diagnostic_step(advance(s,leg_pos=q),active_wheel=0,lift=False)
    assert invalid.diagnostic[0,t.TEACHER_DIAGNOSTIC_FIELDS.index('reference_valid')]==0
    assert invalid.diagnostic[0,t.TEACHER_DIAGNOSTIC_FIELDS.index('preparation_ready')]==0
    reset=advance(s,episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask))
    after=teacher.diagnostic_step(reset,active_wheel=0,lift=False)
    assert after.diagnostic[0,t.TEACHER_DIAGNOSTIC_FIELDS.index('preparation_ready')]==0


def feedback(s, teacher, out):
    """Ideal kinematic tracking, not physics or a crossing certificate."""
    t = api()
    from ame_baseline.m1_ame_contract import m1_action_targets
    q = m1_action_targets(out.action, s.default_joint_pos)[:, t.LEG_COLUMNS]
    root, quat, wheels, com = (s.root_pos_w.clone(), s.root_quat_w.clone(),
                               s.wheel_pos_w.clone(), s.com_pos_w.clone())
    for i, row in enumerate(teacher._rows):
        if row.get('accepted') is not None and out.valid[i]:
            ref = row['accepted']
            com[i] += ref.body.pos_w[0]-root[i]
            root[i], quat[i], wheels[i] = ref.body.pos_w[0], ref.body.quat_w[0], ref.wheels_w[0]
    return advance(s, root_pos_w=root, root_quat_w=quat, wheel_pos_w=wheels,
                   com_pos_w=com, leg_pos=q.clone(), last_applied_leg_target=q.clone())


def prepared_teacher(wheel=0, diagnostic=False):
    t = api()
    teacher, s = t.ReferenceTeacher(), near_state(wheel=wheel)
    for _ in range(4):
        out = (teacher.diagnostic_step(s, active_wheel=wheel, lift=False)
               if diagnostic else teacher.step(s))
        if teacher._rows[0].get('prepared', False):
            return teacher, feedback(s, teacher, out), out
        s = feedback(s, teacher, out)
    raise AssertionError('fixture did not reach measured preparation')


def test_invalid_ik_freezes_all_reference_clocks():
    t = api()
    teacher, s = t.ReferenceTeacher(), near_state()
    teacher.step(s)
    teacher.step(advance(s))
    row = teacher._rows[0]
    old = tuple(row.get(k, 0) for k in ('age', 'body_age', 'lift_age'))
    # Genuine infeasible input: measured joint is beyond the original limit.
    q = s.leg_pos.clone()
    q[:, 0] = 3.
    s = replace(s, leg_pos=q, control_step=s.control_step+2)
    for index in range(5):
        out = teacher.step(s)
        assert tuple(row.get(k, 0) for k in ('age', 'body_age', 'lift_age')) == old
        assert not out.valid.any() and not out.action[:, t.WHEEL_COLUMNS].any()
        assert out.failure_locked.item() == (index == 4)
        s = advance(s)


def test_hold_last_applied_target_not_falling_measured_q():
    t = api()
    from ame_baseline.m1_ame_contract import m1_action_targets
    teacher, s = t.ReferenceTeacher(), near_state()
    first = teacher.step(s)
    applied = m1_action_targets(first.action, s.default_joint_pos)[:, t.LEG_COLUMNS]
    q = s.leg_pos.clone()
    q[:, 0] = 3.
    out = teacher.step(advance(s, leg_pos=q, last_applied_leg_target=applied))
    held = m1_action_targets(out.action, s.default_joint_pos)[:, t.LEG_COLUMNS]
    assert not out.valid.item()
    assert torch.equal(held, applied), 'fallback must hold accepted execution, not measured falling joints'


def test_lift_requires_measured_com_and_three_loads():
    t = api()
    teacher, s = t.ReferenceTeacher(), near_state()
    teacher.step(s)
    teacher.step(advance(s))
    # All loads/root ready; measured COM is on the diagonal support edge.
    # A predicted inward shift is feasible but does not certify real support.
    s = advance(advance(s))
    s.com_pos_w[:, :2] = (s.wheel_pos_w[:, 1, :2]+s.wheel_pos_w[:, 2, :2])/2
    out = teacher.step(s)
    assert out.valid.item()
    assert out.diagnostic[0, t.TEACHER_DIAGNOSTIC_FIELDS.index('candidate_com_margin_m')] >= .01
    assert out.diagnostic[0, t.TEACHER_DIAGNOSTIC_FIELDS.index('measured_com_margin_m')] < .01
    assert out.phase.item() == t.Phase.BALANCE
    assert not out.failure_locked.item()


def test_prepare_anchor_does_not_follow_slip():
    teacher, s, _ = prepared_teacher(diagnostic=True)
    before = teacher._rows[0]['accepted'].wheels_w.clone()
    slipped = s.wheel_pos_w.clone()
    slipped[:, 1, 0] += .005
    teacher.diagnostic_step(replace(s, wheel_pos_w=slipped), active_wheel=0, lift=False)
    assert torch.equal(teacher._rows[0]['accepted'].wheels_w, before)


def test_diagnostic_lift_uses_same_constraints_without_course_receipt():
    t = api()
    teacher, s = t.ReferenceTeacher(), near_state()
    receipt, course = s.recovered.clone(), s.course_valid.clone()
    for _ in range(5):
        out = teacher.diagnostic_step(s, active_wheel=0, lift=True)
        assert out.active_target.item() == -1 and not out.valid.item()
        assert not out.failure_locked.item()
        s = feedback(s, teacher, replace(out, valid=torch.ones_like(out.valid)))
    assert out.phase.item() == t.Phase.LIFT
    assert torch.equal(s.recovered, receipt) and torch.equal(s.course_valid, course)
    assert out.diagnostic.shape == (1, len(t.TEACHER_DIAGNOSTIC_FIELDS))


def test_initial_zero_applied_target_is_not_silently_replaced():
    t = api()
    s = state(targets=False)
    s.last_applied_leg_target.zero_()
    out = t.ReferenceTeacher().step(s)
    assert not out.valid.item(), 'nominal request exceeds actual reset target slew'


def test_missing_measurement_and_execution_evidence_fail_closed():
    t = api()
    for field in ('measurement_valid', 'applied_target_valid'):
        s = state(targets=False)
        getattr(s, field).zero_()
        out = t.ReferenceTeacher().step(s)
        assert not out.valid.item()


@pytest.mark.parametrize('case', ['missing-evidence', 'illegal-hold', 'discontinuous-hold'])
def test_uncertifiable_hold_is_nonexecutable_without_nominal_jump(case):
    from ame_baseline.m1_ame_contract import m1_action_targets
    t = api(); s = state(targets=False); s.leg_pos[:, 0] = .3
    s.last_applied_leg_target.copy_(s.leg_pos)
    teacher = t.ReferenceTeacher(); first = teacher.step(s)
    prior = m1_action_targets(first.action, s.default_joint_pos)[:, t.LEG_COLUMNS]
    s = advance(s, leg_pos=prior.clone(), last_applied_leg_target=prior.clone())
    if case == 'missing-evidence': s.applied_target_valid.zero_()
    elif case == 'illegal-hold':
        teacher._rows[0]['last_q'][:, 0] = 3.; s.leg_pos[:, 0] = 3.
    else:
        s.last_applied_leg_target[:, 0] += .5; s.leg_pos[:, 0] = 3.
    out = teacher.step(s)
    assert not out.valid.item()
    assert hasattr(out, 'executable'), 'label validity cannot certify command execution'
    assert not out.executable.item()
    assert torch.isnan(out.action).all(), 'non-command placeholder must never decode to nominal'


def test_mixed_rows_distinguish_legal_invalid_hold_and_nonexecutable():
    from ame_baseline.m1_ame_contract import m1_action_targets
    t = api(); teacher = t.ReferenceTeacher(); s = state(3, targets=False)
    first = teacher.step(s)
    prior = m1_action_targets(first.action, s.default_joint_pos)[:, t.LEG_COLUMNS]
    s = advance(s, leg_pos=prior.clone(), last_applied_leg_target=prior.clone())
    s.leg_pos[1, 0] = 3.; s.applied_target_valid[2] = False
    out = teacher.step(s)
    assert hasattr(out, 'executable')
    assert out.executable.tolist() == [True, True, False]
    assert out.valid.tolist() == [True, False, False]
    assert torch.equal(m1_action_targets(out.action[1:2], s.default_joint_pos[1:2])[:, t.LEG_COLUMNS], prior[1:2])
    assert not out.failure_locked.any()


@pytest.mark.parametrize('knee,executable', [(0.,False),(.099,False),(.10,True)])
def test_raw_held_target_respects_existing_near_straight_guard(knee,executable):
    t=api(); s=state(targets=False); s.measurement_valid.zero_()
    s.last_applied_leg_target[:,[2,5,8,11]]=torch.tensor([-knee,-knee,knee,knee])
    out=t.ReferenceTeacher().step(s)
    assert out.executable.item() is executable
    assert not out.valid.item()
    if not executable: assert torch.isnan(out.action).all()


def test_held_target_cannot_change_captured_knee_branch():
    teacher,s,_=prepared_teacher(); row=teacher._rows[0]
    last=row['last_q'].clone(); last[:,2]=-last[:,2]
    row['last_q']=last
    s=advance(s,last_applied_leg_target=last.clone(),measurement_valid=torch.zeros_like(s.measurement_valid))
    out=teacher.step(s)
    assert not out.executable.item() and not out.valid.item()
    assert torch.isnan(out.action).all()


@pytest.mark.parametrize('rate,quiet', [([0.,0.,.201],False),([.15,.15,0.],False),
    ([0.,0.,.20],True),([.12,.16,0.],True)])
def test_quiet_uses_complete_angular_velocity_norm(rate, quiet):
    s = state(targets=False); s.root_ang_vel_w[:] = torch.tensor(rate)
    assert api().ReferenceTeacher()._quiet(s, 0) is quiet


@pytest.mark.parametrize('rate', [[0.,0.,.201],[.15,.15,0.]])
def test_restore_rejects_complete_angular_speed_over_bound(rate):
    from test_m1_reference_teacher import restoring_teacher
    teacher, s = restoring_teacher(); s.root_ang_vel_w[:] = torch.tensor(rate)
    teacher.step(s)
    assert teacher._rows[0]['stable'] == 0


def rotated_pass(captured_yaw, measured_yaw=None):
    from ame_baseline.m1_teacher_pose import BodyPose, PoseReference
    from extension.parallelism.kinematics import rpy_to_rotation_matrix
    teacher, s, _ = prepared_teacher(); row = teacher._rows[0]
    yaw = torch.tensor(captured_yaw)
    quat = torch.tensor([[yaw.div(2).cos(),0.,0.,yaw.div(2).sin()]])
    rotation = rpy_to_rotation_matrix(torch.tensor([[0.,0.,captured_yaw]]))[0]
    rot = lambda x: x@rotation.T
    pose = lambda p: BodyPose(rot(p.pos_w),quat.clone())
    ref = lambda p: PoseReference(pose(p.body),rot(p.wheels_w))
    s = replace(s,root_pos_w=rot(s.root_pos_w),root_quat_w=quat.clone(),
        wheel_pos_w=rot(s.wheel_pos_w),com_pos_w=rot(s.com_pos_w))
    for key in ('accepted','goal'): row[key]=ref(row[key])
    row['anchor_pose']=pose(row['anchor_pose'])
    for key in ('anchor','wheel_anchor','support_origin','support_previous'): row[key]=rot(row[key])
    row['yaw']=torch.tensor([captured_yaw]); row.update(phase=api().Phase.PASS,age=10,lift_age=0)
    s.centers_top[:,0,0]=2.
    if measured_yaw is not None:
        angle=torch.tensor(measured_yaw/2)
        s=replace(s,root_quat_w=torch.tensor([[angle.cos(),0.,0.,angle.sin()]]))
    return teacher,s


@pytest.mark.parametrize('captured,measured,error', [(.3,.3,0.),(.3,.34,.04),
    (3.12,-3.12,2*torch.pi-6.24)])
def test_pass_wheel_correction_tracks_wrapped_captured_heading(captured,measured,error):
    from ame_baseline.m1_ame_contract import m1_action_targets, M1_WHEEL_RADIUS_M
    t=api(); teacher,s=rotated_pass(captured,measured); out=teacher.step(s)
    assert out.valid.item()
    speed=m1_action_targets(out.action,s.default_joint_pos)[:,t.WHEEL_COLUMNS]*M1_WHEEL_RADIUS_M
    # Compare left/right correction: common nominal speed cancels.
    assert torch.allclose(speed[:,0]-speed[:,1], speed.new_tensor([teacher.cfg.yaw_gain_s_inv*.43*error]),atol=1e-6)


def test_pass_transports_common_xy_only():
    t = api()
    teacher, s, _ = prepared_teacher()
    row = teacher._rows[0]
    row.update(phase=t.Phase.PASS, lift_age=0)
    before, quat = row['wheel_anchor'].clone(), row['accepted'].body.quat_w.clone()
    wheels = s.wheel_pos_w.clone()
    deltas = torch.tensor([[.004, .001], [.001, -.002], [.001, .004]])
    wheels[:, 1:, :2] += deltas
    out = teacher.step(replace(s, wheel_pos_w=wheels))
    assert out.valid.item()
    common = deltas.mean(0)
    assert torch.allclose(row['wheel_anchor'][..., :2], before[..., :2]+common)
    assert torch.equal(row['wheel_anchor'][..., 2], before[..., 2])
    assert torch.equal(row['accepted'].body.quat_w, quat)
    for leg in range(1, 4):
        ids = [t.TEACHER_DIAGNOSTIC_FIELDS.index(f'support_slip_{leg}_{a}') for a in ('x', 'y')]
        assert torch.allclose(out.diagnostic[0, ids], deltas[leg-1]-common, atol=1e-7)


def test_restore_receipt_is_not_phase_certificate():
    from test_m1_reference_teacher import restoring_teacher
    teacher, s = restoring_teacher()
    for _ in range(7):
        out = teacher.step(s)
        assert out.valid.item() and out.active_target.item() == 0
        s = feedback(s, teacher, out)
    assert teacher._rows[0]['stable'] >= 5
    s.recovered[:, 0, 0] = True
    assert teacher.step(s).active_target.item() == -1


def test_duplicate_gap_and_one_row_reset():
    from test_m1_reference_teacher import restoring_teacher_with_four_stable_samples
    t = api()
    teacher, s = restoring_teacher_with_four_stable_samples()
    cached = teacher.step(s)
    for _ in range(3):
        assert torch.equal(teacher.step(s).action, cached.action)
        assert teacher._rows[0]['stable'] == 4
    s = replace(s, control_step=s.control_step+2)
    out = teacher.step(s)
    assert out.active_target.item() == 0 and teacher._rows[0]['stable'] == 1
    teacher, s = t.ReferenceTeacher(), near_state(2)
    original = teacher.step(s)
    s = replace(s, reset_mask=torch.tensor([True, False]), episode_id=torch.tensor([1, 0]),
                recovered=torch.ones_like(s.recovered))
    out = teacher.step(s)
    assert out.active_target[0] == -1 and not out.valid[0]
    assert torch.equal(out.action[1], original.action[1])
    assert 'accepted' not in teacher._rows[0]


def test_untracked_reference_freezes_ages_and_accepted():
    teacher, s, _ = prepared_teacher(diagnostic=True)
    row = teacher._rows[0]
    ages = tuple(row[k] for k in ('age', 'body_age', 'lift_age'))
    accepted = row['accepted']
    root = s.root_pos_w.clone()
    root[:, 0] += .02
    out = teacher.diagnostic_step(replace(s, root_pos_w=root), active_wheel=0, lift=False)
    assert not out.failure_locked.item()
    assert tuple(row[k] for k in ('age', 'body_age', 'lift_age')) == ages
    assert torch.equal(row['accepted'].body.pos_w, accepted.body.pos_w)
    assert torch.equal(row['accepted'].wheels_w, accepted.wheels_w)


def test_invalid_result_keeps_accepted_pose_separate_from_diagnostic_candidate():
    teacher, s, _ = prepared_teacher(diagnostic=True)
    row = teacher._rows[0]
    accepted = row['accepted']
    s.last_applied_leg_target[:, 0] += .5
    out = teacher.diagnostic_step(s, active_wheel=0, lift=False)
    assert not out.valid.item()
    assert row['accepted'] is accepted
    t = api()
    assert out.diagnostic[0, t.TEACHER_DIAGNOSTIC_FIELDS.index('backtrack_index')] == -1
    assert out.diagnostic[0, t.TEACHER_DIAGNOSTIC_FIELDS.index('reference_valid')] == 0


def test_preparation_slip_is_not_later_transported_as_pass_motion():
    t = api()
    teacher, s, _ = prepared_teacher()
    wheels = s.wheel_pos_w.clone()
    wheels[:, 1, 0] += .006
    out = teacher.step(replace(s, wheel_pos_w=wheels))
    assert out.valid.item()
    row = teacher._rows[0]
    before = row['wheel_anchor'].clone()
    row['phase'] = t.Phase.PASS
    # Same measured support positions: no new rolling displacement exists.
    s = advance(s, wheel_pos_w=wheels, leg_pos=row['last_q'].clone(),
                last_applied_leg_target=row['last_q'].clone())
    out = teacher.step(s)
    assert out.valid.item()
    assert torch.equal(row['wheel_anchor'], before)


def test_predicted_margin_is_available_on_lift_and_matches_attempted_pose():
    from test_m1_reference_teacher import teacher_in_lift
    from ame_baseline.m1_teacher_pose import support_margin
    t = api()
    teacher, s = teacher_in_lift()
    out = teacher.step(s)
    value = out.diagnostic[0, t.TEACHER_DIAGNOSTIC_FIELDS.index('predicted_com_margin_m')]
    expected, _ = support_margin(s.com_pos_w, teacher._rows[0]['accepted'].wheels_w,
                                 torch.tensor([0]))
    assert torch.isfinite(value)
    assert torch.allclose(value, expected[0], atol=1e-6)


@pytest.mark.parametrize('field,value', [('backtrack_steps', 8.), ('candidate_limit', 126.),
                                        ('invalid_lock_steps', 5.)])
def test_discrete_bounds_reject_float_configuration(field, value):
    with pytest.raises(ValueError):
        api().TeacherConfig(**{field: value})


@pytest.mark.parametrize('mode', ['reset', 'nan', 'collision', 'target', 'normal'])
def test_all_output_paths_have_owned_complete_diagnostic_schema(mode):
    t = api()
    teacher, s = t.ReferenceTeacher(), near_state()
    out = teacher.step(s)
    s = feedback(s, teacher, out)
    if mode == 'reset':
        s = replace(s, reset_mask=torch.ones_like(s.reset_mask))
    elif mode == 'nan':
        s.root_pos_w[0, 0] = float('nan')
    elif mode == 'collision':
        s.collision[0] = True
    elif mode == 'target':
        s.course_ids[0, 0] += 1
    out = teacher.step(s)
    assert out.diagnostic.shape == (1, len(t.TEACHER_DIAGNOSTIC_FIELDS))
    assert torch.isfinite(out.action[out.executable]).all()
    assert torch.isnan(out.action[~out.executable]).all()
    saved = out.diagnostic.clone()
    out.diagnostic.zero_()
    assert torch.allclose(teacher.step(s).diagnostic, saved, equal_nan=True)


@pytest.mark.parametrize('phase', ['approach', 'restore'])
@pytest.mark.parametrize('dt', [.01, .02, .04])
def test_approach_and_restore_use_actual_execution_slew(phase, dt):
    from test_m1_reference_teacher import restoring_teacher
    from ame_baseline.m1_ame_contract import m1_action_targets
    t = api()
    if phase == 'restore':
        teacher, s = restoring_teacher()
    else:
        teacher, s = t.ReferenceTeacher(), state(targets=False)
    actual = s.last_applied_leg_target.clone()
    actual[:, 0] += .4
    out = teacher.step(replace(s, last_applied_leg_target=actual, dt=torch.tensor([dt])))
    decoded = m1_action_targets(out.action, s.default_joint_pos)[:, t.LEG_COLUMNS]
    assert not out.valid.item() or bool(((decoded-actual).abs() <= 2.5*dt).all())


def test_failed_reference_freezes_pose_even_after_four_invalid_and_then_locks():
    teacher, s, _ = prepared_teacher()
    row, ref = teacher._rows[0], teacher._rows[0]['accepted']
    ages = tuple(row[k] for k in ('age', 'body_age', 'lift_age'))
    q = s.leg_pos.clone()
    q[:, 0] = 3.
    s = replace(s, leg_pos=q)
    for index in range(6):
        out = teacher.step(s)
        assert row['accepted'] is ref
        assert tuple(row[k] for k in ('age', 'body_age', 'lift_age')) == ages
        assert out.failure_locked.item() == (index >= 4)
        s = advance(s)
