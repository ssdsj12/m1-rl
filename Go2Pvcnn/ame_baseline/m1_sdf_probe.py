"""Default-off original-mesh SDF experiment; never mutates source USD."""


def allowed_sdf_cycle(standing,lift,land,fixed_physics,prism):
    return fixed_physics and not prism and (standing or (lift>0 and land>0))


def configure_mesh(mesh,resolution=128,rest_offset=0.,clean_pairs=False):
    from pxr import UsdPhysics, PhysxSchema
    if not mesh or not mesh.GetPrim().HasAPI(UsdPhysics.CollisionAPI):
        raise ValueError('SDF experiment requires collision mesh')
    if clean_pairs:
        import numpy as np
        from .m1_mesh_pairs import clean_opposite_pairs
        if not np.all(np.asarray(mesh.GetFaceVertexCountsAttr().Get())==3):
            raise ValueError('pair cleanup requires triangles')
        indices=clean_opposite_pairs(np.asarray(mesh.GetPointsAttr().Get()),
            np.asarray(mesh.GetFaceVertexIndicesAttr().Get()))
        mesh.GetFaceVertexIndicesAttr().Set(indices.tolist())
        mesh.GetFaceVertexCountsAttr().Set([3]*(len(indices)//3))
        mesh.GetNormalsAttr().Clear()
    api=PhysxSchema.PhysxSDFMeshCollisionAPI.Apply(mesh.GetPrim())
    api.CreateSdfResolutionAttr().Set(resolution)
    api.CreateSdfSubgridResolutionAttr().Set(6)
    api.CreateSdfEnableRemeshingAttr().Set(False)
    api.CreateSdfTriangleCountReductionFactorAttr().Set(1.)
    if rest_offset:
        collision=PhysxSchema.PhysxCollisionAPI.Apply(mesh.GetPrim())
        if collision.GetContactOffsetAttr().Get()<=rest_offset:
            collision.CreateContactOffsetAttr().Set(2*rest_offset)
        collision.CreateRestOffsetAttr().Set(rest_offset)
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim()).CreateApproximationAttr().Set('sdf')


def spawn_source_sdf(prim_path,cfg,translation=None,orientation=None,resolution=128,rest_offset=0.,clean_pairs=False):
    from .m1_ame_assets import spawn_m1_floating_usd
    import isaaclab.sim as sim_utils
    from pxr import UsdGeom
    from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES
    import hashlib
    import json
    import numpy as np
    prim=spawn_m1_floating_usd(prim_path,cfg,translation,orientation)
    changed=0
    for robot in sim_utils.find_matching_prims(prim_path):
        stage=robot.GetStage()
        for joint in M1_WHEEL_JOINT_NAMES:
            body=joint.replace('_JOINT','_LINK')
            path=str(robot.GetPath())+'/'+body+'/collisions'
            for suffix in ('','/'+body):
                parent=stage.GetPrimAtPath(path+suffix)
                if parent.IsInstance(): parent.SetInstanceable(False)
            mesh=UsdGeom.Mesh(stage.GetPrimAtPath(path+'/'+body+'/mesh'))
            points=np.asarray(mesh.GetPointsAttr().Get()).copy()
            indices=np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).copy()
            expected=indices
            if clean_pairs:
                from .m1_mesh_pairs import clean_opposite_pairs
                expected=clean_opposite_pairs(points,indices)
            configure_mesh(mesh,resolution=resolution,rest_offset=rest_offset,clean_pairs=clean_pairs)
            if not (np.array_equal(points,np.asarray(mesh.GetPointsAttr().Get())) and
                    np.array_equal(expected,np.asarray(mesh.GetFaceVertexIndicesAttr().Get()))):
                raise RuntimeError('SDF diagnostic changed original mesh')
            print('M1_SDF_SOURCE '+json.dumps(dict(path=str(mesh.GetPath()),
                points=len(points),indices=len(indices),resolution=resolution,remeshing=False,rest_offset=rest_offset,
                clean_pairs=clean_pairs,removed_faces=(len(indices)-len(expected))//3,
                sha256=hashlib.sha256(points.tobytes()+indices.tobytes()).hexdigest())),flush=True)
            changed+=1
    if not changed or changed%4:
        raise RuntimeError('SDF diagnostic did not configure complete wheel sets')
    return prim
