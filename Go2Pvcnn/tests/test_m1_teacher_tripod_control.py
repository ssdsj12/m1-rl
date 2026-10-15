"""Tripod reserve integration; synthetic control, not physical proof."""
import pytest
import torch
from ame_baseline.m1_teacher_dynamic_support import measured_lift_step
from test_m1_reference_teacher import api, advance
from test_m1_teacher_reference_commit import near_state


@pytest.mark.parametrize('reserve', [0., .5, 1.])
def test_reserve_30_37p5_45_is_0_half_1(reserve):
    x=lambda v: torch.tensor([v], dtype=torch.float64)
    out=measured_lift_step(x(0),x(0),x(.2),x(100),x(.1),x(100),x(.1),
        torch.tensor([False]),x(.02),rate_m_s=.02,lead_m=.01,
        force_floor_n=30.,force_band_n=15.,margin_floor_m=.01,margin_band_m=.01,
        external_reserve=x(reserve))
    assert out.reserve.item()==pytest.approx(reserve)
    assert out.increment.item()==pytest.approx(.0004*reserve)


def capture():
    t=api(); teacher=t.ReferenceTeacher(t.TeacherConfig(slow_rolling=True))
    s=near_state()
    assert teacher.step(s).valid.item()
    s=advance(s)
    return teacher,s


def test_capture_and_spike_no_extra_reserve():
    teacher,s=capture()
    assert teacher.step(s).valid.item()
    row=teacher._rows[0]
    expected=s.wheel_force_w[:,:,2].clamp_min(0).sum(-1)
    assert torch.equal(row['tripod_captured_load_n'],expected)
    s=advance(s); s.wheel_force_w[:,:,2]*=2
    out=teacher.step(s)
    names=api().TEACHER_DIAGNOSTIC_FIELDS
    assert out.diagnostic[0,names.index('tripod_effective_total_n')].item()==pytest.approx(expected.item())


def test_capture_rejection_not_committed(monkeypatch):
    import ame_baseline.m1_reference_teacher as module
    teacher,s=capture()
    monkeypatch.setattr(module,'encode_targets',lambda q,v,d:(q.new_zeros(1,16),torch.tensor([False])))
    out=teacher.step(s)
    assert not out.valid.item()
    assert 'tripod_captured_load_n' not in teacher._rows[0]


def test_reset_drops_capture():
    teacher,s=capture(); teacher.step(s)
    assert 'tripod_captured_load_n' in teacher._rows[0]
    teacher.step(advance(s,episode_id=s.episode_id+1,reset_mask=torch.ones_like(s.reset_mask)))
    assert 'tripod_captured_load_n' not in teacher._rows[0]


def test_legacy_does_not_capture():
    t=api(); teacher=t.ReferenceTeacher(); s=near_state()
    teacher.step(s); teacher.step(advance(s))
    assert 'tripod_captured_load_n' not in teacher._rows[0]


def test_four_loaded_18n_cannot_start_lift():
    from test_m1_teacher_lift_decoupling import crossing
    teacher,s=crossing('BALANCE')
    s.com_pos_w[:,:2]=(s.wheel_pos_w[:,1:,:2]*s.root_pos_w.new_tensor([.4625,.4625,.075])[None,:,None]).sum(1)
    out=teacher.step(s)
    names=api().TEACHER_DIAGNOSTIC_FIELDS
    assert out.diagnostic[0,names.index('tripod_min_load_n')].item()==pytest.approx(18.,abs=1e-4)
    assert teacher._rows[0]['phase']==api().Phase.BALANCE


def test_no_reserve_keeps_body_and_rolling_updates():
    from test_m1_teacher_lift_decoupling import crossing
    teacher,s=crossing()
    s.com_pos_w[:,:2]=(s.wheel_pos_w[:,1:,:2]*s.root_pos_w.new_tensor([.4625,.4625,.075])[None,:,None]).sum(1)
    before=teacher._rows[0]['accepted']
    out=teacher.step(s); row=teacher._rows[0]; names=api().TEACHER_DIAGNOSTIC_FIELDS
    assert out.valid.item()
    assert out.diagnostic[0,names.index('tripod_reserve')]==0
    assert torch.equal(row['accepted'].wheels_w[:,0,2],before.wheels_w[:,0,2])
    assert (row['accepted'].body.pos_w-before.body.pos_w).norm()>0
    assert (row['last_surface_speed']>0).all()


def test_reset_one_captured_row_preserves_other_scale():
    t=api(); teacher=t.ReferenceTeacher(t.TeacherConfig(slow_rolling=True))
    s=near_state(batch=2); s.wheel_force_w[1,:,2]=80.
    teacher.step(s); s=advance(s); out=teacher.step(s)
    assert out.valid.all()
    assert [r['tripod_captured_load_n'].item() for r in teacher._rows]==[240.,320.]
    episode=s.episode_id.clone(); episode[0]+=1
    reset=s.reset_mask.clone(); reset[0]=True
    teacher.step(advance(s,episode_id=episode,reset_mask=reset))
    assert 'tripod_captured_load_n' not in teacher._rows[0]
    assert teacher._rows[1]['tripod_captured_load_n'].item()==320.
