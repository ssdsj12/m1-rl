from __future__ import annotations

from pathlib import Path
import ast

import pytest
import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES,
    M1_PLANNER_JOINT_NAMES,
    M1_WHEEL_JOINT_NAMES,
)
from extension.parallelism.rl_adapter import select_named_joint_state


def test_m1_ame_config_wires_nonfinite_robot_state_termination():
    source = (
        Path(__file__).resolve().parents[1] / "ame_baseline" / "m1_ame_env_cfg.py"
    ).read_text(encoding="utf-8")

    assert "class M1AmeTerminationsCfg" in source
    assert "nonfinite_robot_state = DoneTerm(" in source
    assert "func=nonfinite_robot_state" in source
    assert "terminations: M1AmeTerminationsCfg = M1AmeTerminationsCfg()" in source


def test_m1_policy_joint_terms_exclude_wheels():
    asset = torch.arange(16, dtype=torch.float32).reshape(1, 16)
    selected = select_named_joint_state(asset, source_names=M1_ASSET_JOINT_NAMES, selected_names=M1_PLANNER_JOINT_NAMES)
    assert tuple(selected.shape) == (1, 12)
    assert not set((3, 7, 11, 15)) & set(selected.flatten().tolist())


def test_m1_reward_config_enables_m1_collision_and_wheel_rolling():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline/m1_ame_env_cfg.py").read_text()
    assert "class M1AmeRewardsCfg" in source
    assert "func=m1_rewards.m1_wheel_rolling_residual_l2" in source
    assert "func=m1_obstacle_rewards.m1_obstacle_collision_penalty" in source
    assert "self.rewards.parallelism_geometry_collision = None" not in source
    assert "rewards: M1AmeRewardsCfg = M1AmeRewardsCfg()" in source


def test_m1_reward_config_replaces_airtime_with_named_progress_and_climb():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline/m1_ame_env_cfg.py").read_text()
    tree = ast.parse(source)
    reward_class = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                        and node.name == "M1AmeRewardsCfg")
    fields = {target.id: node.value for node in reward_class.body if isinstance(node, ast.Assign)
              for target in node.targets if isinstance(target, ast.Name)}
    for name in ('feet_air_time', 'air_time_variance'):
        assert isinstance(fields[name], ast.Constant) and fields[name].value is None
    for name, function, weight in (
        ('small_obstacle_progress', 'm1_obstacle_rewards.m1_small_obstacle_progress', 1.),
                ('small_obstacle_climb', 'm1_obstacle_rewards.m1_small_obstacle_climb', 1.5),
            ('parallelism_geometry_collision', 'm1_obstacle_rewards.m1_obstacle_collision_penalty', -10.),
    ):
        kwargs = {item.arg: item.value for item in fields[name].keywords}
        assert ast.unparse(kwargs['func']) == function
        assert ast.literal_eval(kwargs['weight']) == weight


def test_physical_reward_probe_can_align_command_without_changing_training():
    source = (Path(__file__).resolve().parents[1] / "scripts/probe_m1_rewards.py").read_text()
    assert 'if "PROBE_COMMAND_X" in os.environ:' in source
    assert 'cfg.commands.base_velocity.ranges.lin_vel_x = (probe_command_x, probe_command_x)' in source
    assert 'cfg.commands.base_velocity.rel_standing_envs = 0.' in source


def test_m1_training_disables_usd_fixed_world_joint():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline/m1_ame_env_cfg.py").read_text()
    assert "self.scene.robot.spawn.articulation_props.fix_root_link = False" in source


def test_m1_ame_uses_fixed_course_without_terrain_level_curriculum():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline/m1_ame_env_cfg.py").read_text()
    assert "self.curriculum.terrain_levels = None" in source
    assert "class M1AmeCrossLargeComplexEnvCfg" in source


def test_m1_curriculum_contact_probe_accepts_named_uppercase_links():
    source = (
        Path(__file__).resolve().parents[1]
        / "extension/mdp/semantic_body_part_clearance.py"
    ).read_text()
    assert '".*_FOOT_LINK"' in source
    assert '".*_KNEE_LINK"' in source
    assert '".*_HIP_LINK"' in source


