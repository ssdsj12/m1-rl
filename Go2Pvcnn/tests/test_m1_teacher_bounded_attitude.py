"""Bounded orientation pool plus a recorded physical failure's real IK search."""
import json
from pathlib import Path
import math
import pytest
import torch
from ame_baseline import m1_teacher_pose as pose
from ame_baseline import m1_reference_teacher as teacher
from ame_baseline.m1_teacher_ik import IKConfig
from ame_baseline.m1_teacher_tripod_load import tripod_load
from test_m1_teacher_pose import setup,quat
from test_m1_teacher_probe_contract import probe


def frozen_args(monkeypatch):
    raw=json.loads((Path(__file__).parent/'fixtures/m1_v34_attitude130.json').read_text())
    assert raw['source_archive_sha256']=='ba2001283bbc209910d865bdeef8280685ecef290179ffceb2f6d377ce3168db'
    p=probe();c=raw['dynamic_support'];t=teacher.ReferenceTeacher(teacher.TeacherConfig(slow_rolling=True,load_feedback=True))
    t._rows=[p._dynamic_unpack(c['pre'],'cpu')]
    s=teacher.TeacherState(**p._dynamic_unpack(c['input'],'cpu'))
    captured=[]
    def capture(*args,**kw):
        captured.append((args,kw));return pose.choose_support_pose(*args,**kw)
    monkeypatch.setattr(teacher,'choose_support_pose',capture)
    t._step_row(s,0,None)
    assert len(captured)==1
    return captured[0]


@pytest.mark.parametrize('yaw',[-2.3,0.,1.7])
def test_nine_fixed_orientations_preserve_heading_and_bound(yaw):
    q=pose._bounded_attitude_quaternions(torch.tensor([yaw],dtype=torch.float64))
    assert q.shape==(1,9,4)
    assert torch.allclose(q.norm(dim=-1),torch.ones(1,9,dtype=q.dtype))
    assert torch.allclose(q[:,0],quat(y=yaw))
    assert len(torch.unique(q[0],dim=0))==9
    r=pose._rotation(q.reshape(-1,4))
    assert torch.all(r[:,2,2]>=math.cos(.15))
    actual_yaw=torch.atan2(r[:,1,0],r[:,0,0])
    assert torch.allclose(actual_yaw,torch.full_like(actual_yaw,yaw))


@pytest.mark.parametrize('active',range(4))
def test_pool_has1126_and_preserves_anchors(active):
    q,body,ref=setup(pose);support=[j for j in range(4) if j!=active]
    anchors=ref.wheels_w.clone()
    choice=pose.choose_support_pose(body,body,body,anchors[:,support].mean(1),anchors,
        torch.tensor([active]),body.pos_w[:,2],q,q,IKConfig(),measured_wheels_w=anchors,
        bounded_attitude=True)
    assert choice.candidate_count.item()==1126
    assert choice.valid.item()
    assert torch.equal(choice.reference.wheels_w,anchors)


@pytest.mark.parametrize('r,y',[(.2,0.),(0.,.2)])
def test_invalid_accepted_tilt_or_heading_not_counted(r,y):
    q,body,ref=setup(pose)
    accepted=pose.BodyPose(body.pos_w,quat(r=r,y=y))
    choice=pose.choose_support_pose(body,body,accepted,ref.wheels_w[:,1:].mean(1),ref.wheels_w,
        torch.tensor([0]),body.pos_w[:,2],q,q,IKConfig(),measured_wheels_w=ref.wheels_w,
        bounded_attitude=True)
    assert choice.candidate_count.item()==1125
    assert choice.valid.item()
    assert choice.candidate_index.item()!=1125


@pytest.mark.parametrize('flag',[1,None,'true'])
def test_mode_requires_real_bool(flag):
    q,b,r=setup(pose)
    with pytest.raises((ValueError,TypeError),match='bounded_attitude'):
        pose.choose_support_pose(b,b,b,r.wheels_w[:,1:].mean(1),r.wheels_w,
            torch.tensor([0]),b.pos_w[:,2],q,q,IKConfig(),measured_wheels_w=r.wheels_w,
            bounded_attitude=flag)


def test_recorded130_level_rejects_bounded_pool_passes_real_ik(monkeypatch):
    args,kw=frozen_args(monkeypatch)
    old=pose.choose_support_pose(*args,**kw)
    explicit=pose.choose_support_pose(*args,**dict(kw,bounded_attitude=False))
    assert not old.valid.item()
    assert torch.equal(old.ik.q,explicit.ik.q)
    new=pose.choose_support_pose(*args,**dict(kw,bounded_attitude=True))
    assert new.valid.item() and new.ik.valid.item()
    measured=args[0];com=args[3];active=args[5]
    offset=torch.einsum('bij,bj->bi',pose._rotation(measured.quat_w).transpose(-1,-2),com-measured.pos_w)
    predicted=new.reference.body.pos_w+torch.einsum('bij,bj->bi',pose._rotation(new.reference.body.quat_w),offset)
    for wheels in (args[4],kw['measured_wheels_w']):
        load=tripod_load(predicted,wheels,active,kw['tripod_total_load_n'])
        assert load.valid.item() and load.min_load_n.item()>30
    assert new.reference.body.quat_w[0,1:3].abs().max()>.01


def test_nonfinite_measured_pose_fails_closed():
    q,b,r=setup(pose);bad=pose.BodyPose(b.pos_w.clone(),b.quat_w.clone());bad.pos_w[0,0]=float('nan')
    out=pose.choose_support_pose(bad,b,b,r.wheels_w[:,1:].mean(1),r.wheels_w,
        torch.tensor([0]),b.pos_w[:,2],q,q,IKConfig(),measured_wheels_w=r.wheels_w,
        bounded_attitude=True)
    assert not out.valid.item()
