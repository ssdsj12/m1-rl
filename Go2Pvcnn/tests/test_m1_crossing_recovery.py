"""Measured whole-robot recovery; no simulator, commands or teacher state."""
from dataclasses import fields, replace
import importlib
import importlib.util
import math

import pytest
import torch


@pytest.fixture
def recovery():
    assert importlib.util.find_spec('ame_baseline.m1_crossing_recovery') is not None, 'pure recovery API is absent'
    return importlib.import_module('ame_baseline.m1_crossing_recovery')


def quat(roll=0., pitch=0., yaw=0., dtype=torch.float64):
    cr, sr = math.cos(roll/2), math.sin(roll/2)
    cp, sp = math.cos(pitch/2), math.sin(pitch/2)
    cy, sy = math.cos(yaw/2), math.sin(yaw/2)
    return torch.tensor([cr*cp*cy+sr*sp*sy, sr*cp*cy-cr*sp*sy,
                         cr*sp*cy+sr*cp*sy, cr*cp*sy-sr*sp*cy], dtype=dtype)


def scope(api, batch=1, courses=1, dtype=torch.float64):
    return api.RecoveryScope(
        env_id=torch.arange(batch, dtype=torch.long),
        episode_id=torch.full((batch,), 7, dtype=torch.long),
        scope_id=torch.full((batch,), 13, dtype=torch.long),
        course_ids=torch.arange(101, 101+courses, dtype=torch.long).repeat(batch, 1),
        required=torch.ones(batch, courses, 4, dtype=torch.bool),
        centers_w=torch.zeros(batch, courses, 3, dtype=dtype),
        half_extents=torch.full((batch, courses, 2), .05, dtype=dtype),
        forward_w=torch.tensor([[1., 0., 0.]], dtype=dtype).repeat(batch, 1))


def frame(api, frozen, step=0, time=None, dt=.02, x=None):
    batch, courses = frozen.course_ids.shape
    dtype = frozen.centers_w.dtype
    root = torch.zeros(batch, 13, dtype=dtype)
    root[:, 0] = 1.+step*.002 if x is None else x
    root[:, 2], root[:, 3], root[:, 7] = .62, 1., .1
    wheels = torch.zeros(batch, 4, 3, dtype=dtype)
    wheels[:, :, 0], wheels[:, :, 2] = 1.+step*.002, .0959
    wheel_quat = torch.zeros(batch, 4, 4, dtype=dtype)
    wheel_quat[:, :, 0] = 1.
    force = torch.zeros(batch, 4, 3, dtype=dtype)
    force[:, :, 2] = 20.
    masks = dict(valid=torch.ones(batch, dtype=torch.bool))
    masks.update({name: torch.zeros(batch, dtype=torch.bool) for name in
                  ('collision', 'penetration', 'base_contact', 'physical_failure', 'reset', 'ended')})
    return api.RecoveryFrame(
        env_id=frozen.env_id.clone(), episode_id=frozen.episode_id.clone(), scope_id=frozen.scope_id.clone(),
        frame=torch.full((batch,), step, dtype=torch.long),
        sim_time_s=torch.full((batch,), step*dt if time is None else time, dtype=dtype),
        dt_s=torch.full((batch,), dt, dtype=dtype), root_state_w=root,
        leg_pos=torch.zeros(batch, 12, dtype=dtype), default_leg_pos=torch.zeros(batch, 12, dtype=dtype),
        wheel_pos_w=wheels, wheel_quat_w=wheel_quat, wheel_force_w=force,
        nominal_root_z_w=torch.full((batch,), .62, dtype=dtype),
        recovered=torch.ones(batch, courses, 4, dtype=torch.bool), **masks)


def row(value, index):
    return type(value)(**{f.name: getattr(value, f.name)[index:index+1].clone() for f in fields(value)})


def run(api, tracker, frozen, start=0, count=16, **kwargs):
    result = None
    for step in range(start, start+count):
        result = tracker.update(frame(api, frozen, step, **kwargs))
    return result


