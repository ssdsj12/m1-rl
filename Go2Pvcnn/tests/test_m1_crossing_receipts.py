"""Persistent strict receipts and obstacle-height prelift reward bounds."""
import pytest
import torch

from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker


def _scene(*, top=.10, wheel=0, slot=0, batch=1):
    tracker = EncounterCrossingTracker(batch, 'cpu', obstacle_count=2)
    course = {
        'centers_top': torch.tensor([[[2., 3., top], [99., 99., top]]]).repeat(batch, 1, 1),
        'half_extents': torch.full((batch, 2, 2), .025),
        'valid': torch.zeros(batch, 2, dtype=torch.bool),
        'ids': torch.full((batch, 2), -1, dtype=torch.long),
    }
    course['centers_top'][:, slot] = torch.tensor([2., 3., top])
    course['valid'][:, slot] = True
    course['ids'][:, slot] = 17
    return tracker, course, wheel


def _step(t, c, wheel, x=-.22, bottom=0., *, loaded=False, paired=False,
          touch=False, support=True, collision=False, required_clearance=.03):
    batch = c['ids'].shape[0]
    pos = torch.zeros(batch, 4, 3)
    pos[:, :, 0] = 2. + x
    pos[:, :, 1] = torch.tensor([4., 5., 6., 7.])
    pos[:, wheel, 1] = 3.
    pos[:, :, 2] = .1
    pos[:, wheel, 2] = .1 + bottom
    measured = torch.zeros(batch, 4)
    measured[:, wheel] = bottom
    grounded = torch.ones(batch, 4, dtype=torch.bool)
    grounded[:, wheel] = loaded
    if paired:
        grounded[:, (wheel + 1) % 4] = False
    quat = torch.zeros(batch, 4, 4)
    quat[:, :, 0] = 1.
    return t.update(wheel_pos_w=pos, wheel_quat_w=quat, course=c,
        direction_w=torch.tensor([[1., 0.]]).repeat(batch, 1),
        wheel_bottom_z_w=measured, wheel_grounded=grounded,
        support_safe=torch.as_tensor(support).bool().expand(batch),
        touchdown_safe=torch.full((batch,), touch, dtype=torch.bool),
        collision=torch.full((batch,), collision, dtype=torch.bool),
        wheel_horizontal_radius=.1, wheel_vertical_radius=.1, wheel_thickness=.04,
        required_clearance=required_clearance, required_far_margin=.04, stable_frames=2)


def _touchdown(t, c, wheel):
    assert _step(t, c, wheel, -.32, loaded=True)['attempt_started'].all()
    _step(t, c, wheel, bottom=.04)
    _step(t, c, wheel, 0., .14)
    out = _step(t, c, wheel, .30, loaded=True, touch=True)
    assert out['event_complete'].all()
    assert not out['recovery_complete'].any()
    return out


@pytest.mark.parametrize('wheel', range(4))
@pytest.mark.parametrize('slot', range(2))
def test_receipt_records_only_selected_pair_after_strict_recovery(wheel, slot):
    t, c, wheel = _scene(wheel=wheel, slot=slot)
    assert t.recovered.shape == (1, 2, 4)
    assert t.recovered.dtype == torch.bool
    assert not t.recovered_for_course(c).any()
    _touchdown(t, c, wheel)
    assert not t.recovered.any()  # Attempt and loaded touchdown are insufficient.
    assert not _step(t, c, wheel, .30, loaded=True, touch=True)['recovery_complete'].item()
    assert not t.recovered.any()
    out = _step(t, c, wheel, .30, loaded=True, touch=True)
    assert out['recovery_complete'].item()
    assert t.slot.item() == -1  # Release must preserve the persistent receipt.
    expected = torch.zeros_like(t.recovered)
    expected[0, slot, wheel] = True
    assert torch.equal(t.recovered, expected)
    assert torch.equal(t.recovered_for_course(c), expected)
    _step(t, c, wheel, 1., loaded=True)
    assert torch.equal(t.recovered, expected)


@pytest.mark.parametrize('failure', ['late_lift', 'scrape', 'collision', 'paired', 'early_touchdown'])
def test_failed_or_abandoned_encounter_never_produces_receipt(failure):
    t, c, wheel = _scene()
    _step(t, c, wheel, -.32, loaded=True)
    if failure != 'late_lift':
        _step(t, c, wheel, bottom=.04, paired=failure == 'paired')
    _step(t, c, wheel, 0., .11 if failure == 'scrape' else .14,
          collision=failure == 'collision')
    if failure == 'early_touchdown':
        _step(t, c, wheel, .02, loaded=True, touch=True)
    for _ in range(4):
        out = _step(t, c, wheel, .30, loaded=True, touch=True)
        assert not out['recovery_complete'].item()
    _step(t, c, wheel, 1., loaded=True)
    assert t.slot.item() == -1
    assert t.used[0, 0, wheel]
    assert not t.recovered.any()


