"""Synthetic gate/transaction tests, not physical crossing evidence."""
from dataclasses import replace

import pytest
import torch

from test_m1_reference_teacher import api, advance
from test_m1_teacher_reference_commit import prepared_teacher


def crossing(phase='LIFT', rolling=True):
    t=api(); teacher,s,_=prepared_teacher(rolling=rolling)
    teacher.cfg=t.TeacherConfig(slow_rolling=rolling)
    teacher._rows[0].update(phase=getattr(t.Phase,phase))
    s.centers_top[:,0,0] += .2  # Keep actual near-side safety guard out of fixture.
    return teacher,s


@pytest.mark.parametrize('phase',['LIFT','PASS'])
def test_body_position_error_does_not_freeze_safe_rolling_lift(phase):
    teacher,s=crossing(phase); row=teacher._rows[0]
    s.root_pos_w[:,2] -= .015
    old=row['accepted']; ages={k:row[k] for k in ('body_age','lift_age')}
    out=teacher.step(s)
    assert out.valid.item()
    assert row['body_age']==ages['body_age']
    assert row['lift_age']==ages['lift_age']+1
    # Tracking age stays frozen, while dynamic support may lower the body
    # toward a safer knee reserve within its existing physical rate bound.
    motion=row['accepted'].body.pos_w-old.body.pos_w
    assert motion.norm()<=teacher.cfg.dynamic_body_rate_m_s*s.dt[0]+1e-7
    assert motion[0,2]<=0
    assert row['accepted'].wheels_w[0,0,2]>old.wheels_w[0,0,2]
    names=api().TEACHER_DIAGNOSTIC_FIELDS
    assert out.diagnostic[0,names.index('body_tracking_ready')]==0
    assert out.diagnostic[0,names.index('wheel_progress_ready')]==1


@pytest.mark.parametrize('unsafe',['com','attitude'])
def test_unsafe_crossing_evidence_freezes_lift_even_if_body_position_tracked(unsafe):
    teacher,s=crossing(); row=teacher._rows[0]
    if unsafe=='com':
        s.com_pos_w[:,:2]=(s.wheel_pos_w[:,1,:2]+s.wheel_pos_w[:,2,:2])/2
    else:
        angle=torch.tensor(.16/2)
        s.root_quat_w[:]=torch.tensor([angle.cos(),angle.sin(),0.,0.])
    old=row['accepted']; age=row['lift_age']
    out=teacher.step(s)
    assert out.valid.item() and not out.failure_locked.item()
    assert out.diagnostic[0,api().TEACHER_DIAGNOSTIC_FIELDS.index('wheel_progress_ready')]==0
    assert row['lift_age']==age
    assert torch.equal(row['accepted'].wheels_w,old.wheels_w)


@pytest.mark.parametrize('unsafe',['collision','support'])
def test_physical_failure_still_locks(unsafe):
    teacher,s=crossing(); row=teacher._rows[0]; age=row['lift_age']
    if unsafe=='collision': s.collision[:]=True
    else: s.wheel_force_w[:,1,2]=0
    out=teacher.step(s)
    assert out.failure_locked.item() and not out.valid.item()
    assert row['lift_age']==age


def test_rejected_ik_does_not_commit_decoupled_lift(monkeypatch):
    import ame_baseline.m1_teacher_pose as p
    teacher,s=crossing(); row=teacher._rows[0]
    s.root_pos_w[:,2] -= .015
    old=row['accepted']; ages=tuple(row[k] for k in ('age','body_age','lift_age'))
    real=p.solve_constrained_ik
    monkeypatch.setattr(p,'solve_constrained_ik',lambda *a:replace(real(*a),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
    out=teacher.step(s)
    assert not out.valid.item() and row['accepted'] is old
    assert tuple(row[k] for k in ('age','body_age','lift_age'))==ages
    names=api().TEACHER_DIAGNOSTIC_FIELDS
    assert out.diagnostic[0,names.index('wheel_progress_ready')]==0


def test_legacy_lift_still_freezes_on_position_error():
    teacher,s=crossing(rolling=False); row=teacher._rows[0]; age=row['lift_age']
    s.root_pos_w[:,2] -= .015
    out=teacher.step(s)
    assert out.valid.item() and row['lift_age']==age


@pytest.mark.parametrize('clear',[False,True])
def test_rolling_pass_requires_actual_bottom_clearance_not_reference(clear):
    teacher,s=crossing(); row=teacher._rows[0]
    s.root_pos_w[:,2] -= .015
    # Change obstacle top, not the reference, to isolate measured clearance.
    s.centers_top[:,0,2] = -.01 if clear else .10
    out=teacher.step(s)
    assert out.valid.item()
    assert row['phase']==(api().Phase.PASS if clear else api().Phase.LIFT)


def test_rolling_restore_transition_does_not_relax_restore_tracking():
    teacher,s=crossing('PASS'); row=teacher._rows[0]
    s.root_pos_w[:,2] -= .015
    s.centers_top[:,0,0] = s.wheel_pos_w[:,0,0]-.5
    out=teacher.step(s)
    assert out.valid.item() and row['phase']==api().Phase.RESTORE
    assert row['stable']==0 and row['age']==0


def test_balance_still_requires_body_tracking_before_lift():
    teacher,s=crossing('BALANCE'); row=teacher._rows[0]
    s.root_pos_w[:,2] -= .015
    age=row['lift_age']; out=teacher.step(s)
    assert out.valid.item() and row['phase']==api().Phase.BALANCE
    assert row['lift_age']==age


def test_rejected_lift_retries_once_and_reset_clears_progress(monkeypatch):
    import ame_baseline.m1_teacher_pose as p
    teacher,s=crossing(); row=teacher._rows[0]; s.root_pos_w[:,2] -= .015
    age=row['lift_age']; real=p.solve_constrained_ik
    with monkeypatch.context() as patch:
        patch.setattr(p,'solve_constrained_ik',lambda *a:replace(real(*a),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
        assert not teacher.step(s).valid.item()
    out=teacher.step(advance(s))
    assert out.valid.item() and row['lift_age']==age+1
    reset=advance(advance(s),episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask))
    out=teacher.step(reset)
    assert teacher._rows[0]['lift_age']==0 and 'accepted' not in teacher._rows[0]
    assert out.diagnostic[0,api().TEACHER_DIAGNOSTIC_FIELDS.index('wheel_progress_ready')]==0


def test_transaction_replay_checks_wheel_commands_not_outer_phase_gate():
    import copy
    from test_m1_teacher_probe_contract import probe
    from ame_baseline.m1_ame_contract import m1_action_targets
    teacher,s=crossing(); s.root_pos_w[:,2] -= .015
    p=probe(); p.observe_feedback_transactions(teacher)
    out=teacher.step(s)
    sample=dict(teacher_diagnostic=p.diagnostic_json(out.diagnostic[0].tolist()),
        feedback_context=teacher._probe_feedback_context[0],action_target_dtype='float32',
        teacher_action=out.action[0].tolist(),
        applied_targets=m1_action_targets(out.action,s.default_joint_pos)[0].tolist(),
        phase=int(out.phase[0]))
    assert sample['teacher_diagnostic']['wheel_progress_ready']==1
    assert p.verify_feedback_transaction(sample,teacher.cfg)==[]
    for field in ('wheel_nominal_surface_speed_0','wheel_final_surface_speed_0'):
        changed=copy.deepcopy(sample); changed['teacher_diagnostic'][field]+=.01
        assert p.verify_feedback_transaction(changed,teacher.cfg)
