"""CPU contract and counterexample tests for the independent teacher."""
import importlib.util
from dataclasses import replace, FrozenInstanceError
from types import SimpleNamespace

import pytest
import torch


def api():
    assert importlib.util.find_spec('ame_baseline.m1_reference_teacher') is not None, 'independent teacher is missing'
    from ame_baseline import m1_reference_teacher as t
    return t


def state(batch=1, targets=True):
    t = api()
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS
    from extension.parallelism.m1_kinematics import m1_fk
    defaults = torch.tensor(M1_TRAINING_JOINT_POS).repeat(batch, 1)
    q = defaults[:, t.LEG_COLUMNS].clone()
    root = torch.tensor([0., 0., .62]).repeat(batch, 1)
    wheels = m1_fk(root, torch.zeros_like(root), q).foot_pos_w
    quat = torch.tensor([1., 0., 0., 0.]).repeat(batch, 4, 1)
    centers = torch.tensor([.6, .215, .1]).repeat(batch, 1, 1)
    required = torch.tensor([True, False, True, False]).repeat(batch, 1, 1)
    return t.TeacherState(root_pos_w=root, root_quat_w=quat[:, 0].clone(),
        root_lin_vel_w=torch.zeros(batch, 3), root_ang_vel_w=torch.zeros(batch, 3),
        leg_pos=q, default_joint_pos=defaults, wheel_pos_w=wheels, wheel_quat_w=quat,
        wheel_force_w=torch.tensor([0., 0., 60.]).repeat(batch, 4, 1),
        centers_top=centers, half_extents=torch.tensor([.05, .09]).repeat(batch, 1, 1),
        ground_z=torch.zeros(batch, 1), course_valid=torch.full((batch, 1), targets),
        course_ids=torch.zeros(batch, 1, dtype=torch.long), required_wheels=required,
        recovered=torch.zeros(batch, 1, 4, dtype=torch.bool),
        nominal_root_z_w=root[:, 2].clone(), dt=torch.full((batch,), .02),
        reset_mask=torch.zeros(batch, dtype=torch.bool), episode_id=torch.zeros(batch, dtype=torch.long),
        control_step=torch.zeros(batch, dtype=torch.long), collision=torch.zeros(batch, dtype=torch.bool))


def advance(s, **kw):
    return replace(s, control_step=s.control_step + 1, **kw)


def measured_shift_ready(s, wheel=0):
    """Synthetic measured body motion; supporting wheel positions stay measured."""
    root = s.root_pos_w.clone()
    root[:,0] += -.04 if wheel < 2 else .04
    root[:,1] += -.06 if wheel % 2 == 0 else .06
    return replace(s, root_pos_w=root)


def teacher_in_lift():
    """Downstream phase tests explicitly supply the new preparation evidence."""
    t = api()
    teacher, s = t.ReferenceTeacher(), state()
    s.wheel_pos_w[:,0,0] = .39
    assert teacher.step(s).phase.item() == t.Phase.BALANCE
    s = advance(measured_shift_ready(s))
    assert teacher.step(s).phase.item() == t.Phase.LIFT
    return teacher, advance(s)


def test_config_is_immutable_and_fingerprints_semantics():
    t = api()
    cfg = t.TeacherConfig()
    assert (cfg.balance_steps, cfg.lift_steps, cfg.pass_steps, cfg.restore_steps) == (30, 10, 20, 20)
    assert (cfg.front_max_lift_m, cfg.rear_max_lift_m, cfg.far_margin_m) == (.22, .20, .15)
    assert cfg.fingerprint != replace(cfg, pass_steps=21).fingerprint
    with pytest.raises(FrozenInstanceError):
        cfg.far_margin_m = 0.


def test_singular_dls_is_finite_and_clips_components_not_vector_norm():
    t = api()
    assert torch.equal(t.dls_step(torch.zeros(1, 3, 3), torch.ones(1, 3)), torch.zeros(1, 3))
    dq = t.dls_step(torch.eye(3)[None], torch.ones(1, 3))
    assert torch.allclose(dq, torch.full((1, 3), .25))


