from types import SimpleNamespace as NS
import pytest
import torch
from ame_baseline import m1_ame_contract as c
from ame_baseline.m1_ame_rewards import m1_action_rate_l2

LEG = [0,1,2,4,5,6,8,9,10,12,13,14]
WHEEL = [3,7,11,15]

def expand(a, speed=.3):
    assert hasattr(c, 'expand_fixed_wheel_actions'), 'fixed wheel expansion missing'
    return c.expand_fixed_wheel_actions(a, speed)

def test_arbitrary_legs_cannot_change_wheel_targets():
    a=torch.arange(24,dtype=torch.float64).reshape(2,12)/100
    out=expand(a)
    assert out.shape==(2,16) and out.dtype==a.dtype
    torch.testing.assert_close(out[:,LEG],a)
    torch.testing.assert_close(out[:,WHEEL],torch.full((2,4),.3,dtype=a.dtype))
    targets=c.m1_action_targets(out,torch.zeros_like(out))
    torch.testing.assert_close(targets[:,WHEEL],torch.full((2,4),.3/.095958,dtype=a.dtype))

@pytest.mark.parametrize('speed',[0,-.3,float('nan'),float('inf'),2.1])
def test_invalid_fixed_speed_rejected(speed):
    with pytest.raises(ValueError): expand(torch.zeros(2,12),speed)

def test_sixteen_policy_actions_rejected_in_leg_only_contract():
    with pytest.raises(ValueError): expand(torch.zeros(2,16))

def env(a):
    return NS(cfg=NS(m1_fixed_wheel_speed_m_s=.3,asset_joint_names=c.M1_ASSET_JOINT_NAMES),action_manager=NS(action=a,prev_action=torch.zeros_like(a)))

def test_history_is_executed_sixteen_channels_but_leg_history_is_twelve():
    a=torch.arange(12.).reshape(1,12)/100
    e=env(a)
    torch.testing.assert_close(c.m1_last_action(e)[:,LEG],a)
    torch.testing.assert_close(c.m1_last_action(e)[:,WHEEL],torch.full((1,4),.3))
    torch.testing.assert_close(c.m1_last_leg_action(e),a)

def test_action_rate_preserves_sum_scale_and_excludes_fixed_wheels():
    a=torch.ones(2,12)*.1
    torch.testing.assert_close(m1_action_rate_l2(env(a)),torch.full((2,),.12))
