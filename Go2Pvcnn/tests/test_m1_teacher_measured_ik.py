from dataclasses import replace
import pytest
import torch
from test_m1_teacher_lift_decoupling import crossing
from test_m1_reference_teacher import api, advance


@pytest.mark.parametrize('phase,mode',[('LIFT',1),('PASS',1),('RESTORE',2),('BALANCE',0)])
def test_teacher_selects_measured_execution_only_in_crossing(monkeypatch,phase,mode):
    t=api(); teacher,s=crossing(phase); seen=[]
    if phase=='BALANCE': s.root_pos_w[:,2]-=.015  # Stay in BALANCE, not its ready→LIFT transition.
    real=t.backtrack_feedback_reference
    def observe(*a,**kw):
        seen.append(kw); return real(*a,**kw)
    monkeypatch.setattr(t,'backtrack_feedback_reference',observe)
    teacher.step(s)
    assert seen
    if mode:
        assert all(x['execution_mode'].item()==mode for x in seen)
        assert all(torch.equal(x['measured'].quat_w,s.root_quat_w) for x in seen)
        assert all(x['active_wheel'].item()==0 for x in seen)
    else: assert all(x.get('execution_mode') is None for x in seen)


def test_execution_diagnostic_and_duplicate_are_exact():
    teacher,s=crossing(); s.root_pos_w[:,2]-=.015
    out=teacher.step(s); names=api().TEACHER_DIAGNOSTIC_FIELDS
    assert out.valid.item()
    assert out.diagnostic[0,names.index('execution_mode')]==1
    assert 0<out.diagnostic[0,names.index('execution_fraction')]<=1
    again=teacher.step(s)
    torch.testing.assert_close(out.diagnostic,again.diagnostic,equal_nan=True,rtol=0,atol=0)


def test_encode_failure_does_not_commit_execution_state(monkeypatch):
    t=api(); teacher,s=crossing(); teacher.step(s); row=teacher._rows[0]
    old={k:row[k] for k in ('accepted','accepted_command','feedback','last_q','age','body_age','lift_age')}
    original=t.encode_targets
    def reject(*a):
        action,valid=original(*a); return action,torch.zeros_like(valid)
    monkeypatch.setattr(t,'encode_targets',reject)
    out=teacher.step(advance(s)); assert not out.valid.item()
    assert all(row[k] is value if not isinstance(value,int) else row[k]==value for k,value in old.items())


@pytest.mark.parametrize('wheel',range(4))
def test_each_active_leg_consumes_current_pose_across_gap(monkeypatch,wheel):
    from test_m1_teacher_reference_commit import prepared_teacher
    t=api(); teacher,s,_=prepared_teacher(wheel=wheel,rolling=True)
    teacher.cfg=t.TeacherConfig(slow_rolling=True)
    teacher._rows[0]['phase']=t.Phase.LIFT
    s.centers_top[:,0,0]+=.2
    s=replace(s,control_step=s.control_step+3)
    seen=[]; real=t.backtrack_feedback_reference
    def observe(*a,**kw): seen.append(kw); return real(*a,**kw)
    monkeypatch.setattr(t,'backtrack_feedback_reference',observe)
    teacher.step(s)
    assert seen and all(x['active_wheel'].item()==wheel for x in seen)
    assert all(torch.equal(x['measured'].pos_w,s.root_pos_w) for x in seen)


def test_single_row_reset_does_not_change_other_row_cached_state():
    import copy
    from dataclasses import fields
    from test_m1_teacher_probe_contract import probe
    teacher,s=crossing()
    teacher._rows.append(copy.deepcopy(teacher._rows[0]))
    s=replace(s,**{f.name:torch.cat((getattr(s,f.name),getattr(s,f.name)),0)
        for f in fields(s) if isinstance(getattr(s,f.name),torch.Tensor)})
    teacher.step(s); p=probe(); old=p._dynamic_pack(teacher._rows[1])
    episode=s.episode_id.clone(); episode[0]+=1
    reset=s.reset_mask.clone(); reset[0]=True
    after=teacher.step(replace(s,episode_id=episode,reset_mask=reset))
    assert p._dynamic_equal(old,p._dynamic_pack(teacher._rows[1]))
    assert teacher._rows[0]['episode']!=teacher._rows[1]['episode']


def test_restore_receipt_cannot_skip_incomplete_handover(monkeypatch):
    t=api(); teacher,s=crossing('RESTORE'); row=teacher._rows[0]
    s.centers_top[:,0,0]-=2
    s.recovered[:,0,0]=True
    s=replace(s,leg_pos=s.default_joint_pos[:,t.LEG_COLUMNS].clone(),
        nominal_root_z_w=s.root_pos_w[:,2].clone())
    row['stable']=teacher.cfg.stable_samples
    monkeypatch.setattr(teacher,'_tracked',lambda *a:True)
    real=teacher._feedback_transaction
    def bounded(*a):
        solved,selected=real(*a)
        assert solved.valid.item() and solved.execution_target.mode.item()==2
        return replace(solved,execution_target=replace(solved.execution_target,
            fraction=solved.output.new_tensor([.5]))),selected
    monkeypatch.setattr(teacher,'_feedback_transaction',bounded)
    out=teacher.step(s)
    assert out.valid.item() and row['stable']>=teacher.cfg.stable_samples
    assert row['phase']==t.Phase.RESTORE and row['target']==0