def test_fifteen_intervals_not_fifteen_observations(recovery):
    frozen = scope(recovery)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    for step in range(16):
        result = tracker.update(frame(recovery, frozen, step))
        assert result.success.item() == (step == 15)
        assert result.interval_count.item() == step
    assert result.elapsed_s.dtype == torch.float64
    assert result.elapsed_s.item() == pytest.approx(.3)
    assert result.start_frame.item() == 0 and result.last_frame.item() == 15
    assert result.start_time_s.item() == 0.
    assert result.net_forward_m.item() == pytest.approx(.03)


@pytest.mark.parametrize('start,dt,intervals',[(100.,.02,15),(10000.,.02,15),(10000.,.03,10)])
def test_global_clock_roundoff_does_not_lose_a_complete_window(recovery,start,dt,intervals):
    frozen=scope(recovery); tracker=recovery.CrossingRecoveryTracker(frozen)
    for step in range(intervals+1):
        result=tracker.update(frame(recovery,frozen,step,time=start+step*dt,dt=dt))
        assert result.success.item()==(step==intervals)
    assert result.interval_count.item()==intervals


@pytest.mark.parametrize('start', [100.,10000.,1e16])
def test_global_clock_never_rounds_up_missing_intervals(recovery,start):
    frozen=scope(recovery); tracker=recovery.CrossingRecoveryTracker(frozen)
    for step in range(15):
        result=tracker.update(frame(recovery,frozen,step,time=start+step*.02))
    assert not result.success.item()
    # A missing step is invalid even when the two endpoints span .3 seconds.
    result=tracker.update(frame(recovery,frozen,16,time=start+.32))
    assert not result.success.item() and result.interval_count.item()==0


@pytest.mark.parametrize('dtype', [torch.float32, torch.float64])
def test_real_nonstandard_dt_and_no_step_sized_epsilon(recovery, dtype):
    frozen = scope(recovery, dtype=dtype)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    times = [0., .05, .12, .18, .25, .30]
    for step, time in enumerate(times):
        dt = .05 if step == 0 else time-times[step-1]
        result = tracker.update(frame(recovery, frozen, step, time=time, dt=dt, x=1.+step*.003))
        assert result.success.item() == (step == 5)
    assert result.interval_count.item() == 5
    tracker = recovery.CrossingRecoveryTracker(frozen)
    for step in range(300):
        result = tracker.update(frame(recovery, frozen, step, dt=.001, x=2.+step*.0001))
    assert not result.success.item()
    assert result.elapsed_s.item() == pytest.approx(.299)
    # Positive displacement cannot fill the missing interval either.
    result = tracker.update(frame(recovery, frozen, 300, dt=.001, x=2.03))
    assert result.success.item()


def test_identity_and_window_isolation(recovery):
    frozen = scope(recovery, batch=2)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    first = frame(recovery, frozen)
    tracker.update(first)
    duplicate = tracker.update(first)
    assert duplicate.interval_count.tolist() == [0, 0]
    changed = frame(recovery, frozen)
    changed.leg_pos[0, 0] = .01
    with pytest.raises(ValueError, match='duplicate'):
        tracker.update(changed)
    run(recovery, tracker, frozen, start=1, count=8)
    interrupted = frame(recovery, frozen, 9)
    interrupted.valid[0] = False
    result = tracker.update(interrupted)
    assert result.start_frame.tolist() == [-1, 0]
    assert math.isnan(result.start_time_s[0].item())
    assert result.elapsed_s[0].item() == 0.
    result = run(recovery, tracker, frozen, start=10, count=8)
    assert result.elapsed_s.tolist() == pytest.approx([.14, .34])
    assert result.success.tolist() == [False, True]
    new_scope = row(frozen, 0)
    new_scope.episode_id[:] = 8
    new_scope.scope_id[:] = 14
    tracker.reset(torch.tensor([0]), new_scope)
    with pytest.raises(ValueError, match='identity'):
        tracker.update(frame(recovery, frozen, 18))
    updated = replace(frozen, episode_id=torch.tensor([8, 7]), scope_id=torch.tensor([14, 13]))
    result = tracker.update(frame(recovery, updated, 18))
    assert result.interval_count.tolist() == [0, 18]
    assert result.start_frame.tolist() == [18, 0]


