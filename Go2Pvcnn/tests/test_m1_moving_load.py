import torch
from test_m1_load_transfer import force_ready_inputs


def test_probe_wires_opt_in_load_feedback_without_replacing_final_joint_guard():
    from pathlib import Path
    source=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert "--roll_load_feedback" in source
    assert 'load_proposal=moving_load_target(' in source
    assert "roll_com_offset=proposal['root']-previous_root-transport['shift']" in source


def test_moving_load_correction_is_translation_invariant_and_bounded():
    from ame_baseline.m1_moving_load import moving_load_target
    a=force_ready_inputs()
    args=dict(entry_root=a['entry_root'],prepared_root=a['previous_root'],
              rpy=a['entry_rpy'],anchor=a['anchor_w'],shift=torch.zeros(4,3),
              offset=torch.zeros(4,3),height=torch.zeros(4),
              support=a['support_w'],live_root=a['live_root'],com=a['live_com'],
              selected=a['selected_leg'],force=torch.full((4,4),100.),dt=.02)
    args['force'][0,3]=33.
    base=moving_load_target(**args)
    assert base['valid'].all(),base['reason']
    assert base['offset'][0].norm()>0
    assert (base['offset'].norm(dim=-1)<=.000801).all()
    delta=torch.tensor([.12,-.03,0.])
    args['shift']+=delta
    for key in ('support','live_root','com'):args[key]=args[key]+delta
    moved=moving_load_target(**args)
    torch.testing.assert_close(moved['offset'],base['offset'],atol=1e-6,rtol=0)
    torch.testing.assert_close(moved['root'],base['root']+delta,atol=1e-6,rtol=0)


def test_transport_uses_support_wheels_not_lifted_wheel_or_body_shift():
    from ame_baseline.m1_moving_load import support_center
    wheels=torch.zeros(4,4,3)
    selected=torch.arange(4)
    wheels[torch.arange(4),selected]=10.
    torch.testing.assert_close(support_center(wheels,selected),torch.zeros(4,3))
    wheels+=torch.tensor([.02,-.01,0.])
    torch.testing.assert_close(support_center(wheels,selected),torch.tensor([[.02,-.01,0.]]).repeat(4,1))
