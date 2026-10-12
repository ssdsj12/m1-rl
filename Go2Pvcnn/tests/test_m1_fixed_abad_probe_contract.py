from copy import deepcopy
import importlib.util
from pathlib import Path
import pytest

def validator():
    path=Path(__file__).parents[1]/'scripts/probe_m1_fixed_abad.py'
    assert path.exists(),'native evidence validator not implemented'
    spec=importlib.util.spec_from_file_location('abad_probe',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.validate_evidence

def valid():
    return dict(complete=True,stages=[0,1,2,3,4],policy_dim=8,history_dim=16,
        policy_state_dim=85,critic_state_dim=88,rewards_finite=True,raw_rewards_finite=True,abad_target_error=0.,
        wheel_target_error=0.,elapsed_100=2.,apply_calls=600,terminal_row_reset=True,
        flat_resets=0,flat_advance_min=.4,flat_max_tilt=.05)

def test_valid_probe_contract():validator()(valid())

def test_nan_targets_cannot_hide_in_max_aggregation():
    import torch
    check=validator().__globals__.get('require_finite')
    assert check is not None
    with pytest.raises(ValueError):check(torch.tensor([0.,float('nan')]))
    with pytest.raises(ValueError):check(torch.tensor([float('inf')]))
    check(torch.tensor([0.,.3]))

@pytest.mark.parametrize('field,value',[
    ('complete',False),('stages',[0,1]),('policy_dim',12),('history_dim',8),
    ('rewards_finite',False),('raw_rewards_finite',False),('abad_target_error',.001),('wheel_target_error',.1),
    ('elapsed_100',4.),('elapsed_100',float('nan')),('apply_calls',0),
    ('terminal_row_reset',False),('flat_resets',1),('flat_advance_min',-.1)])
def test_reject_incomplete_or_incorrect_probe(field,value):
    data=deepcopy(valid());data[field]=value
    with pytest.raises(ValueError):validator()(data)
