import math
import pytest
import torch
from ame_baseline.m1_teacher_tripod_load import tripod_load, capped_load_scale


def fixture(dtype=torch.float64):
    wheels=torch.tensor([[[9.,9.,0.],[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]],dtype=dtype)
    return torch.tensor([[1/3,1/3,.5]],dtype=dtype),wheels,torch.tensor([0]),torch.tensor([300.],dtype=dtype)


def test_triangle_center():
    c,w,a,f=fixture();r=tripod_load(c,w,a,f)
    assert r.valid.tolist()==[True]
    assert r.support_indices.tolist()==[[1,2,3]]
    torch.testing.assert_close(r.loads_n,torch.tensor([[100.,100.,100.]],dtype=c.dtype))
    assert r.min_load_n.item()==pytest.approx(100.)


def test_outside_preserves_negative():
    c,w,a,f=fixture();c[0,:2]=torch.tensor([.8,.8])
    r=tripod_load(c,w,a,f)
    assert r.valid.item()
    assert r.min_load_n.item()==pytest.approx(-180.,abs=1e-4)
    assert r.fractions[0,0]<0


@pytest.mark.parametrize('bad', ['degenerate','nan','zero','negative','near_degenerate'])
def test_degenerate_and_nan_invalid(bad):
    c,w,a,f=fixture()
    c=c.repeat(2,1);w=w.repeat(2,1,1);a=a.repeat(2);f=f.repeat(2)
    if bad=='degenerate': w[0,3]=w[0,2]
    if bad=='near_degenerate': w[0,3,1]=1e-11
    if bad=='nan': c[0,0]=float('nan')
    if bad=='zero': f[0]=0
    if bad=='negative': f[0]=-1
    r=tripod_load(c,w,a,f)
    assert r.valid.tolist()==[False,True]
    assert torch.isnan(r.min_load_n[0])
    assert r.min_load_n[1].item()==pytest.approx(100)


@pytest.mark.parametrize('active',range(4))
def test_four_active_wheels(active):
    c,w,a,f=fixture()
    permutation=[i for i in range(4) if i!=active]
    out=w.clone();out[0,active]=w[0,0];out[0,permutation]=w[0,1:]
    r=tripod_load(c,out,torch.tensor([active]),f)
    assert r.support_indices.tolist()==[permutation]
    torch.testing.assert_close(r.loads_n,torch.full((1,3),100.,dtype=c.dtype))


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_translation_rotation_float32_float64(dtype):
    c,w,a,f=fixture(dtype);angle=.7
    rot=c.new_tensor([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
    shift=c.new_tensor([100.,-152.,7.])
    r=tripod_load(c@rot.T+shift,w@rot.T+shift,a,f)
    assert r.valid.item()
    torch.testing.assert_close(r.loads_n,torch.full((1,3),100.,dtype=dtype),atol=.01,rtol=0)


def test_spike_is_capped():
    raw=torch.tensor([[50.,50.,50.,50.],[10.,10.,10.,10.],[-10.,30.,30.,40.]])
    torch.testing.assert_close(capped_load_scale(raw,torch.tensor([100.,100.,100.])),torch.tensor([100.,40.,100.]))


@pytest.mark.parametrize('bad',['shape','index','dtype'])
def test_contract_rejected(bad):
    c,w,a,f=fixture()
    if bad=='shape': c=c[:,:2]
    if bad=='index': a[0]=4
    if bad=='dtype': f=f.float()
    with pytest.raises(ValueError):tripod_load(c,w,a,f)


def test_invalid_scale_does_not_become_positive():
    r=capped_load_scale(torch.tensor([[1.,2.,3.,4.],[1.,2.,3.,float('nan')]]),torch.tensor([0.,100.]))
    assert r[0]<=0 or torch.isnan(r[0])
    assert torch.isnan(r[1])