def test_body_jacobian_matches_autograd_and_is_world_origin_independent():
    t = api()
    s = state()
    jac = t.body_jacobian(s.leg_pos)
    assert jac.shape == (1, 4, 3, 3)
    q = s.leg_pos[0].clone().requires_grad_()
    exact = torch.autograd.functional.jacobian(lambda a: t.body_feet(a[None])[0], q)
    for wheel in range(4):
        assert torch.allclose(jac[0, wheel], exact[wheel, :, wheel*3:wheel*3+3], atol=6e-4)


def test_ik_preserves_negative_front_branch_and_mirrored_pose():
    t = api()
    s = state()
    target = t.body_feet(s.leg_pos)
    target[:, :, 2] += .07
    q, valid = t.solve_ik_body(s.leg_pos, target)
    assert valid.all()
    assert (q[:, [2, 5]] < 0).all() and (q[:, [8, 11]] > 0).all()
    assert torch.allclose(q[:, 1:3], q[:, 4:6], atol=1e-4)
    assert torch.allclose(t.body_feet(q), target, atol=.002)


@pytest.mark.parametrize('bad', ['unreachable', 'nan'])
def test_ik_invalid_is_finite_without_reachable_label(bad):
    t = api()
    s = state()
    target = t.body_feet(s.leg_pos)
    target[:, 0, 2] = 10. if bad == 'unreachable' else float('nan')
    q, valid = t.solve_ik_body(s.leg_pos, target)
    assert not valid[0] and torch.isfinite(q).all()


def test_inverse_encoding_uses_live_defaults_and_real_decoder():
    t = api()
    from ame_baseline.m1_ame_contract import m1_action_targets
    s = state()
    defaults = s.default_joint_pos.clone()
    defaults[:, t.LEG_COLUMNS] += .025
    q = defaults[:, t.LEG_COLUMNS] + .01
    speed = torch.tensor([[.3, -.2, .0, .5]])
    action, valid = t.encode_targets(q, speed, defaults)
    actual = m1_action_targets(action, defaults)
    assert valid.all()
    assert torch.allclose(actual[:, t.LEG_COLUMNS], q)
    assert torch.allclose(actual[:, t.WHEEL_COLUMNS] * .0959, speed)
    assert t.WHEEL_COLUMNS == [3, 7, 11, 15]


def test_inverse_encoding_rejects_clipping_and_nan_and_stops_wheels():
    t = api()
    s = state(3)
    q = s.leg_pos.clone()
    q[0, 0] = 3.
    q[1, 0] = float('nan')
    speeds = torch.zeros(3, 4)
    speeds[2] = 3.
    action, valid = t.encode_targets(q, speeds, s.default_joint_pos)
    assert not valid.any() and torch.isfinite(action).all()
    assert not action[:, t.WHEEL_COLUMNS].any()


def test_flat_roll_keeps_live_nominal_and_never_selects_padding():
    t = api()
    s = state(targets=False)
    out = t.ReferenceTeacher().step(s)
    assert out.valid.all() and (out.active_wheel == -1).all()
    assert torch.equal(out.action[:, t.LEG_COLUMNS], torch.zeros(1, 12))
    assert (out.action[:, t.WHEEL_COLUMNS] > 0).all()


def test_same_control_step_is_idempotent():
    t = api()
    s = state()
    teacher = t.ReferenceTeacher()
    a = teacher.step(s)
    b = teacher.step(s)
    assert torch.equal(a.action, b.action) and torch.equal(a.phase, b.phase)
    assert torch.equal(a.active_wheel, b.active_wheel)


def test_clock_does_not_lift_without_three_measured_supports():
    t = api()
    s = state()
    s.wheel_pos_w[:, 0, 0] = .39
    s.wheel_force_w[:, 1] = 0
    teacher = t.ReferenceTeacher()
    for _ in range(40):
        out = teacher.step(s)
        s = advance(s)
    assert out.phase.item() == t.Phase.BALANCE


def test_clock_does_not_pass_without_measured_cylinder_bottom_clearance():
    t = api()
    teacher, s = teacher_in_lift()
    for _ in range(40):
        out = teacher.step(s)
        s = advance(s)
    assert out.phase.item() == t.Phase.LIFT
    assert out.active_wheel.item() == 0