@pytest.mark.parametrize('bad', ['missing', 'backward_time', 'dt_mismatch', 'nan', 'bad_quat', 'negative_dt', 'invalid'])
def test_bad_observation_rejects_evidence_and_restarts(recovery, bad):
    frozen = scope(recovery)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    run(recovery, tracker, frozen, count=15)
    sample = frame(recovery, frozen, 15)
    if bad == 'missing':
        sample = replace(sample, frame=torch.tensor([16]), sim_time_s=torch.tensor([.32]))
        sample = replace(sample, sim_time_s=sample.sim_time_s.to(frozen.centers_w.dtype))
    elif bad == 'backward_time':
        sample.sim_time_s[:] = .27
    elif bad == 'dt_mismatch':
        sample.dt_s[:] = .03
    elif bad == 'nan':
        sample.wheel_force_w[0, 0, 0] = float('nan')
    elif bad == 'bad_quat':
        sample.root_state_w[0, 3:7] = 0.
    elif bad == 'negative_dt':
        sample.dt_s[:] = -1.
    else:
        sample.valid[:] = False
    result = tracker.update(sample)
    assert not result.success.item() and not result.stable.item()
    assert result.start_frame.item() == -1 and result.interval_count.item() == 0
    assert math.isnan(result.net_forward_m.item())
    assert result.reason[0] != 'success'


def test_scope_requires_all_receipts_and_cylinder_far_side(recovery):
    for courses in (0, 1):
        frozen = scope(recovery, courses=courses)
        if courses:
            frozen.required[:] = False
        result = run(recovery, recovery.CrossingRecoveryTracker(frozen), frozen)
        assert not result.eligible.item() and not result.success.item()
    frozen = scope(recovery, courses=2)
    sample = frame(recovery, frozen)
    sample.recovered[:] = False
    sample.recovered[:, :, 0] = True
    tracker = recovery.CrossingRecoveryTracker(frozen)
    assert not tracker.update(sample).eligible.item()
    # A scope with duplicate IDs cannot bind obstacle obligations uniquely.
    wrong = replace(frozen, course_ids=torch.tensor([[101, 101]]))
    with pytest.raises(ValueError, match='course_ids'):
        recovery.CrossingRecoveryTracker(wrong)
    # Root beyond the obstacle is insufficient: a yawed Y-cylinder's rear
    # extent is its half-width, .02325, rather than an unrotated point.
    frozen = scope(recovery)
    sample = frame(recovery, frozen)
    sample.wheel_quat_w[:] = quat(yaw=math.pi/2)
    sample.wheel_pos_w[:, :, 0] = .07  # rear .04675 <= obstacle far side .05
    assert not recovery.CrossingRecoveryTracker(frozen).update(sample).eligible.item()
    sample.wheel_pos_w[:, :, 0] = .074
    assert recovery.CrossingRecoveryTracker(frozen).update(sample).eligible.item()
    # An arbitrary yaw uses the analytic cylinder support function.
    sample.wheel_quat_w[:] = quat(yaw=math.pi/4)
    sample.wheel_pos_w[:, :, 0] = .134  # .05 + (.0959+.02325)/sqrt(2) > .134
    assert not recovery.CrossingRecoveryTracker(frozen).update(sample).eligible.item()
    sample.wheel_pos_w[:, :, 0] = .135
    assert recovery.CrossingRecoveryTracker(frozen).update(sample).eligible.item()


def test_last_obstacle_and_fixed_non_x_course_direction(recovery):
    frozen = scope(recovery, courses=2)
    frozen.centers_w[0, 1, 0] = 2.
    sample = frame(recovery, frozen)
    assert not recovery.CrossingRecoveryTracker(frozen).update(sample).eligible.item()
    frozen = scope(recovery)
    frozen.forward_w[:] = torch.tensor([[0., 1., 0.]])
    tracker = recovery.CrossingRecoveryTracker(frozen)
    for step in range(16):
        sample = frame(recovery, frozen, step)
        sample.root_state_w[:, 0], sample.root_state_w[:, 1] = 0., 1.+step*.002
        sample.root_state_w[:, 3:7] = quat(yaw=math.pi/2)
        sample.root_state_w[:, 7:10] = torch.tensor([[0., .1, 0.]])
        sample.wheel_pos_w[:, :, 1] = 1.
        result = tracker.update(sample)
    assert result.success.item() and result.net_forward_m.item() == pytest.approx(.03)


