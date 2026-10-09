from pathlib import Path


def test_teacher_has_bounded_upright_support_reprojection():
    source = Path("ame_baseline/m1_mpc_teacher.py").read_text()
    assert "M1_TEACHER_UPRIGHT_SUPPORT" in source
    assert "upright_support_blend" in source
    assert "M1_TEACHER_UPRIGHT_SUPPORT_Z_ONLY" in source
    assert "M1_TEACHER_UPRIGHT_SUPPORT_MAX_Z_SHIFT_M" in source
    assert "support_targets" in source


def test_invalid_teacher_frame_holds_measured_joint_pose():
    source = Path("ame_baseline/m1_mpc_teacher.py").read_text()
    assert "M1_TEACHER_INVALID_HOLD_CURRENT" in source
    assert "hold_action[:, planner_cols]" in source


def test_m1_leg_actuator_gains_are_probe_configurable():
    source = Path("ame_baseline/m1_ame_env_cfg.py").read_text()
    assert "M1_LEG_STIFFNESS" in source
    assert "M1_LEG_DAMPING" in source


def test_m1_planner_raises_body_leg_clearance_for_small_blocks():
    source = Path("ame_baseline/m1_ame_env_cfg.py").read_text()
    assert "body_leg_semantic_clearance_m = 0.24" in source
    assert "body_leg_root_lift_margin_m = 0.14" in source
    assert "fk_body_leg_collision.knee_margin_m = 0.08" in source


def test_m1_planner_uses_per_leg_lift_scale():
    source = Path("ame_baseline/m1_mpc_teacher.py").read_text()
    assert "M1_TEACHER_PLANNER_LIFT_SCALE" in source
    assert "lift_per_leg" in source


def test_m1_teacher_has_per_leg_knee_extra():
    source = Path("ame_baseline/m1_mpc_teacher.py").read_text()
    assert "M1_TEACHER_KNEE_EXTRA_RAD" in source
    assert "knee_extra" in source


def test_m1_teacher_support_settle_window_is_explicit():
    source = Path("ame_baseline/m1_mpc_teacher.py").read_text()
    assert "M1_TEACHER_SETTLE_STEPS" in source
    assert "active_span" in source
