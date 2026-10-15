import torch
from test_m1_teacher_load_feedback_transaction import load_teacher
from test_m1_reference_teacher import advance


def test_capture_is_committed_and_reset_discards_it():
    teacher,s=load_teacher();out=teacher.step(s)
    assert out.valid.item()
    assert 'support_attitude_error0' in teacher._rows[0], 'attitude capture missing'
    saved=teacher._rows[0]['support_attitude_error0'].clone()
    assert saved.shape==(1,4) and saved[0,0]==0
    s=advance(s);assert teacher.step(s).valid.item()
    assert torch.equal(saved,teacher._rows[0]['support_attitude_error0'])
    teacher.step(advance(s,episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask)))
    assert 'support_attitude_error0' not in teacher._rows[0]


def test_restore_does_not_capture_attitude():
    teacher,s=load_teacher('RESTORE');assert teacher.step(s).valid.item()
    assert 'support_attitude_error0' not in teacher._rows[0]


def test_float32_delta_cancellation_does_not_abort_step(monkeypatch):
    import ame_baseline.m1_reference_teacher as module
    from ame_baseline.m1_teacher_attitude import SupportAttitudeError
    teacher,s=load_teacher()
    teacher._rows[0]['support_attitude_error0']=torch.tensor([[0.,.049061208963394165,-.04395217075943947,-.005109038203954697]])
    error=torch.tensor([[0.,-.07713910192251205,.09218646585941315,-.015047363936901093]])
    monkeypatch.setattr(module,'centered_support_attitude_error',lambda *a:SupportAttitudeError(error,torch.tensor([True])))
    teacher.step(s)  # A finite pose may reject IK, but must not crash the probe.


@__import__('pytest').mark.parametrize('captured',[False,True])
def test_rejected_transaction_keeps_capture_and_offset(monkeypatch,captured):
    from dataclasses import replace
    import ame_baseline.m1_teacher_pose as pose
    teacher,s=load_teacher()
    if captured:
        assert teacher.step(s).valid.item();s=advance(s)
    before={k:v.clone() for k,v in teacher._rows[0].items() if k in ('support_attitude_error0','support_load_offset')}
    real=pose.solve_constrained_ik
    monkeypatch.setattr(pose,'solve_constrained_ik',lambda *a,**kw:replace(real(*a,**kw),valid=torch.zeros(a[0].shape[0],dtype=torch.bool)))
    assert not teacher.step(s).valid.item()
    after={k:v for k,v in teacher._rows[0].items() if k in ('support_attitude_error0','support_load_offset')}
    assert set(after)==set(before)
    for k in before:assert torch.equal(before[k],after[k])
