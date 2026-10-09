"""Training-only floating-root conversion for the fixed-root M1 USD."""
from __future__ import annotations


def apply_m1_leg_joint_limits(robot_prim):
    """Intersect source USD limits with the shared M1 controller limits.

    Only the spawned instance is edited. Do not reinterpret the advertised
    180 Nm maximum as a rating for every motor or alter authored inertias.
    """
    from math import degrees
    from pxr import Usd, UsdPhysics
    from extension.parallelism.m1_kinematics import (
        M1_PLANNER_JOINT_NAMES, M1_ABAD_LOWER, M1_ABAD_UPPER,
        M1_HIP_LOWER, M1_HIP_UPPER, M1_KNEE_LOWER, M1_KNEE_UPPER,
    )
    lower = [v for triple in zip(M1_ABAD_LOWER, M1_HIP_LOWER, M1_KNEE_LOWER) for v in triple]
    upper = [v for triple in zip(M1_ABAD_UPPER, M1_HIP_UPPER, M1_KNEE_UPPER) for v in triple]
    bounds = dict(zip(M1_PLANNER_JOINT_NAMES, zip(lower, upper)))
    for prim in Usd.PrimRange(robot_prim):
        if prim.GetName() not in bounds:
            continue
        joint = UsdPhysics.RevoluteJoint(prim)
        lo, hi = bounds[prim.GetName()]
        joint.GetLowerLimitAttr().Set(max(joint.GetLowerLimitAttr().Get(), degrees(lo)))
        joint.GetUpperLimitAttr().Set(min(joint.GetUpperLimitAttr().Get(), degrees(hi)))


def spawn_m1_floating_usd(prim_path, cfg, translation=None, orientation=None):
    import isaaclab.sim as sim_utils
    from pxr import Usd, UsdPhysics, PhysxSchema
    from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES

    prim = sim_utils.spawn_from_usd(prim_path, cfg, translation=translation, orientation=orientation)
    # spawn_from_usd can expand a regex; move the root schema in every actual
    # spawned robot before PhysX creates articulation handles.
    for robot_prim in sim_utils.find_matching_prims(prim_path):
        apply_m1_leg_joint_limits(robot_prim)
        stage = robot_prim.GetStage()
        base = stage.GetPrimAtPath(str(robot_prim.GetPath()) + "/BASE_LINK")
        if not base or not base.HasAPI(UsdPhysics.RigidBodyAPI):
            raise RuntimeError("M1 USD is missing the BASE_LINK rigid body")
        old_roots = [p for p in Usd.PrimRange(robot_prim) if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
        for old in old_roots:
            if old == base:
                continue
            UsdPhysics.ArticulationRootAPI.Apply(base)
            PhysxSchema.PhysxArticulationAPI.Apply(base)
            for name in PhysxSchema.PhysxArticulationAPI.GetSchemaAttributeNames():
                attribute = old.GetAttribute(name)
                if attribute and attribute.Get() is not None:
                    base.GetAttribute(name).Set(attribute.Get())
            old.RemoveAPI(UsdPhysics.ArticulationRootAPI)
            old.RemoveAPI(PhysxSchema.PhysxArticulationAPI)
        root_joint = stage.GetPrimAtPath(str(robot_prim.GetPath()) + "/root_joint")
        if root_joint:
            UsdPhysics.FixedJoint(root_joint).GetJointEnabledAttr().Set(False)
        for joint_prim in Usd.PrimRange(robot_prim):
            if joint_prim.GetName() in M1_WHEEL_JOINT_NAMES:
                joint = UsdPhysics.RevoluteJoint(joint_prim)
                joint.GetLowerLimitAttr().Set(float("-inf"))
                joint.GetUpperLimitAttr().Set(float("inf"))
    return prim
