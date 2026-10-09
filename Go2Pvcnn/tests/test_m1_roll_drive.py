import ast
from pathlib import Path
import pytest


def test_gain_schedule_does_not_change_prepare_lift_or_landing():
    from ame_baseline.m1_rolling_speed import rolling_damping
    for phase in ('prepare','unload','lift','land','settle'):
        assert rolling_damping(phase,20.) == 5.
    assert rolling_damping('roll',20.) == 20.
    assert rolling_damping('roll',5.) == 5.
    for phase,gain in [('bad',20.),('roll',50.),('roll',float('nan'))]:
        with pytest.raises(ValueError): rolling_damping(phase,gain)


def test_runtime_updates_backend_and_estimator_only_at_phase_boundary():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    source=ast.unparse(tree)
    assert "'--roll_wheel_damping'" in source
    assert 'rolling_damping(control_phase, args.roll_wheel_damping)' in source
    assert 'robot.write_joint_damping_to_sim(drive_damping, joint_ids=wheel_joint_ids)' in source
    assert "robot.actuators['wheels'].damping.fill_(drive_damping)" in source
    assert 'if drive_damping != active_wheel_damping:' in source
