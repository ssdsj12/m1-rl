"""Measured trajectories, not commanded swing references, for autonomous timing."""
import inspect
import pytest
import torch
from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker


class Frames:
    def __init__(self, modes=(True,)):
        self.modes = torch.tensor(modes, dtype=torch.bool)
        self.n = len(modes)
        self.tracker = EncounterCrossingTracker(self.n, 'cpu', obstacle_count=1)
        self.course = {
            'centers_top': torch.tensor([[[0., 0., .1]]]).repeat(self.n, 1, 1),
            'half_extents': torch.full((self.n, 1, 2), .025),
            'valid': torch.ones(self.n, 1, dtype=torch.bool),
            'ids': torch.full((self.n, 1), 17, dtype=torch.long),
        }

    def step(self, x, bottom, *, contacts=None, touch=False, collision=False, y=0., mode=True):
        pos = torch.zeros(self.n, 4, 3)
        pos[:, :, 0] = x
        pos[:, :, 1] = torch.tensor([y, 1., 1.5, 2.])
        pos[:, :, 2] = .1
        pos[:, 0, 2] += bottom
        q = torch.zeros(self.n, 4, 4); q[:, :, 0] = 1.
        grounded = torch.ones(self.n, 4, dtype=torch.bool)
        grounded[:, 0] = bottom <= .001
        if contacts is not None:
            grounded[:] = torch.tensor(contacts, dtype=torch.bool)
        args = dict(wheel_pos_w=pos, wheel_quat_w=q, course=self.course,
            direction_w=torch.tensor([[1., 0.]]).repeat(self.n, 1),
            wheel_bottom_z_w=pos[:, :, 2] - .1, wheel_grounded=grounded,
            support_safe=torch.ones(self.n, dtype=torch.bool),
            touchdown_safe=torch.full((self.n,), touch, dtype=torch.bool),
            collision=torch.full((self.n,), collision, dtype=torch.bool),
            wheel_horizontal_radius=.1, wheel_vertical_radius=.1, wheel_thickness=.04,
            required_clearance=.03, required_far_margin=.04, stable_frames=5)
        # On the pre-feature baseline, expose semantic failures rather than
        # stopping every trajectory at an unexpected-keyword TypeError.
        if mode and 'autonomous_lift' in inspect.signature(self.tracker.update).parameters:
            args['autonomous_lift'] = self.modes
        return self.tracker.update(**args)


@pytest.mark.parametrize('gap', [.24, .05, .02, .005])
def test_already_lifted_entry_needs_no_2cm_history_at_any_distance(gap):
    f = Frames()
    out = f.step(-.125-gap, .14)
    assert out['attempt_started'].item()
    assert out['prelift_progress_delta'].item() == 0  # no loaded baseline
    assert not f.tracker.early_lift.item()
    f.step(0., .14)
    assert f.step(.30, 0., touch=True)['event_complete'].item()
    for i in range(5):
        out = f.step(.30, 0., touch=True)
        assert out['recovery_complete'].item() == (i == 4)
    assert f.tracker.recovered_for_course(f.course)[0, 0, 0]


def test_safe_pre_obstacle_landing_allows_retry_without_reward_refresh():
    f = Frames()
    f.step(-.32, 0.)
    first = f.step(-.25, .025)
    assert first['single_prelift_event'].item()
    assert not f.step(-.24, 0., touch=True)['failed'].item()
    repeated = f.step(-.22, .025)
    assert repeated['prelift_progress_delta'].item() == 0
    assert not repeated['single_prelift_event'].item()
    last = f.step(-.18, .14)
    total = first['prelift_progress_delta'] + last['prelift_progress_delta']
    assert total.item() == pytest.approx(.13/.02)
    f.step(0., .14)
    assert f.step(.30, 0., touch=True)['event_complete'].item()


@pytest.mark.parametrize('rise', [.001, .005, .019, .021])
def test_support_loss_during_lift_fails_without_height_threshold(rise):
    f = Frames()
    f.step(-.32, 0.)
    out = f.step(-.24, rise, contacts=[False, False, True, True])
    assert out['failed'].item()
    assert out['prelift_progress_delta'].item() == 0
    assert f.step(-.23, 0., touch=True)['failed'].item()
    f.step(0., .14)
    assert not f.step(.30, 0., touch=True)['event_complete'].item()


