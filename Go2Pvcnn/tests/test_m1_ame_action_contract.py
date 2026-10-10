from types import SimpleNamespace

import torch

from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES, M1_WHEEL_RADIUS_M


def test_policy_action_history_excludes_wheel_columns():
    from ame_baseline.m1_ame_contract import m1_last_leg_action
    actions = torch.arange(16.).reshape(1, 16)
    env = SimpleNamespace(cfg=SimpleNamespace(asset_joint_names=M1_ASSET_JOINT_NAMES), action_manager=SimpleNamespace(action=actions))
    selected = m1_last_leg_action(env)
    assert selected.shape == (1, 12)
    assert selected.tolist()[0] == [float(M1_ASSET_JOINT_NAMES.index(n)) for n in M1_PLANNER_JOINT_NAMES]


def test_mixed_targets_keep_interleaved_order_and_allow_continuous_wheel_velocity():
    from ame_baseline.m1_ame_contract import m1_action_targets, M1_LEG_ACTION_SCALE_RAD
    default = torch.zeros(2, 16)
    actions = torch.zeros_like(default)
    wheel_ids = [M1_ASSET_JOINT_NAMES.index(n) for n in M1_WHEEL_JOINT_NAMES]
    actions[:, wheel_ids] = 1.
    actions[:, 1] = 0.4
    default[:, wheel_ids] = 1000.
    targets = m1_action_targets(actions, default)
    torch.testing.assert_close(targets[:, wheel_ids], torch.full((2, 4), 1. / M1_WHEEL_RADIUS_M))
    torch.testing.assert_close(targets[:, 1], torch.full((2,), 0.4 * M1_LEG_ACTION_SCALE_RAD))


def test_mixed_targets_clip_to_leg_limits_and_wheel_surface_speed_limit():
    from ame_baseline.m1_ame_contract import m1_action_targets
    from extension.parallelism.m1_kinematics import M1_ABAD_UPPER
    targets = m1_action_targets(torch.full((1, 16), 1e5), torch.zeros(1, 16))
    assert targets[0, 0] <= M1_ABAD_UPPER[0]
    assert targets[0, 3] <= 2. / M1_WHEEL_RADIUS_M + 1e-5


def test_training_stance_centers_the_wheels_under_the_four_hip_mounts():
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS, M1_TRAINING_ROOT_Z_M
    from extension.parallelism.m1_kinematics import m1_fk
    from extension.parallelism.rl_adapter import select_named_joint_state
    joints = select_named_joint_state(torch.tensor(M1_TRAINING_JOINT_POS)[None], source_names=M1_ASSET_JOINT_NAMES, selected_names=M1_PLANNER_JOINT_NAMES)
    geometry = m1_fk(torch.tensor([[0., 0., M1_TRAINING_ROOT_Z_M]]), torch.zeros(1, 3), joints)
    torch.testing.assert_close(geometry.foot_pos_w[0, :, 0], torch.tensor([.3295, .3295, -.3295, -.3295]))
    # Analytic tire radius differs from the source collision mesh by 0.21 mm.
    torch.testing.assert_close(geometry.foot_pos_w[0, :, 2], torch.full((4,), M1_WHEEL_RADIUS_M), atol=0.001, rtol=0.)


def test_training_stance_matches_approved_585mm_total_mesh_height():
    from ame_baseline.m1_ame_contract import M1_TRAINING_ROOT_Z_M
    # Independent BASE_LINK visual mesh upper bound from source USD audit.
    base_top_above_root = 0.128999188542366
    assert abs(M1_TRAINING_ROOT_Z_M + base_top_above_root - .585) < 1e-6
