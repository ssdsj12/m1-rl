import importlib.util
from pathlib import Path
import pytest
import torch
from extension.parallelism.m1_kinematics import m1_fk, m1_joint_limit_mask


def controller():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_load_transfer.py'
    assert path.exists(), 'bounded M1 load transfer missing'
    spec = importlib.util.spec_from_file_location('load_transfer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.transfer_target


def inputs():
    root = torch.tensor([[0., 0., .554]]).repeat(4, 1)
    rpy = torch.zeros_like(root)
    q = torch.tensor([[0., -.57, 1.10] * 4]).repeat(4, 1)
    return dict(entry_root=root, entry_rpy=rpy,
                anchor_w=m1_fk(root, rpy, q).foot_pos_w,
                support_w=m1_fk(root, rpy, q).foot_pos_w.clone(),
                live_root=root.clone(), live_com=root.clone(),
                selected_leg=torch.arange(4), previous_root=root.clone(),
                previous_joint=q.clone(), dt=.02)


def test_feasible_target_preserves_anchors_and_height_with_bounded_motion():
    args = inputs()
    result = controller()(**args)
    assert result['valid'].all(), result['reason']
    assert m1_joint_limit_mask(result['joint']).all()
    torch.testing.assert_close(result['root'][:, 2], args['entry_root'][:, 2])
    assert (torch.linalg.vector_norm(result['root'] - args['previous_root'], dim=-1) <= .000401).all()
    assert ((result['joint'] - args['previous_joint']).abs() <= .010001).all()
    torch.testing.assert_close(m1_fk(result['root'], args['entry_rpy'], result['joint']).foot_pos_w,
                               args['anchor_w'], atol=.002, rtol=0)
    assert (result['root'][:2, 0] < 0).all()
    assert (result['root'][2:, 0] > 0).all()


def test_soft_margin_outside_bound_uses_feasible_hard_margin():
    args = inputs()
    soft = controller()(**args)
    soft_distance = (soft['desired_root'][0] - args['entry_root'][0]).norm().item()
    bound = soft_distance - .005
    result = controller()(**args, max_root_shift=bound)
    assert result['valid'][0], result['reason']
    assert (result['desired_root'][0] - args['entry_root'][0]).norm() <= bound + 1e-6
    from scripts.m1_support_geometry import triangle_margin
    triangle = args['support_w'][0, [1, 2, 3], :2]
    predicted_com = args['live_com'][0, :2] + result['desired_root'][0, :2] - args['live_root'][0, :2]
    assert triangle_margin(predicted_com.tolist(), triangle.tolist()) >= .02 - 1e-6


def test_existing_command_tracking_offset_does_not_reverse_needed_correction():
    from extension.parallelism.m1_kinematics import m1_ik
    args = inputs()
    tri = args['support_w'][0, [1, 2, 3], :2]
    a, b = tri[1] - tri[0], tri[2] - tri[0]
    normal = torch.stack((-a[1], a[0])) * torch.sign(a[0]*b[1]-a[1]*b[0]) / a.norm()
    args['live_com'][0, :2] = (tri[0] + tri[1])*.5 + normal*.015
    # The commanded body is20mm ahead of the measured body along the needed
    # correction direction. The measured margin still needs at least5mm.
    args['previous_root'][0, :2] += normal*.02
    joint, reachable = m1_ik(args['previous_root'], args['entry_rpy'], args['anchor_w'])
    assert reachable.all()
    args['previous_joint'] = joint.reshape(4, 12)
    result = controller()(**args)
    assert result['valid'][0], result['reason']
    desired_increment = result['desired_root'][0, :2] - args['previous_root'][0, :2]
    assert (desired_increment * normal).sum() >= .005 - 1e-6


def force_ready_inputs():
    args = inputs()
    for row in range(4):
        legs = [i for i in range(4) if i != row]
        args['live_com'][row, :2] = args['support_w'][row, legs, :2].mean(0)
    return args


def test_post_lift_force_floor_continues_past_geometric_ready():
    import inspect
    fn = controller()
    assert 'total_weight' in inspect.signature(fn).parameters
    args = inputs()
    tri = args['support_w'][0, [1, 2, 3], :2]
    edge = tri[1] - tri[0]
    normal = torch.stack((-edge[1], edge[0]))
    normal *= torch.sign(torch.dot(tri[2]-tri[0], normal)) / normal.norm()
    args['live_com'][0, :2] = (tri[0]+tri[1])*.5 + normal*.021
    result = fn(**args, total_weight=torch.full((4,), 400.), max_root_shift=.08)
    assert result['valid'][0], result['reason']
    assert not result['post_lift_load_ready'][0]
    assert torch.dot(result['root'][0, :2]-args['previous_root'][0, :2], normal) > 0
    predicted = args['live_com'][0, :2] + result['desired_root'][0, :2]-args['previous_root'][0, :2]
    bary = torch.linalg.solve(torch.cat((tri.T, torch.ones(1, 3))),
                              torch.cat((predicted, torch.ones(1))))
    assert (bary * 400. >= 30.-1e-4).all()


def test_invalid_weight_rejected_without_poisoning_other_rows():
    import inspect
    fn = controller()
    assert 'total_weight' in inspect.signature(fn).parameters
    args = force_ready_inputs()
    result = fn(**args, total_weight=torch.tensor([float('nan'), 0., 80., 400.]))
    assert not result['valid'][:3].any()
    assert result['valid'][3]
    assert result['post_lift_load_ready'][3]


def test_support_reserve_does_not_relax_existing_bounds():
    args = inputs()
    result = controller()(**args, total_weight=torch.full((4,), 400.), support_floor=35., max_root_shift=.08)
    assert result['valid'].all(), result['reason']
    for row in range(4):
        tri = args['support_w'][row, [i for i in range(4) if i != row], :2]
        predicted = args['live_com'][row, :2] + result['desired_root'][row, :2]-args['previous_root'][row, :2]
        bary = torch.linalg.solve(torch.cat((tri.T, torch.ones(1, 3))), torch.cat((predicted, torch.ones(1))))
        assert (bary*400. >= 35.-1e-4).all()
    assert ((result['root']-args['previous_root']).norm(dim=-1) <= .000401).all()


def force_controller():
    import inspect
    fn = controller()
    assert 'wheel_force' in inspect.signature(fn).parameters, 'support-force feedback missing'
    return fn


def test_low_force_moves_toward_weak_support_even_with_geometric_margin():
    args = force_ready_inputs()
    force = torch.full((4, 4), 100.)
    force[0, 3] = 29.
    result = force_controller()(**args, wheel_force=force)
    assert result['valid'].all(), result['reason']
    direction = args['support_w'][0, 3, :2] - args['support_w'][0, [1, 2], :2].mean(0)
    assert ((result['root'][0, :2]-args['previous_root'][0, :2])*direction).sum() > 0
    torch.testing.assert_close(result['root'][1:], args['previous_root'][1:])


def test_force_feedback_cannot_claim_support_with_missing_or_lost_contact():
    args = force_ready_inputs()
    force = torch.full((4, 4), 100.)
    force[0, 3] = 0.
    force[1, 3] = float('nan')
    result = force_controller()(**args, wheel_force=force)
    assert not result['valid'][:2].any()
    assert result['valid'][2:].all()
    torch.testing.assert_close(result['joint'][:2], args['previous_joint'][:2])


def test_force_rebalance_preserves_total_load_and_minimum():
    args = force_ready_inputs()
    force = torch.full((4, 4), 100.)
    force[0, 3] = 20.
    result = force_controller()(**args, wheel_force=force)
    target = result['support_force_target']
    assert (target >= 30. - 1e-6).all()
    torch.testing.assert_close(target[0].sum(), force[0, [1, 2, 3]].sum())


def test_measured_reserve_acts_before_hard_thirty_newton_violation():
    args=force_ready_inputs()
    force=torch.full((4,4),100.)
    force[0,3]=33.
    result=force_controller()(**args,wheel_force=force,support_floor=35.)
    assert result['valid'].all(), result['reason']
    assert result['support_force_target'][0,-1]>=35.-1e-6
    assert (result['root'][0]-args['previous_root'][0]).norm()>0
    torch.testing.assert_close(result['support_force_target'][0].sum(),force[0,[1,2,3]].sum())


def test_measured_reserve_rejects_insufficient_total_for_requested_floor():
    args=force_ready_inputs()
    force=torch.full((4,4),34.)
    result=force_controller()(**args,wheel_force=force,support_floor=35.)
    assert (result['reason']==6).all()


@pytest.mark.parametrize('mode',['measured','hypothetical'])
def test_row_specific_reserve_matches_independent_scalar_calls(mode):
    args=force_ready_inputs()
    extra={'wheel_force':torch.full((4,4),33.)} if mode=='measured' else {'total_weight':torch.full((4,),400.)}
    if mode=='measured':extra['wheel_force'][:,1]=200.
    floors=torch.tensor([35.,35.,40.,40.])
    batch=controller()(**args,**extra,support_floor=floors,max_root_shift=.08)
    for row in range(4):
        one={k:(v[row:row+1] if torch.is_tensor(v) else v) for k,v in args.items()}
        result=controller()(**one,**{k:v[row:row+1] for k,v in extra.items()},
                            support_floor=float(floors[row]),max_root_shift=.08)
        torch.testing.assert_close(batch['root'][row:row+1],result['root'])
        torch.testing.assert_close(batch['reason'][row:row+1],result['reason'])


@pytest.mark.parametrize('floor',[torch.ones(4,1)*35.,torch.tensor([35.,35.,float('nan'),40.]),
                                 torch.tensor([35.,35.,29.,40.]),torch.tensor([35,35,40,40])])
def test_invalid_row_reserve_is_rejected(floor):
    with pytest.raises(ValueError,match='support_floor'):
        controller()(**inputs(),support_floor=floor)


def test_repeated_feedback_cannot_ratchet_height_or_exceed_entry_bound():
    args = inputs()
    entry = args['entry_root'].clone()
    for _ in range(180):
        result = controller()(**args)
        assert result['valid'].all()
        args['previous_root'] = result['root']
        args['previous_joint'] = result['joint']
        args['live_root'] = result['root']
        args['live_com'] = result['root']
    assert (torch.linalg.vector_norm(result['root'] - entry, dim=-1) <= .060001).all()
    torch.testing.assert_close(result['root'][:, 2], entry[:, 2])


@pytest.mark.parametrize('kind', ['nan', 'degenerate', 'outside_bound', 'unreachable'])
def test_infeasible_row_returns_previous_command_with_reason(kind):
    args = inputs()
    if kind == 'nan': args['live_com'][0, 0] = float('nan')
    if kind == 'degenerate': args['anchor_w'][0] = 0
    if kind == 'outside_bound': args['live_com'][0, 0] = 2
    if kind == 'unreachable': args['anchor_w'][0, :, 2] -= 2
    result = controller()(**args)
    assert not result['valid'][0]
    assert result['reason'][0] != 0
    torch.testing.assert_close(result['joint'][0], args['previous_joint'][0])
    torch.testing.assert_close(result['root'][0], args['previous_root'][0])
    assert result['valid'][1:].all()


def test_yaw_rotation_does_not_change_joint_solution():
    args = inputs()
    base = controller()(**args)
    rotation = torch.tensor([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
    for name in ('entry_root', 'live_root', 'live_com', 'previous_root', 'anchor_w', 'support_w'):
        args[name] = args[name] @ rotation.T
    args['entry_rpy'][:, 2] = torch.pi / 2
    rotated = controller()(**args)
    assert rotated['valid'].all()
    torch.testing.assert_close(base['joint'], rotated['joint'], atol=1e-5, rtol=0)


def test_bad_dt_rejected():
    args = inputs()
    args['dt'] = 0
    with pytest.raises(ValueError, match='dt'):
        controller()(**args)


def test_joint_jump_is_rejected_not_clipped_into_different_foot_target():
    args = inputs()
    args['previous_joint'][0, 1] += .1
    result = controller()(**args)
    assert result['reason'][0].item() == 5
    assert not result['valid'][0]
    torch.testing.assert_close(result['joint'][0], args['previous_joint'][0])


def test_converged_command_reaches_requested_geometric_margin():
    from scripts.m1_support_geometry import triangle_margin
    args = inputs()
    for _ in range(150):
        result = controller()(**args)
        assert result['valid'].all()
        args['previous_root'] = result['root']
        args['previous_joint'] = result['joint']
        args['live_root'] = result['root']
        args['live_com'] = result['root']
    for row in range(4):
        supports = [args['anchor_w'][row, leg, :2].tolist() for leg in range(4) if leg != row]
        assert triangle_margin(result['root'][row, :2].tolist(), supports) >= .019999


def test_use_nearest_feasible_shift_not_long_detour_toward_incenter():
    args = inputs()
    args['live_com'][0, 0] += .045
    result = controller()(**args)
    assert result['valid'][0], 'a feasible <=6cm projection must not be rejected due to an incenter detour'
    assert (result['desired_root'][0] - args['entry_root'][0]).norm() < .06


def test_explicit_diagnostic_speed_keeps_joint_slew_and_translation_bounds():
    args = inputs()
    result = controller()(**args, root_speed=.04)
    assert result['valid'].all()
    motion = (result['root'] - args['previous_root']).norm(dim=-1)
    assert (motion <= .000801).all()
    assert (motion > .0007).all()
    assert ((result['joint'] - args['previous_joint']).abs() <= .010001).all()


def test_satisfied_margin_does_not_recapture_measured_root_drift():
    args = inputs()
    for row in range(4):
        args['live_com'][row, :2] = args['anchor_w'][row, [leg for leg in range(4) if leg != row], :2].mean(0)
    args['live_root'][:, 0] += .01
    result = controller()(**args)
    assert result['valid'].all()
    torch.testing.assert_close(result['root'], args['previous_root'], atol=0, rtol=0)


def test_live_support_geometry_changes_projection_without_moving_ik_anchors():
    args = inputs()
    baseline = controller()(**args)
    anchor_before = args['anchor_w'].clone()
    support = anchor_before.clone()
    support[:, :, 0] += .01
    args['support_w'] = support
    result = controller()(**args)
    assert result['valid'].all()
    assert not torch.allclose(result['desired_root'], baseline['desired_root'])
    torch.testing.assert_close(args['anchor_w'], anchor_before, atol=0, rtol=0)
    torch.testing.assert_close(m1_fk(result['root'], args['entry_rpy'], result['joint']).foot_pos_w,
                               anchor_before, atol=.002, rtol=0)


def test_bad_live_support_data_cannot_fall_back_to_frozen_geometry():
    args = inputs()
    support = args['anchor_w'].clone()
    support[0, 1, 0] = float('nan')
    args['support_w'] = support
    result = controller()(**args)
    assert not result['valid'][0]
    assert result['valid'][1:].all()


def test_explicit_eight_cm_probe_bound_leaves_default_six_cm_unchanged():
    args = inputs()
    # Require >6cm even for the hard20mm fallback, not just the soft30mm target.
    args['live_com'][0, 0] += .085
    assert not controller()(**args)['valid'][0]
    result = controller()(**args, max_root_shift=.08)
    assert result['valid'][0]
    assert (result['desired_root'][0] - args['entry_root'][0]).norm() <= .08
    assert ((result['joint'] - args['previous_joint']).abs() <= .010001).all()


@pytest.mark.parametrize('bound', [0., -.01, .081, float('nan')])
def test_displacement_bound_cannot_be_disabled_or_unbounded(bound):
    with pytest.raises(ValueError, match='max_root_shift'):
        controller()(**inputs(), max_root_shift=bound)


def test_hold_at_hard_ready_margin_instead_of_chasing_soft_target():
    from scripts.m1_support_geometry import triangle_margin
    args = inputs()
    for row in range(4):
        tri = args['support_w'][row, [leg for leg in range(4) if leg != row], :2]
        a, b = tri[1]-tri[0], tri[2]-tri[0]
        sign = torch.sign(a[0]*b[1]-a[1]*b[0])
        inward = torch.stack((-a[1], a[0])) * sign / a.norm()
        point = (tri[0]+tri[1])*.5 + inward*.025
        assert triangle_margin(point.tolist(), tri.tolist()) == pytest.approx(.025, abs=1e-6)
        args['live_com'][row, :2] = point
    result = controller()(**args)
    assert result['valid'].all()
    torch.testing.assert_close(result['root'], args['previous_root'], atol=0, rtol=0)
