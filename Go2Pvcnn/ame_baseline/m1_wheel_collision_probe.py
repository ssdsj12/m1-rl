"""Opt-in collision-envelope experiment, NOT a production tire model."""
import math


def fix_diagnostic_physics(cfg):
    """Opt-in controlled comparison, never applied to production training."""
    cfg.events.add_base_mass=None
    cfg.events.physics_material.params.update(static_friction_range=(.8,.8),
        dynamic_friction_range=(.8,.8),restitution_range=(0.,0.))
    cfg.events.reset_robot_joints.params.update(position_range=(1.,1.),velocity_range=(0.,0.))


def allowed_cycle(profile,standing,lift,land):
    return profile in ('cylinder','shoulder','shoulder_split') and (standing or (lift>0 and land>0))


def wheel_prism(profile='cylinder'):
    if profile not in ('cylinder','shoulder'):
        raise ValueError('unknown diagnostic profile')
    n=32 if profile=='cylinder' else 20
    rings=[(-.01594940573,.095963),(.03054940514,.095963)] if profile=='cylinder' else [(-.01594940573,.084966),(.0073,.095963),(.03054940514,.084966)]
    points=[(r*math.cos(2*math.pi*i/n),y,r*math.sin(2*math.pi*i/n))
            for y,r in rings for i in range(n)]
    faces=[[j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i] for j in range(len(rings)-1) for i in range(n)]
    faces += [list(reversed(range(n))),list(range((len(rings)-1)*n,len(rings)*n))]
    return points,[len(f) for f in faces],[i for f in faces for i in f]


def wheel_parts(profile='cylinder'):
    if profile!='shoulder_split':
        return [wheel_prism(profile)]
    rings=[(-.01594940573,.084966),(.0073,.095963),(.03054940514,.084966)]
    parts=[]
    for side in range(2):
        points=[(r*math.cos(2*math.pi*i/32),y,r*math.sin(2*math.pi*i/32))
                for y,r in rings[side:side+2] for i in range(32)]
        faces=[[i,(i+1)%32,32+(i+1)%32,32+i] for i in range(32)]
        faces += [list(reversed(range(32))),list(range(32,64))]
        parts.append((points,[len(f) for f in faces],[i for f in faces for i in f]))
    return parts


def spawn_diagnostic_wheels(prim_path,cfg,translation=None,orientation=None,profile='cylinder'):
    from .m1_ame_assets import spawn_m1_floating_usd
    import isaaclab.sim as sim_utils
    from pxr import UsdGeom,UsdPhysics,Gf
    from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES
    prim=spawn_m1_floating_usd(prim_path,cfg,translation,orientation)
    parts=wheel_parts(profile)
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
            if not mesh or not mesh.GetPrim().HasAPI(UsdPhysics.CollisionAPI):
                raise RuntimeError('diagnostic wheel collision mesh missing')
            meshes=[mesh]
            if len(parts)==2:
                extra=stage.DefinePrim(str(mesh.GetPath())+'_shoulder','Mesh')
                extra.GetReferences().AddInternalReference(mesh.GetPath())
                meshes.append(UsdGeom.Mesh(extra))
            for mesh,(points,counts,indices) in zip(meshes,parts):
                mesh.GetPointsAttr().Set([Gf.Vec3f(*p) for p in points])
                mesh.GetFaceVertexCountsAttr().Set(counts)
                mesh.GetFaceVertexIndicesAttr().Set(indices)
                mesh.GetNormalsAttr().Clear()
                mesh.GetSubdivisionSchemeAttr().Set('none')
                mesh.GetExtentAttr().Set([Gf.Vec3f(*[min(p[i] for p in points) for i in range(3)]),Gf.Vec3f(*[max(p[i] for p in points) for i in range(3)])])
                changed+=1
    print('M1_DIAGNOSTIC_WHEEL_MESHES '+str(changed),flush=True)
    return prim