def test_m1_ame_adds_failure_penalty_and_success_gated_velocity_curriculum():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline/m1_ame_env_cfg.py").read_text()
    assert "m1_failure_termination_penalty" in source
    assert "weight=-20.0" in source
    assert "require_success" in source


def test_m1_ame_increases_upright_penalty_for_recovery_signal():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline/m1_ame_env_cfg.py").read_text()
    assert "flat_orientation_l2" in source
    assert "weight=-4.0" in source


def test_m1_observation_contract_declares_asset_and_planner_widths():
    pytest.importorskip("isaaclab")
    pytest.importorskip("omni.kit.app", reason="Isaac Sim application modules are unavailable in plain pytest")
    from ame_baseline.m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
    from ame_baseline.m1_ame_terminations import nonfinite_robot_state
    cfg = M1AmeCrossLargeComplexEnvCfg()
    assert cfg.robot_name == "m1"
    assert tuple(cfg.planner_joint_names) == M1_PLANNER_JOINT_NAMES
    assert tuple(cfg.wheel_joint_names) == M1_WHEEL_JOINT_NAMES
    assert cfg.action_dim == 16
    assert cfg.asset_joint_names == M1_ASSET_JOINT_NAMES
    assert cfg.terminations.nonfinite_robot_state.func is nonfinite_robot_state


def test_m1_teacher_uses_visible_but_stable_swing_height():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "ame_baseline" / "m1_ame_env_cfg.py").read_text()
    assert "nominal_swing_height_m = 0.30" in source


def test_m1_scanner_and_mpc_trigger_have_pre_lift_horizon():
    root = Path(__file__).resolve().parents[1]
    scanner_source = (root / "go2_pvcnn/tasks/teacher_elevation_trajectory_mpc_semantic_env_cfg.py").read_text()
    assert "pattern_cfg=patterns.GridPatternCfg(resolution=0.01, size=[1.5, 1.5])" in scanner_source
    cfg_source = (root / "ame_baseline/m1_ame_env_cfg.py").read_text()
    assert "losses.low_small_crossing.forward_distance_m = 1.8" in cfg_source
    assert "losses.obstacle_risk.linear_forward_distance_m = 1.8" in cfg_source
    reward_source = (root / "ame_baseline/m1_obstacle_rewards.py").read_text()
    # The pre-lift probe now reaches 1.6 m (31 samples) so the teacher can
    # see the first fixed block before its 1.15 m leading edge.
    assert "round(0.10 + 0.05 * i, 2) for i in range(31)" in reward_source
    assert "for y in (-.15, 0., .15)" in reward_source


def test_m1_teacher_latch_spans_a_complete_single_leg_crossing():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline" / "ame_env_wrapper.py").read_text()
    assert "M1_TEACHER_MAX_STEPS" in source
    assert "max(\n            256," in source
    assert "int(os.environ.get(\"M1_TEACHER_MAX_STEPS\", \"2048\"))" in source


def test_m1_small_crossing_has_center_corridor_reward_and_large_escape():
    root = Path(__file__).resolve().parents[1]
    cfg_source = (root / "ame_baseline" / "m1_ame_env_cfg.py").read_text()
    reward_source = (root / "ame_baseline" / "m1_obstacle_rewards.py").read_text()
    assert "small_obstacle_corridor" in cfg_source
    assert "m1_small_obstacle_corridor_penalty" in cfg_source
    assert "small & ~large" in reward_source
    assert "0.22" in reward_source


def test_m1_disables_inherited_terrain_level_curriculum_for_fixed_course():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline" / "m1_ame_env_cfg.py").read_text()
    assert "self.curriculum.terrain_levels = None" in source


def test_m1_amp_training_uses_conservative_fixed_learning_rate():
    from ame_baseline.m1_ame_train_cfg import get_m1_ame_amp_train_cfg
    cfg = get_m1_ame_amp_train_cfg()
    assert cfg["algorithm"]["learning_rate"] == 2.0e-5
    assert cfg["algorithm"]["schedule"] == "fixed"
