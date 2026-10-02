"""Real tensor/map contracts for M1's movement-coupled obstacle rewards."""
from types import SimpleNamespace
import math

import pytest
import torch

from extension.parallelism.types import ParallelismTerrain
from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M, M1_WHEEL_HORIZONTAL_ENVELOPE_M


def _case(batch=1, semantic=1):
    height = torch.full((batch, 121, 121), .1)
    terrain = ParallelismTerrain(
        height_w=height, semantic_id=torch.full_like(height, semantic, dtype=torch.long),
        valid_mask=torch.ones_like(height, dtype=torch.bool),
        origin_w=torch.tensor([[-1.2, -1.2, 0.]]).expand(batch, -1).clone(),
        yaw_w=torch.zeros(batch), resolution=.02,
    )
    wheels = torch.zeros(batch, 4, 3)
    wheels[..., 2] = .121
    return dict(
        command_xy_b=torch.tensor([[.5, 0.]]).expand(batch, -1).clone(),
        root_pos_w=torch.tensor([[0., 0., .55]]).expand(batch, -1).clone(),
        root_quat_w=torch.tensor([[1., 0., 0., 0.]]).expand(batch, -1).clone(),
        root_lin_vel_w=torch.tensor([[.25, 0., 0.]]).expand(batch, -1).clone(),
        root_ang_vel_w=torch.zeros(batch, 3), wheel_pos_w=wheels,
        wheel_lin_vel_w=torch.tensor([.25, 0., .1]).expand(batch, 4, -1).clone(),
        terrain=terrain,
    )


def _terms(case):
    from ame_baseline.m1_obstacle_rewards import wheel_obstacle_reward_terms
    return wheel_obstacle_reward_terms(**case)


def test_forward_progress_and_articulated_wheel_lift_have_bounded_signal():
    progress, climb = _terms(_case())
    torch.testing.assert_close(progress, torch.tensor([.5]))
    assert 0.0 < climb.item() < 0.25


@pytest.mark.parametrize('root_velocity,expected', [
    ((-.25, 0., 0.), -.5), ((0., .25, 0.), 0.),
    ((0., 0., 0.), 0.), ((.019, 0., 0.), 0.), ((.021, 0., 0.), .042),
])
def test_progress_is_actual_signed_command_projection_with_deadzone(root_velocity, expected):
    case = _case()
    case['root_lin_vel_w'][0] = torch.tensor(root_velocity)
    progress, climb = _terms(case)
    assert progress.item() == pytest.approx(expected)
    if expected <= 0:
        assert climb.item() == 0.


def test_zero_command_cannot_farm_moving_or_lifting():
    case = _case()
    case['command_xy_b'].zero_()
    assert all(value.item() == 0 for value in _terms(case))


def test_stopped_chassis_with_moving_lifting_wheels_has_no_reward():
    case = _case()
    case['root_lin_vel_w'].zero_()
    case['wheel_lin_vel_w'][:] = torch.tensor([2., 0., 3.])
    assert all(value.item() == 0 for value in _terms(case))


def test_spin_only_wheel_link_origin_does_not_move_or_earn_reward():
    case = _case()
    case['root_lin_vel_w'].zero_()
    case['wheel_lin_vel_w'].zero_()
    # Angular wheel speed is deliberately not an input to either term.
    assert all(value.item() == 0 for value in _terms(case))


def test_forward_chassis_without_forward_wheel_motion_cannot_earn_climb():
    case = _case()
    case['wheel_lin_vel_w'][..., 0] = 0.
    progress, climb = _terms(case)
    assert progress.item() == .5 and climb.item() == 0.


def test_global_yaw_rotation_preserves_both_rewards():
    case = _case()
    case['root_quat_w'][0] = torch.tensor([math.sqrt(.5), 0., 0., math.sqrt(.5)])
    case['root_lin_vel_w'][0] = torch.tensor([0., .25, 0.])
    case['wheel_lin_vel_w'][:] = torch.tensor([0., .25, .1])
    progress, climb = _terms(case)
    assert progress.item() == pytest.approx(.5)
    assert climb.item() > 0.0


