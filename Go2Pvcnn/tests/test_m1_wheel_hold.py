import math
import pytest
import torch
from ame_baseline import m1_rolling_speed as control


def call(position=None, yaw=None, previous=None):
    position = torch.zeros(2,4,3) if position is None else position
    return control.anchor_hold_speed(torch.zeros_like(position), position,
        torch.zeros(2) if yaw is None else yaw,
        torch.zeros(2,4) if previous is None else previous, .02)


def test_backward_drift_commands_bounded_forward_correction():
    position=torch.zeros(2,4,3); position[:,:,0]=-.035
    assert torch.allclose(call(position),torch.full((2,4),.004))


def test_yaw_projects_world_error_without_holonomic_lateral_command():
    position=torch.zeros(2,4,3); position[:,:,0]=-.035
    assert call(position,torch.full((2,),math.pi/2)).abs().max()<1e-7
    position.zero_(); position[:,:,1]=-.035
    assert torch.allclose(call(position,torch.full((2,),math.pi/2)),torch.full((2,4),.004))


def test_hold_caps_velocity_and_brakes_without_jump():
    position=torch.zeros(2,4,3); position[:,:,0]=-.035
    previous=torch.zeros(2,4)
    for _ in range(100):
        result=call(position,previous=previous)
        assert (result-previous).abs().max()<=.004001
        previous=result
    assert torch.allclose(previous,torch.full((2,4),.04))
    assert torch.allclose(call(previous=previous),torch.full((2,4),.036))


def test_rows_and_wheels_do_not_share_error():
    position=torch.zeros(2,4,3); position[1,2,0]=.01
    expected=torch.zeros(2,4); expected[1,2]=-.004
    assert torch.allclose(call(position),expected)


def test_invalid_state_is_rejected_instead_of_silent_action():
    p=torch.zeros(2,4,3); p[0,0,0]=float('nan')
    with pytest.raises(ValueError):call(p)
    with pytest.raises(ValueError):call(previous=torch.full((2,4),.05))
    with pytest.raises(ValueError):call(yaw=torch.zeros(3))
    with pytest.raises(ValueError):
        control.anchor_hold_speed(torch.zeros(2,4,3),torch.zeros(2,4,3),torch.zeros(2),torch.zeros(2,4),0.)


def test_hold_effort_uses_angular_velocity_and_rejects_limit():
    speed=torch.full((2,4),.04); qd=torch.full((2,4),-.2)
    damping=torch.full((2,4),5.); limit=torch.full((2,4),50.)
    effort=control.hold_effort(speed,qd,damping,limit,10.)
    assert torch.allclose(effort,torch.full((2,4),3.))
    with pytest.raises(ValueError):control.hold_effort(speed,qd,damping,limit*.01,10.)


def test_hold_effort_rejects_invalid_mapping_and_nonfinite():
    a=torch.zeros(2,4); d=torch.ones_like(a); limit=d*50
    with pytest.raises(ValueError):control.hold_effort(a,a,d,limit,0.)
    with pytest.raises(ValueError):control.hold_effort(a,a,d,-limit,10.)
    with pytest.raises(ValueError):control.hold_effort(a,a,d*float('nan'),limit,10.)


def test_phase_handoff_brakes_selected_and_preserves_support_hold():
    p=torch.zeros(2,4,3);p[:,:,0]=-.01
    prev=torch.full((2,4),.02);sel=torch.tensor([0,3]);yaw=torch.zeros(2)
    out=control.phase_hold_speed(torch.zeros_like(p),p,yaw,prev,.02,'unload',sel)
    expected=prev.clone();expected[0,0]=.016;expected[1,3]=.016
    assert torch.allclose(out,expected)
    for _ in range(5):out=control.phase_hold_speed(torch.zeros_like(p),p,yaw,out,.02,'lift',sel)
    assert out[0,0]==0 and out[1,3]==0


def test_roll_release_and_land_braking_are_slew_limited():
    p=torch.zeros(2,4,3);sel=torch.tensor([0,3]);yaw=torch.zeros(2)
    prev=torch.full((2,4),.02)
    out=control.phase_hold_speed(p,p,yaw,prev,.02,'roll',sel,.036)
    assert out[0,1]==pytest.approx(.024)
    assert out[0,0]==pytest.approx(.016)
    land=control.phase_hold_speed(p,p,yaw,out,.02,'land',sel)
    assert torch.allclose(land,out-.004)
    with pytest.raises(ValueError):control.phase_hold_speed(p,p,yaw,prev,.02,'land',sel,.01)
    with pytest.raises(ValueError):control.phase_hold_speed(p,p,yaw,prev,.02,'bad',sel)
