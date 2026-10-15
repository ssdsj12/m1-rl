"""Measured progress math; synthetic tests are not physical crossing evidence."""
import importlib
import math

import pytest
import torch


def api():
    return importlib.import_module('ame_baseline.m1_teacher_dynamic_support')


def lift(**changes):
    values = dict(accepted_z=.10, measured_z=.10, max_z=.30, min_fz=45.,
                  margin=.015, previous_min_fz=45., previous_margin=.015, dt=.02)
    valid = changes.pop('history_valid', False)
    values.update(changes)
    args = {k: torch.tensor([v], dtype=torch.float64) for k, v in values.items()}
    args['history_valid'] = torch.tensor([valid])
    return api().measured_lift_step(**args, rate_m_s=.02, lead_m=.02,
        force_floor_n=30., force_band_n=15., margin_floor_m=.01, margin_band_m=.005)


@pytest.mark.parametrize('changes,want', [({}, .0004), ({'dt': .01}, .0002),
    ({'min_fz': 37.5}, .0002), ({'margin': .0125}, .0002),
    ({'min_fz': 30.}, 0.), ({'margin': .01}, 0.),
    ({'accepted_z': .12, 'measured_z': .09}, 0.),
    ({'accepted_z': .30}, 0.)])
def test_lift_is_limited_by_rate_load_margin_lead_and_ceiling(changes, want):
    result = lift(**changes)
    assert result.increment.item() == pytest.approx(want)
    assert result.next_z.item() == pytest.approx(changes.get('accepted_z', .10)+want)


def test_declining_force_anticipates_one_step_but_gap_does_not():
    assert lift(min_fz=40., previous_min_fz=45., history_valid=True).increment.item() == pytest.approx(.0004/3)
    assert lift(min_fz=40., previous_min_fz=45.).increment.item() == pytest.approx(.0004*2/3)
    assert lift(margin=.0125, previous_margin=.015, history_valid=True).increment.item() == pytest.approx(0.)


def test_sink_never_pushes_old_reference_down():
    result = lift(accepted_z=.12, measured_z=.05)
    assert result.next_z.item() == .12 and result.increment.item() == 0.
    assert result.lead_error.item() == pytest.approx(.07)


@pytest.mark.parametrize('changes', [{'dt':0.}, {'dt':-1.}, {'dt':float('nan')},
                                    {'min_fz':float('nan')}, {'measured_z':float('inf')}])
def test_nonfinite_or_invalid_time_is_rejected(changes):
    with pytest.raises(ValueError):
        lift(**changes)


def test_ema_uses_dt_and_does_not_mutate_inputs():
    raw=torch.tensor([[40.,40.,40.,40.]])
    old=torch.tensor([[50.,50.,50.,50.]])
    out=api().filter_support_fz(raw,old,torch.tensor([True]),torch.tensor([.02]),.10)
    assert out.tolist()[0] == pytest.approx([48.18730753]*4)
    assert torch.equal(old,torch.full_like(old,50.))
    assert torch.equal(raw,torch.full_like(raw,40.))
    assert torch.equal(api().filter_support_fz(raw,old,torch.tensor([False]),torch.tensor([.02]),.10),raw)


def test_inverse_force_target_excludes_active_wheel():
    wheels=torch.tensor([[[999.,999.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,0.]]])
    fz=torch.tensor([[.001,20.,40.,40.]])
    out=api().desired_support_com_xy(wheels,fz,torch.tensor([0]))
    assert out.tolist()[0] == pytest.approx([.5,.25])
    fz[:,0]=10000.
    assert torch.equal(out,api().desired_support_com_xy(wheels,fz,torch.tensor([0])))


def test_repeated_lift_is_pure():
    assert torch.equal(lift().next_z,lift().next_z)


def test_pose_ranks_com_before_motion_and_preserves_wheel_targets(monkeypatch):
    from ame_baseline import m1_teacher_pose as p
    from ame_baseline.m1_teacher_ik import IKConfig
    from test_m1_teacher_pose import triangle_setup, fixed_solver
    fixed_solver(p,monkeypatch)
    q,body,ref,com=triangle_setup(p)
    ref.wheels_w[:,0,2]=.2
    anchors=ref.wheels_w.clone()
    def choose(target, measured=None):
        return p.choose_support_pose(body,body,body,com,ref.wheels_w,torch.tensor([0]),
            body.pos_w[:,2],q,q,IKConfig(),measured_wheels_w=anchors if measured is None else measured,
            desired_com_xy=target)
    old=choose(None)
    right=choose(q.new_tensor([[.34,.30]]))
    left=choose(q.new_tensor([[.26,.30]]))
    assert old.candidate_index.item()==60
    assert right.candidate_index.item()==110
    assert left.candidate_index.item()==10
    assert torch.equal(right.reference.wheels_w,anchors)
    assert right.candidate_count.item()==126
    invalid=choose(q.new_tensor([[.34,.30]]),anchors+2.)
    assert not invalid.valid.item() and invalid.candidate_index.item()==-1
    with pytest.raises(ValueError): choose(q.new_tensor([[float('nan'),0.]]))