def test_local_obstacle_patch_rotates_with_command_not_world_x():
    case = _case(semantic=0)
    terrain = case['terrain']
    far_cell = round((M1_WHEEL_HORIZONTAL_ENVELOPE_M + .30 + 1.2) / .02)
    terrain.semantic_id[0, 60, far_cell] = 1
    assert _terms(case)[0].item() == pytest.approx(.5)
    case['root_quat_w'][0] = torch.tensor([math.sqrt(.5), 0., 0., math.sqrt(.5)])
    case['root_lin_vel_w'][0] = torch.tensor([0., .25, 0.])
    case['wheel_lin_vel_w'][:] = torch.tensor([0., .25, .1])
    assert all(value.item() == 0 for value in _terms(case))
    terrain.semantic_id.zero_()
    terrain.semantic_id[0, far_cell, 60] = 1
    assert _terms(case)[0].item() == pytest.approx(.5)


@pytest.mark.parametrize('motion', ['heave', 'pitch', 'root_falls'])
def test_rigid_body_motion_and_falling_chassis_do_not_earn_lift(motion):
    case = _case()
    if motion == 'heave':
        case['root_lin_vel_w'][0, 2] = .1
    elif motion == 'pitch':
        case['wheel_pos_w'][..., 0] = .4
        case['root_ang_vel_w'][0, 1] = -.25
        offset = case['wheel_pos_w'] - case['root_pos_w'][:, None]
        case['wheel_lin_vel_w'] = case['root_lin_vel_w'][:, None] + torch.linalg.cross(
            case['root_ang_vel_w'][:, None].expand_as(offset), offset,
        )
    else:
        case['root_lin_vel_w'][0, 2] = -.2
        case['wheel_lin_vel_w'][..., 2] = -.1
    progress, climb = _terms(case)
    assert progress.item() > 0 and climb.item() == pytest.approx(0., abs=1e-7)


def test_climb_does_not_stop_above_target_and_averages_over_all_four_wheels():
    case = _case()
    case['wheel_pos_w'][0, :2, 2] = .1 + M1_WHEEL_RADIUS_M + .021
    _, climb = _terms(case)
    # Positive articulated lift remains rewarded even when the wheel is
    # already above the nominal clearance band; the policy must be encouraged
    # to lift over an obstacle instead of being capped by height.
    assert climb.item() > 0.0


def test_success_clearance_is_separate_from_low_lift_reward():
    from ame_baseline.m1_obstacle_rewards import wheel_obstacle_reward_terms
    case = _case()
    case['wheel_pos_w'][..., 2] = .115
    progress, climb, clearance = wheel_obstacle_reward_terms(**case, return_clearance=True)
    assert climb.item() > 0.0
    assert not bool(clearance.item())
    case['wheel_pos_w'][..., 2] = .251
    _, climb, clearance = wheel_obstacle_reward_terms(**case, return_clearance=True)
    assert climb.item() > 0.0
    assert bool(clearance.item())


def test_climb_reward_requires_two_cm_clearance_above_obstacle_top():
    from ame_baseline.m1_obstacle_rewards import wheel_obstacle_reward_terms
    case = _case()
    case['wheel_pos_w'][..., 2] = .119
    _, climb_below = wheel_obstacle_reward_terms(**case)
    assert climb_below.item() > 0.0
    case['wheel_pos_w'][..., 2] = .121
    _, climb_above = wheel_obstacle_reward_terms(**case)
    assert climb_above.item() > 0.0
    case['wheel_pos_w'][..., 2] = 0.26
    _, _, clearance = wheel_obstacle_reward_terms(**case, return_clearance=True)
    assert bool(clearance.item())


@pytest.mark.parametrize('semantic', [0, 2])
def test_flat_and_large_obstacles_do_not_enable_small_obstacle_rewards(semantic):
    assert all(value.item() == 0 for value in _terms(_case(semantic=semantic)))


def test_large_obstacle_in_any_patch_vetoes_mixed_small_large_rewards():
    case = _case()
    case['terrain'].semantic_id[0, 60, 60] = 2
    assert all(value.item() == 0 for value in _terms(case))


