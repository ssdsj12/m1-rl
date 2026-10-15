import importlib.util
import pytest
import torch

def api():
    assert importlib.util.find_spec('ame_baseline.m1_teacher_load_feedback') is not None, 'load feedback module missing'
    from ame_baseline.m1_teacher_load_feedback import propose_load_feedback
    def with_geometry(*args):
        raw=args[0]
        wheels=raw.new_tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]]).repeat(len(raw),1,1)
        return propose_load_feedback(*args,wheels_w=wheels)
    return with_geometry

def inputs(dtype=torch.float64,active=0,batch=1):
    f=torch.tensor([[12.,179.,159.,35.]],dtype=dtype).repeat(batch,1)
    a=torch.full((batch,),active,dtype=torch.long)
    p=torch.tensor([[.45,.43,.12]],dtype=dtype).repeat(batch,1)
    old=torch.zeros_like(f);dt=torch.full((batch,),.02,dtype=dtype)
    valid=torch.ones(batch,dtype=torch.bool)
    return f,p,a,old,dt,valid

@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
def test_projection_conserves_support_and_masks_active(dtype,active):
    args=inputs(dtype,active);f,p,a,old,dt,v=args
    out=api()(*args);mask=torch.arange(4)!=active
    assert out.valid.all()
    assert out.offset[0,active]==0 and out.velocity[0,active]==0
    assert out.target_fz[0,active]==0
    assert torch.all(out.target_fz[0,mask]>=45-1e-5)
    assert torch.allclose(out.target_fz.sum(-1),f[:,mask].sum(-1),atol=1e-5,rtol=1e-6)
    assert out.offset.sum(-1).abs().max()<1e-7
    assert out.velocity.abs().max()<=.010001
    assert out.offset.abs().max()<=.00020001

def test_weak_right_rear_corrects_downward():
    out=api()(*inputs())
    assert out.offset[0,3]<0
    assert out.target_fz[0,3]>=45

def test_invalid_measurement_and_insufficient_sum_freeze_only_row():
    args=list(inputs(batch=3));args[0][1]=1;args[0][2,3]=float('nan')
    out=api()(*args)
    assert out.valid.tolist()==[True,False,False]
    assert torch.equal(out.offset[1:],args[3][1:])
    assert torch.equal(out.velocity[1:],torch.zeros_like(out.velocity[1:]))

def test_invalid_geometry_and_mask_freeze():
    args=list(inputs(batch=3));args[1][1,0]=-1;args[-1][2]=False
    out=api()(*args)
    assert out.valid.tolist()==[True,False,False]
    assert out.offset[1:].abs().max()==0

def test_offset_saturation_preserves_zero_sum():
    args=list(inputs());args[3][0]=torch.tensor([0.,.015,0.,-.015])
    out=api()(*args)
    assert out.valid.all()
    assert out.offset.abs().max()<=.01500001
    assert out.offset.sum().abs()<1e-10
    assert ((out.offset-args[3]).abs()<=.00020001).all()

def test_long_float32_mixed_wheel_sequence_stays_feasible():
    args=list(inputs(torch.float32,batch=4));args[2]=torch.arange(4)
    for step in range(400):
        args[0]=torch.tensor([[150.,85.,190.,40.]],dtype=torch.float32).repeat(4,1).roll(step//35,dims=1)
        out=api()(*args)
        assert out.valid.all() and out.offset.sum(-1).abs().max()<=1e-8
        assert out.offset.abs().max()<=.015000001
        assert (out.offset-args[3]).abs().max()<=.00020001
        args[3]=out.offset

@pytest.mark.parametrize('case',['dt_zero','dt_nan','bad_shape','old_sum','old_active','old_nan','old_limit'])
def test_bad_contract_rejected(case):
    args=list(inputs())
    if case=='dt_zero':args[4][0]=0
    if case=='dt_nan':args[4][0]=float('nan')
    if case=='bad_shape':args[1]=args[1][:,:2]
    if case=='old_sum':args[3][0,1]=.001
    if case=='old_active':args[3][0,0]=.001;args[3][0,1]=-.001
    if case=='old_nan':args[3][0,1]=float('nan')
    if case=='old_limit':args[3][0,1]=.02;args[3][0,2]=-.02
    with pytest.raises(ValueError):api()(*args)
