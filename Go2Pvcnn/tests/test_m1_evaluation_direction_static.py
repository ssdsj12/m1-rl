from pathlib import Path

from ame_baseline.m1_obstacle_profile import M1_FIXED_SMALL_OBSTACLE_LOCAL_XY


def test_m1_evaluation_obstacles_are_in_forward_positive_x_corridor():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'scripts' / 'evaluate_m1_ame.py').read_text()
    assert 'cfg.commands.base_velocity.ranges.lin_vel_x = (.35, .35)' in source
    # Evaluation must use the exact same left/right wheel-track course as
    # training; a body-centerline course cannot validate per-leg crossings.
    assert 'M1_FIXED_SMALL_OBSTACLE_LOCAL_XY' in source
    assert 'M1_SMALL_OBSTACLE_DIAMETER_M' in source
    assert 'for i, (x, y) in enumerate(M1_FIXED_SMALL_OBSTACLE_LOCAL_XY)' in source
    assert '(x, y, small_height / 2)' in source
    assert len(M1_FIXED_SMALL_OBSTACLE_LOCAL_XY) == 6
    assert all(x > 0 for x, _ in M1_FIXED_SMALL_OBSTACLE_LOCAL_XY)
    assert [1 if y > 0 else -1 for _, y in M1_FIXED_SMALL_OBSTACLE_LOCAL_XY] == [1, -1, 1, -1, 1, -1]
    assert 'pos=(1.5, 0., height / 2)' in source