def test_far_envelope_margin_is_not_reduced_and_receipt_is_required():
    t = api()
    teacher, s = teacher_in_lift()
    for _ in range(3):
        teacher.step(s)
        s = advance(s)
    s.wheel_pos_w[:, 0, 2] = .30
    teacher.step(s)
    s = advance(s)
    s.wheel_pos_w[:, 0, 0] = .85  # beyond box, but not .65 + .11915 + .15
    for _ in range(25):
        out = teacher.step(s)
        s = advance(s)
    assert out.phase.item() == t.Phase.PASS
    s.wheel_pos_w[:, 0, 0] = .93
    for _ in range(30):
        out = teacher.step(s)
        s = advance(s)
    assert out.phase.item() == t.Phase.RESTORE
    assert out.active_wheel.item() == 0
    s.recovered[:, 0, 0] = True
    out = teacher.step(s)
    assert out.active_wheel.item() == -1
    out = teacher.step(advance(s))
    assert out.active_wheel.item() == 2


def test_reset_row_and_episode_identity_cannot_finish_old_target():
    t = api()
    s = state(2)
    s.wheel_pos_w[:, 0, 0] = .39
    teacher = t.ReferenceTeacher()
    teacher.step(s)
    fresh = advance(s, reset_mask=torch.tensor([True, False]), episode_id=torch.tensor([1, 0]))
    fresh.recovered[0] = True  # terminal receipt cannot be re-used on reset row
    out = teacher.step(fresh)
    assert not out.valid[0] and out.active_wheel[0] == -1
    assert out.active_wheel[1] == 0


def test_collision_and_lost_support_latch_failure_until_reset():
    t = api()
    teacher, s = teacher_in_lift()
    for _ in range(3):
        teacher.step(s)
        s = advance(s)
    s.wheel_force_w[:, 1] = 0
    out = teacher.step(s)
    assert not out.valid.item() and out.reason.item() == t.Reason.SUPPORT_LOST
    s.wheel_force_w[:, 1, 2] = 60
    out = teacher.step(advance(s))
    assert not out.valid.item()
    other = t.ReferenceTeacher().step(replace(state(), collision=torch.tensor([True])))
    assert not other.valid.item() and other.reason.item() == t.Reason.COLLISION


def test_body_shift_is_closed_loop_and_mirrors_left_right():
    t = api()
    actual = torch.zeros(2, 3)
    anchor = actual.clone()
    wheels = torch.tensor([0, 1])
    error = t.body_shift_error(anchor, actual, torch.zeros(2), wheels, torch.ones(2), t.TeacherConfig())
    assert torch.allclose(error[:, 0], torch.tensor([-.04, -.04]))
    assert torch.allclose(error[:, 1], torch.tensor([-.06, .06]))
    assert torch.allclose(t.body_shift_error(anchor, error, torch.zeros(2), wheels, torch.ones(2), t.TeacherConfig()), torch.zeros(2, 3))


def test_adapter_is_read_only_named_and_uses_required_course_not_fill():
    t = api()
    assert importlib.util.find_spec('ame_baseline.m1_teacher_adapter') is not None
    from ame_baseline.m1_teacher_adapter import ReferenceTeacherAdapter
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES
    s = state()
    names = tuple(reversed(M1_ASSET_JOINT_NAMES))
    body_names = tuple(reversed(tuple(n.replace('_JOINT', '_LINK') for n in M1_WHEEL_JOINT_NAMES)))
    robot = SimpleNamespace(joint_names=names, body_names=body_names, data=SimpleNamespace(
        root_pos_w=s.root_pos_w, root_quat_w=s.root_quat_w, root_lin_vel_w=s.root_lin_vel_w,
        root_ang_vel_w=s.root_ang_vel_w, joint_pos=s.default_joint_pos.flip(-1),
        default_joint_pos=s.default_joint_pos.flip(-1), body_pos_w=s.wheel_pos_w.flip(1),
        body_quat_w=s.wheel_quat_w.flip(1), default_root_state=torch.tensor([[0.,0.,.62]+[0.]*10])))
    sensor = SimpleNamespace(body_names=body_names, data=SimpleNamespace(net_forces_w=s.wheel_force_w.flip(1)))
    class Scene(dict):
        env_origins = torch.zeros(1, 3)
    scene = Scene(robot=robot, contact_forces=sensor)
    course = dict(centers_top=s.centers_top, half_extents=s.half_extents, ground_z=s.ground_z,
        valid=s.course_valid, ids=s.course_ids, landing_centers_top=torch.ones(1, 5, 3)*99)
    class Tracker:
        def recovered_for_course(self, value):
            assert value is course
            return s.recovered
        def update(self, *args, **kw):
            raise AssertionError('adapter must not update tracker')
    wrapper = SimpleNamespace(unwrapped=SimpleNamespace(scene=scene, step_dt=.02),
        _m1_current_course=lambda: course, _m1_strict_crossing=Tracker())
    snapshot = ReferenceTeacherAdapter(wrapper).snapshot(control_step=s.control_step,
        episode_id=s.episode_id, reset_mask=s.reset_mask, collision=s.collision)
    assert torch.equal(snapshot.leg_pos, s.leg_pos)
    assert torch.equal(snapshot.wheel_pos_w, s.wheel_pos_w)
    assert torch.equal(snapshot.required_wheels, s.required_wheels)
    snapshot.wheel_pos_w.zero_()
    assert robot.data.body_pos_w.abs().sum() > 0
    with pytest.raises(ValueError, match='control_step'):
        ReferenceTeacherAdapter(wrapper).snapshot(control_step=torch.zeros(1),
            episode_id=s.episode_id, reset_mask=s.reset_mask, collision=s.collision)


