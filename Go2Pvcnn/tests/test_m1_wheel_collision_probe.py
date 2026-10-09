import math
import pytest


def test_diagnostic_prism_preserves_envelope_and_vertex_budget():
    from ame_baseline.m1_wheel_collision_probe import wheel_prism
    points,counts,indices=wheel_prism()
    assert len(points)==64
    assert len(counts)==34 and sum(counts)==len(indices)
    assert set(indices)==set(range(64))
    assert min(p[1] for p in points)==pytest.approx(-.01594940573)
    assert max(p[1] for p in points)==pytest.approx(.03054940514)
    assert all(math.hypot(p[0],p[2])==pytest.approx(.095963) for p in points)


def test_shoulder_profile_keeps_three_rings_and_bounded_hull():
    from ame_baseline.m1_wheel_collision_probe import wheel_prism
    points,counts,indices=wheel_prism('shoulder')
    assert len(points)==60 and len(counts)==42
    assert sum(counts)==len(indices)
    assert sorted(set(p[1] for p in points))==pytest.approx([-.01594940573,.0073,.03054940514])
    assert all(math.hypot(p[0],p[2])==pytest.approx(.095963 if p[1]==.0073 else .084966) for p in points)


def test_diagnostic_profiles_require_complete_lift_cycle_or_standing():
    from ame_baseline.m1_wheel_collision_probe import allowed_cycle
    assert allowed_cycle('cylinder',True,0,0)
    assert allowed_cycle('shoulder',False,90,90)
    assert allowed_cycle('cylinder',False,90,90)
    assert not allowed_cycle('cylinder',False,90,0)
    assert not allowed_cycle('cylinder',False,0,90)
    assert not allowed_cycle('shoulder',False,90,0)
    assert not allowed_cycle('shoulder',False,0,90)


def test_split_shoulder_refines_tread_without_changing_axial_profile():
    from ame_baseline.m1_wheel_collision_probe import wheel_parts, allowed_cycle
    parts=wheel_parts('shoulder_split')
    assert len(parts)==2
    for points,counts,indices in parts:
        assert len(points)==64 and len(counts)==34 and max(counts)==32
        assert sum(counts)==len(indices)
        assert set(indices)==set(range(64))
        assert all(math.hypot(p[0],p[2])==pytest.approx(.095963 if p[1]==.0073 else .084966) for p in points)
    assert parts[0][0][32:]==parts[1][0][:32]
    assert min(p[1] for p in parts[0][0])==pytest.approx(-.01594940573)
    assert max(p[1] for p in parts[1][0])==pytest.approx(.03054940514)
    assert allowed_cycle('shoulder_split',False,90,90)
    assert not allowed_cycle('shoulder_split',False,90,0)


def test_controlled_physics_removes_shape_count_randomization_confounds():
    from types import SimpleNamespace as NS
    from ame_baseline.m1_wheel_collision_probe import fix_diagnostic_physics
    cfg=NS(events=NS(add_base_mass=object(),physics_material=NS(params={'num_buckets':64}),
                    reset_robot_joints=NS(params={})))
    fix_diagnostic_physics(cfg)
    assert cfg.events.add_base_mass is None
    assert cfg.events.physics_material.params['static_friction_range']==(.8,.8)
    assert cfg.events.physics_material.params['dynamic_friction_range']==(.8,.8)
    assert cfg.events.physics_material.params['restitution_range']==(0.,0.)
    assert cfg.events.reset_robot_joints.params['position_range']==(1.,1.)