@pytest.mark.parametrize('problem', ['invalid', 'out_of_bounds', 'nan_height', 'nan_velocity', 'inverted'])
def test_invalid_or_unsafe_state_never_produces_new_reward(problem):
    case = _case()
    if problem == 'invalid':
        case['terrain'].valid_mask.zero_()
    elif problem == 'out_of_bounds':
        case['wheel_pos_w'][..., 0] = 5.
    elif problem == 'nan_height':
        case['terrain'].height_w.fill_(float('nan'))
    elif problem == 'nan_velocity':
        case['root_lin_vel_w'][0, 0] = float('nan')
    else:
        case['root_quat_w'][0] = torch.tensor([0., 1., 0., 0.])
    terms = _terms(case)
    assert all(torch.isfinite(value).all() and value.item() == 0 for value in terms)


def test_batch_semantic_and_motion_are_independent():
    case = _case(batch=3)
    case['terrain'].semantic_id[1] = 2
    case['root_lin_vel_w'][2, 0] = -.25
    progress, climb = _terms(case)
    torch.testing.assert_close(progress, torch.tensor([.5, 0., -.5]))
    assert climb[0].item() > 0.0
    assert climb[1:].tolist() == [0.0, 0.0]


def test_wrapper_selects_named_link_state_independent_of_body_order():
    from ame_baseline import m1_obstacle_rewards as module
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    case = _case()
    names = [M1_SUPPORT_BODY_NAMES[2], 'BASE_LINK', M1_SUPPORT_BODY_NAMES[0],
             'EXTRA_LINK', M1_SUPPORT_BODY_NAMES[3], M1_SUPPORT_BODY_NAMES[1]]
    body_positions = torch.full((1, len(names), 3), 999.)
    body_velocities = torch.full((1, len(names), 3), 999.)
    for index, name in enumerate(M1_SUPPORT_BODY_NAMES):
        body_positions[:, names.index(name)] = torch.tensor([.02 * index, 0., .121])
        body_velocities[:, names.index(name)] = torch.tensor([.1 * (index + 1), 0., .05 * (index + 1)])
    data = SimpleNamespace(
        root_pos_w=case['root_pos_w'], root_quat_w=case['root_quat_w'],
        root_link_lin_vel_w=case['root_lin_vel_w'], root_ang_vel_w=case['root_ang_vel_w'],
        body_link_pos_w=body_positions,
        body_link_lin_vel_w=body_velocities,
    )
    terrain = case['terrain']
    axis = torch.arange(121) * .02 - 1.2
    yy, xx = torch.meshgrid(axis, axis, indexing='ij')
    hits = torch.stack((xx, yy, torch.full_like(xx, .1)), -1).reshape(1, -1, 3)
    scanner = SimpleNamespace(cfg=SimpleNamespace(pattern_cfg=SimpleNamespace(resolution=.02)),
        data=SimpleNamespace(ray_hits_w=hits, semantic_map=terrain.semantic_id, valid_mask=terrain.valid_mask))
    env = SimpleNamespace(scene={'robot': SimpleNamespace(data=data, body_names=names),
        'semantic_height_scanner': scanner}, command_manager=SimpleNamespace(
            get_command=lambda name: torch.tensor([[.5, 0., 0.]])))
    assert module.m1_small_obstacle_progress(env).item() == pytest.approx(.5)
    assert module.m1_small_obstacle_climb(env).item() > 0.0


def test_forward_probe_does_not_fabricate_wheel_clearance():
    """A corridor-only detection must not mark an unlifted wheel as clear."""
    from ame_baseline.m1_obstacle_rewards import wheel_obstacle_reward_terms
    case = _case(semantic=0)
    # Probe corridor sees a small block at (0.30, 0.45), but no wheel-local
    # patch contains it. This is intentionally outside the wheel envelope.
    ix = round((0.30 + 1.2) / 0.02)
    iy = round((0.45 + 1.2) / 0.02)
    case['terrain'].semantic_id[0, iy, ix] = 1
    _, climb, clearance = wheel_obstacle_reward_terms(**case, return_clearance=True)
    assert climb.item() == pytest.approx(0.0)
    assert not bool(clearance.item())
