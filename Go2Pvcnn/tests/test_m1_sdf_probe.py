import pytest
from pxr import Usd, UsdGeom, UsdPhysics, PhysxSchema


def test_explicit_pair_cleanup_changes_only_canceling_faces():
    from ame_baseline.m1_sdf_probe import configure_mesh
    stage=Usd.Stage.CreateInMemory();mesh=UsdGeom.Mesh.Define(stage,'/wheel')
    mesh.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,0),(0,0,1),(.1,.1,.1),(.2,.1,.1),(.1,.2,.1)])
    mesh.CreateFaceVertexCountsAttr([3]*6)
    mesh.CreateFaceVertexIndicesAttr([0,2,1,0,1,3,0,3,2,1,2,3,4,5,6,6,5,4])
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim());points=list(mesh.GetPointsAttr().Get())
    configure_mesh(mesh,clean_pairs=True)
    assert list(mesh.GetPointsAttr().Get())==points
    assert list(mesh.GetFaceVertexIndicesAttr().Get())==[0,2,1,0,1,3,0,3,2,1,2,3]


def test_sdf_requires_controlled_standing_or_complete_cycle():
    from ame_baseline.m1_sdf_probe import allowed_sdf_cycle
    assert allowed_sdf_cycle(True,0,0,True,False)
    assert allowed_sdf_cycle(False,90,90,True,False)
    assert not allowed_sdf_cycle(False,90,0,True,False)
    assert not allowed_sdf_cycle(False,0,90,True,False)
    assert not allowed_sdf_cycle(False,90,90,False,False)
    assert not allowed_sdf_cycle(False,90,90,True,True)


@pytest.mark.parametrize('resolution',[128,256])
def test_sdf_preserves_mesh_and_disables_implicit_geometry_repair(resolution):
    from ame_baseline.m1_sdf_probe import configure_mesh
    stage=Usd.Stage.CreateInMemory()
    mesh=UsdGeom.Mesh.Define(stage,'/wheel')
    mesh.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,0),(0,0,1)])
    mesh.CreateFaceVertexCountsAttr([3]*4)
    mesh.CreateFaceVertexIndicesAttr([0,2,1,0,1,3,0,3,2,1,2,3])
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    before=(list(mesh.GetPointsAttr().Get()),list(mesh.GetFaceVertexIndicesAttr().Get()))
    configure_mesh(mesh,resolution=resolution)
    assert before==(list(mesh.GetPointsAttr().Get()),list(mesh.GetFaceVertexIndicesAttr().Get()))
    assert UsdPhysics.MeshCollisionAPI(mesh.GetPrim()).GetApproximationAttr().Get()=='sdf'
    api=PhysxSchema.PhysxSDFMeshCollisionAPI(mesh.GetPrim())
    assert api.GetSdfResolutionAttr().Get()==resolution
    assert api.GetSdfSubgridResolutionAttr().Get()==6
    assert not api.GetSdfEnableRemeshingAttr().Get()
    assert api.GetSdfTriangleCountReductionFactorAttr().Get()==1


def test_noncollider_is_rejected():
    from ame_baseline.m1_sdf_probe import configure_mesh
    stage=Usd.Stage.CreateInMemory()
    mesh=UsdGeom.Mesh.Define(stage,'/visual')
    with pytest.raises(ValueError,match='collision'):
        configure_mesh(mesh)


def test_optional_sdf_rest_margin_is_conservative_and_preserves_contact_offset():
    from ame_baseline.m1_sdf_probe import configure_mesh
    stage=Usd.Stage.CreateInMemory()
    mesh=UsdGeom.Mesh.Define(stage,'/wheel')
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    collision=PhysxSchema.PhysxCollisionAPI.Apply(mesh.GetPrim())
    collision.CreateContactOffsetAttr().Set(.02)
    collision.CreateRestOffsetAttr().Set(0.)
    configure_mesh(mesh,rest_offset=.001)
    assert collision.GetRestOffsetAttr().Get()==pytest.approx(.001)
    assert collision.GetContactOffsetAttr().Get()==pytest.approx(.02)


def test_auto_contact_offset_is_explicitly_above_requested_rest_margin():
    from ame_baseline.m1_sdf_probe import configure_mesh
    stage=Usd.Stage.CreateInMemory()
    mesh=UsdGeom.Mesh.Define(stage,'/wheel')
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    configure_mesh(mesh,rest_offset=.001)
    collision=PhysxSchema.PhysxCollisionAPI(mesh.GetPrim())
    assert collision.GetContactOffsetAttr().Get()==pytest.approx(.002)
