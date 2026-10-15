"""Catch a selected tilted pose silently replaced by a level execution request."""
import json
from pathlib import Path
from dataclasses import asdict
import pytest
import torch
from ame_baseline import m1_reference_teacher as m
from test_m1_teacher_probe_contract import probe


def frozen_teacher(enabled=True):
    p=probe()
    c=json.loads((Path(__file__).parent/'fixtures/m1_v34_attitude130.json').read_text())['dynamic_support']
    cfg=m.TeacherConfig(slow_rolling=True,load_feedback=True,bounded_crossing_attitude=enabled)
    t=m.ReferenceTeacher(cfg);t._rows=[p._dynamic_unpack(c['pre'],'cpu')]
    s=m.TeacherState(**p._dynamic_unpack(c['input'],'cpu'))
    return t,s


@pytest.mark.parametrize('flag',[1,None,'yes'])
def test_config_rejects_nonbool_mode(flag):
    with pytest.raises(ValueError,match='bounded'):
        m.TeacherConfig(slow_rolling=True,load_feedback=True,bounded_crossing_attitude=flag)


@pytest.mark.parametrize('rolling,load',[(False,False),(True,False)])
def test_config_requires_dynamic_load_feedback(rolling,load):
    with pytest.raises(ValueError,match='bounded'):
        m.TeacherConfig(slow_rolling=rolling,load_feedback=load,bounded_crossing_attitude=True)


def test_probe_mode_roundtrip_and_actual_search_budget():
    p=probe();cfg=p.probe_teacher_config(slow_rolling=True,load_feedback=True,bounded_crossing_attitude=True)
    assert cfg.dynamic_candidate_limit==1126
    assert m.TeacherConfig().dynamic_candidate_limit==126
    data=asdict(cfg);data['feedback']=m.BodyFeedbackConfig(**data['feedback'])
    assert m.TeacherConfig(**data).fingerprint==cfg.fingerprint
    assert cfg.fingerprint!=m.TeacherConfig(slow_rolling=True,load_feedback=True).fingerprint


def test_frozen_selection_reaches_real_transaction_with_slew(monkeypatch):
    t,s=frozen_teacher();real=t._feedback_transaction;seen=[]
    def record(*args,**kw):
        result=real(*args,**kw);seen.append((args[4],result[0]));return result
    monkeypatch.setattr(t,'_feedback_transaction',record)
    out=t._step_row(s,0,None)
    assert seen and seen[0][1].valid.item()
    request,solved=seen[0]
    assert request.body.quat_w[0,1:3].abs().max()>.01
    assert torch.allclose(request.body.quat_w,t._rows[0]['goal'].body.quat_w,atol=1e-7,rtol=0)
    assert (t._rows[0]['last_q']-s.last_applied_leg_target).abs().max()<=.0500001
    assert torch.isfinite(solved.command_ik.q).all()
    assert solved.command_ik.residual_m.max()<=.0001


def test_published_com_uses_selected_orientation(monkeypatch):
    from ame_baseline.m1_teacher_pose import _rotation
    t,s=frozen_teacher();out=t._step_row(s,0,None)
    goal=t._rows[0]['goal'].body
    local=torch.einsum('bij,bj->bi',_rotation(s.root_quat_w).transpose(1,2),s.com_pos_w-s.root_pos_w)
    expected=goal.pos_w+torch.einsum('bij,bj->bi',_rotation(goal.quat_w),local)
    for j,axis in enumerate('xy'):
        actual=out.diagnostic[0,m.TEACHER_DIAGNOSTIC_FIELDS.index('dynamic_com_target_'+axis)]
        assert torch.allclose(actual,expected[0,j],atol=1e-6,rtol=0)


def test_cli_attitude_option_is_explicit_and_validated():
    import argparse
    p=probe();parser=argparse.ArgumentParser();p.add_teacher_motion_options(parser)
    args=parser.parse_args(['--slow-rolling','--load-feedback','--bounded-crossing-attitude'])
    cfg=p.probe_teacher_config(**vars(args))
    assert cfg.bounded_crossing_attitude and cfg.dynamic_candidate_limit==1126
    assert not p.probe_teacher_config(**vars(parser.parse_args([]))).bounded_crossing_attitude
    with pytest.raises(ValueError):
        p.probe_teacher_config(**vars(parser.parse_args(['--bounded-crossing-attitude'])))