@pytest.mark.parametrize('gate', ['roll', 'pitch', 'rate', 'leg', 'height', 'load', 'lateral', 'yaw', 'velocity'])
def test_real_restored_motion_and_sticky_veto(recovery, gate):
    frozen = scope(recovery)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    process = frame(recovery, frozen)
    process.root_state_w[:, 3:7] = quat(roll=.4)
    assert not tracker.update(process).vetoed.item()
    run(recovery, tracker, frozen, start=1, count=15)
    bad = frame(recovery, frozen, 16)
    if gate in ('roll', 'pitch', 'yaw'):
        bad.root_state_w[:, 3:7] = quat(**{gate: .151})
    elif gate == 'rate':
        bad.root_state_w[:, 10] = .201
    elif gate == 'leg':
        bad.leg_pos[:, 11] = .151
    elif gate == 'height':
        bad.root_state_w[:, 2] = .701
    elif gate == 'load':
        bad.wheel_force_w[:, 3, 2] = 10.
    elif gate == 'lateral':
        bad.wheel_force_w[:, 2, 0] = 20.01
    else:
        bad.root_state_w[:, 7] = 0.
    result = tracker.update(bad)
    assert not result.stable.item() and not result.success.item() and not result.vetoed.item()
    assert result.start_frame.item() == -1
    result = run(recovery, tracker, frozen, start=17)
    assert result.success.item()


@pytest.mark.parametrize('failure', ['collision', 'penetration', 'base_contact', 'physical_failure'])
def test_physical_veto_is_sticky_until_explicit_row_reset(recovery, failure):
    frozen = scope(recovery, batch=2)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    bad = frame(recovery, frozen)
    getattr(bad, failure)[0] = True
    tracker.update(bad)
    result = run(recovery, tracker, frozen, start=1)
    assert result.vetoed.tolist() == [True, False]
    assert result.success.tolist() == [False, True]
    assert failure in result.reason[0]
    tracker.reset(torch.tensor([True, False]), row(frozen, 0))
    result = tracker.update(frame(recovery, frozen, 17))
    assert result.vetoed.tolist() == [False, False]
    assert result.interval_count.tolist() == [0, 17]


@pytest.mark.parametrize('motion', ['stationary', 'lateral', 'loop', 'backwards'])
def test_actual_fixed_direction_net_displacement(recovery, motion):
    frozen = scope(recovery)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    for step in range(16):
        sample = frame(recovery, frozen, step, x=1.)
        if motion == 'lateral':
            sample.root_state_w[:, 1] = step*.1
        elif motion == 'loop':
            sample.root_state_w[:, 0] = 1.+.1*math.sin(step*2*math.pi/15)
        elif motion == 'backwards':
            sample.root_state_w[:, 0] = 1.-step*.01
        result = tracker.update(sample)
    assert not result.success.item()
    assert result.net_forward_m.item() <= 1.e-12


@pytest.mark.parametrize('terminal', ['reset', 'ended'])
def test_terminal_sample_cannot_complete_window(recovery, terminal):
    frozen = scope(recovery)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    run(recovery, tracker, frozen, count=15)
    last = frame(recovery, frozen, 15)
    getattr(last, terminal)[:] = True
    result = tracker.update(last)
    assert not result.success.item() and result.start_frame.item() == -1
    # Ending an episode cannot be undone by a later ordinary sample.
    assert not run(recovery, tracker, frozen, start=16).success.item()


