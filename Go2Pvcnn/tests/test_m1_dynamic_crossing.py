import math
import torch
import pytest


def scene(theta=0.):
    e=torch.tensor([math.cos(theta),math.sin(theta)])
    v=torch.tensor([-e[1],e[0]])
    center=torch.tensor([2.,3.])
    course={'centers_top':torch.tensor([[[2.,3.,.10],[99.,99.,.1]]]),
        'half_extents':torch.full((1,2,2),.025), 'ground_z':torch.zeros(1,2),
        'valid':torch.tensor([[True,False]]),'ids':torch.tensor([[17,-1]])}
    def frame(x,z):
        pos=torch.zeros(1,4,3)
        for i,side in enumerate((0.,1.,1.5,2.)):
            pos[0,i,:2]=center+x*e+side*v
        pos[:,:,2]=.10
        pos[:,0,2]=z  # one target wheel moves; the other three keep supporting
        return pos
    return course,e[None],frame


def tick(tracker,course,direction,pos,*,touch=False,collision=False,grounded=None):
    theta=torch.atan2(direction[:,1],direction[:,0])
    q=torch.zeros(1,4,4);q[:,:,0]=torch.cos(theta/2)[:,None];q[:,:,3]=torch.sin(theta/2)[:,None]
    return tracker.update(wheel_pos_w=pos,wheel_quat_w=q,course=course,direction_w=direction,
        wheel_bottom_z_w=pos[:,:,2]-.10,support_safe=torch.tensor([True]),
        wheel_grounded=(pos[:,:,2]<=.101) if grounded is None else grounded,
        touchdown_safe=torch.tensor([touch]),collision=torch.tensor([collision]),
        wheel_horizontal_radius=.1,wheel_vertical_radius=.1,wheel_thickness=.04,
        required_clearance=.03,required_far_margin=.04,stable_frames=2)


@pytest.mark.parametrize('angle',[0.,math.pi/2,math.pi,-.7])
def test_direction_relative_early_lift_clearance_landing_counts_once(angle):
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2)
    c,d,f=scene(angle)
    assert tick(t,c,d,f(-.32,.10))['attempt_started'].item()
    assert t.target_obstacle_id.item()==17
    tick(t,c,d,f(-.22,.14))  # Actual2cm+ lift strictly before leading edge.
    tick(t,c,d,f(0.,.24))
    out=tick(t,c,d,f(.30,.10),touch=True)
    assert out['event_complete'].item()
    assert not out['episode_complete'].item()  # Random course is not finished by1event.
    for _ in range(4):
        assert not tick(t,c,d,f(.30,.10),touch=True)['event_complete'].item()
    # The same wheel/obstacle pair is not an additional attempt even if reversed.
    assert not tick(t,c,d,f(-.32,.10))['attempt_started'].item()


@pytest.mark.parametrize('failure',['late_lift','scrape','collision','early_touchdown'])
def test_invalid_crossings_never_count(failure):
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2);c,d,f=scene()
    tick(t,c,d,f(-.32,.10))
    if failure!='late_lift': tick(t,c,d,f(-.22,.14))
    tick(t,c,d,f(0.,.18 if failure=='scrape' else .24),touch=failure=='early_touchdown',collision=failure=='collision')
    out=tick(t,c,d,f(.30,.10),touch=failure!='early_touchdown')
    assert not out['event_complete'].item()


def test_empty_padding_and_no_command_do_not_start_attempts():
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2);c,d,f=scene()
    assert not tick(t,c,torch.zeros_like(d),f(-.32,.1))['attempt_started'].item()
    c['valid'][:]=False
    assert not tick(t,c,d,f(-.32,.1))['attempt_started'].item()


def test_reset_clears_identity_and_terrain_switch_cancels_active_event():
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2);c,d,f=scene()
    tick(t,c,d,f(-.32,.1)); assert t.target_obstacle_id.item()==17
    c['ids'][0,0]=25
    assert not tick(t,c,d,f(0.,.24))['event_complete'].item()
    assert t.target_obstacle_id.item()==-1
    t.reset(torch.tensor([True]))
    assert tick(t,c,d,f(-.32,.1))['attempt_started'].item()


def test_legacy_tracker_supports_per_env_projected_extents():
    from ame_baseline.m1_strict_crossing import StrictCrossingTracker
    t=StrictCrossingTracker(1,'cpu',obstacle_count=1)
    c,d,f=scene()
    out=t.update(wheel_pos_w=f(-.32,.1),obstacle_centers_top_w=c['centers_top'][:,:1],
        support_safe=torch.tensor([True]),touchdown_safe=torch.tensor([False]),collision=torch.tensor([False]),
        wheel_horizontal_radius=.1,wheel_vertical_radius=.1,wheel_lateral_half_width=.02,
        obstacle_half_extents=torch.tensor([[.025,.035]]))
    assert out['attempt_started'].item()


def test_failed_encounter_releases_after_exit_and_next_obstacle_counts_attempt():
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2);c,d,f=scene()
    c['valid'][0,1]=True;c['ids'][0,1]=18;c['centers_top'][0,1]=torch.tensor([3.,3.,.1])
    tick(t,c,d,f(-.32,.1));tick(t,c,d,f(0.,.1))
    tick(t,c,d,f(.68,.1))  # Leave failed obstacle, do not erase its attempt.
    out=tick(t,c,d,f(.68,.1))
    assert out['attempt_started'].item() and t.target_obstacle_id.item()==18


def test_grounded_uphill_motion_is_not_early_lift_and_airborne_uses_last_contact():
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2);c,d,f=scene()
    grounded=torch.ones(1,4,dtype=torch.bool)
    tick(t,c,d,f(-.32,.15),touch=True,grounded=grounded)
    assert not t.early_lift.item()
    tick(t,c,d,f(-.27,.18),touch=True,grounded=grounded)
    assert not t.early_lift.item()
    airborne=grounded.clone();airborne[:,0]=False
    tick(t,c,d,f(-.22,.19),grounded=airborne)
    assert not t.early_lift.item()  # Only 1 cm above last loaded support.
    tick(t,c,d,f(-.20,.21),grounded=airborne)
    assert t.early_lift.item()


@pytest.mark.parametrize('blocked_wheel',[0,1,2,3])
def test_large_obstacle_blocks_target_or_support_landing(blocked_wheel):
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2);c,d,f=scene()
    landing=f(.30,.10)
    c['landing_centers_top']=landing[:,blocked_wheel:blocked_wheel+1].clone()
    c['landing_half_extents']=torch.full((1,1,2),.225)
    c['landing_valid']=torch.ones(1,1,dtype=torch.bool)
    tick(t,c,d,f(-.32,.1));tick(t,c,d,f(-.22,.14));tick(t,c,d,f(0.,.24))
    assert not tick(t,c,d,landing,touch=True)['event_complete'].item()


def test_early_touchdown_then_rolling_past_cannot_reuse_prior_clearance():
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2);c,d,f=scene()
    tick(t,c,d,f(-.32,.1));tick(t,c,d,f(-.22,.14));tick(t,c,d,f(0.,.24))
    tick(t,c,d,f(.02,.10),touch=True)
    assert not tick(t,c,d,f(.30,.10),touch=True)['event_complete'].item()


def test_bypass_releases_encounter_without_claiming_crossing():
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=2);c,d,f=scene()
    tick(t,c,d,f(-.32,.1))
    retreat=f(-.60,.1)
    out=tick(t,c,d,retreat)
    assert not out['event_complete'].item()
    assert t.target_obstacle_id.item()==-1
