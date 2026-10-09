import pytest
import torch


def test_root_reference_ramp_preserves_entry_height_and_acceleration():
    from ame_baseline.m1_com_trajectory import root_step
    entry=torch.tensor([[2.,-3.,.45]],dtype=torch.float64)
    previous=entry+torch.tensor([[.04,.01,0.]])
    target=previous+torch.tensor([[.01,.01,0.]])
    v=torch.zeros(1,2,dtype=entry.dtype)
    r=root_step(entry,previous,v,target,dt=.02)
    assert r['valid'].all()
    assert r['velocity'].norm() <= .00100001
    torch.testing.assert_close(r['root'][:,:2]-previous[:,:2],r['velocity']*.02)
    torch.testing.assert_close(r['root'][:,2],entry[:,2])


def test_root_reference_rejects_height_drift_and_entry_bound():
    from ame_baseline.m1_com_trajectory import root_step
    entry=torch.zeros(2,3)
    target=torch.tensor([[0.,0.,.001],[.081,0.,0.]])
    r=root_step(entry,entry.clone(),torch.zeros(2,2),target,dt=.02)
    assert not r['valid'].any()
    torch.testing.assert_close(r['root'],entry)


def test_probe_keeps_com_velocity_through_landing():
    from pathlib import Path
    source=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert '--roll_com_trajectory' in source
    assert "com_velocity=com_proposal['velocity']" in source
    assert "com_velocity.norm(dim=-1)<=1e-4" in source
    # COM motion is retained from the actual roll handoff through landing;
    # roll_start may be measured dynamically when lift_handoff is enabled.
    assert 'args.roll_com_trajectory and roll_age>=0' in source


def test_start_brake_and_endpoint_preserve_acceleration_bound():
    from ame_baseline.m1_com_trajectory import com_step
    x=torch.zeros(2,2);v=torch.zeros_like(x)
    target=torch.tensor([[.004,.002],[-.003,.001]])
    for _ in range(120):
        result=com_step(x,v,target,dt=.02)
        assert result['valid'].all()
        assert ((result['velocity']-v).norm(dim=-1)<=.001001).all()
        assert (result['velocity'].norm(dim=-1)<=.040001).all()
        x,v=result['position'],result['velocity']
    torch.testing.assert_close(x,target,atol=1e-5,rtol=0)
    assert v.norm(dim=-1).max()<1e-5


def test_invalid_measurement_does_not_generate_motion():
    from ame_baseline.m1_com_trajectory import com_step
    x=torch.zeros(1,2);v=torch.zeros_like(x)
    result=com_step(x,v,torch.full_like(x,float('nan')),dt=.02)
    assert not result['valid'].any()
    torch.testing.assert_close(result['position'],x)
    with pytest.raises(ValueError):com_step(x,v,x,dt=0)


def test_abrupt_target_reversal_cannot_jump_velocity():
    from ame_baseline.m1_com_trajectory import com_step
    x=torch.zeros(1,2);v=torch.tensor([[.02,0.]])
    result=com_step(x,v,torch.tensor([[-.01,0.]]),dt=.02)
    assert result['valid'].all()
    assert (result['velocity']-v).norm()<=.001001
    assert result['velocity'][0,0]>0  # brake, do not instantaneously reverse


def test_rejects_offset_bound_without_clipping_velocity_into_false_success():
    from ame_baseline.m1_com_trajectory import com_step
    x=torch.tensor([[.0799,0.]])
    v=torch.tensor([[.04,0.]])
    result=com_step(x,v,torch.zeros_like(x),dt=.02)
    assert not result['valid'].any()
    torch.testing.assert_close(result['position'],x)
