"""Read-only authored M1 mass/joint inventory; does not launch physics."""
import json
from pxr import Usd, UsdPhysics

stage = Usd.Stage.Open('/home/hexinkun/m1_rl/.worktrees/m1-contact-crossing/m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd')
bodies, joints = [], []
for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
    if prim.HasAPI(UsdPhysics.RigidBodyAPI):
        mass = UsdPhysics.MassAPI(prim)
        bodies.append(dict(name=prim.GetName(), path=str(prim.GetPath()),
                           mass=mass.GetMassAttr().Get(),
                           com=list(mass.GetCenterOfMassAttr().Get())))
    if prim.IsA(UsdPhysics.Joint):
        joint = UsdPhysics.Joint(prim)
        joints.append(dict(name=prim.GetName(), type=prim.GetTypeName(),
            parent=[str(p) for p in joint.GetBody0Rel().GetTargets()],
            child=[str(p) for p in joint.GetBody1Rel().GetTargets()],
            pos0=list(joint.GetLocalPos0Attr().Get()),
            pos1=list(joint.GetLocalPos1Attr().Get()),
            rot0=str(joint.GetLocalRot0Attr().Get()),
            rot1=str(joint.GetLocalRot1Attr().Get()),
            axis=prim.GetAttribute('physics:axis').Get()))
print(json.dumps(dict(bodies=bodies,joints=joints,
                     total_mass=sum(b['mass'] for b in bodies)), indent=2))