def test_wheel_decoder_allows_full_motor_envelope():
    t = api()
    s = state()
    action, valid = t.encode_targets(s.leg_pos, torch.full((1,4), 1.5), s.default_joint_pos)
    assert valid.item() and (action[:,t.WHEEL_COLUMNS] > 1).all()


def test_flat_uses_task_speed_and_approach_has_finite_capture_band():
    t = api()
    out = t.ReferenceTeacher().step(state(targets=False))
    assert torch.allclose(out.action[:,t.WHEEL_COLUMNS], torch.full((1,4), .3))
    s = state()
    s.wheel_pos_w[:,0,0] = .6-.05-.11915-.06-.005
    out = t.ReferenceTeacher().step(s)
    assert out.phase.item() == t.Phase.BALANCE


def test_same_step_reset_does_not_return_old_cached_action():
    t = api()
    teacher = t.ReferenceTeacher()
    s = state()
    teacher.step(s)
    fresh = replace(s, episode_id=torch.ones(1,dtype=torch.long), reset_mask=torch.ones(1,dtype=torch.bool))
    out = teacher.step(fresh)
    assert not out.valid.item() and out.reason.item() == t.Reason.RESET
    assert out.active_wheel.item() == -1
    assert torch.equal(teacher.step(fresh).action, out.action)


def test_identity_change_without_reset_mask_still_discards_terminal_receipts():
    t = api()
    teacher = t.ReferenceTeacher()
    s = state()
    teacher.step(s)
    s = advance(s, episode_id=torch.ones(1,dtype=torch.long), recovered=torch.ones(1,1,4,dtype=torch.bool))
    out = teacher.step(s)
    assert not out.valid.item() and out.reason.item() == t.Reason.RESET


def test_five_consecutive_stable_measurements_even_when_receipt_already_exists():
    t = api()
    teacher, s = teacher_in_lift()
    for _ in range(3):
        teacher.step(s)
        s = advance(s)
    s.wheel_pos_w[:,0,2] = .30
    teacher.step(s)
    s = advance(s)
    s.wheel_pos_w[:,0,0] = .93
    out = teacher.step(s)
    assert out.phase.item() == t.Phase.RESTORE
    s.recovered[:,0,0] = True
    for index in range(5):
        s = advance(s)
        out = teacher.step(s)
        assert out.active_wheel.item() == (0 if index < 4 else -1)


def test_translation_of_measured_rolling_supports_does_not_world_lock_feet():
    t = api()
    first, second = t.ReferenceTeacher(), t.ReferenceTeacher()
    a, b = state(), state()
    a.wheel_pos_w[:,0,0] = b.wheel_pos_w[:,0,0] = .39
    first.step(a)
    second.step(b)
    a, b = advance(a), advance(b)
    b.root_pos_w[:,0] += 10.
    b.wheel_pos_w[:,:,0] += 10.
    b.centers_top[:,:,0] += 10.
    result_a, result_b = first.step(a), second.step(b)
    assert torch.equal(result_a.valid, result_b.valid)
    assert torch.allclose(result_a.action, result_b.action, atol=2e-4)


