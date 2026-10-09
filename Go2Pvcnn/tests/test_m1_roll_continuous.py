import pytest
from ame_baseline.m1_rolling_speed import rolling_speed


@pytest.mark.parametrize('initial',[0.,.02,.04])
def test_roll_profile_preserves_incoming_command_and_can_brake_to_zero(initial):
    speed=[rolling_speed(k,20,.02,.1,initial=initial) for k in range(20)]
    assert speed[0]==pytest.approx(initial)
    assert speed[-1]==0
    assert max(speed)<=.1
    assert all(abs(b-a)<=.00400001 for a,b in zip(speed,speed[1:]))
    assert speed[1]>=speed[0]


def test_unreachable_braking_deadline_rejected_instead_of_initial_jump():
    with pytest.raises(ValueError):rolling_speed(0,5,.02,.1,initial=.04)


def test_probe_uses_incoming_hold_for_continuous_profile():
    import ast
    from pathlib import Path
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
    assert any(any(isinstance(a,ast.Constant) and a.value=='--roll_continuous_ramp' for a in n.args) for n in calls)
    assert any(isinstance(n.func,ast.Name) and n.func.id=='rolling_speed' and any(k.arg=='initial' for k in n.keywords) for n in calls)
