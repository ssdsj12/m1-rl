"""Shared M1 teacher defaults for production and physics verification.

Explicit environment overrides win. This does not certify physical crossing.
The legacy placeholder wrapper exports matching values for compatibility.
"""
import os

M1_RUNTIME_DEFAULTS = {
    "M1_TEACHER_FOOT_TRAJECTORY": "1",
    "M1_TEACHER_SERIAL_FORCE": "1",
    # Legacy timed fallback must allow the 0.10-rad Cartesian rate bound
    # to complete descent. Real obstacle events remain measurement-held.
    "M1_TEACHER_PHASE_BLOCK": "128",
    "M1_TEACHER_LEG_SEQUENCE": "0,3,2,1",
    "M1_TEACHER_STRICT_SEQUENCE": "1",
    "M1_TEACHER_USE_ACTUAL_CONTACT": "0",
    "M1_TEACHER_COLLISION_LOOKAHEAD_M": "0.0",
    "M1_TEACHER_COLLISION_LOOKAHEAD_X_M": "0.0",
    "M1_TEACHER_USE_PLANNER_FOOT_TARGET": "1",
    "M1_TEACHER_USE_PLANNER_CONTACT": "0",
    "M1_TEACHER_SLEW_RAD": "0.10",
    "M1_TEACHER_FOOT_LIFT_M": "0.20",
    "M1_TEACHER_FOOT_LIFT_SCALE": "1.20,1.30,1.05,1.05",
    "M1_TEACHER_FOOT_ADVANCE_M": "0.22",
    "M1_TEACHER_FOOT_BACKSTEP_M": "0.12",
    "M1_TEACHER_DRIVE_WHEELS": "1",
    "M1_TEACHER_REPROJECT_STANCE": "0",
    "M1_TEACHER_UPRIGHT_SUPPORT": "0",
    "M1_TEACHER_UPRIGHT_SUPPORT_BLEND": "0.15",
    "M1_TEACHER_UPRIGHT_SUPPORT_MAX_SHIFT_M": "0.012",
    "M1_TEACHER_IK_FALLBACK": "1",
    "M1_TEACHER_USE_MEASURED_HOLD": "1",
    "M1_TEACHER_USE_PLANNER_TOUCHDOWN": "1",
    "M1_TEACHER_IGNORE_PLANNER_VALID": "1",
    "M1_TEACHER_INVALID_HOLD_CURRENT": "1",
    "M1_TEACHER_RECOVERY_HOLD": "0",
    "M1_TEACHER_RECOVERY_TILT_RAD": "0.45",
    "M1_TEACHER_HOLD_FOOT_USE_CURRENT": "1",
    "M1_TEACHER_WHEEL_SWING_SCALE": "0.15",
    "M1_TEACHER_SUPPORT_WHEEL_SWING_SCALE": "0.50",
    "M1_TEACHER_CROSSING_MAX_TILT_RAD": "0.45",
    "M1_TEACHER_INITIAL_FALLBACK": "0",
    "M1_TEACHER_PRELIFT": "1",
    "M1_TEACHER_HOLD_CONTACT_BLEND": "0.20",
    "M1_TEACHER_MAX_HIP_LIFT_RAD": "0.40",
    "M1_TEACHER_MAX_ABAD_RAD": "0.10",
    "M1_TEACHER_MAX_KNEE_LIFT_RAD": "2.20",
    "M1_TEACHER_SUPPORT_KNEE_COMP_RAD": "0.0",
    "M1_TEACHER_STANCE_KNEE_RAISE_RAD": "0.0",
    "M1_TEACHER_MAX_STEPS": "2048",
    "M1_TEACHER_CLEAR_STEPS": "512"
}


def apply_m1_runtime_defaults():
    for name, value in M1_RUNTIME_DEFAULTS.items():
        os.environ.setdefault(name, value)
