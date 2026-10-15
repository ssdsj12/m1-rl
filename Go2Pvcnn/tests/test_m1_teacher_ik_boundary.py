"""Legal candidate boundary steps, not relaxed residual or final clipping."""
import json
from pathlib import Path
import pytest
import torch
from ame_baseline.m1_teacher_ik import IKConfig,IKReason,body_feet,solve_constrained_ik
from extension.parallelism.m1_kinematics import m1_joint_limit_mask
from test_m1_teacher_ik import nominal
from ame_baseline import m1_teacher_ik as ik


@pytest.mark.parametrize('frame',[123,126])
@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_real_v25_same_target_has_legal_boundary_solution(frame,dtype):
    data=json.loads((Path(__file__).parent/'fixtures/m1_v25_boundary.json').read_text())
    case=next(c for c in data['cases'] if c['frame']==frame)
    q=torch.tensor([case['q']],dtype=dtype)
    target=torch.tensor([case['target']],dtype=dtype)
    branch=torch.tensor([case['branch']],dtype=dtype)
    result=solve_constrained_ik(q,target,branch,tolerance_m=q.new_full((1,4),.0001))
    assert result.valid.all()
    assert (result.residual_m<=.0001).all()
    assert (result.q[:,2::3].abs()>=.1).all()
    assert (result.q[:,2::3]*branch[:,2::3]>0).all()
    assert m1_joint_limit_mask(result.q).all()
    assert ((result.q-q).abs()<=.05).all()


@pytest.mark.parametrize('leg',range(4))
@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('minimum',[.1,.3])
def test_four_leg_configured_boundary_preserves_legal_domain(leg,dtype,minimum):
    q=nominal(dtype=dtype)
    sign=q[0,3*leg+2].sign()
    q[0,3*leg+2]=sign*(minimum+.00015)
    desired=q.clone()
    desired[0,3*leg]+=.0003
    desired[0,3*leg+1]+=.0004
    desired[0,3*leg+2]=sign*(minimum+.000001)
    target=body_feet(desired)
    result=solve_constrained_ik(q,target,q,IKConfig(min_knee_abs_rad=minimum),
                              tolerance_m=q.new_full((1,4),.0001))
    assert result.valid.all()
    assert (result.q[:,2::3].abs()>=minimum).all()
    assert (result.q[:,2::3]*q[:,2::3]>0).all()
    assert m1_joint_limit_mask(result.q).all()
    assert ((target-body_feet(result.q)).norm(dim=-1)<=.0001).all()


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_boundary_step_does_not_repair_invalid_seed_or_unreachable_target(dtype):
    q=nominal(3,dtype);branch=q.clone()
    q[0,8]=.099
    q[1,8]=float('nan')
    target=body_feet(nominal(3,dtype));target[2,2,2]=-2.
    result=solve_constrained_ik(q,target,branch,tolerance_m=q.new_full((3,4),.0001))
    assert not result.valid.any()
    assert result.reason[0,2]==IKReason.NEAR_STRAIGHT
    assert result.reason[1,2]==IKReason.NONFINITE
    assert result.reason[2,2]==IKReason.WORKSPACE
    assert result.q[0,8]==q[0,8]


@pytest.mark.parametrize('leg',range(4))
@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_outward_infinite_candidate_is_not_projected_into_valid_solution(monkeypatch,leg,dtype):
    q=nominal(dtype=dtype);sign=q[0,3*leg+2].sign()
    q[0,3*leg+2]=sign*.12
    desired=q.clone();desired[0,3*leg+2]=sign*.1
    target=body_feet(desired)
    def nonfinite_proposal(jacobian,error,damping,component_limit):
        step=torch.zeros_like(error)
        step[:,leg,2]=-sign*float('inf')
        return step
    monkeypatch.setattr(ik,'dls_step',nonfinite_proposal)
    result=solve_constrained_ik(q,target,q,tolerance_m=q.new_full((1,4),.0001))
    assert not result.valid.any()
    assert torch.equal(result.q,q)
