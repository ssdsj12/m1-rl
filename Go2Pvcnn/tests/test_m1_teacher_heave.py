import pytest
import torch

def propose(command,measured,error,old,dt=.02,restore=False,valid=True):
    from ame_baseline.m1_teacher_heave import propose_support_heave
    t=lambda v:torch.tensor([v],dtype=torch.float64)
    return propose_support_heave(t(command),t(measured),t(error),t(old),t(dt),
        torch.tensor([restore]),torch.tensor([valid]))

@pytest.mark.parametrize('difference,expected',[(.001,-.0004),(-.001,.0004),(0.,0.)])
def test_heave_negative_feedback_and_rate(difference,expected):
    out=propose(.62+difference,.60,.02,0.)
    assert out.valid.item()
    assert out.offset.item()==pytest.approx(expected,abs=1e-12)

@pytest.mark.parametrize('old,expected',[(.0199,.02),(-.0199,-.02)])
def test_heave_amplitude_bound(old,expected):
    out=propose(-1. if old>0 else 1.,0.,0.,old)
    assert out.offset.item()==pytest.approx(expected)

def test_first_captured_error_has_no_jump():
    assert abs(propose(.607,.599,.607-.599,0.).offset.item())<1e-12

@pytest.mark.parametrize('old,expected',[(.001,.0006),(-.001,-.0006),(.0001,0.)])
def test_restore_decays_without_overshoot(old,expected):
    assert propose(.62,.4,0.,old,restore=True).offset.item()==pytest.approx(expected)

@pytest.mark.parametrize('bad',['command_nan','measurement_nan','invalid'])
def test_invalid_measurement_freezes_heave(bad):
    out=propose(float('nan') if bad=='command_nan' else .62,
                float('nan') if bad=='measurement_nan' else .60,.02,.001,valid=bad!='invalid')
    assert not out.valid.item() and out.offset.item()==.001

@pytest.mark.parametrize('bad',['old_nan','old_limit','dt_zero','baseline_nan','shape','dtype','flag'])
def test_heave_rejects_invalid_contract(bad):
    from ame_baseline.m1_teacher_heave import propose_support_heave
    values=[torch.tensor([v],dtype=torch.float64) for v in (.62,.60,.02,0.,.02)]
    flags=[torch.tensor([False]),torch.tensor([True])]
    if bad=='old_nan':values[3][0]=float('nan')
    if bad=='old_limit':values[3][0]=.0201
    if bad=='dt_zero':values[4][0]=0
    if bad=='baseline_nan':values[2][0]=float('nan')
    if bad=='shape':values[0]=values[0][:,None]
    if bad=='dtype':values[1]=values[1].float()
    if bad=='flag':flags[0]=flags[0].long()
    with pytest.raises(ValueError):propose_support_heave(*values,*flags)

@pytest.mark.parametrize('active',range(4))
@pytest.mark.parametrize('mode',[1,2])
@pytest.mark.parametrize('beta',[1.,.25])
def test_heave_changes_only_common_support_z_once(active,mode,beta):
    from test_m1_teacher_load_feedback_transaction import fixture
    from ame_baseline.m1_teacher_execution_targets import execution_targets
    from ame_baseline.m1_teacher_pose import _rotation
    q,ref=fixture();height=ref.wheels_w[:,:,2]
    args=(ref,ref.body,torch.tensor([active]),q,q.new_tensor([beta]),torch.tensor([mode]))
    old=execution_targets(*args,support_reference_w_z=height)
    new=execution_targets(*args,support_reference_w_z=height,support_heave_w_z=q.new_tensor([-.003]))
    change=torch.einsum('bij,bkj->bki',_rotation(ref.body.quat_w),new.body_goal-old.body_goal)
    support=[j for j in range(4) if j!=active]
    assert change[:,:,:2].abs().max()<1e-12
    assert change[:,active].abs().max()<1e-12
    assert torch.allclose(change[:,support,2],q.new_full((1,3),-.003),atol=1e-12,rtol=0)
    assert torch.allclose(new.body_step-old.body_step,beta*(new.body_goal-old.body_goal),atol=1e-12,rtol=0)

@pytest.mark.parametrize('bad',['without_height','shape','nan','limit'])
def test_invalid_heave_target_rejected(bad):
    from test_m1_teacher_load_feedback_transaction import fixture
    from ame_baseline.m1_teacher_execution_targets import execution_targets
    q,ref=fixture();height=ref.wheels_w[:,:,2];heave=q.new_tensor([0.])
    if bad=='without_height':height=None
    if bad=='shape':heave=heave[:,None]
    if bad=='nan':heave[0]=float('nan')
    if bad=='limit':heave[0]=.021
    with pytest.raises(ValueError):
        execution_targets(ref,ref.body,torch.tensor([0]),q,q.new_ones(1),torch.tensor([1]),
            support_reference_w_z=height,support_heave_w_z=heave)
