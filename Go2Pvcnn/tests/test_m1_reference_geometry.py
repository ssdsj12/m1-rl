import importlib.util
import torch
import pytest


def module():
    assert importlib.util.find_spec('ame_baseline.m1_reference_geometry') is not None
    from ame_baseline import m1_reference_geometry
    return m1_reference_geometry


def test_cylinder_bottom_uses_measured_orientation_not_old_mesh():
    g=module(); p=torch.tensor([[[0.,0.,.2]]]); q=torch.tensor([[[1.,0.,0.,0.]]])
    torch.testing.assert_close(g.cylinder_bottom(p,q),torch.tensor([[.1041]]))
    q=torch.tensor([[[2**-.5,2**-.5,0.,0.]]])
    torch.testing.assert_close(g.cylinder_bottom(p,q),torch.tensor([[.2-.0465/2]]))
    with pytest.raises(ValueError): g.cylinder_bottom(p,torch.zeros_like(q))


def test_round_leading_edge_clearance_not_whole_bottom():
    g=module()
    # Box near x=-.05/top=.03. Circle overlaps in XY, but its curved tip is above top.
    p=torch.tensor([[[-.13,0.,.105],[0.,0.,.105],[0.,0.,.14]]])
    q=torch.tensor([[[1.,0.,0.,0.]]]).expand(1,3,4)
    result=g.cylinder_clears_box(p,q,torch.tensor([[0.,0.,.03]]),torch.tensor([[.05,.09]]))
    assert result.tolist()==[[True,False,True]]
    assert (g.cylinder_bottom(p,q)[0,:2]<.03).all()


def test_separation_certificate_invariant_to_translation_and_rejects_invalid_pose():
    g=module(); p=torch.tensor([[[-.13,0.,.105]]]);q=torch.tensor([[[1.,0.,0.,0.]]])
    box=torch.tensor([[0.,0.,.03]]); ext=torch.tensor([[.05,.09]])
    off=torch.tensor([5.,3.,.9])
    assert torch.equal(g.cylinder_clears_box(p,q,box,ext),g.cylinder_clears_box(p+off,q,box+off,ext))
    with pytest.raises(ValueError):g.cylinder_clears_box(p,q*float('nan'),box,ext)


def test_runtime_cylinder_measurement_is_wired():
    from pathlib import Path
    root=Path(__file__).parents[1]/'ame_baseline'
    assert 'cylinder_bottom(' in (root/'ame_env_wrapper.py').read_text()
    assert 'cylinder_geometry=True' in (root/'ame_env_wrapper.py').read_text()
    assert 'clearance_safe=' in (root/'m1_dynamic_crossing.py').read_text()


def test_empty_flat_registry_cylinder_query_has_no_phantom_geometry():
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    tracker=EncounterCrossingTracker(1,'cpu',obstacle_count=1)
    out=tracker.update(wheel_pos_w=torch.zeros(1,4,3),wheel_quat_w=torch.tensor([[[1.,0.,0.,0.]]]).expand(1,4,4),
        course=dict(centers_top=torch.zeros(1,1,3),half_extents=torch.zeros(1,1,2),
            valid=torch.zeros(1,1,dtype=torch.bool),ids=torch.full((1,1),-1)),
        direction_w=torch.tensor([[1.,0.]]),wheel_bottom_z_w=torch.zeros(1,4),
        wheel_grounded=torch.ones(1,4,dtype=torch.bool),support_safe=torch.tensor([True]),
        touchdown_safe=torch.tensor([True]),collision=torch.tensor([False]),
        wheel_horizontal_radius=.12,wheel_vertical_radius=.0959,wheel_thickness=.0465,
        cylinder_geometry=True,required_clearance=0.)
    assert not out['attempt_started'].item() and not out['event_complete'].item()


@pytest.mark.parametrize('case',['skip','side','real'])
def test_separation_alone_without_actual_xy_passage_never_recovers(case):
    from ame_baseline.m1_dynamic_crossing import EncounterCrossingTracker
    t=EncounterCrossingTracker(1,'cpu',obstacle_count=1)
    course=dict(centers_top=torch.tensor([[[0.,0.,.03]]]),half_extents=torch.tensor([[[.025,.09]]]),
        valid=torch.tensor([[True]]),ids=torch.tensor([[1]]))
    def step(x,air):
        height=(.14 if case=='real' else .0969) if air else .0959
        p=torch.tensor([[[x,.11325 if case=='side' else 0.,height],
                         [x,1.,.0959],[x,1.5,.0959],[x,2.,.0959]]])
        forces=torch.zeros(1,4,3);forces[:,:,2]=25.;forces[:,0,2]=0. if air else 25.
        return t.update(wheel_pos_w=p,wheel_quat_w=torch.tensor([[[1.,0.,0.,0.]]]).expand(1,4,4),
            course=course,direction_w=torch.tensor([[1.,0.]]),wheel_bottom_z_w=p[:,:,2]-.0959,
            wheel_grounded=torch.tensor([[not air,True,True,True]]),support_safe=torch.tensor([True]),
            touchdown_safe=torch.tensor([not air]),collision=torch.tensor([False]),
            wheel_horizontal_radius=.11915,wheel_vertical_radius=.0959,wheel_thickness=.0465,
            cylinder_geometry=True,required_clearance=0.,autonomous_lift=torch.tensor([True]),
            wheel_forces=forces,robot_weight=torch.tensor([100.]),attitude_safe=torch.tensor([True]))
    step(-.36,False)
    positions=torch.arange(-.354,.195,.006).tolist() if case!='skip' else [-.14]
    passage=0.
    for x in positions:passage+=step(x,True)['passage_delta'].item()
    assert step(.20,False)['event_complete'].item()==(case=='real')
    for _ in range(4):assert not step(.20,False)['recovery_complete'].item()
    assert step(.20,False)['recovery_complete'].item()==(case=='real')
    assert (passage>0)==(case=='real')
