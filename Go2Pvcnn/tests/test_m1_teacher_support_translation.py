import pytest
import torch
from ame_baseline.m1_teacher_pose import BodyPose,PoseReference,_rotation
from ame_baseline.m1_teacher_execution_targets import execution_targets
from ame_baseline.m1_teacher_ik import body_feet
from test_m1_teacher_execution_targets import fixture


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
def test_crossing_support_xy_tracks_translation_not_pose_rotation(dtype,active):
    q,cmd,measured=fixture(dtype)
    # Pure roll isolates the retained tilt/translation contract; yaw has its
    # own bounded feedback tests rather than the former yaw-insensitivity.
    quat=q.new_tensor([[.99,-.07,0.,0.]])
    measured=BodyPose(measured.pos_w,quat/quat.norm(dim=-1,keepdim=True))
    cmd=PoseReference(BodyPose(cmd.body.pos_w+q.new_tensor([[.02,-.03,0.]]),cmd.body.quat_w),cmd.wheels_w)
    height=cmd.wheels_w[:,:,2]-.002
    off=q.new_zeros(1,4);ids=[j for j in range(4) if j!=active]
    off[:,ids[0]]=.001;off[:,ids[1]]=-.001
    fraction=q.new_tensor([.25])
    result=execution_targets(cmd,measured,torch.tensor([active]),q,fraction,torch.tensor([1]),
        support_reference_w_z=height,support_offset_w_z=off,support_heave_w_z=q.new_tensor([-.003]))
    world=measured.pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(measured.quat_w),result.body_goal)
    expected=cmd.wheels_w+measured.pos_w[:,None]-cmd.body.pos_w[:,None]
    torch.testing.assert_close(world[:,ids,:2],expected[:,ids,:2],atol=2e-7,rtol=0)
    torch.testing.assert_close(world[:,ids,2],(height+off-.003)[:,ids],atol=2e-7,rtol=0)
    torch.testing.assert_close(world[:,active],cmd.wheels_w[:,active],atol=2e-7,rtol=0)
    torch.testing.assert_close(result.body_step,body_feet(q)+.25*(result.body_goal-body_feet(q)))


@pytest.mark.parametrize('mode',[1,2])
def test_translation_gate_keeps_restore_and_missing_height_legacy(mode):
    q,cmd,m=fixture()
    plain=execution_targets(cmd,m,torch.tensor([0]),q,q.new_ones(1),torch.tensor([mode]))
    if mode==1:
        expected=torch.einsum('bij,bkj->bki',_rotation(cmd.body.quat_w).transpose(-1,-2),cmd.wheels_w-cmd.body.pos_w[:,None])
        torch.testing.assert_close(plain.body_goal[:,1:],expected[:,1:])
    else:
        height=cmd.wheels_w[:,:,2]
        out=execution_targets(cmd,m,torch.tensor([0]),q,q.new_ones(1),torch.tensor([mode]),support_reference_w_z=height)
        transform=lambda v:m.pos_w[:,None]+torch.einsum('bij,bkj->bki',_rotation(m.quat_w),v)
        torch.testing.assert_close(transform(out.body_goal)[:,:,:2],transform(plain.body_goal)[:,:,:2])


