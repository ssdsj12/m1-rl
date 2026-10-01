from pathlib import Path


def test_m1_evaluation_obstacles_are_in_forward_positive_x_corridor():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'scripts' / 'evaluate_m1_ame.py').read_text()
    assert 'cfg.commands.base_velocity.ranges.lin_vel_x = (.35, .35)' in source
    assert '(-1.10, 0.25' not in source
    assert '(-1.70, -0.25' not in source
    assert '(-2.30, 0.20' not in source
    assert '(1.10, 0.25' in source
    assert '(1.70, -0.25' in source
    assert '(2.30, 0.20' in source
    assert 'pos=(1.5, 0., height / 2)' in source