def test_legacy_frozen_frame_still_rejects():
    t,s=frozen_teacher(False);before=t._rows[0]['accepted'].body.quat_w.clone()
    t._step_row(s,0,None)
    assert t._rows[0]['invalid_streak']>0
    assert torch.equal(t._rows[0]['accepted'].body.quat_w,before)


def test_duplicate_keeps_selected_pose_and_action():
    t,s=frozen_teacher();out=t.step(s)
    assert out.valid.item()
    before=t._rows[0]['accepted'].body.quat_w.clone()
    again=t.step(s)
    assert torch.equal(again.action,out.action)
    assert torch.equal(t._rows[0]['accepted'].body.quat_w,before)


def test_final_encode_failure_rolls_back_tilt_and_retry_succeeds(monkeypatch):
    t,s=frozen_teacher();before=t._rows[0]['accepted'].body.quat_w.clone()
    real=t._feedback_transaction;encode=m.encode_targets;armed=[False]
    def transaction(*a,**kw):
        result=real(*a,**kw);assert result[0].valid.item();armed[0]=True;return result
    def reject(*a,**kw):
        action,valid=encode(*a,**kw)
        if armed[0]:
            armed[0]=False;return action,torch.zeros_like(valid)
        return action,valid
    with monkeypatch.context() as patch:
        patch.setattr(t,'_feedback_transaction',transaction)
        patch.setattr(m,'encode_targets',reject)
        t._step_row(s,0,None)
    assert torch.equal(t._rows[0]['accepted'].body.quat_w,before)
    from test_m1_reference_teacher import advance
    t._step_row(advance(s),0,None)
    assert t._rows[0]['invalid_streak']==0
    assert t._rows[0]['goal'].body.quat_w[0,1:3].abs().max()>.01


def test_restore_keeps_original_level_goal(monkeypatch):
    from dataclasses import replace
    from test_m1_teacher_load_feedback_transaction import load_teacher
    t,s=load_teacher('RESTORE')
    t.cfg=replace(t.cfg,bounded_crossing_attitude=True)
    original=t._rows[0]['anchor_pose'].quat_w.clone()
    from ame_baseline.m1_teacher_pose import PoseReference,BodyPose
    from test_m1_teacher_pose import quat
    old=t._rows[0]['goal']
    t._rows[0]['goal']=PoseReference(BodyPose(old.body.pos_w,quat(r=.1).to(old.body.quat_w)),old.wheels_w)
    assert t.step(s).valid.item()
    assert torch.allclose(t._rows[0]['goal'].body.quat_w,original,atol=1e-9,rtol=0)


def test_episode_reset_discards_crossing_pose():
    from test_m1_reference_teacher import advance
    t,s=frozen_teacher();assert t.step(s).valid.item()
    t.step(advance(s,episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask)))
    assert not t._rows[0]['prepared']
    assert 'support_attitude_error0' not in t._rows[0]


def test_reset_peer_does_not_change_live_bounded_crossing():
    import copy
    from dataclasses import fields
    single,state=frozen_teacher();expected=single.step(state)
    t,s=frozen_teacher();t._rows=[copy.deepcopy(t._rows[0]),copy.deepcopy(t._rows[0])]
    batch=m.TeacherState(**{f.name:getattr(s,f.name).repeat((2,)+(1,)*(getattr(s,f.name).ndim-1)) for f in fields(s)})
    batch.episode_id[1]+=1;batch.reset_mask[1]=True
    out=t.step(batch)
    assert out.valid[0] and torch.equal(out.action[0],expected.action[0])
    assert torch.equal(t._rows[0]['goal'].body.quat_w,single._rows[0]['goal'].body.quat_w)
    assert not t._rows[1]['prepared']
