import torch


def sample():
    return dict(height=torch.tensor([.16]),previous_height=torch.tensor([.16]),
        force=torch.tensor([[0.,50.,150.,200.]]),selected=torch.tensor([0]),
        tilt=torch.zeros(1,2),tilt_rate=torch.zeros(1,2),margin=torch.tensor([.03]),
        valid=torch.tensor([True]),collision=torch.tensor([False]),target=.16,dt=.02)


def test_handoff_requires_five_consecutive_settled_samples():
    from ame_baseline.m1_lift_handoff import LiftHandoffGate
    gate=LiftHandoffGate(1);x=sample()
    for k in range(4):assert not gate.update(k,**x).item()
    assert gate.update(4,**x).item()
    assert not gate.update(6,**x).item()


def test_near_height_while_moving_or_underloaded_is_not_ready():
    from ame_baseline.m1_lift_handoff import LiftHandoffGate
    gate=LiftHandoffGate(1);x=sample();x['previous_height']=torch.tensor([.159])
    for k in range(6):assert not gate.update(k,**x).item()
    x=sample();x['force'][0,1]=29.
    for k in range(6,12):assert not gate.update(k,**x).item()


def test_collision_is_not_forgotten_by_waiting():
    from ame_baseline.m1_lift_handoff import LiftHandoffGate
    gate=LiftHandoffGate(1);x=sample();x['collision'][0]=True
    assert not gate.update(0,**x).item()
    x['collision'][0]=False
    for k in range(1,8):assert not gate.update(k,**x).item()


def test_runtime_exposes_opt_in_gate_and_preserves_main_budget():
    from pathlib import Path
    source=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert "'--lift_handoff'" in source
    assert 'handoff_gate.update(' in source
    assert 'main_budget=args.lift_steps+args.roll_steps+args.land_steps' in source
    assert "stopped='lift_handoff_timeout'" in source
