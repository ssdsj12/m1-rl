import inspect
import pytest
import torch
from ame_baseline.m1_teacher_load_feedback import propose_load_feedback


def call(dtype=torch.float64, attitude=None, raw=None, old=None, active=0):
    assert 'attitude_error_m' in inspect.signature(propose_load_feedback).parameters, 'unified attitude preference missing'
    f=torch.tensor([raw or [12.,179.,159.,35.]],dtype=dtype)
    wheels=f.new_tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]])
    return propose_load_feedback(f,f.new_tensor([[.45,.43,.12]]),torch.tensor([active]),
        f.new_zeros(1,4) if old is None else old,f.new_tensor([.02]),torch.tensor([True]),
        wheels_w=wheels,attitude_error_m=f.new_tensor([attitude]) if attitude is not None else None)


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_opposing_attitude_cannot_retract_weak_rr(dtype):
    out=call(dtype,attitude=[0.,-.02,-.02,.04])
    assert out.valid.item()
    assert out.velocity[0,3]<0
    assert out.offset.sum().abs()<1e-8
    assert out.offset.abs().max()<=.00020001


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_direction_survives_position_projection_at_saturation(dtype):
    old=torch.tensor([[0.,.015,0.,-.015]],dtype=dtype)
    out=call(dtype,attitude=[0.,-.02,-.02,.04],old=old)
    assert out.valid.item()
    assert out.offset[0,3]<=old[0,3]+1e-9
    assert out.offset.sum().abs()<1e-8
    assert out.offset.abs().max()<=.015000001


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
def test_balanced_support_retains_attitude_authority(dtype,active):
    f=torch.full((1,4),100.,dtype=dtype);f[0,active]=0
    ids=[j for j in range(4) if j!=active]
    attitude=torch.zeros_like(f);attitude[0,ids[0]]=.002;attitude[0,ids[1]]=-.002
    wheels=f.new_tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]])
    args=(f,f.new_full((1,3),1/3),torch.tensor([active]),torch.zeros_like(f),f.new_tensor([.02]),torch.tensor([True]))
    out=propose_load_feedback(*args,wheels_w=wheels,attitude_error_m=attitude)
    assert out.valid.item()
    assert out.velocity[0,ids[0]]>0 and out.velocity[0,ids[1]]<0
    assert out.offset[0,active]==0 and out.offset.sum().abs()<1e-8
    legacy=propose_load_feedback(*args,wheels_w=wheels)
    explicit=propose_load_feedback(*args,wheels_w=wheels,attitude_error_m=None)
    assert torch.equal(legacy.offset,explicit.offset)


def test_nonfinite_attitude_freezes_only_affected_row():
    f=torch.tensor([[12.,179.,159.,35.]]).repeat(3,1)
    wheels=f.new_tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]]).repeat(3,1,1)
    a=f.new_tensor([[0.,-.02,-.02,.04]]).repeat(3,1);a[1,1]=float('nan');a[2,3]=float('inf')
    out=propose_load_feedback(f,f.new_tensor([[.45,.43,.12]]).repeat(3,1),torch.zeros(3,dtype=torch.long),
        torch.zeros_like(f),f.new_full((3,),.02),torch.ones(3,dtype=torch.bool),wheels_w=wheels,attitude_error_m=a)
    assert out.valid.tolist()==[True,False,False]
    assert torch.isfinite(out.offset).all() and out.offset[1:].abs().max()==0


@pytest.mark.parametrize('bad',['shape','dtype','sum','active'])
def test_attitude_structure_rejected(bad):
    f=torch.tensor([[12.,179.,159.,35.]],dtype=torch.float64);a=torch.zeros_like(f)
    if bad=='shape':a=a[:,:3]
    if bad=='dtype':a=a.float()
    if bad=='sum':a[0,2]=.001
    if bad=='active':a[0,0]=.001;a[0,1]=-.001
    with pytest.raises(ValueError):
        propose_load_feedback(f,f.new_tensor([[.45,.43,.12]]),torch.tensor([0]),torch.zeros_like(f),
            f.new_tensor([.02]),torch.tensor([True]),wheels_w=f.new_tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]]),attitude_error_m=a)


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_long_sequence_priority_and_zero_sum(dtype):
    old=torch.zeros(1,4,dtype=dtype)
    for k in range(250):
        raw=[12.,179.,159.,35.] if k%40<20 else [12.,40.,159.,170.]
        out=call(dtype,attitude=[0.,-.02,-.02,.04],old=old,raw=raw)
        assert out.valid.item()
        delta=out.offset-old
        for j in (1,2,3):
            deficit=float(out.target_fz[0,j])-raw[j]
            if raw[j]<45 or deficit>15:assert delta[0,j]<=1e-9
            elif deficit < -15:assert delta[0,j]>=-1e-9
        assert out.offset.sum().abs()<1e-8 and out.offset.abs().max()<=.015000001
        assert delta.abs().max()<=.00020001
        old=out.offset
