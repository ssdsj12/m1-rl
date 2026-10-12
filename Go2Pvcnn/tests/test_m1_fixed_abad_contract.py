import importlib
import pytest
import torch


def module():
    try:
        return importlib.import_module('ame_baseline.m1_fixed_abad')
    except ModuleNotFoundError:
        pytest.fail('fixed ABAD eight-action contract is missing')


@pytest.mark.parametrize('batch', [1, 4])
def test_eight_actions_expand_by_name(batch):
    mod = module()
    actions = torch.arange(8, dtype=torch.float64).repeat(batch, 1)
    saved = actions.clone()
    actual = mod.expand_fixed_abad_actions(actions)
    want = torch.tensor([0,0,1,.3,0,2,3,.3,0,4,5,.3,0,6,7,.3], dtype=torch.float64).repeat(batch, 1)
    torch.testing.assert_close(actual, want)
    torch.testing.assert_close(actions, saved)
    assert actual.device == actions.device
    contract = mod.fixed_abad_contract(.3)
    assert contract['fixed_joint_targets'] == [0.,0.,0.,0.]
    assert contract['policy_joint_names'] == [p+'_'+j+'_JOINT' for p in ('FBL','FAR','RBL','RAR') for j in ('HIP','KNEE')]
    contract['fixed_joint_targets'][0] = 9
    assert mod.fixed_abad_contract(.3)['fixed_joint_targets'][0] == 0


@pytest.mark.parametrize('shape', [(2,12),(2,16),(8,), (1,2,8)])
def test_wrong_shape_rejected(shape):
    with pytest.raises(ValueError):
        module().expand_fixed_abad_actions(torch.zeros(shape))


@pytest.mark.parametrize('value', [float('nan'),float('inf'),-float('inf')])
def test_nonfinite_rejected(value):
    a = torch.zeros(2,8); a[0,2]=value
    with pytest.raises(ValueError):
        module().expand_fixed_abad_actions(a)


@pytest.mark.parametrize('speed', [0.,-.3,2.1,float('nan'),float('inf')])
def test_speed_rejected(speed):
    with pytest.raises(ValueError):
        module().expand_fixed_abad_actions(torch.zeros(2,8),speed)
