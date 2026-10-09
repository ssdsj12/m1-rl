import importlib.util
from pathlib import Path

import numpy as np
import pytest


def swing_module():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_wbc_swing.py'
    assert path.exists(), 'time-parameterized single-wheel crossing reference is missing'
    spec = importlib.util.spec_from_file_location('m1_wbc_swing', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_single_wheel_swing_clears_obstacle_with_wheel_envelope():
    reference = swing_module().single_wheel_swing_reference(
        start=np.array([0.0, 0.1, 0.12]),
        landing=np.array([0.80, 0.1, 0.12]),
        progress=0.5,
        duration=3.0,
        obstacle_front_x=0.35,
        obstacle_far_x=0.48,
        obstacle_top_z=0.10,
        wheel_radius=0.08,
        clearance=0.05,
        approach_distance=0.25,
        exit_distance=0.20,
    )

    assert reference['position'][2] - 0.08 >= 0.10 + 0.05 - 1e-12
    np.testing.assert_allclose(reference['position'][:2], [0.40, 0.1], atol=1e-12)
    assert reference['phase'] == 'SWING'


def test_single_wheel_swing_starts_and_lands_at_requested_points_at_rest():
    module = swing_module()
    start = np.array([0.0, -0.12, 0.11])
    landing = np.array([0.80, -0.12, 0.11])
    for progress, expected, phase in ((0.0, start, 'LIFT_OFF'), (1.0, landing, 'TOUCHDOWN')):
        result = module.single_wheel_swing_reference(
            start=start, landing=landing, progress=progress, duration=3.0,
            obstacle_front_x=0.35, obstacle_far_x=0.48,
            obstacle_top_z=0.16, wheel_radius=0.08, clearance=0.05,
            approach_distance=0.25, exit_distance=0.20)
        np.testing.assert_allclose(result['position'], expected, atol=1e-12)
        np.testing.assert_allclose(result['velocity'], np.zeros(3), atol=1e-12)
        if progress == 0.0:
            np.testing.assert_allclose(result['acceleration'], np.zeros(3), atol=1e-12)
        else:
            np.testing.assert_allclose(result['acceleration'], np.zeros(3), atol=1e-12)
        assert result['phase'] == phase

    approach = module.single_wheel_swing_reference(
        start=start, landing=landing, progress=0.20, duration=3.0,
        obstacle_front_x=0.35, obstacle_far_x=0.48,
        obstacle_top_z=0.16, wheel_radius=0.08, clearance=0.05,
        approach_distance=0.25, exit_distance=0.20)
    assert approach['position'][2] > start[2]
    assert approach['acceleration'][2] > 0.0


def test_single_wheel_swing_rejects_invalid_clearance_inputs():
    module = swing_module()
    valid = dict(start=np.zeros(3), landing=np.array([0.8, 0.0, 0.0]), progress=0.5,
                 duration=3.0, obstacle_front_x=0.35, obstacle_far_x=0.48,
                 obstacle_top_z=0.1, wheel_radius=0.08, clearance=0.05,
                 approach_distance=0.25, exit_distance=0.20)
    for update in ({'progress': 1.1}, {'duration': 0.0}, {'clearance': -0.01},
                   {'wheel_radius': float('nan')},
                   {'obstacle_far_x': 0.1}, {'approach_distance': 0.5}):
        args = dict(valid, **update)
        with pytest.raises(ValueError):
            module.single_wheel_swing_reference(**args)


def test_single_wheel_swing_holds_clearance_for_the_entire_wheel_obstacle_overlap():
    module = swing_module()
    start = np.array([0.0, 0.0, 0.12])
    landing = np.array([0.80, 0.0, 0.12])
    obstacle_front_x, obstacle_far_x = 0.35, 0.48
    top_z, radius, clearance = 0.10, 0.08, 0.05

    samples = [module.single_wheel_swing_reference(
        start=start, landing=landing, progress=float(progress), duration=3.0,
        obstacle_front_x=obstacle_front_x, obstacle_far_x=obstacle_far_x,
        obstacle_top_z=top_z, wheel_radius=radius, clearance=clearance,
        approach_distance=0.25, exit_distance=0.20,
    ) for progress in np.linspace(0.0, 1.0, 501)]

    overlapping = [sample for sample in samples
                   if sample['position'][0] + radius >= obstacle_front_x
                   and sample['position'][0] - radius <= obstacle_far_x]
    assert overlapping, 'the wheel trajectory must traverse the obstacle span'
    assert min(sample['position'][2] - radius for sample in overlapping) >= (
        top_z + clearance - 1e-10
    ), 'wheel must stay clear until its rear envelope passes the obstacle far edge'
    assert max(abs(sample['acceleration'][2]) for sample in samples) <= 3.0, \
        'vertical swing acceleration must stay within the WBC lift-task limit'


def test_single_wheel_swing_qp_task_tracks_reference_after_acceleration_bias():
    module = swing_module()
    jacobian = np.zeros((3, 22))
    jacobian[:, :3] = np.eye(3)
    reference = dict(position=np.array([0.2, 0.0, 0.3]),
                     velocity=np.array([0.1, 0.0, 0.0]),
                     acceleration=np.array([0.0, 0.0, 0.2]))
    task = module.single_wheel_swing_qp_task(
        jacobian=jacobian,
        bias_acceleration=np.array([0.0, 0.0, -9.81]),
        position=np.array([0.1, 0.0, 0.1]),
        velocity=np.array([0.0, 0.0, 0.0]),
        reference=reference, kp=10.0, kd=2.0,
        max_acceleration=3.0, weight=4.0)

    np.testing.assert_allclose(task['matrix'], jacobian)
    np.testing.assert_allclose(task['desired_acceleration'], [1.2, 0.0, 2.2])
    np.testing.assert_allclose(task['target'], [1.2, 0.0, 12.01])
    np.testing.assert_allclose(task['weight'], [4.0, 4.0, 4.0])
