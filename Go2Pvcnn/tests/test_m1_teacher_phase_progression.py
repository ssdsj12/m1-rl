"""Regression tests for the first actionable M1 MPC teacher frame."""

from types import SimpleNamespace

import torch


def _cache_with_pending_single_leg():
    from extension.reference.cache import ReferenceTrajectoryCache

    batch, horizon = 1, 3
    root_pos = torch.zeros((batch, horizon, 3), dtype=torch.float32)
    root_quat = torch.zeros((batch, horizon, 4), dtype=torch.float32)
    root_quat[..., 0] = 1.0
    joint_angles = torch.zeros((batch, horizon, 12), dtype=torch.float32)
    joint_angles[0, 1, 2] = 0.30
    foot_pos_w = torch.zeros((batch, horizon, 4, 3), dtype=torch.float32)
    foot_pos_root = foot_pos_w.clone()
    contact_state = torch.ones((batch, horizon, 4), dtype=torch.bool)
    contact_state[0, 1, 0] = False
    planned_touchdown_w = foot_pos_w.clone()
    phase_index = torch.arange(horizon, dtype=torch.long).view(1, horizon)
    valid_mask = torch.ones((batch, horizon), dtype=torch.bool)
    return ReferenceTrajectoryCache(
        root_pos_w=root_pos,
        root_quat_w=root_quat,
        joint_angles=joint_angles,
        foot_pos_w=foot_pos_w,
        foot_pos_root=foot_pos_root,
        contact_state=contact_state,
        planned_touchdown_w=planned_touchdown_w,
        phase_index=phase_index,
        valid_mask=valid_mask,
    )


def test_m1_teacher_reference_skips_measured_frame_after_replan():
    """A replan must not expose measured frame 0 as the teacher target."""

    from extension.batch_mpc_planner.manager import MpcTrajectoryManager

    manager = MpcTrajectoryManager(SimpleNamespace(), device=torch.device("cpu"))
    manager._cache = _cache_with_pending_single_leg()
    manager._phase_counter = torch.zeros(1, dtype=torch.long)
    reference = manager.current_reference(frame_offset=1)

    assert manager.current_frame_ids().tolist() == [0]
    assert reference["phase_index"].tolist() == [1]
    assert not bool(reference["contact_state"][0, 0].item())
    assert float(reference["joint_angles"][0, 2].item()) > 0.0


