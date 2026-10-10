import torch
import pytest
from test_m1_dynamic_crossing import scene, tick
from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker


def test_clearance_minimum_and_counts_are_not_averaged():
    from ame_baseline.m1_required_crossing import aggregate_metric
    assert aggregate_metric('RequiredCrossing/min_bottom_clearance_m',
        torch.tensor([float('nan'), .04, -.01])).item() == pytest.approx(-.01)
    assert aggregate_metric('RequiredCrossing/clearance_samples', torch.tensor([2., 3., 0.])).item() == 5
    assert torch.isnan(aggregate_metric('RequiredCrossing/min_bottom_clearance_m',
        torch.tensor([float('nan')]))).item()


def test_prelift_reward_pulse_requires_one_airborne_wheel_and_is_once():
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    tick(t, c, d, f(-.32, .10))
    grounded = torch.tensor([[False, True, True, True]])
    out = tick(t, c, d, f(-.22, .14), grounded=grounded)
    assert out.get('single_prelift_event', torch.tensor([False])).item()
    assert not tick(t, c, d, f(-.20, .16), grounded=grounded)['single_prelift_event'].item()


def test_overlap_reports_actual_bottom_clearance_not_center():
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    tick(t, c, d, f(-.32, .10))
    tick(t, c, d, f(-.22, .14))
    out = tick(t, c, d, f(0., .24))
    assert out.get('overlap_sample', torch.tensor([False])).item()
    assert out['bottom_clearance'].item() == pytest.approx(.04, abs=1e-6)


def test_low_second_overlap_cannot_reuse_first_good_clearance():
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    tick(t, c, d, f(-.32, .10))
    tick(t, c, d, f(-.22, .14))
    tick(t, c, d, f(-.02, .24))
    tick(t, c, d, f(.02, .21))  # only1cm net clearance, still airborne
    assert not tick(t, c, d, f(.30, .10), touch=True)['event_complete'].item()


@pytest.mark.parametrize('airborne',[2,4])
def test_multiwheel_lift_never_qualifies_as_single_wheel_crossing(airborne):
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2); c,d,f=scene()
    tick(t,c,d,f(-.32,.10))
    contacts=torch.ones(1,4,dtype=torch.bool); contacts[:,:airborne]=False
    out=tick(t,c,d,f(-.22,.14),grounded=contacts)
    assert not out['single_prelift_event'].item()
    tick(t,c,d,f(0.,.24),grounded=contacts)
    assert not tick(t,c,d,f(.30,.10),touch=True)['event_complete'].item()


def test_required_reward_gate_strips_positive_not_penalties_or_flat_reward():
    from ame_baseline.m1_required_crossing import required_crossing_reward
    parts = torch.tensor([[2., 1., -3.], [2., 1., -3.], [2., 1., -3.]])
    result, removed, bonus = required_crossing_reward(
        parts.sum(-1) * .02, parts, .02,
        blocked=torch.tensor([True, True, False]),
        collision=torch.tensor([True, False, False]),
        done=torch.tensor([False, False, False]),
        prelift=torch.tensor([True, False, False]), recovery=torch.tensor([False, False, False]))
    assert result.tolist() == pytest.approx([-.06, -.06, 0.])
    assert bonus.tolist() == [0., 0., 0.]


def test_terminal_pose_cannot_reward_and_recovery_is_not_touchdown():
    from ame_baseline.m1_required_crossing import required_crossing_reward
    z = torch.zeros(3)
    result, _, bonus = required_crossing_reward(z, z[:, None], .02,
        blocked=torch.ones(3, dtype=torch.bool), collision=torch.zeros(3, dtype=torch.bool),
        done=torch.tensor([False, False, True]), prelift=torch.zeros(3, dtype=torch.bool),
        recovery=torch.tensor([False, True, True]))
    assert bonus.tolist() == [0., 2., 0.]


def test_late_valid_recovery_outside_slab_still_earns_completion_bonus():
    from ame_baseline.m1_required_crossing import required_crossing_reward
    z=torch.zeros(1); no=torch.tensor([False])
    _, _, bonus=required_crossing_reward(z,z[:,None],.02,blocked=no,collision=no,
        done=no,prelift=no,recovery=~no)
    assert bonus.item()==2.


def test_route_zone_does_not_disappear_when_policy_bypasses_laterally():
    from ame_baseline.m1_required_crossing import required_crossing_zone
    c, _, _ = scene()
    for y in (3., 4., 8.):
        assert required_crossing_zone(torch.tensor([[2., y, .45]]), c).item()
    c['valid'].zero_()
    assert not required_crossing_zone(torch.tensor([[2., 3., .45]]), c).item()


