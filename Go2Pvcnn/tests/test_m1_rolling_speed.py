import importlib.util
from pathlib import Path
import pytest


def fn():
    path=Path(__file__).parents[1]/'ame_baseline/m1_rolling_speed.py'
    assert path.exists(),'bounded rolling speed profile missing'
    spec=importlib.util.spec_from_file_location('speed',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.rolling_speed


def test_bounded_start_braking_and_end_within_existing_window():
    speeds=[fn()(step,20,.02,.1) for step in range(20)]
    assert speeds[0]==0. and speeds[-1]==0.
    assert 0<max(speeds)<=.1
    assert all(abs(a-b)<=.2*.02+1e-10 for a,b in zip(speeds,speeds[1:]))
    assert speeds==pytest.approx(speeds[::-1])


def test_zero_command_stays_zero():
    assert all(fn()(step,20,.02,0.)==0 for step in range(20))


def test_standing_window_has_bounded_sustained_comparison():
    from ame_baseline.m1_rolling_speed import standing_window
    assert standing_window(100)==(60,20)
    assert standing_window(180)==(60,100)
    for budget in (0,99,101,181):
        with pytest.raises(ValueError): standing_window(budget)


def test_solver_comparison_requires_standing_control():
    from ame_baseline.m1_rolling_speed import solver_comparison
    assert solver_comparison(False,0)==0
    assert solver_comparison(True,4)==4
    for enabled,value in ((False,4),(True,1),(True,-1)):
        with pytest.raises(ValueError): solver_comparison(enabled,value)


def test_standing_control_window_is_zero_outside_same_roll_profile():
    from ame_baseline.m1_rolling_speed import window_speed
    for step in range(100):
        expected=fn()(step-60,20,.02,.1) if 60<=step<80 else 0.
        assert window_speed(step,60,20,.02,.1)==expected


@pytest.mark.parametrize('args',[(-1,20,.02,.1),(20,20,.02,.1),(0,0,.02,.1),(0,20,0.,.1),(0,20,.02,-.1),(0,20,.02,float('nan'))])
def test_invalid_profile_input_rejected(args):
    with pytest.raises(ValueError):fn()(*args)