def test_inputs_are_frozen_unmodified_and_batch_matches_rows(recovery):
    frozen = scope(recovery, batch=2, dtype=torch.float32)
    snapshot = {f.name: getattr(frozen, f.name).clone() for f in fields(frozen)}
    tracker = recovery.CrossingRecoveryTracker(frozen)
    singles = [recovery.CrossingRecoveryTracker(row(frozen, i)) for i in range(2)]
    frozen.centers_w[:] = 100.  # monitor owns a clone of the original scope
    original = recovery.RecoveryScope(**snapshot)
    for step in range(16):
        sample = frame(recovery, original, step)
        before = {f.name: getattr(sample, f.name).clone() for f in fields(sample)}
        result = tracker.update(sample)
        for f in fields(sample):
            assert torch.equal(getattr(sample, f.name), before[f.name])
        for i, single in enumerate(singles):
            one = single.update(row(sample, i))
            for f in fields(result):
                if f.name == 'reason':
                    assert result.reason[i] == one.reason[0]
                else:
                    torch.testing.assert_close(getattr(result, f.name)[i:i+1], getattr(one, f.name), equal_nan=True)
    assert result.success.tolist() == [True, True]
    result.elapsed_s[:] = 99.  # result must not expose internal mutable state
    assert tracker.update(sample).elapsed_s.tolist() == pytest.approx([.3, .3])


def test_structural_contract_and_reset_subbatch(recovery):
    frozen = scope(recovery, batch=2)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    with pytest.raises(ValueError):
        tracker.update(replace(frame(recovery, frozen), recovered=torch.ones(2, 1, 1, dtype=torch.bool)))
    with pytest.raises(ValueError):
        tracker.update(replace(frame(recovery, frozen), env_id=torch.tensor([1, 0])))
    with pytest.raises(ValueError):
        tracker.reset(torch.tensor([0]), frozen)
    with pytest.raises(ValueError):
        tracker.reset(torch.tensor([0, 0]), frozen)
    with pytest.raises(ValueError):
        recovery.CrossingRecoveryTracker(replace(frozen, forward_w=torch.tensor([[1., 0., 1.], [1., 0., 0.]])))
    with pytest.raises(ValueError):
        recovery.CrossingRecoveryTracker(replace(frozen, half_extents=torch.full((2, 1, 2), -1.)))
    with pytest.raises(ValueError):
        tracker.update(replace(frame(recovery, frozen), valid=torch.ones(2)))
    selected = row(frozen, 1)
    selected.episode_id[:] = 8
    tracker.reset(torch.tensor([False, True]), selected)
    updated = replace(frozen, episode_id=torch.tensor([7, 8]))
    assert tracker.update(frame(recovery, updated)).start_frame.tolist() == [0, 0]


def test_monitor_does_not_retain_action_autograd_graph(recovery):
    frozen = scope(recovery)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    for step in range(16):
        sample = frame(recovery, frozen, step)
        sample.root_state_w.requires_grad_(True)
        result = tracker.update(sample)
    assert result.success.item()
    assert not result.net_forward_m.requires_grad


@pytest.mark.parametrize('rows,order',[(torch.tensor([2,0]),[2,0]),
    (torch.tensor([True,False,True]),[0,2])],ids=['long-reversed','bool-ascending'])
