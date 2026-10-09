"""Published M1 bounds are ceilings, not new per-joint motor ratings."""
import math

import pytest

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES,
    M1_ABAD_LOWER, M1_ABAD_UPPER, M1_HIP_LOWER, M1_HIP_UPPER,
    M1_KNEE_LOWER, M1_KNEE_UPPER,
)


def test_m1_has_twelve_leg_and_four_independent_wheel_motors():
    assert len(M1_ASSET_JOINT_NAMES) == 16
    assert len(M1_PLANNER_JOINT_NAMES) == 12
    assert len(M1_WHEEL_JOINT_NAMES) == 4
    assert set(M1_PLANNER_JOINT_NAMES).isdisjoint(M1_WHEEL_JOINT_NAMES)


def test_planner_bounds_do_not_exceed_official_joint_ranges():
    for i in range(4):
        # Right abduction axes are mirrored in the supplied USD.
        lo, hi = (-30, 40) if i in (0, 2) else (-40, 30)
        assert M1_ABAD_LOWER[i] >= math.radians(lo)
        assert M1_ABAD_UPPER[i] <= math.radians(hi)
        assert M1_HIP_LOWER[i] >= math.radians(-140)
        assert M1_HIP_UPPER[i] <= math.radians(140)
        assert M1_KNEE_LOWER[i] >= math.radians(-160)
        assert M1_KNEE_UPPER[i] <= math.radians(160)


def test_usd_guard_intersects_bounds_without_changing_drives_or_mass():
    pytest.importorskip('pxr.Usd')
    from pxr import Usd, UsdPhysics
    from ame_baseline.m1_ame_assets import apply_m1_leg_joint_limits
    stage = Usd.Stage.CreateInMemory()
    robot = stage.DefinePrim('/Robot', 'Xform')
    for name in M1_PLANNER_JOINT_NAMES:
        joint = UsdPhysics.RevoluteJoint.Define(stage, '/Robot/' + name)
        joint.CreateLowerLimitAttr(-160.48547)
        joint.CreateUpperLimitAttr(160.48547)
        drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), 'angular')
        drive.CreateMaxForceAttr(150.0)
    # An existing tighter restriction must not be expanded.
    tighter = UsdPhysics.RevoluteJoint(stage.GetPrimAtPath('/Robot/FBL_KNEE_JOINT'))
    tighter.GetUpperLimitAttr().Set(150.0)
    apply_m1_leg_joint_limits(robot)
    for name in M1_PLANNER_JOINT_NAMES:
        prim = stage.GetPrimAtPath('/Robot/' + name)
        joint = UsdPhysics.RevoluteJoint(prim)
        if 'KNEE' in name:
            assert joint.GetLowerLimitAttr().Get() == pytest.approx(-160.0)
            expected = 150.0 if name == 'FBL_KNEE_JOINT' else 160.0
            assert joint.GetUpperLimitAttr().Get() == pytest.approx(expected)
        assert UsdPhysics.DriveAPI(prim, 'angular').GetMaxForceAttr().Get() == 150.0
