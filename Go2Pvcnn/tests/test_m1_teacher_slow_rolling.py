"""Slow rolling control tests; ideal fixtures are not physical crossing proof."""
from dataclasses import replace
import math

import pytest
import torch

from test_m1_reference_teacher import api, state, advance
from test_m1_teacher_reference_commit import near_state, prepared_teacher, feedback


def slow_config():
    return api().TeacherConfig(slow_rolling=True)


def wheel_speeds(out, s):
    t = api()
    from ame_baseline.m1_ame_contract import m1_action_targets
    return m1_action_targets(out.action, s.default_joint_pos)[:, t.WHEEL_COLUMNS]*t.M1_WHEEL_RADIUS_M


def test_slow_approach_is_slew_limited_from_rest():
    t = api(); teacher = t.ReferenceTeacher(slow_config()); s = state(targets=False)
    previous = torch.zeros(1, 4)
    for _ in range(30):
        out = teacher.step(s); speed = wheel_speeds(out, s)
        assert out.valid.all()
        assert (speed > 0).all() and (speed <= .050001).all()
        assert ((speed-previous).abs() <= .002001).all()
        previous = speed
        s = feedback(s, teacher, out)
    assert torch.allclose(previous, torch.full_like(previous,.05))


@pytest.mark.parametrize("phase", ["BALANCE", "LIFT", "PASS", "RESTORE"])
def test_normal_phases_keep_slow_positive_wheel_command(phase):
    t=api(); teacher,s,_=prepared_teacher(rolling=True)
    teacher.cfg=slow_config()
    teacher._rows[0].update(phase=getattr(t.Phase,phase),last_surface_speed=torch.full((1,4),.05))
    s.root_lin_vel_w[:,0]=.05
    out=teacher.step(s)
    assert out.valid.all() and not out.failure_locked.any()
    assert torch.allclose(wheel_speeds(out,s),torch.full((1,4),.05),atol=1e-6)


def test_capture_does_not_require_zero_forward_velocity():
    t=api(); teacher=t.ReferenceTeacher(slow_config()); s=near_state()
    s.root_lin_vel_w[:,0]=.05
    first=teacher.step(s)
    s=feedback(s,teacher,first)
    out=teacher.step(s)
    assert teacher._rows[0]['prepared']
    assert out.valid.all() and (wheel_speeds(out,s)>0).all()


@pytest.mark.parametrize("yaw", [0., math.pi/2])
def test_rolling_transport_moves_reference_but_preserves_lateral_slip(yaw):
    t=api(); teacher,s,_=prepared_teacher(); teacher.cfg=slow_config()
    work=dict(teacher._rows[0]); work['yaw']=torch.tensor([yaw])
    accepted=work['accepted']; old_anchor=work['anchor'].clone()
    old_wheels=work['wheel_anchor'].clone(); old_origin=work['support_origin'].clone()
    old_pose=work['anchor_pose'].pos_w.clone()
    forward=torch.tensor([[math.cos(yaw),math.sin(yaw),0.]])
    sideways=torch.tensor([[-math.sin(yaw),math.cos(yaw),0.]])
    actual=work['support_previous']+.003*forward[:,None]+.007*sideways[:,None]
    evidence={}
    updated=teacher._transport_rolling(work,accepted,actual,[1,2,3],evidence)
    delta=.003*forward
    assert torch.allclose(updated.body.pos_w,accepted.body.pos_w+delta,atol=1e-7)
    assert torch.allclose(work['anchor'],old_anchor+delta,atol=1e-7)
    assert torch.allclose(work['anchor_pose'].pos_w,old_pose+delta,atol=1e-7)
    assert torch.allclose(work['support_origin'],old_origin+delta,atol=1e-7)
    assert torch.allclose(work['wheel_anchor'],old_wheels+delta[:,None],atol=1e-7)
    assert torch.allclose(evidence['slip'][:,1:,:2],(.007*sideways[:,None,:2]).expand(1,3,2),atol=1e-7)
    assert torch.equal(teacher._rows[0]['wheel_anchor'],old_wheels)


def test_collision_stops_and_does_not_commit_transport():
    t=api(); teacher,s,_=prepared_teacher(); teacher.cfg=slow_config()
    row=teacher._rows[0]; row['last_surface_speed']=torch.full((1,4),.05)
    before=row['wheel_anchor'].clone()
    s.wheel_pos_w[:,:,0]+=.003; s.collision[:]=True
    out=teacher.step(s)
    assert out.failure_locked.all()
    assert torch.equal(wheel_speeds(out,s),torch.zeros(1,4))
    assert torch.equal(row['wheel_anchor'],before)
    assert torch.equal(row['last_surface_speed'],torch.zeros(1,4))


def test_probe_explicitly_selects_slow_rolling_config():
    from test_m1_teacher_probe_contract import probe
    p=probe()
    cfg=p.probe_teacher_config(slow_rolling=True)
    assert cfg.slow_rolling and cfg.rolling_speed_m_s==.05
    assert not p.probe_teacher_config(slow_rolling=False).slow_rolling


