import torch


def test_m1_leg_scale_allows_visible_lift():
    from ame_baseline.m1_ame_contract import M1_LEG_ACTION_SCALE_RAD

    assert M1_LEG_ACTION_SCALE_RAD >= 0.65


def test_crossing_collision_cannot_be_counted_as_success():
    from ame_baseline.m1_crossing_metrics import CrossingEpisodeAccumulator

    metrics = CrossingEpisodeAccumulator(1, "cpu")
    metrics.update(
        candidate=torch.tensor([True]),
        large_candidate=torch.tensor([False]),
        crossing_complete=torch.tensor([False]),
        done=torch.tensor([False]),
        terminated=torch.tensor([False]),
        collision=torch.tensor([True]),
        large_avoided=torch.tensor([False]),
    )
    metrics.update(
        candidate=torch.tensor([False]),
        large_candidate=torch.tensor([False]),
        crossing_complete=torch.tensor([True]),
        done=torch.tensor([True]),
        terminated=torch.tensor([False]),
        collision=torch.tensor([False]),
        large_avoided=torch.tensor([False]),
    )
    snapshot = metrics.snapshot()
    assert snapshot["crossing_collision_episodes"] == 1.0
    assert snapshot["crossing_episodes"] == 0.0
    assert snapshot["crossing_success_rate"] == 0.0


def test_m1_mpc_ik_uses_m1_leg_geometry():
    from extension.batch_mpc_planner.kinematics import solve_joint_angles_from_trajectory
    from extension.parallelism.m1_kinematics import m1_fk, M1_DEFAULT_JOINT_POS

    root = torch.tensor([[[0.0, 0.0, 0.55]]])
    rpy = torch.zeros_like(root)
    joints = torch.tensor(M1_DEFAULT_JOINT_POS).view(1, 1, 12)
    target = m1_fk(root, rpy, joints).foot_pos_w
    recovered = solve_joint_angles_from_trajectory(root, rpy, target, robot_name="m1")
    assert torch.allclose(recovered, joints, atol=2.0e-3)