def test_progressive_target_covers_lane_drift_without_blocking_opposite_support(monkeypatch):
    from test_semantic_course_curriculum_layout import _install_fake_isaaclab
    _install_fake_isaaclab(monkeypatch)
    from extension.semantic_course import SemanticCourseLayoutCfg, build_course_anchors
    from extension.semantic_curriculum import SemanticObstacleCurriculumCfg, SemanticObstacleCount
    anchors = build_course_anchors([[[16.*i,0.,0.]] for i in range(4)], tile_size=(16.,16.),
        terrain_names=('flat',),
        semantic_curriculum_cfg=SemanticObstacleCurriculumCfg(
            plane_counts=tuple(SemanticObstacleCount(n,0) for n in (0,2,4,8)), min_spacing_clearance_m=(.45,)),
        layout_cfg=SemanticCourseLayoutCfg(placement_strategy='m1_progressive', small_shape_pool=('cuboid','cylinder')),
        scale_profile_overrides={'small':(.05,.10),'large':(.45,.55)})
    for a in anchors:
        assert a.shape_kind == 'cuboid'
        hx, hy = a.shape_params['size'][0]/2, a.shape_params['size'][1]/2
        assert hy >= .08  # covers +/-8cm center drift even before tire width
        assert .43 - hy - .05 >= .25  # opposite wheel support stays free
        assert .9 - 2*hx - .20 >= .5  # open longitudinal rolling/landing space


def _prelift_delta(out):
    return out.get('prelift_progress_delta', torch.zeros(1)).item()


def test_millimeter_airborne_prelift_is_incremental_capped_and_not_success():
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    tick(t, c, d, f(-.32, .10))
    airborne = torch.tensor([[False, True, True, True]])
    deltas = []
    for rise in (.003, .008, .012, .03, .04):
        out = tick(t, c, d, f(-.22, .10 + rise), grounded=airborne)
        deltas.append(_prelift_delta(out))
        assert not out['event_complete'].item()
        assert not out['recovery_complete'].item()
        if rise < .02:
            assert not out['single_prelift_event'].item()
    assert deltas == pytest.approx([.15, .25, .20, .40, 0.], abs=1e-6)
    assert sum(deltas) == pytest.approx(1.)
    assert t.crossing_count.item() == 0


def test_prelift_bobbing_and_recontact_cannot_repeat_paid_height():
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    tick(t, c, d, f(-.32, .10))
    airborne = torch.tensor([[False, True, True, True]])
    assert _prelift_delta(tick(t, c, d, f(-.22, .11), grounded=airborne)) == pytest.approx(.5)
    assert _prelift_delta(tick(t, c, d, f(-.22, .104), grounded=airborne)) == 0.
    assert _prelift_delta(tick(t, c, d, f(-.22, .10), touch=True)) == 0.
    assert _prelift_delta(tick(t, c, d, f(-.22, .11), grounded=airborne)) == 0.
    assert _prelift_delta(tick(t, c, d, f(-.22, .115), grounded=airborne)) == pytest.approx(.25, abs=1e-6)


def test_lower_loaded_reference_cannot_reward_repeating_world_bottom_height():
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    tick(t, c, d, f(-.32, .10))
    airborne = torch.tensor([[False, True, True, True]])
    assert _prelift_delta(tick(t, c, d, f(-.22, .106), grounded=airborne)) == pytest.approx(.3, abs=1e-6)
    tick(t, c, d, f(-.22, .094), grounded=torch.ones(1, 4, dtype=torch.bool))
    assert _prelift_delta(tick(t, c, d, f(-.22, .106), grounded=airborne)) == 0.


@pytest.mark.parametrize('unsafe', ['loaded', 'paired', 'collision', 'failed', 'missing_reference',
                                  'before_edge', 'bypass', 'no_encounter'])
def test_prelift_increment_requires_actual_safe_single_wheel_approach(unsafe):
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    airborne = torch.tensor([[False, True, True, True]])
    if unsafe != 'missing_reference':
        tick(t, c, d, f(-.32, .10))
    if unsafe == 'failed':
        t.inner.failed.fill_(True)
    if unsafe == 'loaded':
        airborne.fill_(True)
    if unsafe == 'paired':
        airborne[:, 1] = False
    if unsafe == 'no_encounter':
        c['valid'].zero_()
        t.reset(torch.tensor([True]))
    pos = f(-.12 if unsafe == 'before_edge' else -.22, .103)
    if unsafe == 'bypass':
        pos[:, 0, 1] += .1
    out = tick(t, c, d, pos, grounded=airborne, collision=unsafe == 'collision')
    assert _prelift_delta(out) == 0.