def test_receipt_requires_consecutive_nominal_support_and_no_recovery_collision():
    t, c, wheel = _scene()
    _touchdown(t, c, wheel)
    _step(t, c, wheel, .30, loaded=True, touch=True)
    _step(t, c, wheel, .30, loaded=True, touch=True, support=False)
    assert not _step(t, c, wheel, .30, loaded=True, touch=True)['recovery_complete'].item()
    assert not t.recovered.any()
    out = _step(t, c, wheel, .30, loaded=True, touch=True, collision=True)
    assert out['failed'].item()
    assert not out['recovery_complete'].item()
    assert not t.recovered.any()


def test_receipts_reset_only_done_rows_and_copy_cannot_mutate_ledger():
    t, c, wheel = _scene(batch=2)
    _touchdown(t, c, wheel)
    for _ in range(2):
        _step(t, c, wheel, .30, loaded=True, touch=True)
    snapshot = t.recovered_for_course(c)
    snapshot.zero_()
    assert t.recovered[:, 0, 0].all()
    t.reset(torch.tensor([True, False]))
    assert not t.recovered[0].any()
    assert t.recovered[1, 0, 0]
    assert not t.recovered_for_course(c)[0].any()


def test_registry_identity_mismatch_fails_closed_before_update_then_resets_row():
    t, c, wheel = _scene(batch=2)
    _touchdown(t, c, wheel)
    for _ in range(2):
        _step(t, c, wheel, .30, loaded=True, touch=True)
    c['ids'][0, 0] = 42
    snapshot = t.recovered_for_course(c)
    assert not snapshot[0].any()
    assert snapshot[1, 0, 0]
    assert t.recovered[0, 0, 0]  # Read-only pre-step query must not reset state.
    out = _step(t, c, wheel, -.32, loaded=True)
    assert not out['attempt_started'][0]
    assert not t.recovered[0].any()
    assert t.recovered[1, 0, 0]
    c['valid'][1, 0] = False
    assert not t.recovered_for_course(c).any()


def test_next_encounter_gets_new_budget_without_erasing_prior_receipt():
    t, c, wheel = _scene()
    c['centers_top'][0, 1] = torch.tensor([3., 3., .10])
    c['valid'][0, 1] = True
    c['ids'][0, 1] = 18
    _touchdown(t, c, wheel)
    for _ in range(2):
        _step(t, c, wheel, .30, loaded=True, touch=True)
    assert t.recovered[0, 0, wheel]
    assert _step(t, c, wheel, .68, loaded=True)['attempt_started'].item()
    out = _step(t, c, wheel, .78, .003)
    assert out['prelift_progress_delta'].item() == pytest.approx(.15)
    assert t.recovered[0, 0, wheel]
    assert not t.recovered[0, 1].any()
    _step(t, c, wheel, .78, .04)
    _step(t, c, wheel, 1., .14)
    assert _step(t, c, wheel, 1.30, loaded=True, touch=True)['event_complete'].item()
    for _ in range(2):
        _step(t, c, wheel, 1.30, loaded=True, touch=True)
    assert t.recovered[0, :, wheel].all()
    assert t.recovered.sum().item() == 2


@pytest.mark.parametrize('top', [.03, .06, .10])
def test_increment_continues_at_same_slope_through_actual_obstacle_target(top):
    t, c, wheel = _scene(top=top)
    _step(t, c, wheel, -.32, loaded=True)
    target = top + .03
    deltas = []
    for bottom in (.003, .008, .012, .02, .04, target, target + .05):
        out = _step(t, c, wheel, bottom=bottom)
        deltas.append(out['prelift_progress_delta'].item())
        assert not out['event_complete'].item()
        assert not out['recovery_complete'].item()
    assert deltas[:5] == pytest.approx([.15, .25, .20, .40, 1.], abs=1e-6)
    assert deltas[-1] == 0.
    assert sum(deltas) == pytest.approx(target / .02, abs=1e-6)
    assert t.prelift_high_water.item() == pytest.approx(target / .02, abs=1e-6)


@pytest.mark.parametrize('top,clearance', [(.03, .03), (.06, .04), (.10, .05)])
def test_one_large_measured_increment_is_not_clamped_to_one_unit(top, clearance):
    t, c, wheel = _scene(top=top)
    _step(t, c, wheel, -.32, loaded=True, required_clearance=clearance)
    out = _step(t, c, wheel, bottom=.5, required_clearance=clearance)
    assert out['prelift_progress_delta'].item() == pytest.approx((top + clearance) / .02)
    assert out['single_prelift_event'].item()
    assert not out['event_complete'].item()
    assert not _step(t, c, wheel, bottom=.6,
        required_clearance=clearance)['prelift_progress_delta'].item()