@pytest.mark.parametrize('bad', ['loaded', 'lost_support', 'low_clearance', 'collision', 'early_land'])
def test_crossing_physical_failures_cannot_be_retried_away(bad):
    f = Frames()
    f.step(-.32, 0.)
    f.step(-.23, .03)
    if bad == 'loaded':
        out = f.step(0., .14, contacts=[True]*4)
    elif bad == 'lost_support':
        out = f.step(0., .14, contacts=[False, False, True, True])
    elif bad == 'low_clearance':
        f.step(-.02, .14)
        out = f.step(.02, .12)
    elif bad == 'collision':
        out = f.step(0., .14, collision=True)
    else:
        f.step(0., .14)
        out = f.step(.14, 0., touch=True)  # past top but before required .04 margin
    assert out['failed'].item()
    f.step(-.23, 0., touch=True)
    f.step(-.20, .14)
    f.step(0., .14)
    assert not f.step(.30, 0., touch=True)['event_complete'].item()


@pytest.mark.parametrize('bypass', [False, True])
def test_no_actual_overlap_cannot_certify_success(bypass):
    f = Frames()
    f.step(-.32, 0.)
    f.step(-.22, .14)
    if bypass:
        f.step(0., .14, y=.3)
    assert not f.step(.30, 0., touch=True)['event_complete'].item()


def test_current_support_failure_trace_stays_failed():
    f = Frames()
    f.step(-.374, 0.)
    # Near-gap .246 and off-lane as in captured env283; selected encounter persists.
    f.step(-.371, .022032, y=.151259)
    out = f.step(-.3695, .021808, contacts=[False]*4, y=.151259)
    assert out['failed'].item()
    assert out['prelift_progress_delta'].item() == 0
    assert not out['event_complete'].item()


def test_batch_mixed_mode_keeps_legacy_2cm_gate():
    f = Frames((True, False))
    f.step(-.32, .14)
    f.step(0., .14)
    assert f.step(.30, 0., touch=True)['event_complete'].tolist() == [True, False]


def test_default_call_remains_legacy():
    f = Frames()
    f.step(-.32, .14, mode=False)
    f.step(0., .14, mode=False)
    assert not f.step(.30, 0., touch=True, mode=False)['event_complete'].item()


@pytest.mark.parametrize('clear', ['reset', 'identity', 'mode'])
def test_state_changes_do_not_reuse_previous_overlap(clear):
    f = Frames()
    f.step(-.32, 0.)
    f.step(-.23, .03)
    f.step(0., .14)
    if clear == 'reset':
        f.tracker.reset(torch.tensor([True]))
    elif clear == 'identity':
        f.course['ids'][:] = 18
    else:
        f.modes[:] = False
    assert not f.step(.30, 0., touch=True)['event_complete'].item()
    assert not f.tracker.recovered_for_course(f.course).any()


def test_nonfinite_bottom_rejected():
    f = Frames()
    f.step(-.32, 0.)
    with pytest.raises(ValueError, match='finite'):
        f.step(0., float('nan'))


def test_lateral_escape_after_partial_overlap_cannot_reuse_clearance():
    f = Frames()
    f.step(-.32, 0.)
    f.step(-.23, .14)
    f.step(-.12, .14)  # only leading tire tip has entered
    out = f.step(-.10, .14, y=.2)  # divert around the side before passing
    assert out['failed'].item()
    assert not f.step(.30, 0., touch=True)['event_complete'].item()


def test_telemetry_stays_vertical_2cm_while_small_rises_are_rewarded():
    f = Frames()
    f.step(-.32, 0.)
    out = f.step(-.25, .005)
    assert out['prelift_progress_delta'].item() == pytest.approx(.005/.02)
    assert not out['single_prelift_event'].item()
    out = f.step(-.22, .025)
    assert out['single_prelift_event'].item()


def test_mode_change_clears_existing_recovery_receipt():
    f = Frames()
    f.step(-.32, .14); f.step(0., .14); f.step(.30, 0., touch=True)
    for _ in range(5):
        f.step(.30, 0., touch=True)
    assert f.tracker.recovered_for_course(f.course).any()
    f.modes[:] = False
    f.step(.30, 0., touch=True)
    assert not f.tracker.recovered_for_course(f.course).any()