def test_m1_teacher_adapter_emits_nonzero_action_for_pending_swing():
    """The M1 adapter must preserve a pending single-leg swing as an action."""

    from ame_baseline.m1_mpc_teacher import reference_to_m1_action

    reference = {
        "joint_angles": torch.zeros((1, 12), dtype=torch.float32),
        "contact_state": torch.tensor([[False, True, True, True]]),
        "phase_index": torch.tensor([1]),
        "valid_mask": torch.ones(1, dtype=torch.bool),
    }
    reference["joint_angles"][0, 2] = 0.30
    default = torch.zeros((1, 16), dtype=torch.float32)
    current = default.clone()
    action, valid = reference_to_m1_action(reference, default, current_joint_pos=current)

    assert bool(valid.item())
    assert float(action[0, 2].abs().item()) > 1.0e-4
    stance_cols = [0, 1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    assert torch.count_nonzero(action[0, stance_cols]) == 0


def test_m1_small_obstacle_plan_uses_single_leg_swing_and_clearance():
    """A semantic small obstacle must produce a one-leg-at-a-time M1 swing."""
    from extension.batch_mpc_planner.config import MpcPlannerCfg
    from extension.batch_mpc_planner.planner import plan_segment
    from extension.batch_mpc_planner.types import MpcPlannerTerrain, MpcRobotState
    from extension.parallelism.m1_kinematics import M1_DEFAULT_JOINT_POS, M1_ROOT_Z_M, M1_WHEEL_RADIUS_M, m1_fk

    root = torch.tensor([[0.0, 0.0, M1_ROOT_Z_M]], dtype=torch.float32)
    rpy = torch.zeros((1, 3), dtype=torch.float32)
    joints = torch.tensor(M1_DEFAULT_JOINT_POS, dtype=torch.float32).view(1, 12)
    feet = m1_fk(root, rpy, joints).foot_pos_w
    height = torch.zeros((1, 41, 41), dtype=torch.float32)
    semantic = torch.zeros((1, 41, 41), dtype=torch.long)
    xs = torch.linspace(-0.5, 0.5, 41)
    ys = torch.linspace(-0.5, 0.5, 41)
    yy, xx = torch.meshgrid(ys, xs, indexing='ij')
    obstacle = (xx >= 0.10) & (xx <= 0.16) & (yy.abs() <= 0.18)
    height[0, obstacle] = 0.05
    semantic[0, obstacle] = 1
    terrain = MpcPlannerTerrain(
        height_map=height, semantic_map=semantic,
        world_x_range=(-0.5, 0.5), world_y_range=(-0.5, 0.5),
        is_plane_terrain=torch.tensor([True]),
    )
    state = MpcRobotState(root_pos=root, root_rpy=rpy, foot_pos=feet, joint_angles=joints)
    cfg = MpcPlannerCfg()
    cfg.runtime.robot_name = 'm1'
    cfg.runtime.horizon_steps = 16
    cfg.runtime.optimize_steps = 0
    cfg.runtime.nominal_swing_height_m = 0.18
    cfg.runtime.foot_contact_offset_m = M1_WHEEL_RADIUS_M
    result = plan_segment(terrain, state, torch.tensor([[0.8, 0.0, 0.0]]), cfg=cfg)
    assert bool(result.feasible[0].item())
    swing = ~result.contact_state[0]
    assert int(swing.sum(dim=-1).max().item()) <= 1
    swing_z = result.foot_pos[0, :, :, 2][swing]
    assert swing_z.numel() > 0
    assert float(swing_z.max().item()) >= 0.05 + M1_WHEEL_RADIUS_M + 0.10


def test_m1_parametric_plan_preserves_the_real_root_height():
    """M1 planning must not use the Go2 0.32 m root-height constant."""

    from extension.batch_mpc_planner.config import MpcPlannerCfg
    from extension.batch_mpc_planner.planner import plan_segment
    from extension.batch_mpc_planner.types import MpcPlannerTerrain, MpcRobotState
    from extension.parallelism.m1_kinematics import M1_DEFAULT_JOINT_POS, M1_ROOT_Z_M, m1_fk

    root = torch.tensor([[0.0, 0.0, M1_ROOT_Z_M]], dtype=torch.float32)
    rpy = torch.zeros((1, 3), dtype=torch.float32)
    joints = torch.tensor(M1_DEFAULT_JOINT_POS, dtype=torch.float32).view(1, 12)
    feet = m1_fk(root, rpy, joints).foot_pos_w
    terrain = MpcPlannerTerrain(
        height_map=torch.zeros((1, 33, 33), dtype=torch.float32),
        semantic_map=torch.zeros((1, 33, 33), dtype=torch.long),
        world_x_range=(-0.75, 0.75),
        world_y_range=(-0.75, 0.75),
        is_plane_terrain=torch.tensor([True]),
    )
    state = MpcRobotState(root_pos=root, root_rpy=rpy, foot_pos=feet, joint_angles=joints)
    cfg = MpcPlannerCfg()
    cfg.runtime.robot_name = "m1"
    cfg.runtime.horizon_steps = 8
    cfg.runtime.optimize_steps = 0
    result = plan_segment(terrain, state, torch.tensor([[0.8, 0.0, 0.0]]), cfg=cfg)

    assert bool(result.feasible[0].item())
    assert not bool(result.safe_fallback[0].item())
    assert float(result.root_pos[0, 1:, 2].min().item()) >= float(M1_ROOT_Z_M) - 0.08


def test_m1_teacher_holds_nonselected_legs_at_nominal_action_zero():
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action
    from ame_baseline.m1_ame_contract import m1_action_targets
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    reference = {
        "joint_angles": torch.zeros((1, 12), dtype=torch.float32),
        "contact_state": torch.tensor([[False, True, True, True]]),
        "phase_index": torch.tensor([1]),
        "valid_mask": torch.ones(1, dtype=torch.bool),
    }
    reference["joint_angles"][0, 2] = 0.30
    default = torch.zeros((1, 16), dtype=torch.float32)
    current = default.clone()
    current[:, [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]] = 0.12
    action, valid = reference_to_m1_action(reference, default, current_joint_pos=current)
    decoded = m1_action_targets(action, default)
    assert bool(valid.item())
    # Zero action is not a hold command: the action decoder maps it to the
    # asset default pose.  Verify the physical contract after decoding.
    planner_cols = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
    stance_cols = planner_cols[3:]
    assert torch.allclose(decoded[0, stance_cols], current[0, stance_cols], atol=1e-5)
    assert not torch.allclose(decoded[0, planner_cols[2]], current[0, planner_cols[2]], atol=1e-5)


def test_m1_teacher_keeps_one_leg_for_the_full_phase_block():
    """A diagonal planner swing must not alternate legs every frame."""
    from ame_baseline.m1_mpc_teacher import reference_to_m1_action

    reference = {
        "joint_angles": torch.zeros((3, 12), dtype=torch.float32),
        "contact_state": torch.tensor(
            [[False, False, True, True],
             [False, False, True, True],
             [False, False, True, True]],
        ),
        # The production M1 teacher uses a 32-step serial phase. Check the
        # last frame of one phase and the first frame of the handoff.
        "phase_index": torch.tensor([1, 31, 32]),
        "valid_mask": torch.ones(3, dtype=torch.bool),
    }
    for row in range(3):
        reference["joint_angles"][row, 2] = 0.30
        reference["joint_angles"][row, 5] = 0.40
    default = torch.zeros((3, 16), dtype=torch.float32)
    current = default.clone()
    action, valid = reference_to_m1_action(reference, default, current_joint_pos=current)

    assert bool(valid.all().item())
    active = action[:, :12].reshape(3, 4, 3).abs().amax(dim=-1) > 1.0e-4
    assert active[0].tolist() == [True, False, False, False]
    assert active[1].tolist() == [True, False, False, False]
    assert int(active[2].sum().item()) == 1
    assert not bool(torch.equal(active[2], active[0]))


def test_m1_ten_cm_obstacle_reference_has_five_cm_wheel_clearance():
    from extension.batch_mpc_planner.config import MpcPlannerCfg
    from extension.batch_mpc_planner.planner import plan_segment
    from extension.batch_mpc_planner.types import MpcPlannerTerrain, MpcRobotState
    from extension.parallelism.m1_kinematics import M1_DEFAULT_JOINT_POS, M1_ROOT_Z_M, M1_WHEEL_RADIUS_M, m1_fk

    root = torch.tensor([[0.0, 0.0, M1_ROOT_Z_M]], dtype=torch.float32)
    rpy = torch.zeros((1, 3), dtype=torch.float32)
    joints = torch.tensor(M1_DEFAULT_JOINT_POS, dtype=torch.float32).view(1, 12)
    feet = m1_fk(root, rpy, joints).foot_pos_w
    height = torch.zeros((1, 61, 61), dtype=torch.float32)
    semantic = torch.zeros((1, 61, 61), dtype=torch.long)
    xs = torch.linspace(-0.75, 0.75, 61)
    ys = torch.linspace(-0.75, 0.75, 61)
    yy, xx = torch.meshgrid(ys, xs, indexing='ij')
    obstacle = (xx >= 0.10) & (xx <= 0.20) & (yy.abs() <= 0.18)
    height[0, obstacle] = 0.10
    semantic[0, obstacle] = 1
    terrain = MpcPlannerTerrain(
        height_map=height, semantic_map=semantic,
        world_x_range=(-0.75, 0.75), world_y_range=(-0.75, 0.75),
        is_plane_terrain=torch.tensor([True]),
    )
    state = MpcRobotState(root_pos=root, root_rpy=rpy, foot_pos=feet, joint_angles=joints)
    cfg = MpcPlannerCfg()
    cfg.runtime.robot_name = 'm1'
    cfg.runtime.horizon_steps = 20
    cfg.runtime.optimize_steps = 0
    cfg.runtime.nominal_swing_height_m = 0.30
    cfg.runtime.foot_contact_offset_m = M1_WHEEL_RADIUS_M
    result = plan_segment(terrain, state, torch.tensor([[0.8, 0.0, 0.0]]), cfg=cfg)
    swing = ~result.contact_state[0]
    swing_z = result.foot_pos[0, :, :, 2][swing]
    assert float(swing_z.max().item()) >= 0.10 + M1_WHEEL_RADIUS_M + 0.05
