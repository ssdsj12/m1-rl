"""Measured one-dimensional wheel/box corridor, not a success counter."""
import torch
import pytest
import importlib.util
from pathlib import Path


def gate():
    path=Path(__file__).parents[1]/'ame_baseline/m1_traverse_gate.py'
    assert path.exists(), 'measured obstacle traverse gate missing'
    spec=importlib.util.spec_from_file_location('traverse_gate',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.traverse_gate


def inputs():
    return dict(wheel_x=torch.tensor([0.]),wheel_z=torch.tensor([.26]),
                radius=torch.tensor([.096]),near=torch.tensor([.15]),
                far=torch.tensor([.21]),top=torch.tensor([.10]),
                support_safe=torch.tensor([True]),collision=torch.tensor([False]),
                evidence_fresh=torch.tensor([True]),landing_available=torch.tensor([True]))


def test_high_wheel_may_traverse_but_cannot_land_before_far_edge():
    args=inputs();result=gate()(**args)
    assert result['advance'].item()
    assert not result['land'].item()
    assert result['clearance'].item()==pytest.approx(.064)


def test_wheel_center_past_box_is_not_envelope_past_box():
    args=inputs();args['wheel_x'].fill_(.23)
    result=gate()(**args)
    assert not result['land'].item()
    args['wheel_x'].fill_(.347)
    assert gate()(**args)['land'].item()


def test_height_is_measured_bottom_not_center_or_command():
    args=inputs();args['wheel_x'].fill_(.18);args['wheel_z'].fill_(.22)
    result=gate()(**args)
    assert not result['advance'].item()
    assert not result['land'].item()
    assert result['clearance'].item()==pytest.approx(.024)


def test_after_far_edge_can_lower_below_top_without_requiring_high_hold():
    args=inputs();args['wheel_x'].fill_(.347);args['wheel_z'].fill_(.096)
    result=gate()(**args)
    assert result['land'].item()
    assert not result['advance'].item(), 'stop forward command during landing'


@pytest.mark.parametrize('field',['support_safe','evidence_fresh','landing_available','collision','nan','bounds','radius'])
def test_invalid_or_unsafe_rows_fail_closed(field):
    args=inputs()
    if field in ('support_safe','evidence_fresh','landing_available'):args[field].fill_(False)
    elif field=='collision':args[field].fill_(True)
    elif field=='nan':args['wheel_z'].fill_(float('nan'))
    elif field=='bounds':args['far'].fill_(.1)
    else:args['radius'].fill_(-.1)
    result=gate()(**args)
    assert not result['advance'].item() and not result['land'].item()


def test_batch_rows_do_not_share_clearance_or_far_side_state():
    args={key:value.repeat(2) for key,value in inputs().items()}
    args['wheel_x'][1]=.347;args['wheel_z'][1]=.096
    result=gate()(**args)
    assert result['advance'].tolist()==[True,False]
    assert result['land'].tolist()==[False,True]