def test_mixed_modes_match_individual_rows_and_invalid_command_stays_invalid():
    q,c,m=fixture()
    q=q.repeat(3,1)
    cmd=PoseReference(BodyPose(c.body.pos_w.repeat(3,1),c.body.quat_w.repeat(3,1)),c.wheels_w.repeat(3,1,1))
    measured=BodyPose(m.pos_w.repeat(3,1),m.quat_w.repeat(3,1))
    active=torch.tensor([0,2,3]);mode=torch.tensor([1,2,1]);frac=q.new_tensor([.25,.5,1.])
    height=cmd.wheels_w[:,:,2]
    combined=execution_targets(cmd,measured,active,q,frac,mode,support_reference_w_z=height)
    for i in range(3):
        ci=PoseReference(BodyPose(cmd.body.pos_w[i:i+1],cmd.body.quat_w[i:i+1]),cmd.wheels_w[i:i+1])
        mi=BodyPose(measured.pos_w[i:i+1],measured.quat_w[i:i+1])
        one=execution_targets(ci,mi,active[i:i+1],q[i:i+1],frac[i:i+1],mode[i:i+1],support_reference_w_z=height[i:i+1])
        torch.testing.assert_close(combined.body_goal[i:i+1],one.body_goal)
    bad=PoseReference(BodyPose(cmd.body.pos_w,cmd.body.quat_w*2),cmd.wheels_w)
    out=execution_targets(bad,measured,active,q,frac,mode,support_reference_w_z=height)
    assert not torch.isfinite(out.body_goal).all(-1).all(-1).any()


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('measured_yaw',[0.,.08])
def test_global_yaw_translation_equivariance(dtype,measured_yaw):
    import math
    q,c,m=fixture(dtype)
    if measured_yaw:
        m=BodyPose(m.pos_w,q.new_tensor([[math.cos(measured_yaw/2),0.,0.,math.sin(measured_yaw/2)]]))
    z=q.new_tensor([[math.cos(.35),0.,0.,math.sin(.35)]])
    rz=_rotation(z);shift=q.new_tensor([[100.,-152.,.7]])
    def yaw_quat(quat):
        w,x,y,k=quat.unbind(-1);a=z[:,0];b=z[:,3]
        return torch.stack((a*w-b*k,a*x-b*y,a*y+b*x,a*k+b*w),-1)
    def move(body):
        return BodyPose(torch.einsum('bij,bj->bi',rz,body.pos_w)+shift,yaw_quat(body.quat_w))
    moved=PoseReference(move(c.body),torch.einsum('bij,bkj->bki',rz,c.wheels_w)+shift[:,None])
    args=(torch.tensor([0]),q,q.new_tensor([.375]),torch.tensor([1]))
    original=execution_targets(c,m,*args,support_reference_w_z=c.wheels_w[:,:,2])
    result=execution_targets(moved,move(m),*args,support_reference_w_z=c.wheels_w[:,:,2]+.7)
    torch.testing.assert_close(result.body_goal,original.body_goal,atol=3e-5 if dtype==torch.float32 else 1e-12,rtol=0)
    torch.testing.assert_close(result.body_step,original.body_step,atol=3e-5 if dtype==torch.float32 else 1e-12,rtol=0)


def evidence_sample(phase='LIFT', yaw=None, quat_scale=1.):
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_teacher_probe_contract import probe
    from ame_baseline.m1_ame_contract import m1_action_targets
    p=probe();teacher,s=load_teacher(phase)
    s.root_quat_w[0]=s.root_pos_w.new_tensor([.9999968750016276,.002499997395834147,0.,0.])
    if yaw is not None:
        import math
        s.root_quat_w[0]=s.root_pos_w.new_tensor([math.cos(yaw/2),0.,0.,math.sin(yaw/2)])*quat_scale
    p.observe_feedback_transactions(teacher);p.observe_dynamic_support(teacher)
    out=teacher.step(s);assert out.valid.item()
    sample=dict(dynamic_support=p.dynamic_context_for(teacher,s,0),feedback_context=p.feedback_context_for(teacher,s,0),
        teacher_diagnostic=p.diagnostic_json(out.diagnostic[0].tolist()),teacher_action=out.action[0].tolist(),
        applied_targets=m1_action_targets(out.action,s.default_joint_pos)[0].tolist(),preparation_input=p.readiness_measurement(s,0,0.),
        action_target_dtype='float32',phase=int(out.phase[0]),teacher_input_frame=int(s.control_step[0]),
        teacher_input_episode_id=int(s.episode_id[0]),teacher_input_leg_pos=s.leg_pos[0].tolist(),
        last_applied_leg_target=s.last_applied_leg_target[0].tolist(),action_default_joint_pos=s.default_joint_pos[0].tolist())
    return p,teacher,sample


@pytest.mark.parametrize('phase',['LIFT','RESTORE'])
def test_nonzero_rotation_transaction_matches_independent_audit(phase):
    p,t,s=evidence_sample(phase)
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]


@pytest.mark.parametrize('kind',['goal','step'])
def test_corrupted_support_xy_is_rejected(kind):
    p,t,s=evidence_sample()
    s['teacher_diagnostic'][f'execution_body_{kind}_3_y']+=.01
    assert p.verify_feedback_transaction(s,t.cfg)
