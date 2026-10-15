"""Near-boundary measurements may seed a safe solve, never a relaxed output."""
import importlib.util
import pytest
import torch
from ame_baseline.m1_teacher_ik import body_feet,IKConfig

def api():
    assert importlib.util.find_spec('ame_baseline.m1_teacher_seed_recovery') is not None, 'bounded pose seed recovery is missing'
    from ame_baseline.m1_teacher_seed_recovery import recovered_pose_seed,solve_pose_ik
    return recovered_pose_seed,solve_pose_ik

def nominal(dtype):
    return torch.tensor([[0.,.3,-.6,0.,.3,-.6,0.,-.3,.6,0.,-.3,.6]],dtype=dtype)

@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('leg',range(4))
def test_near_boundary_seed_recovers_without_relaxing_solution(leg,dtype):
    recover,solve=api();branch=nominal(dtype);seed=branch.clone()
    sign=branch[0,3*leg+2].sign();seed[0,3*leg+2]=sign*.0975
    target_q=seed.clone();target_q[0,3*leg+2]=sign*.15
    target=body_feet(target_q);saved=seed.clone();cfg=IKConfig()
    initial=recover(seed,target,branch,cfg)
    assert torch.equal(seed,saved)
    mask=torch.ones(12,dtype=torch.bool);mask[3*leg+2]=False
    assert torch.equal(initial[:,mask],seed[:,mask])
    assert initial[0,3*leg+2]*sign>=cfg.min_knee_abs_rad
    result=solve(seed,target,branch,cfg)
    assert result.valid.all()
    assert (result.q[:,2::3].abs()>=cfg.min_knee_abs_rad).all()
    assert (body_feet(result.q)-target).norm(dim=-1).max()<=cfg.ik_tolerance_m

@pytest.mark.parametrize('case',['legal','deep','opposite','zero','nonfinite','hardware'])
def test_unsupported_seed_is_not_rewritten(case):
    recover,_=api();branch=nominal(torch.float64);seed=branch.clone()
    seed[0,2]=-.0975
    if case=='legal':seed[0,2]=-.3
    if case=='deep':seed[0,2]=-.089
    if case=='opposite':seed[0,2]=.0975
    if case=='zero':seed[0,2]=0
    if case=='nonfinite':seed[0,0]=float('nan')
    if case=='hardware':seed[0,0]=10.
    target=body_feet(branch)
    actual=recover(seed,target,branch,IKConfig())
    torch.testing.assert_close(actual,seed,rtol=0,atol=0,equal_nan=True)

@pytest.mark.parametrize('frame,expected',[(132,True),(133,True),(134,True),(137,True)])
def test_actual_v28_transaction_recovery_keeps_execution_gates(frame,expected):
    import json
    from pathlib import Path
    from ame_baseline.m1_reference_teacher import ReferenceTeacher,TeacherConfig,TeacherState,m1_action_targets
    from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig
    from scripts.probe_m1_teacher import _dynamic_unpack,diagnostic_json,verify_execution_geometry,observe_feedback_transactions,feedback_context_for
    data=json.loads((Path(__file__).parent/'fixtures/m1_v28_seed_recovery.json').read_text())
    config=dict(data['config']);config['feedback']=BodyFeedbackConfig(**config['feedback'])
    row=next(r for r in data['cases'] if r['frame']==frame)
    teacher=ReferenceTeacher(TeacherConfig(**config));context=row['dynamic_support']
    teacher._rows=[_dynamic_unpack(context['pre'],'cpu')]
    state=TeacherState(**_dynamic_unpack(context['input'],'cpu'))
    # Explicit zero-delta v33 test transition; original fixture stays immutable.
    teacher._rows[0]['support_capture_root_z']=state.root_pos_w[:,2].clone()
    observe_feedback_transactions(teacher)
    result=teacher._step_row(state,0,None)
    assert bool(result.valid[0])==expected
    if expected:
        d=diagnostic_json(result.diagnostic[0].tolist())
        if frame!=137:
            assert d['execution_active_fraction']==1.
        else:
            # Previously rejected frame now admits a bounded partial step,
            # not a complete lift. Keep the same residual/slew gates below.
            assert d['execution_fraction']<=d['execution_active_fraction']<=1.
        assert all(d[f'ik_residual_m_{j}']<=.0001 for j in range(4))
        attempted=state.leg_pos.new_tensor([[d[f'attempted_q_{j}'] for j in range(12)]])
        assert ((attempted-state.last_applied_leg_target).abs()<=.0500001).all()
        row['teacher_diagnostic']=d
        row['feedback_context']=feedback_context_for(teacher,state,0)
        row['applied_targets']=m1_action_targets(result.action,state.default_joint_pos)[0].tolist()
        verify_execution_geometry(row,TeacherConfig(**config),replay_backend='cpu')