def test_reset_multiple_rows_consumes_scope_in_selection_order_and_preserves_peer(recovery,rows,order):
    frozen=scope(recovery,batch=3)
    tracker=recovery.CrossingRecoveryTracker(frozen)
    first=frame(recovery,frozen)
    first.collision[0]=True; first.ended[2]=True
    tracker.update(first)
    before=run(recovery,tracker,frozen,start=1,count=15)
    assert before.success.tolist()==[False,True,False]
    selected=recovery.RecoveryScope(**{f.name:getattr(frozen,f.name)[order].clone() for f in fields(frozen)})
    selected.episode_id[:]=torch.tensor([81,82]); selected.scope_id[:]=torch.tensor([91,92])
    selected.course_ids[:]=torch.tensor([[201],[202]])
    selected.centers_w[:,0,0]=torch.tensor([-2.,2.])
    tracker.reset(rows,selected)
    updated=recovery.RecoveryScope(**{f.name:getattr(frozen,f.name).clone() for f in fields(frozen)})
    for f in fields(updated): getattr(updated,f.name)[order]=getattr(selected,f.name)
    result=tracker.update(frame(recovery,updated,16))
    assert result.vetoed.tolist()==[False,False,False]
    assert result.interval_count[order].tolist()==[0,0]
    assert result.start_frame[order].tolist()==[16,-1]
    assert result.eligible[order].tolist()==[True,False]
    assert result.success[order].tolist()==[False,False]
    assert result.start_frame[1].item()==before.start_frame[1].item()==0
    assert result.interval_count[1].item()==16
    assert result.elapsed_s[1].item()==pytest.approx(.32)
    assert result.success[1].item()
    # The second selected scope can start a fresh window once its own far side
    # is reached; no terminal state survives reset and the peer keeps counting.
    next_frame=frame(recovery,updated,17)
    next_frame.wheel_pos_w[order[1],:,0]=3.
    result=tracker.update(next_frame)
    assert result.start_frame[order].tolist()==[16,17]
    assert result.interval_count[order].tolist()==[1,0]
    assert result.interval_count[1].item()==17 and result.success[1].item()


@pytest.mark.parametrize('name', ['sim_time_s', 'dt_s', 'root_state_w', 'leg_pos', 'default_leg_pos',
                                  'wheel_pos_w', 'wheel_quat_w', 'wheel_force_w', 'nominal_root_z_w'])
def test_each_numeric_input_must_be_finite(recovery, name):
    frozen = scope(recovery, batch=2)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    run(recovery, tracker, frozen, count=15)
    bad = frame(recovery, frozen, 15)
    getattr(bad, name)[0].fill_(float('inf'))
    result = tracker.update(bad)
    assert result.success.tolist() == [False, True]
    assert result.start_frame.tolist() == [-1, 0]


def test_out_of_order_samples_cannot_replay_window(recovery):
    frozen = scope(recovery)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    run(recovery, tracker, frozen, count=15)
    assert not tracker.update(frame(recovery, frozen, 0)).stable.item()
    result = run(recovery, tracker, frozen, start=1, count=14)
    assert not result.success.item() and result.interval_count.item() == 0
    result = tracker.update(frame(recovery, frozen, 15))
    assert result.start_frame.item() == 15 and result.interval_count.item() == 0


def test_success_clears_when_subsequent_observation_is_not_restored(recovery):
    frozen = scope(recovery)
    tracker = recovery.CrossingRecoveryTracker(frozen)
    assert run(recovery, tracker, frozen).success.item()
    bad = frame(recovery, frozen, 16)
    bad.root_state_w[:, 3:7] = quat(roll=.4)
    result = tracker.update(bad)
    assert not result.success.item() and not result.vetoed.item()


def test_heading_wrap_and_exact_geometric_contact(recovery):
    frozen = scope(recovery)
    frozen.forward_w[:] = torch.tensor([[-1., 0., 0.]])
    sample = frame(recovery, frozen)
    sample.root_state_w[:, 3:7] = quat(yaw=-math.pi+.01)
    sample.root_state_w[:, 7] = -.1
    sample.wheel_pos_w[:, :, 0] = -1.
    assert recovery.CrossingRecoveryTracker(frozen).update(sample).stable.item()
    frozen = scope(recovery)
    sample = frame(recovery, frozen)
    sample.wheel_pos_w[:, :, 0] = .1459  # tangent at far .05, still not beyond
    assert not recovery.CrossingRecoveryTracker(frozen).update(sample).eligible.item()


def test_safe_negative_boundary_values_and_partial_obligations(recovery):
    frozen = scope(recovery)
    frozen.required[:] = False
    frozen.required[:, :, :2] = True
    sample = frame(recovery, frozen)
    sample.recovered[:, :, 2:] = False
    sample.root_state_w[:, 3:7] = quat(roll=-.149, pitch=-.149)
    sample.root_state_w[:, 2] = .541
    sample.leg_pos[:] = -.149
    sample.wheel_force_w[:, :, 0] = 20.  # equality with current vertical load is permitted
    assert recovery.CrossingRecoveryTracker(frozen).update(sample).stable.item()
