"""Actual v26 failures must converge without changing targets or budget."""
import json
from pathlib import Path
import pytest
import torch
from ame_baseline.m1_teacher_ik import solve_constrained_ik
from extension.parallelism.m1_kinematics import m1_joint_limit_mask
from ame_baseline import m1_teacher_ik as ik

@pytest.mark.parametrize('frame',[133,134,137])
@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_real_v26_same_target_converges_inside_existing_budget(frame,dtype):
    data=json.loads((Path(__file__).parent/'fixtures/m1_v26_tangent.json').read_text())
    c=next(c for c in data['cases'] if c['frame']==frame)
    q=torch.tensor([c['q']],dtype=dtype)
    target=torch.tensor([c['target']],dtype=dtype)
    branch=torch.tensor([c['branch']],dtype=dtype)
    result=solve_constrained_ik(q,target,branch,tolerance_m=q.new_full((1,4),.0001))
    assert result.valid.all()
    assert (result.residual_m<=.0001).all()
    assert (result.iterations<=32).all()
    assert (result.q[:,2::3].abs()>=.1).all()
    assert (result.q[:,2::3]*branch[:,2::3]>0).all()
    assert m1_joint_limit_mask(result.q).all()
    assert ((result.q-q).abs()<=.05).all()

@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('frame',[118,122])
def test_interior_trace_never_uses_tangent_candidate(monkeypatch,frame,dtype):
    data=json.loads((Path(__file__).parent/'fixtures/m1_v26_tangent.json').read_text())
    c=next(c for c in data['cases'] if c['frame']==frame)
    q=torch.tensor([c['q']],dtype=dtype);target=torch.tensor([c['target']],dtype=dtype)
    branch=torch.tensor([c['branch']],dtype=dtype)
    original=ik.dls_step
    def no_tangent(jacobian,*args):
        assert jacobian.shape[-1]==3
        return original(jacobian,*args)
    monkeypatch.setattr(ik,'dls_step',no_tangent)
    result=solve_constrained_ik(q,target,branch,tolerance_m=q.new_full((1,4),.0001))
    assert result.valid.all()

@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_nonfinite_tangent_keeps_legal_normal_candidate(monkeypatch,dtype):
    data=json.loads((Path(__file__).parent/'fixtures/m1_v25_boundary.json').read_text())
    c=next(c for c in data['cases'] if c['frame']==123)
    q=torch.tensor([c['q']],dtype=dtype);target=torch.tensor([c['target']],dtype=dtype)
    branch=torch.tensor([c['branch']],dtype=dtype);original=ik.dls_step;calls=[]
    def bad_tangent(jacobian,error,*args):
        if jacobian.shape[-1]==2:
            calls.append(True)
            return torch.full_like(error[...,:2],float('nan'))
        return original(jacobian,error,*args)
    monkeypatch.setattr(ik,'dls_step',bad_tangent)
    result=solve_constrained_ik(q,target,branch,tolerance_m=q.new_full((1,4),.0001))
    assert calls
    assert result.valid.all()
    assert torch.isfinite(result.q).all()
    assert (result.residual_m<=.0001).all()

def test_tangent_iterates_preserve_monotonicity_and_component_bound(monkeypatch):
    data=json.loads((Path(__file__).parent/'fixtures/m1_v26_tangent.json').read_text())
    c=next(c for c in data['cases'] if c['frame']==137)
    q=torch.tensor([c['q']],dtype=torch.float64);target=torch.tensor([c['target']],dtype=q.dtype)
    branch=torch.tensor([c['branch']],dtype=q.dtype);states=[];original=ik.body_jacobian
    def record(value,*args):
        states.append(value.clone())
        return original(value,*args)
    monkeypatch.setattr(ik,'body_jacobian',record)
    result=solve_constrained_ik(q,target,branch,tolerance_m=q.new_full((1,4),.0001))
    states.append(result.q)
    assert result.valid.all()
    for before,after in zip(states,states[1:]):
        assert ((after-before).abs()<=.25).all()
        assert ((target-ik.body_feet(after)).norm(dim=-1)
                <= (target-ik.body_feet(before)).norm(dim=-1)).all()
        assert m1_joint_limit_mask(after).all()
        assert (after[:,2::3].abs()>=.1).all()