def test_legal_leg_target_is_not_rejected_for_raw_action_above_one():
    t = api()
    s = state()
    q = s.leg_pos.clone()
    q[:,2] = -2.3
    action, valid = t.encode_targets(q, torch.zeros(1,4), s.default_joint_pos)
    assert valid.item() and action[:,t.LEG_COLUMNS].abs().max() > 1


def test_horizontal_wall_force_cannot_certify_three_supports():
    t = api()
    s = state()
    s.wheel_pos_w[:,0,0] = .39
    s.wheel_force_w[:,1] = torch.tensor([60.,0.,0.])
    teacher = t.ReferenceTeacher()
    for _ in range(3):
        out = teacher.step(s)
        s = advance(s)
    assert out.phase.item() == t.Phase.BALANCE


@pytest.mark.parametrize('field', ['root_pos_w','root_quat_w','root_lin_vel_w','root_ang_vel_w',
    'leg_pos','default_joint_pos','wheel_pos_w','wheel_quat_w','wheel_force_w','centers_top'])
def test_nonfinite_measured_state_is_not_a_label(field):
    t = api()
    s = state(targets=False)
    value = getattr(s,field)
    value[(0,)*value.ndim] = float('nan')
    out = t.ReferenceTeacher().step(s)
    assert not out.valid.item() and torch.isfinite(out.action).all()
    assert out.reason.item() == t.Reason.NONFINITE


@pytest.mark.parametrize('field', ['root_quat_w','wheel_quat_w'])
def test_zero_measured_quaternion_is_not_a_label(field):
    t = api()
    s = state(targets=False)
    getattr(s,field).zero_()
    out = t.ReferenceTeacher().step(s)
    assert not out.valid.item() and torch.isfinite(out.action).all()


def test_target_identity_change_fails_closed():
    t = api()
    s = state()
    teacher = t.ReferenceTeacher()
    teacher.step(s)
    s = advance(s, course_ids=torch.ones_like(s.course_ids))
    out = teacher.step(s)
    assert not out.valid.item() and out.reason.item() == t.Reason.TARGET_CHANGED


def test_reset_same_step_keeps_other_batch_rows_idempotent():
    t = api()
    teacher = t.ReferenceTeacher()
    s = state(2)
    a = teacher.step(s)
    b = teacher.step(replace(s, reset_mask=torch.tensor([True,False]), episode_id=torch.tensor([1,0])))
    assert not b.valid[0] and torch.equal(a.action[1], b.action[1])


def test_world_offset_does_not_change_body_ik_labels():
    t = api()
    a, b = state(), state()
    a.wheel_pos_w[:,0,0] = b.wheel_pos_w[:,0,0] = .39
    b.root_pos_w[:,:2] += 100.
    b.wheel_pos_w[:,:,:2] += 100.
    b.centers_top[:,:,:2] += 100.
    first, second = t.ReferenceTeacher(), t.ReferenceTeacher()
    for _ in range(3):
        out_a, out_b = first.step(a), second.step(b)
        a,b = advance(a),advance(b)
    assert torch.equal(out_a.valid, out_b.valid)
    assert torch.allclose(out_a.action,out_b.action,atol=3e-4)


def test_balance_reference_ramp_remains_continuous_when_measured_gate_advances():
    t = api()
    s = state()
    s.wheel_pos_w[:,0,0] = .39
    teacher = t.ReferenceTeacher()
    a = teacher.step(s)
    b = teacher.step(advance(measured_shift_ready(s)))
    assert a.phase.item() == t.Phase.BALANCE and b.phase.item() == t.Phase.LIFT
    # Two measured gates are allowed to advance, but do not skip 28 samples
    # of the 30-sample reference body-shift interpolation.
    # Supporting-wheel ABAD reference remains at 2/30; the swinging wheel
    # also responds to the explicitly changed measured root in this fixture.
    assert b.action[:,[4,8,12]].abs().max() < .02