@pytest.mark.parametrize('phase',['LIFT','PASS'])
def test_dynamic_crossing_corrects_body_when_not_tracked_and_limits_z(phase):
    from test_m1_teacher_lift_decoupling import crossing
    teacher,s=crossing(phase)
    row=teacher._rows[0]; before=row['accepted']
    s.root_pos_w[:,2]-=.015
    s.wheel_force_w[:,3,2]=35.
    s.com_pos_w[:,0]+=.02  # New ranking reacts to predicted tripod geometry.
    out=teacher.step(s)
    assert out.valid.item()
    delta=(row['accepted'].body.pos_w-before.body.pos_w).norm().item()
    assert 0 < delta <= .02*float(s.dt[0])+1e-7
    zdelta=(row['accepted'].wheels_w[0,0,2]-before.wheels_w[0,0,2]).item()
    assert 0 <= zdelta <= .02*float(s.dt[0])+1e-7
    assert 'dynamic_support_fz' in row


def test_dynamic_ik_rejection_does_not_commit_filter_or_trend(monkeypatch):
    from test_m1_teacher_lift_decoupling import crossing
    from dataclasses import replace
    from ame_baseline import m1_teacher_pose as p
    teacher,s=crossing(); row=teacher._rows[0]; old=row['accepted']
    real=p.solve_constrained_ik
    def rejected(*args):
        result=real(*args)
        return replace(result,valid=torch.zeros_like(result.valid))
    monkeypatch.setattr(p,'solve_constrained_ik',rejected)
    assert not teacher.step(s).valid.item()
    assert row['accepted'] is old and 'dynamic_support_fz' not in row


def test_dynamic_history_is_not_reused_across_gap_or_leg_change():
    from test_m1_teacher_lift_decoupling import crossing
    teacher,s=crossing(); row=teacher._rows[0]
    row.update(dynamic_previous_step=-100,dynamic_active_wheel=3,
               dynamic_support_fz=s.wheel_force_w[:,:,2]*100,
               dynamic_previous_min_fz=torch.tensor([1000.]),
               dynamic_previous_margin=torch.tensor([1.]),dynamic_history_valid=True)
    out=teacher.step(s)
    assert out.valid.item()
    assert torch.equal(row['dynamic_support_fz'],s.wheel_force_w[:,:,2])
    assert row['dynamic_active_wheel']==0


def test_existing_dynamic_state_survives_encode_rejection_and_duplicate(monkeypatch):
    from test_m1_teacher_lift_decoupling import crossing
    from test_m1_reference_teacher import advance
    from ame_baseline import m1_reference_teacher as t
    teacher,s=crossing()
    assert teacher.step(s).valid.item()
    row=teacher._rows[0]
    old_filter=row['dynamic_support_fz'].clone()
    old_step=row['dynamic_previous_step']
    original=t.encode_targets
    def rejected(*args):
        action,valid=original(*args)
        return action,torch.zeros_like(valid)
    next_s=advance(s)
    with monkeypatch.context() as patch:
        patch.setattr(t,'encode_targets',rejected)
        assert not teacher.step(next_s).valid.item()
    assert torch.equal(row['dynamic_support_fz'],old_filter)
    assert row['dynamic_previous_step']==old_step
    # Duplicate preserves failed cached decision, not another state update.
    assert not teacher.step(next_s).valid.item()
    later=advance(next_s); later.wheel_force_w[:,3,2]=40.
    assert teacher.step(later).valid.item()
    assert torch.equal(row['dynamic_support_fz'],later.wheel_force_w[:,:,2])


def test_raw_support_failure_overrides_existing_high_ema():
    from test_m1_teacher_lift_decoupling import crossing
    from test_m1_reference_teacher import advance
    teacher,s=crossing()
    assert teacher.step(s).valid.item()
    next_s=advance(s); next_s.wheel_force_w[:,3,2]=29.
    result=teacher.step(next_s)
    assert result.failure_locked.item()
    assert teacher._rows[0]['dynamic_support_fz'][0,3]>30.