def test_budget_uses_initial_loaded_bottom_and_lower_recontact_never_refills_it():
    t, c, wheel = _scene(top=.03)
    _step(t, c, wheel, -.32, .01, loaded=True)
    first = _step(t, c, wheel, bottom=.016)['prelift_progress_delta'].item()
    assert first == pytest.approx(.3)
    _step(t, c, wheel, bottom=-.03, loaded=True)
    assert _step(t, c, wheel, bottom=.016)['prelift_progress_delta'].item() == 0.
    last = _step(t, c, wheel, bottom=.09)['prelift_progress_delta'].item()
    assert first + last == pytest.approx((.06 - .01) / .02)
    assert _step(t, c, wheel, bottom=.20)['prelift_progress_delta'].item() == 0.


@pytest.mark.parametrize('baseline', [-.01, .01, .06, .10])
def test_budget_measures_world_rise_from_loaded_baseline_and_never_pays_above_target(baseline):
    t, c, wheel = _scene(top=.03)
    _step(t, c, wheel, -.32, baseline, loaded=True)
    out = _step(t, c, wheel, bottom=.20)
    assert out['prelift_progress_delta'].item() == pytest.approx(max(0., .06-baseline)/.02)
    for bottom in (.15, .30, .07, .20):
        assert _step(t, c, wheel, bottom=bottom)['prelift_progress_delta'].item() == 0.


@pytest.mark.parametrize('restart', ['reset', 'registry_change'])
def test_new_episode_or_registry_discards_old_height_budget(restart):
    t, c, wheel = _scene(top=.03)
    _step(t, c, wheel, -.32, loaded=True)
    assert _step(t, c, wheel, bottom=.20)['prelift_progress_delta'].item() == pytest.approx(3.)
    if restart == 'reset':
        t.reset(torch.tensor([True]))
    else:
        c['ids'][0, 0] = 24
        _step(t, c, wheel, -.32, loaded=True)
    _step(t, c, wheel, -.32, .01, loaded=True)
    assert _step(t, c, wheel, bottom=.20)['prelift_progress_delta'].item() == pytest.approx(2.5)


def test_loaded_uphill_rise_and_bobbing_do_not_earn_or_repeat_height():
    t, c, wheel = _scene(top=.06)
    _step(t, c, wheel, -.32, loaded=True)
    assert _step(t, c, wheel, bottom=.03, loaded=True)['prelift_progress_delta'].item() == 0.
    assert _step(t, c, wheel, bottom=.036)['prelift_progress_delta'].item() == pytest.approx(.3)
    for bottom in (.032, .036, .035, .036):
        assert _step(t, c, wheel, bottom=bottom)['prelift_progress_delta'].item() == 0.
    assert _step(t, c, wheel, bottom=.09)['prelift_progress_delta'].item() == pytest.approx(2.7)
    assert t.prelift_high_water.item() == pytest.approx(3.)


def test_subthreshold_paired_rise_cannot_be_paid_after_other_wheel_recontacts():
    t, c, wheel = _scene(top=.03)
    _step(t, c, wheel, -.32, loaded=True)
    paired = _step(t, c, wheel, bottom=.01, paired=True)
    assert paired['prelift_progress_delta'].item() == 0.
    assert not paired['failed'].item()
    single = _step(t, c, wheel, bottom=.01)
    assert single['prelift_progress_delta'].item() == 0.
    assert not single['single_prelift_event'].item()
    assert _step(t, c, wheel, bottom=.015)['prelift_progress_delta'].item() == pytest.approx(.25)


def test_retreating_release_frame_does_not_pay_airborne_height():
    t, c, wheel = _scene(top=.03)
    _step(t, c, wheel, -.32, loaded=True)
    assert _step(t, c, wheel, bottom=.01)['prelift_progress_delta'].item() == pytest.approx(.5)
    out = _step(t, c, wheel, -.60, .06)
    assert out['failed'].item()
    assert t.slot.item() == -1
    assert out['prelift_progress_delta'].item() == 0.
    assert not t.recovered.any()


@pytest.mark.parametrize('unsafe', ['loaded', 'paired', 'collision', 'missing_reference'])
def test_target_extension_keeps_contact_and_collision_guards(unsafe):
    t, c, wheel = _scene(top=.10)
    if unsafe != 'missing_reference':
        _step(t, c, wheel, -.32, loaded=True)
    out = _step(t, c, wheel, bottom=.14, loaded=unsafe == 'loaded',
        paired=unsafe == 'paired', collision=unsafe == 'collision')
    assert out['prelift_progress_delta'].item() == 0.
    assert not out['single_prelift_event'].item()
    assert not t.recovered.any()


def test_fractional_progress_does_not_relax_two_centimeter_event_or_clearance():
    t, c, wheel = _scene(top=.03)
    _step(t, c, wheel, -.32, loaded=True)
    out = _step(t, c, wheel, bottom=.019)
    assert out['prelift_progress_delta'].item() == pytest.approx(.95)
    assert not out['single_prelift_event'].item()
    assert not t.early_lift.item()
    _step(t, c, wheel, 0., .059)  # <3cm above the actual top remains failure.
    out = _step(t, c, wheel, .30, loaded=True, touch=True)
    assert out['failed'].item()
    assert not out['event_complete'].item()
    assert not t.recovered.any()
