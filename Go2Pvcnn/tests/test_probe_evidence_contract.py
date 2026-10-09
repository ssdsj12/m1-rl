"""Inspect report expressions without booting Isaac or allocating a GPU."""
import ast
from pathlib import Path


SOURCE = Path(__file__).with_name('probe_m1_teacher_physx.py')
if not SOURCE.exists():
    SOURCE = Path(__file__).resolve().parents[1] / 'scripts/probe_m1_teacher_physx.py'


def field(name):
    for node in ast.walk(ast.parse(SOURCE.read_text())):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == name:
                    return value
    raise AssertionError(f'Missing evidence field: {name}')


def test_complete_crossing_is_not_inferred_from_lift():
    assert ast.literal_eval(field('strict_obstacle_crossing_verified')) is None


def test_effective_environment_is_recorded():
    expression = ast.Expression(field('effective_environment'))
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {'M1_PROBE_SPEED': '0.18', 'M1_TEACHER_LEG_SEQUENCE': '0,1,2,3', 'UNRELATED_SECRET': 'omit'}, clear=True):
        result = eval(compile(expression, '<report>', 'eval'), {'os': os})
    assert result == {'M1_PROBE_SPEED': '0.18', 'M1_TEACHER_LEG_SEQUENCE': '0,1,2,3'}


def test_control_phase_is_separate_from_planner_phase():
    field('serial_phase_before_action')
    field('episode_id')


def test_world_geometry_and_errors_are_reported_separately():
    field('obstacle_collision_bounds_w')
    field('obstacle_geometry_error')
    field('env_origin_w_m')
    field('geometry_collision')


def test_support_target_drift_can_be_distinguished_from_tracking_error():
    field('measured_joint_before_rad')
    field('decoded_joint_target_rad')
    field('held_joint_target_rad')
    field('measured_joint_after_rad')


def test_balance_evidence_uses_articulation_com_and_signed_attitude():
    field('articulation_com_w_m')
    field('articulation_com_error')
    field('roll_rad')
    field('pitch_rad')


def test_unload_reports_actual_motion_and_hold_causes():
    source = Path(__file__).resolve().parents[1] / 'scripts/probe_m1_contact_prepare.py'
    tree = ast.parse(source.read_text())
    fields = {kw.arg for node in ast.walk(tree) if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Name) and node.func.id == 'dict'
              for kw in node.keywords}
    assert {'wheel_delta_w', 'root_measured', 'joint_tracking_error',
            'effort_settled_before', 'load_ready_before'} <= fields


def test_final_contact_is_observed_after_last_action():
    source=Path(__file__).resolve().parents[1] / 'scripts/probe_m1_contact_prepare.py'
    tree=ast.parse(source.read_text())
    fields={kw.arg for node in ast.walk(tree) if isinstance(node,ast.Call)
            and isinstance(node.func,ast.Name) and node.func.id=='dict' for kw in node.keywords}
    assert {'final_observation','final_height_reference'} <= fields