def test_early_lift_gate_does_not_jump_to_full_lift_reference():
    t = api()
    s = state()
    s.wheel_pos_w[:,0,0] = .39
    teacher = t.ReferenceTeacher()
    teacher.step(s)
    s = advance(measured_shift_ready(s))
    a = teacher.step(s)
    s = advance(s)
    s.wheel_pos_w[:,0,2] = .30
    b = teacher.step(s)
    assert b.phase.item() == t.Phase.PASS
    assert (a.action[:,2]-b.action[:,2]).abs().max() < .2


def restoring_teacher_with_four_stable_samples():
    t = api()
    teacher, s = teacher_in_lift()
    for _ in range(3):
        teacher.step(s)
        s = advance(s)
    s.wheel_pos_w[:,0,2] = .30
    teacher.step(s)
    s = advance(s)
    s.wheel_pos_w[:,0,0] = .93
    assert teacher.step(s).phase.item() == t.Phase.RESTORE
    s.recovered[:,0,0] = True
    for _ in range(4):
        s = advance(s)
        assert teacher.step(s).active_wheel.item() == 0
    return teacher, s


@pytest.mark.parametrize('interruption', ['nan', 'geometry', 'invalid_action'])
def test_invalid_restore_sample_breaks_five_consecutive_measurements(interruption):
    t = api()
    teacher, s = restoring_teacher_with_four_stable_samples()
    broken = advance(s)
    if interruption == 'nan':
        velocity = s.root_lin_vel_w.clone()
        velocity[:,0] = float('nan')
        broken = replace(broken, root_lin_vel_w=velocity)
    elif interruption == 'geometry':
        broken = replace(broken, half_extents=torch.zeros_like(s.half_extents))
    else:
        defaults, q = s.default_joint_pos.clone(), s.leg_pos.clone()
        defaults[:,0] = q[:,0] = 3.  # finite but outside the real decoder limits
        broken = replace(broken, default_joint_pos=defaults, leg_pos=q)
    out = teacher.step(broken)
    assert not out.valid.item() and out.active_wheel.item() == 0
    assert torch.isfinite(out.action).all()
    s = replace(s, control_step=broken.control_step)
    for index in range(5):
        s = advance(s)
        out = teacher.step(s)
        assert out.active_wheel.item() == (0 if index < 4 else -1)


def test_control_step_gap_breaks_restore_continuity_but_duplicates_are_idempotent():
    teacher, s = restoring_teacher_with_four_stable_samples()
    cached = teacher.step(s)
    for _ in range(6):
        repeated = teacher.step(s)
        assert repeated.active_wheel.item() == 0
        assert torch.equal(repeated.action, cached.action)
    s = replace(s, control_step=s.control_step+2)
    for index in range(5):
        out = teacher.step(s)
        assert out.active_wheel.item() == (0 if index < 4 else -1)
        s = advance(s)


def test_balance_readiness_configuration_is_immutable_and_fingerprinted():
    t = api()
    cfg = t.TeacherConfig()
    assert cfg.balance_position_tolerance_m == .01
    assert cfg.balance_speed_limit_m_s == .05
    assert cfg.fingerprint != replace(cfg, balance_position_tolerance_m=.009).fingerprint
    assert cfg.fingerprint != replace(cfg, balance_speed_limit_m_s=.04).fingerprint


def test_native_run1_frame36_loads_do_not_mean_ready_to_lift():
    """Frozen run1 env0 gate measurements, not a replay of missing joint targets."""
    t = api()
    s = state()
    # Frame35 is the input that captured the BALANCE anchor for output36.
    root35 = torch.tensor([[-25.73345375,-151.99990845,.60408282]])
    wheels35 = torch.tensor([[[-25.43685150,-151.79243469,.09594408],
        [-25.43788338,-152.20722961,.09593624],[-26.13503838,-151.79258728,.09594838],
        [-26.13437080,-152.20735168,.09595184]]])
    s = replace(s, root_pos_w=root35, wheel_pos_w=wheels35,
        root_quat_w=torch.tensor([[.99996686,-.00150295,-.00799653,.00010485]]),
        centers_top=torch.tensor([[[-25.2,-151.785,.1]]]))
    teacher = t.ReferenceTeacher()
    assert teacher.step(s).phase.item() == t.Phase.BALANCE
    # Frame36 has three loaded supports but ~44/60mm full-shift error and
    # .2816m/s forward velocity, with -.0883m/s vertical velocity.
    s = advance(s, root_pos_w=torch.tensor([[-25.72787857,-151.99993896,.60254341]]),
        root_quat_w=torch.tensor([[.99995822,-.00184114,-.00894464,.00008591]]),
        root_lin_vel_w=torch.tensor([[.28163949,-.00257979,-.08829118]]),
        root_ang_vel_w=torch.tensor([[-.04886337,-.09620775,-.00726071]]),
        wheel_pos_w=torch.tensor([[[-25.43540001,-151.79244995,.09594582],
            [-25.43645096,-152.20726013,.09594304],[-26.13398743,-151.79260254,.09594283],
            [-26.13316345,-152.20733643,.09594650]]]),
        wheel_force_w=torch.tensor([[[0.,0.,116.10949],[0.,0.,93.83890],
            [0.,0.,92.53358],[0.,0.,75.00571]]]))
    out = teacher.step(s)
    assert out.phase.item() == t.Phase.BALANCE
    assert not out.action[:,t.WHEEL_COLUMNS].any()