def test_loaded_uphill_bottom_replaces_ground_reference_before_increment():
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    loaded = torch.ones(1, 4, dtype=torch.bool)
    assert _prelift_delta(tick(t, c, d, f(-.32, .12), grounded=loaded)) == 0.
    assert _prelift_delta(tick(t, c, d, f(-.27, .15), grounded=loaded)) == 0.
    loaded[:, 0] = False
    assert _prelift_delta(tick(t, c, d, f(-.22, .153), grounded=loaded)) == pytest.approx(.15, abs=1e-6)


@pytest.mark.parametrize('restart', ['reset', 'new_obstacle', 'registry_change'])
def test_prelift_high_water_resets_only_with_a_new_encounter(restart):
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    if restart == 'new_obstacle':
        c['valid'][0, 1] = True
        c['ids'][0, 1] = 18
        c['centers_top'][0, 1] = torch.tensor([3., 3., .1])
    airborne = torch.tensor([[False, True, True, True]])
    tick(t, c, d, f(-.32, .10))
    assert _prelift_delta(tick(t, c, d, f(-.22, .11), grounded=airborne)) == pytest.approx(.5)
    if restart == 'reset':
        t.reset(torch.tensor([True]))
        tick(t, c, d, f(-.32, .10))
        pos = f(-.22, .103)
    elif restart == 'registry_change':
        c['ids'][0, 0] = 25
        tick(t, c, d, f(-.32, .10))  # registry invalidation does not start same frame
        tick(t, c, d, f(-.32, .10))
        pos = f(-.22, .103)
    else:
        tick(t, c, d, f(.68, .10))  # release old attempt outside its vicinity
        assert tick(t, c, d, f(.68, .10))['attempt_started'].item()
        pos = f(.78, .103)
    assert _prelift_delta(tick(t, c, d, pos, grounded=airborne)) == pytest.approx(.15, abs=1e-6)


def test_required_reward_uses_progress_without_threshold_double_bonus():
    from ame_baseline.m1_required_crossing import required_crossing_reward
    z = torch.zeros(5)
    _, _, bonus = required_crossing_reward(z, z[:, None], .02,
        blocked=torch.tensor([True, True, True, True, False]),
        collision=torch.tensor([False, False, True, False, False]),
        done=torch.tensor([False, False, False, True, False]),
        prelift=torch.ones(5, dtype=torch.bool), recovery=torch.zeros(5, dtype=torch.bool),
        prelift_progress_delta=torch.tensor([.15, 0., .15, .15, .15]))
    assert bonus.tolist() == pytest.approx([.045, 0., 0., 0., 0.])


def test_increment_uses_measured_bottom_even_when_center_rises_further():
    t = EncounterCrossingTracker(1, 'cpu', obstacle_count=2)
    c, d, f = scene()
    tick(t, c, d, f(-.32, .10))
    pos = f(-.22, .14)
    bottom = torch.zeros(1, 4)
    bottom[:, 0] = .003  # orientation makes actual mesh-bottom rise only3mm
    q = torch.zeros(1, 4, 4); q[:, :, 0] = 1.
    out = t.update(wheel_pos_w=pos, wheel_quat_w=q, course=c, direction_w=d,
        wheel_bottom_z_w=bottom, wheel_grounded=torch.tensor([[False, True, True, True]]),
        support_safe=torch.tensor([True]), touchdown_safe=torch.tensor([False]),
        collision=torch.tensor([False]), wheel_horizontal_radius=.1,
        wheel_vertical_radius=.1, wheel_thickness=.04)
    assert _prelift_delta(out) == pytest.approx(.15, abs=1e-6)
    assert not out['single_prelift_event'].item()
    assert not out['event_complete'].item()


@pytest.mark.parametrize('dt', [.02, .2])
def test_progress_bonus_is_discrete_and_stable_recovery_keeps_two(dt):
    from ame_baseline.m1_required_crossing import required_crossing_reward
    z = torch.zeros(2)
    _, _, bonus = required_crossing_reward(z, z[:, None], dt,
        blocked=torch.ones(2, dtype=torch.bool), collision=torch.zeros(2, dtype=torch.bool),
        done=torch.zeros(2, dtype=torch.bool), prelift=torch.ones(2, dtype=torch.bool),
        recovery=torch.tensor([False, True]), prelift_progress_delta=torch.tensor([.15, 0.]))
    assert bonus.tolist() == pytest.approx([.045, 2.])
