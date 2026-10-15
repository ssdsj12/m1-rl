"""Independent first-moment regressions for an active wheel still in contact."""
import pytest
import torch
from ame_baseline.m1_teacher_load_feedback import propose_load_feedback


def rectangle(dtype=torch.float64):
    return torch.tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]],dtype=dtype)


def call(raw, fractions, active, wheels, previous=None):
    previous=torch.zeros_like(raw) if previous is None else previous
    return propose_load_feedback(raw,fractions,active,previous,
        raw.new_full((len(raw),),.02),torch.ones(len(raw),dtype=torch.bool),wheels_w=wheels)


def test_active_contact_moment_and_rear_support_direction():
    raw=torch.tensor([[60.,100.,100.,100.]],dtype=torch.float64)
    fractions=raw.new_tensor([[.4,.4,.2]])
    out=call(raw,fractions,torch.tensor([0]),rectangle())
    assert torch.allclose(out.target_fz,raw.new_tensor([[0.,84.,84.,132.]]),atol=1e-8)
    assert out.velocity[0,3]<0  # down/load RR, not up/unload
    com=(fractions[:,:,None]*rectangle()[:,1:,:2]).sum(1)
    moment=(out.target_fz[:,:,None]*rectangle()[:,:,:2]).sum(1)+60*rectangle()[:,0,:2]
    assert torch.allclose(moment,360*com,atol=1e-8)


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
def test_affine_moment_and_coordinate_invariance(dtype,active):
    wheels=rectangle(dtype);raw=torch.full((1,4),100.,dtype=dtype);raw[0,active]=30.
    fractions=raw.new_tensor([[.35,.35,.3]]);a=torch.tensor([active])
    out=call(raw,fractions,a,wheels)
    ids=[j for j in range(4) if j!=active]
    assert out.valid.all()
    assert torch.allclose((out.active_affine[:,:,None]*wheels[:,ids,:2]).sum(1),wheels[:,active,:2].double(),atol=1e-6)
    com=(fractions[:,:,None]*wheels[:,ids,:2]).sum(1)
    moment=(out.unprojected_fz[:,:,None]*wheels[:,:,:2]).sum(1)+30*wheels[:,active,:2]
    assert torch.allclose(moment,(330*com).double(),atol=1e-5)
    assert out.moment_residual_xy.abs().max()<1e-5
    transformed=wheels.clone();transformed[:,:,0]=-wheels[:,:,1]+2.;transformed[:,:,1]=wheels[:,:,0]-3.
    other=call(raw,fractions,a,transformed)
    assert torch.allclose(other.target_fz,out.target_fz,atol=2e-4)


def test_airborne_and_projected_residual():
    raw=torch.tensor([[0.,100.,100.,100.]],dtype=torch.float64)
    out=call(raw,raw.new_tensor([[.4,.4,.2]]),torch.tensor([0]),rectangle())
    assert torch.allclose(out.target_fz,raw.new_tensor([[0.,120.,120.,60.]]))
    raw[0,0]=200
    out=call(raw,raw.new_tensor([[.05,.05,.9]]),torch.tensor([0]),rectangle())
    expected=((out.target_fz-out.unprojected_fz)[:,:,None]*rectangle()[:,:,:2]).sum(1)
    assert torch.allclose(out.moment_residual_xy,expected,atol=1e-8)
    assert expected.abs().max()>1 and out.target_fz[:,1:].min()>=45


@pytest.mark.parametrize('case',['nan','degenerate'])
def test_bad_geometry_freezes_only_affected_row(case):
    wheels=rectangle().repeat(2,1,1)
    if case=='nan':wheels[1,0,2]=float('nan')
    else:wheels[1,:,1]=0
    raw=torch.full((2,4),100.,dtype=torch.float64)
    old=raw.new_tensor([[0.,.001,-.001,0.]]).repeat(2,1)
    out=call(raw,raw.new_tensor([[.4,.4,.2]]).repeat(2,1),torch.zeros(2,dtype=torch.long),wheels,old)
    assert out.valid.tolist()==[True,False]
    assert torch.equal(out.offset[1],old[1])
    for field in ('unprojected_fz','active_affine','moment_residual_xy'):
        assert torch.equal(getattr(out,field)[1],torch.zeros_like(getattr(out,field)[1]))


@pytest.mark.parametrize('case',['shape','dtype','device'])
def test_geometry_contract_is_required(case):
    raw=torch.full((1,4),100.,dtype=torch.float64);wheels=rectangle()
    if case=='shape':wheels=wheels[:,:3]
    if case=='dtype':wheels=wheels.float()
    if case=='device':wheels=wheels.to('meta')
    with pytest.raises(ValueError):call(raw,raw.new_tensor([[.4,.4,.2]]),torch.tensor([0]),wheels)


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_frozen_v21_frame114_asymmetric_measured_geometry(dtype):
    # Raw preparation_input from archived v21 env1 frame114, not commanded/FK positions.
    wheels=torch.tensor([[[-25.528789520263672,-151.8015899658203,.0977272167801857],
        [-25.58171272277832,-152.2165985107422,.09777612239122391],
        [-26.32332420349121,-151.80377197265625,.09801492094993591],
        [-26.304149627685547,-152.21885681152344,.09804373234510422]]],dtype=dtype)
    raw=wheels.new_tensor([[69.0726318359375,99.378662109375,144.45980834960938,87.47252655029297]])
    fractions=wheels.new_tensor([[.4785897433757782,.429627925157547,.09178229421377182]])
    out=call(raw,fractions,torch.tensor([0]),wheels)
    assert out.valid.all()
    assert torch.allclose(out.target_fz,wheels.new_tensor([[0.,115.6548932264,102.9935544199,112.6625493630]]),atol=1e-4,rtol=0)
    assert out.velocity[0,3]<0 and out.moment_residual_xy.abs().max()<1e-4


def test_near_collinear_float32_preserves_force_and_reports_true_moment():
    wheels=torch.tensor([[[.3,.2,.1],[0.,0.,.1],[1.,1.,.1],[1.,1.+1e-7,.1]]],dtype=torch.float32)
    raw=wheels.new_tensor([[60.,100.,100.,100.]])
    fractions=wheels.new_tensor([[.4,.4,.2]])
    out=call(raw,fractions,torch.tensor([0]),wheels)
    assert out.valid.all()
    assert abs(out.unprojected_fz.double().sum().item()-300.)<1e-5
    xy=wheels.double()[:,:,:2];lam=fractions.double()/fractions.double().sum(-1,keepdim=True)
    expected=(out.target_fz.double()[:,:,None]*xy).sum(1)+60*xy[:,0]-360*(lam[:,:,None]*xy[:,1:]).sum(1)
    assert torch.allclose(out.moment_residual_xy.double(),expected,atol=1e-5,rtol=0)