@pytest.mark.parametrize('unready', ['position_x','position_y','position_norm','velocity_x','velocity_y',
    'velocity_z','velocity_norm','roll','pitch','roll_rate','pitch_rate','force_threshold','force_tangential'])
def test_balance_gate_requires_each_measured_component(unready):
    t = api()
    s = state()
    s.wheel_pos_w[:,0,0] = .39
    teacher = t.ReferenceTeacher()
    teacher.step(s)
    s = advance(measured_shift_ready(s))
    if unready.startswith('position_'):
        if unready == 'position_norm':
            s.root_pos_w[:,:2] += .008  # each <.01; XY norm >.01
        else:
            s.root_pos_w[:,0 if unready.endswith('x') else 1] += .011
    elif unready.startswith('velocity_'):
        if unready == 'velocity_norm':
            s.root_lin_vel_w[:] = .03  # each <.05; vector norm >.05
        else:
            s.root_lin_vel_w[:,{'velocity_x':0,'velocity_y':1,'velocity_z':2}[unready]] = .051
    elif unready in ('roll','pitch'):
        s.root_quat_w[:,0] = torch.cos(torch.tensor(.16/2))
        s.root_quat_w[:,1 if unready == 'roll' else 2] = torch.sin(torch.tensor(.16/2))
    elif unready == 'force_threshold':
        s.wheel_force_w[:,1,2] = 30.  # original support threshold stays strict >
    elif unready == 'force_tangential':
        s.wheel_force_w[:,1,0] = 61.
    else:
        s.root_ang_vel_w[:,0 if unready == 'roll_rate' else 1] = .201
    out = teacher.step(s)
    assert out.phase.item() == t.Phase.BALANCE


@pytest.mark.parametrize('unready', ['position', 'velocity'])
def test_balance_clock_cannot_replace_preparation_measurements(unready):
    t = api()
    s = state()
    s.wheel_pos_w[:,0,0] = .39
    teacher = t.ReferenceTeacher()
    teacher.step(s)
    if unready == 'velocity':
        s = measured_shift_ready(s)
        s.root_lin_vel_w[:,0] = .1
    for _ in range(35):
        s = advance(s)
        out = teacher.step(s)
    assert out.phase.item() == t.Phase.BALANCE


@pytest.mark.parametrize('wheel', range(4))
def test_ready_balance_gate_mirrors_all_wheels_and_is_not_minimum_dwell(wheel):
    t = api()
    s = state()
    s.required_wheels.zero_()
    s.required_wheels[:,0,wheel] = True
    s.wheel_pos_w[:,wheel,0] = .39
    teacher = t.ReferenceTeacher()
    assert teacher.step(s).phase.item() == t.Phase.BALANCE
    # Full measured offset already exists: the second call may enter LIFT.
    s = advance(measured_shift_ready(s,wheel))
    # The reference follows actual rolling; translation cannot erase readiness.
    s.root_pos_w[:,:2] += .3
    s.wheel_pos_w[:,:,:2] += .3
    s.centers_top[:,:,:2] += .3
    out = teacher.step(s)
    assert out.phase.item() == t.Phase.LIFT and out.active_wheel.item() == wheel
    repeated = teacher.step(s)
    assert torch.equal(repeated.action,out.action) and torch.equal(repeated.phase,out.phase)
