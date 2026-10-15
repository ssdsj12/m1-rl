"""First-LIFT actual XY capture, not repeated snapping or physical proof."""
import torch
import pytest
from dataclasses import replace
from test_m1_teacher_reference_commit import prepared_teacher,feedback
from test_m1_reference_teacher import api,advance


def ready_with_drift(wheel=0,rolling=True):
    teacher,s,_=prepared_teacher(wheel=wheel,rolling=rolling)
    s.centers_top[:,0,0]+=.2
    # Obtain an actual ready BALANCE input, retaining its original references.
    for _ in range(40):
        import copy
        before=copy.deepcopy(teacher._rows)
        out=teacher.step(s)
        if out.valid.item() and out.phase.item()==api().Phase.LIFT:
            teacher._rows=before
            s.wheel_pos_w[:,wheel,0]+=.01
            return teacher,s
        s=feedback(s,teacher,out)
    raise AssertionError('fixture never ready')


@pytest.mark.parametrize('wheel',range(4))
def test_first_lift_captures_only_active_xy_and_keeps_slew(wheel):
    teacher,s=ready_with_drift(wheel)
    row=teacher._rows[0]; old=row['wheel_anchor'].clone()
    out=teacher.step(s)
    assert out.valid.item() and out.phase.item()==api().Phase.LIFT
    expected=old.clone();expected[:,wheel,:2]=s.wheel_pos_w[:,wheel,:2]
    assert torch.allclose(row['wheel_anchor'],expected,atol=1e-7,rtol=0)
    assert (row['last_q']-s.last_applied_leg_target).abs().max()<=.0500001


def test_later_lift_does_not_recapture_differential_motion():
    teacher,s=ready_with_drift();assert teacher.step(s).valid.item()
    row=teacher._rows[0];old=row['wheel_anchor'].clone()
    s=advance(s);s.wheel_pos_w[:,0,0]+=.005
    assert teacher.step(s).valid.item()
    assert torch.equal(row['wheel_anchor'],old)


def test_rejected_capture_rolls_back_and_retry_uses_current_measurement(monkeypatch):
    teacher,s=ready_with_drift();row=teacher._rows[0];old=row['wheel_anchor'].clone()
    import ame_baseline.m1_teacher_pose as p
    real=p.solve_constrained_ik
    with monkeypatch.context() as patch:
        patch.setattr(p,'solve_constrained_ik',lambda *a,**kw:replace(real(*a,**kw),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
        assert not teacher.step(s).valid.item()
    assert row['phase']==api().Phase.BALANCE and torch.equal(row['wheel_anchor'],old)
    s=advance(s);s.wheel_pos_w[:,0,0]+=.002
    assert teacher.step(s).valid.item()
    assert torch.equal(row['wheel_anchor'][:,0,:2],s.wheel_pos_w[:,0,:2])


def test_legacy_balance_does_not_rebase_active_anchor():
    teacher,s=ready_with_drift(rolling=False);old=teacher._rows[0]['wheel_anchor'].clone()
    assert teacher.step(s).valid.item()
    assert torch.equal(teacher._rows[0]['wheel_anchor'],old)


def test_duplicate_step_returns_same_capture_and_action():
    teacher,s=ready_with_drift();out=teacher.step(s)
    assert out.valid.item()
    old=teacher._rows[0]['wheel_anchor'].clone()
    s.wheel_pos_w[:,0,0]+=.005
    again=teacher.step(s)
    assert torch.equal(again.action,out.action)
    assert torch.equal(teacher._rows[0]['wheel_anchor'],old)


def test_pass_does_not_capture_differential_active_motion():
    from test_m1_teacher_lift_decoupling import crossing
    teacher,s=crossing('PASS');old=teacher._rows[0]['wheel_anchor'].clone()
    s.wheel_pos_w[:,0,0]+=.01
    assert teacher.step(s).valid.item()
    assert torch.equal(teacher._rows[0]['wheel_anchor'],old)


def test_final_encode_rejection_cannot_commit_new_anchor(monkeypatch):
    teacher,s=ready_with_drift();row=teacher._rows[0];old=row['wheel_anchor'].clone()
    t=api();real=teacher._feedback_transaction;encode=t.encode_targets;armed=[False]
    def transaction(*a,**kw):
        result=real(*a,**kw)
        assert result[0].valid.item()
        armed[0]=True
        return result
    def reject(*a,**kw):
        action,valid=encode(*a,**kw)
        if armed[0]:
            armed[0]=False
            return action,torch.zeros_like(valid)
        return action,valid
    monkeypatch.setattr(teacher,'_feedback_transaction',transaction)
    monkeypatch.setattr(t,'encode_targets',reject)
    assert not teacher.step(s).valid.item()
    assert row['phase']==t.Phase.BALANCE and torch.equal(row['wheel_anchor'],old)