@pytest.mark.parametrize("scope", ["flat-preparation","single-wheel"])
def test_probe_rejects_rolling_local_diagnostic(scope):
    from test_m1_teacher_probe_contract import probe
    with pytest.raises(ValueError,match="course"):
        probe().probe_teacher_config(slow_rolling=True,scope=scope)


def test_readiness_verifier_uses_rolling_velocity_error():
    from test_m1_teacher_probe_contract import probe
    s=near_state(); s.root_lin_vel_w[:,0]=.08
    teacher=api().ReferenceTeacher(slow_config())
    assert teacher._quiet(s,0,rolling=True)
    assert not teacher._quiet(s,0,rolling=False)
    pose=s.root_pos_w[0].tolist()+s.root_quat_w[0].tolist()
    diagnostic={'reference_valid':1,'preparation_ready':1}
    for prefix in ('preparation_prior_root_','preparation_goal_root_','accepted_root_'):
        diagnostic.update({prefix+key:value for key,value in zip(('x','y','z','qw','qx','qy','qz'),pose)})
    def measured(frame,time):
        return dict(env_id=0,episode_id=0,frame=frame,sim_time=time,
                    root=pose+[.08,0.,0.]+[0.,0.,0.],com=s.com_pos_w[0].tolist(),
                    wheels=s.wheel_pos_w[0].tolist(),forces=s.wheel_force_w[0].tolist(),measurement_valid=True)
    sample=dict(env_id=0,episode_id=0,frame=1,sim_time=.02,teacher_input_frame=0,teacher_input_sim_time=0.,
                active_wheel=0,teacher_diagnostic=diagnostic,failure_locked=False,
                collision=False,support_lost=False,penetration=False,failure=False,
                preparation_input=measured(0,0.),preparation_output=measured(1,.02))
    sample.update(root=sample['preparation_output']['root'],
                  wheel_position=sample['preparation_output']['wheels'],
                  force=sample['preparation_output']['forces'],
                  Fz=[f[2] for f in sample['preparation_output']['forces']])
    assert probe().preparation_observed(sample,teacher.cfg)
    assert not probe().preparation_observed(sample,api().TeacherConfig())


@pytest.mark.parametrize("phase", ["BALANCE", "LIFT"])
def test_unready_wheel_stops_before_consuming_obstacle_gap(phase):
    t=api(); teacher,s,_=prepared_teacher(); teacher.cfg=slow_config()
    row=teacher._rows[0]
    row.update(phase=getattr(t.Phase,phase),last_surface_speed=torch.full((1,4),.05))
    before=row['wheel_anchor'].clone()
    # Actual near-side gap has reached 6 cm; the wheel bottom is still low.
    s.centers_top[:,0,0]=s.wheel_pos_w[:,0,0]+s.half_extents[:,0,0]+t.M1_WHEEL_HORIZONTAL_ENVELOPE_M+.059
    s.centers_top[:,0,2]=1.
    s.root_lin_vel_w[:,0]=.05
    out=teacher.step(s)
    assert out.failure_locked.all()
    assert out.reason.item()==t.Reason.APPROACH_UNREADY
    assert torch.equal(wheel_speeds(out,s),torch.zeros(1,4))
    assert torch.equal(row['wheel_anchor'],before)
    assert not s.collision.any()


def test_rejected_ik_rolls_back_transport_then_retries_once(monkeypatch):
    import ame_baseline.m1_teacher_pose as p
    t=api(); teacher,s,_=prepared_teacher(); teacher.cfg=slow_config()
    row=teacher._rows[0]
    row.update(phase=t.Phase.RESTORE,last_surface_speed=torch.full((1,4),.05))
    before=row['wheel_anchor'].clone(); previous=row['support_previous'].clone()
    delta=s.root_pos_w.new_tensor([[.003,0.,0.]])
    s=replace(s,root_pos_w=s.root_pos_w+delta,com_pos_w=s.com_pos_w+delta,
              wheel_pos_w=s.wheel_pos_w+delta[:,None])
    real=p.solve_constrained_ik
    with monkeypatch.context() as patch:
        patch.setattr(p,'solve_constrained_ik',lambda *a,**kw: replace(real(*a,**kw),valid=torch.tensor([False])))
        out=teacher.step(s)
    assert out.reason.item()==t.Reason.IK_INVALID
    assert torch.equal(row['wheel_anchor'],before)
    assert torch.equal(row['support_previous'],previous)
    assert torch.equal(row['last_surface_speed'],torch.zeros(1,4))
    out=teacher.step(advance(s))
    assert out.valid.all()
    assert torch.allclose(row['wheel_anchor'],before+delta[:,None],atol=1e-7)
    assert torch.allclose(wheel_speeds(out,s),torch.full((1,4),.002),atol=1e-7)
