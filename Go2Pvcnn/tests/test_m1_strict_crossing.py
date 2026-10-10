from pathlib import Path
import importlib.util

import pytest
import torch


def strict_tracker_type():
    path = Path(__file__).parents[1] / "ame_baseline" / "m1_strict_crossing.py"
    assert path.exists(), "per-obstacle strict crossing tracker missing"
    spec = importlib.util.spec_from_file_location("m1_strict_crossing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.StrictCrossingTracker


def scene_inputs(num_envs=1):
    # Course has six small blocks at x=0.55 + 0.55*i, alternating wheel lanes.
    centers = torch.tensor(
        [[0.55 + 0.55 * i, 0.215 if i % 2 == 0 else -0.215, 0.10] for i in range(6)],
        dtype=torch.float32,
    ).unsqueeze(0).repeat(num_envs, 1, 1)
    wheels = torch.tensor(
        [[0.30, 0.215, 0.096], [0.28, -0.215, 0.096],
         [-0.20, 0.215, 0.096], [-0.22, -0.215, 0.096]],
        dtype=torch.float32,
    ).unsqueeze(0).repeat(num_envs, 1, 1)
    return wheels, centers


def update(tracker, wheels, centers, *, support=True, collision=False,
           touchdown_safe=True):
    return tracker.update(
        wheel_pos_w=wheels,
        obstacle_centers_top_w=centers,
        support_safe=torch.full((wheels.shape[0],), support, dtype=torch.bool),
        touchdown_safe=torch.full((wheels.shape[0],), touchdown_safe, dtype=torch.bool),
        collision=torch.full((wheels.shape[0],), collision, dtype=torch.bool),
        wheel_horizontal_radius=0.119208,
        wheel_lateral_half_width=0.02325,
        wheel_vertical_radius=0.095958,
        obstacle_half_extents=(0.025, 0.025),
        required_clearance=0.05,
        required_far_margin=0.04,
        stable_frames=5,
    )


def test_wheel_radius_does_not_make_a_different_lateral_lane_a_crossing_attempt():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()
    # This is the measured false-positive geometry from the PhysX probe:
    # lateral center offset is 14.4 cm, while the wheel is only 4.65 cm wide.
    # Its rolling radius must not be reused as its lateral footprint.
    wheels[0, 0, 1] = centers[0, 0, 1] + 0.144

    result = update(tracker, wheels, centers)

    assert not result["attempt_started"].any()
    assert tracker.target_wheel.tolist() == [-1]


def test_lateral_footprint_uses_world_projection_of_the_oriented_wheel_cylinder():
    path = Path(__file__).parents[1] / "ame_baseline" / "m1_strict_crossing.py"
    spec = importlib.util.spec_from_file_location("m1_strict_crossing_projection", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = getattr(module, "m1_wheel_lateral_half_width_from_quat", None)
    assert callable(project), "strict crossing must use the wheel's oriented physical footprint"

    identity = torch.tensor([1.0, 0.0, 0.0, 0.0]).view(1, 1, 4).expand(1, 4, 4)
    quarter_roll = torch.tensor([2.0 ** -0.5, 2.0 ** -0.5, 0.0, 0.0]).view(1, 1, 4).expand(1, 4, 4)
    upright = project(identity, wheel_radius=0.095958, wheel_thickness=0.04650)
    rolled = project(quarter_roll, wheel_radius=0.095958, wheel_thickness=0.04650)

    assert upright.shape == (1, 4)
    assert torch.allclose(upright, torch.full((1, 4), 0.02325), atol=1e-6)
    assert torch.allclose(rolled, torch.full((1, 4), 0.095958), atol=1e-6)


def test_latched_wheel_that_drifts_out_of_lane_cannot_complete_crossing():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()
    result = update(tracker, wheels, centers)
    assert result["target_wheel"].tolist() == [0]

    # It clears the top while genuinely over the box, then leaves the physical
    # wheel-width lane before its far-side touchdown. A radial envelope must
    # not let the event complete after that lateral escape.
    wheels[0, 0, 0] = centers[0, 0, 0]
    wheels[0, 0, 1] = centers[0, 0, 1]
    wheels[0, 0, 2] = centers[0, 0, 2] + 0.095958 + 0.051
    update(tracker, wheels, centers)
    wheels[0, 0, 0] = 0.55 + 0.025 + 0.119208 + 0.041
    wheels[0, 0, 1] = centers[0, 0, 1] + 0.144
    wheels[0, 0, 2] = centers[0, 0, 2] + 0.095958
    result = update(tracker, wheels, centers, touchdown_safe=True)

    assert not result["event_complete"].any()
    assert tracker.crossing_count.tolist() == [0]


def test_strict_collision_gate_includes_non_support_obstacle_contact_reward():
    path = Path(__file__).parents[1] / "ame_baseline" / "m1_strict_crossing.py"
    spec = importlib.util.spec_from_file_location("m1_strict_crossing_collision", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gate = getattr(module, "strict_collision_from_reward_terms", None)
    assert callable(gate), "strict success must include obstacle scrape/contact events"

    reward = torch.tensor([[0.0, -8.0], [-10.0, 0.0], [0.0, 0.0]])
    collision = gate(
        reward,
        ("parallelism_geometry_collision", "non_support_obstacle_contact"),
    )

    assert collision.tolist() == [True, True, False]


def test_strict_success_requires_same_wheel_clearance_then_far_edge_and_stable_touchdown():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()

    # Scan disappearance / support contact alone cannot count.
    for _ in range(8):
        result = update(tracker, wheels, centers)
    assert not result["event_complete"].any()
    assert not result["episode_complete"].any()

    # First (front-right lane) target wheel clears the top by 5 cm while its
    # envelope is still over the box, then passes the far edge.
    wheels[0, 0, 0] = 0.42
    wheels[0, 0, 2] = 0.10 + 0.095958 + 0.051
    result = update(tracker, wheels, centers)
    assert result["clearance_latched"].tolist() == [True]
    assert not result["event_complete"].any()

    wheels[0, 0, 0] = 0.55 + 0.025 + 0.119208 + 0.041
    wheels[0, 0, 2] = 0.10 + 0.095958
    # Merely clearing the far edge is not complete until a safe touchdown.
    result = update(tracker, wheels, centers, touchdown_safe=False)
    assert not result["event_complete"].any()
    assert not result["episode_complete"].any()
    assert not tracker.awaiting_recovery.any()
    result = update(tracker, wheels, centers, touchdown_safe=True)
    assert result["event_complete"].tolist() == [True]
    assert result["crossing_count"].tolist() == [1]
    assert result["progress"].tolist() == [0]
    assert not result["episode_complete"].any()
    for _ in range(4):
        result = update(tracker, wheels, centers)
        assert not result["recovery_complete"].any()
    result = update(tracker, wheels, centers)
    assert result["recovery_complete"].tolist() == [True]
    assert result["progress"].tolist() == [1]


def test_geometric_crossing_is_recorded_before_balance_recovery():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()

    wheels[0, 0, 0] = 0.42
    wheels[0, 0, 2] = 0.10 + 0.095958 + 0.051
    update(tracker, wheels, centers)
    wheels[0, 0, 0] = 0.55 + 0.025 + 0.119208 + 0.041
    wheels[0, 0, 2] = 0.10 + 0.095958

    # Geometric crossing is already true, even before the robot has recovered
    # its nominal balance. A safe four-wheel landing is the crossing gate;
    # nominal-pose recovery is a separate post-crossing result.
    result = update(tracker, wheels, centers, support=False, touchdown_safe=True)
    assert result["event_complete"].tolist() == [True]
    assert result["crossing_count"].tolist() == [1]
    assert result["recovery_complete"].tolist() == [False]
    assert result["progress"].tolist() == [0]

    for _ in range(4):
        result = update(tracker, wheels, centers, support=True)
        assert not result["recovery_complete"].any()
    result = update(tracker, wheels, centers, support=True)
    assert result["recovery_complete"].tolist() == [True]
    assert result["recovery_frames"].tolist() == [5]
    assert result["progress"].tolist() == [1]


def test_crossing_touchdown_gate_does_not_require_balance_recovery_pose():
    path = Path(__file__).parents[1] / "ame_baseline" / "m1_crossing_landing.py"
    assert path.exists(), "crossing touchdown and balance recovery gates must be separate"
    spec = importlib.util.spec_from_file_location("m1_crossing_landing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    contacts = torch.ones((1, 4), dtype=torch.bool)
    forces = torch.tensor([[40.0, 42.0, 39.0, 11.0]])
    target = torch.tensor([3])
    # Tilt and nominal-joint-pose recovery are intentionally not inputs to the
    # crossing gate: after far-side loaded touchdown, restore them in RECOVER.
    assert module.crossing_touchdown_safe(
        support_contact=contacts,
        support_force=forces,
        target_wheel=target,
    ).tolist() == [True]

    forces[0, 3] = 9.0
    assert module.crossing_touchdown_safe(
        support_contact=contacts,
        support_force=forces,
        target_wheel=target,
    ).tolist() == [False]


def test_crossing_touchdown_gate_rejects_missing_support_contact():
    path = Path(__file__).parents[1] / "ame_baseline" / "m1_crossing_landing.py"
    spec = importlib.util.spec_from_file_location("m1_crossing_landing_contacts", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    contacts = torch.tensor([[True, True, False, True]])
    forces = torch.tensor([[40.0, 42.0, 39.0, 11.0]])
    assert not module.crossing_touchdown_safe(
        support_contact=contacts, support_force=forces,
        target_wheel=torch.tensor([3]),
    ).any()


def test_crossing_landing_and_balance_recovery_gates_are_independent():
    path = Path(__file__).parents[1] / "ame_baseline" / "m1_crossing_landing.py"
    spec = importlib.util.spec_from_file_location("m1_crossing_landing_split", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    crossing, recovery = module.split_crossing_and_recovery_gates(
        touchdown_safe=torch.tensor([True, True, False, True]),
        balance_recovered=torch.tensor([False, True, True, True]),
        nominal_pose_ready=torch.tensor([False, False, True, True]),
        root_height_ready=torch.tensor([False, False, True, True]),
    )

    # A safe far-side four-wheel landing counts as crossing even when the
    # body is still tilted or the joints have not returned to nominal.
    assert crossing.tolist() == [True, True, False, True]
    assert recovery.tolist() == [False, False, False, True]


def test_crossing_counts_before_height_recovery_but_recovery_rejects_collapsed_body():
    path = Path(__file__).parents[1] / "ame_baseline" / "m1_crossing_landing.py"
    spec = importlib.util.spec_from_file_location("m1_crossing_landing_height", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    crossing, recovery = module.split_crossing_and_recovery_gates(
        touchdown_safe=torch.tensor([True, True]),
        balance_recovered=torch.tensor([True, True]),
        nominal_pose_ready=torch.tensor([True, True]),
        root_height_ready=torch.tensor([False, True]),
    )

    assert crossing.tolist() == [True, True]
    assert recovery.tolist() == [False, True]


def test_recovery_root_height_gate_uses_reset_height_and_rejects_nonfinite_state():
    path = Path(__file__).parents[1] / "ame_baseline" / "m1_crossing_landing.py"
    spec = importlib.util.spec_from_file_location("m1_crossing_landing_height_fn", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ready = module.m1_recovery_root_height_ready(
        root_z_w=torch.tensor([0.342, 0.490, 0.554, float("nan")]),
        nominal_root_z_w=torch.tensor([0.554, 0.554, 0.554, 0.554]),
        tolerance_m=0.08,
    )

    assert ready.tolist() == [False, True, True, False]


def test_recovery_diagnostic_failure_cannot_clear_safe_crossing_touchdown():
    source = (Path(__file__).parents[1] / "ame_baseline" / "ame_env_wrapper.py").read_text()
    start = source.index("# A valid loaded touchdown is the crossing result.")
    end = source.index("strict_result = {", start)
    gate_block = source[start:end]

    touchdown_split = gate_block.index("strict_crossing_touchdown = touchdown_safe.clone()")
    recovery_pose = gate_block.index("recovery_pose_ready = m1_recovery_pose_ready(")
    recovery_except = gate_block.rindex("except Exception as exc:")
    recovery_failure = gate_block[recovery_except:]

    assert touchdown_split < recovery_pose < recovery_except
    assert "strict_crossing_touchdown = torch.zeros_like(done)" not in recovery_failure


def test_runtime_strict_tracker_receives_landing_gate_before_balance_recovery():
    source = (Path(__file__).parents[1] / "ame_baseline" / "ame_env_wrapper.py").read_text()
    assert "split_crossing_and_recovery_gates(" in source
    assert "support_safe=recovery_balance_safe" in source
    assert "touchdown_safe=strict_crossing_touchdown" in source
    assert "strict_touchdown = recovery_balance_safe.clone()" not in source
def test_touchdown_back_on_obstacle_after_far_edge_does_not_count_as_crossing():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()
    wheels[0, 0, 0] = 0.42
    wheels[0, 0, 2] = 0.10 + 0.095958 + 0.051
    update(tracker, wheels, centers)

    # The wheel crosses the far edge while still airborne, then retreats over
    # the obstacle and lands there. Historical far-edge evidence must not turn
    # this into a completed crossing.
    wheels[0, 0, 0] = 0.55 + 0.025 + 0.119208 + 0.041
    result = update(tracker, wheels, centers, touchdown_safe=False)
    assert not result["event_complete"].any()
    wheels[0, 0, 0] = centers[0, 0, 0]
    wheels[0, 0, 2] = centers[0, 0, 2] - 0.10 + 0.095958
    result = update(tracker, wheels, centers, touchdown_safe=True)
    assert not result["event_complete"].any()
    assert result["crossing_count"].tolist() == [0]
    assert not tracker.awaiting_recovery.any()


def test_clearance_from_other_lane_or_other_wheel_cannot_complete_target_event():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()
    # Wrong-side wheel lifts, then target wheel merely coasts beyond the box.
    wheels[0, 0, 0] = 0.42
    wheels[0, 1, 2] = 0.30
    result = update(tracker, wheels, centers)
    assert not result["clearance_latched"].any()
    wheels[0, 0, 0] = 0.55 + 0.025 + 0.119208 + 0.041
    wheels[0, 0, 2] = 0.10 + 0.095958
    for _ in range(8):
        result = update(tracker, wheels, centers)
    assert not result["event_complete"].any()


def test_collision_latches_failure_and_breaks_stability_sequence():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()
    wheels[0, 0, 0] = 0.42
    wheels[0, 0, 2] = 0.10 + 0.095958 + 0.051
    update(tracker, wheels, centers)
    wheels[0, 0, 0] = 0.55 + 0.025 + 0.119208 + 0.041
    wheels[0, 0, 2] = 0.10 + 0.095958
    update(tracker, wheels, centers, collision=True)
    for _ in range(10):
        result = update(tracker, wheels, centers)
    assert result["failed"].tolist() == [True]
    assert not result["event_complete"].any()


def test_attempt_is_recorded_when_approach_and_collision_happen_same_frame():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()
    result = update(tracker, wheels, centers, collision=True)
    assert result["attempt_started"].tolist() == [True]
    assert result["failed"].tolist() == [True]
    assert result["target_wheel"].tolist() == [0]
    assert not result["event_complete"].any()


def test_landing_must_remain_support_safe_for_consecutive_frames():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()
    wheels[0, 0, 0] = 0.42
    wheels[0, 0, 2] = 0.10 + 0.095958 + 0.051
    update(tracker, wheels, centers)
    wheels[0, 0, 0] = 0.55 + 0.025 + 0.119208 + 0.041
    wheels[0, 0, 2] = 0.10 + 0.095958
    result = update(tracker, wheels, centers, support=False, touchdown_safe=True)
    assert result["event_complete"].tolist() == [True]
    assert not result["recovery_complete"].any()
    assert result["crossing_count"].tolist() == [1]
    for _ in range(4):
        result = update(tracker, wheels, centers, support=True)
        assert not result["recovery_complete"].any()
    result = update(tracker, wheels, centers, support=False)
    assert not result["recovery_complete"].any()
    result = update(tracker, wheels, centers, support=True)
    assert result["recovery_complete"].tolist() == [False]
    result = update(tracker, wheels, centers, support=True)
    assert result["recovery_complete"].tolist() == [False]
    result = update(tracker, wheels, centers, support=True)
    assert result["recovery_complete"].tolist() == [False]
    result = update(tracker, wheels, centers, support=True)
    assert result["recovery_complete"].tolist() == [False]
    result = update(tracker, wheels, centers, support=True)
    assert result["recovery_complete"].tolist() == [True]
    assert result["recovery_frames"].tolist() == [10]


def test_multi_environment_progress_is_independent_and_reset_is_row_scoped():
    Tracker = strict_tracker_type()
    tracker = Tracker(2, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs(2)
    wheels[0, 0, 0] = 0.42
    wheels[0, 0, 2] = 0.10 + 0.095958 + 0.051
    update(tracker, wheels, centers)
    wheels[0, 0, 0] = 0.55 + 0.025 + 0.119208 + 0.041
    wheels[0, 0, 2] = 0.10 + 0.095958
    for _ in range(6):
        result = update(tracker, wheels, centers, touchdown_safe=True)
    assert result["progress"].tolist() == [1, 0]
    tracker.reset(torch.tensor([True, False]))
    assert tracker.progress.tolist() == [0, 0]
    assert tracker.failed.tolist() == [False, False]


def test_episode_success_is_not_emitted_until_all_six_ordered_obstacles_are_crossed():
    Tracker = strict_tracker_type()
    tracker = Tracker(1, "cpu", obstacle_count=6)
    wheels, centers = scene_inputs()
    saw_episode_success = False
    for obstacle_index in range(6):
        center = centers[0, obstacle_index]
        target_wheel = 0 if center[1] > 0 else 1
        wheels[0, target_wheel] = torch.tensor([center[0] - 0.16, center[1], 0.096])
        update(tracker, wheels, centers)  # latch this obstacle's single wheel
        wheels[0, target_wheel, 0] = center[0]
        wheels[0, target_wheel, 2] = center[2] + 0.095958 + 0.051
        update(tracker, wheels, centers)  # measured clearance while over box
        wheels[0, target_wheel, 0] = center[0] + 0.025 + 0.119208 + 0.041
        wheels[0, target_wheel, 2] = center[2] - 0.10 + 0.095958
        for _ in range(6):
            result = update(tracker, wheels, centers)
        assert result["progress"].item() == obstacle_index + 1
        assert result["episode_complete"].item() == (obstacle_index == 5)
        saw_episode_success |= bool(result["episode_complete"].item())
    assert saw_episode_success
