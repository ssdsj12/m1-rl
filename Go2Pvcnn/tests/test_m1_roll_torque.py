import pytest


def test_explicit_profile_is_bounded_and_returns_to_zero():
    from ame_baseline.m1_rolling_speed import rolling_torque
    values=[rolling_torque(i,20,.02,3.) for i in range(20)]
    assert values[0]==values[-1]==0.
    assert max(values)==3.
    assert all(abs(a-b)<=.4+1e-9 for a,b in zip(values,values[1:]))
    assert values==pytest.approx(values[::-1])
    assert all(rolling_torque(i,20,.02,0.)==0 for i in range(20))


@pytest.mark.parametrize('args',[(0,20,.02,4.),(-1,20,.02,3.),(20,20,.02,3.),(0,20,0.,3.)])
def test_bad_torque_profile_rejected(args):
    from ame_baseline.m1_rolling_speed import rolling_torque
    with pytest.raises(ValueError):rolling_torque(*args)
