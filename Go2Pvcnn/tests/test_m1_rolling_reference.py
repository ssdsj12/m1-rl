import importlib.util
from pathlib import Path
import torch


def fn():
    path=Path(__file__).parents[1]/'ame_baseline/m1_rolling_reference.py'
    assert path.exists(),'rolling reference transport missing'
    spec=importlib.util.spec_from_file_location('rolling',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.rolling_shift


def test_progress_follows_entry_heading_not_global_x_or_vertical_sag():
    origin=torch.zeros(2,3);live=torch.tensor([[.01,0.,-.006],[0.,.01,-.006]])
    result=fn()(origin,live,torch.tensor([0.,torch.pi/2]),torch.zeros(2),.02)
    assert result['valid'].all()
    torch.testing.assert_close(result['shift'],torch.tensor([[.01,0.,0.],[0.,.01,0.]]),atol=1e-6,rtol=0)


def test_repeated_measurement_does_not_integrate_displacement_twice():
    origin=torch.zeros(1,3);live=torch.tensor([[.01,0.,0.]])
    first=fn()(origin,live,torch.zeros(1),torch.zeros(1),.02)
    second=fn()(origin,live,torch.zeros(1),first['progress'],.02)
    torch.testing.assert_close(first['shift'],second['shift'])
    torch.testing.assert_close(second['delta'],torch.zeros(1,3))


def test_lateral_drift_jump_backward_and_nan_are_not_hidden():
    origin=torch.zeros(4,3);live=torch.tensor([[0.,.026,0.],[.05,0.,0.],[-.021,0.,0.],[float('nan'),0.,0.]])
    result=fn()(origin,live,torch.zeros(4),torch.zeros(4),.02)
    assert not result['valid'].any()
