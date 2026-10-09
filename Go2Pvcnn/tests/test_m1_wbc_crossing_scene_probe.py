import ast
from pathlib import Path


def test_opt_in_measured_bottom_probe_exercises_production_wrapper():
    source=(Path(__file__).parents[1]/'scripts/probe_m1_wbc_crossing_scene.py').read_text()
    assert "'--verify-wheel-bottom'" in source
    assert 'AmeRslRlEnvWrapper(env)' in source
    assert "kwargs['wheel_bottom_z_w']" in source
    assert 'return original_update(**kwargs)' in source
    assert 'len(bottom_frames) != 2' in source
    assert 'M1_MEASURED_BOTTOM_RUNTIME ' in source


def test_crossing_scene_probe_uses_real_small_course_and_records_wheel_geometry():
    path = Path(__file__).parents[1] / 'scripts/probe_m1_wbc_crossing_scene.py'
    assert path.exists(), 'single-env obstacle geometry probe is missing'
    source = path.read_text()
    tree = ast.parse(source)
    assert 'M1_OBSTACLE_STAGE' in source and 'small_only' in source
    assert 'SEMANTIC_COURSE_SMALL_ROOT' in source
    assert 'ComputeWorldBound' in source, 'obstacle geometry must come from the live USD stage'
    assert 'M1_SUPPORT_BODY_NAMES' in source and 'body_com_pos_w' in source
    assert 'lateral_overlap_by_obstacle' in source
    assert 'M1_WHEEL_THICKNESS_M' in source
    assert 'wheel_positions[:, 1] > 0.0' in source, \
        'front/rear wheel tracks need tolerance-aware grouping'
    assert 'get_jacobians()' in source and 'M1_WBC_CROSSING_SCENE ' in source
    assert 'jacobians = torch.as_tensor(jacobians).detach().cpu().numpy()' in source, \
        'GPU Jacobian must be copied before NumPy validation'
    assert 'cfg.scene.num_envs = 1' in source
    assert 'crossing_scene_and_swing_geometry_only_not_actuated' in source
    assert "parser.add_argument('--device'" not in source, \
        'AppLauncher already registers --device'
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'set_joint_effort_target' for node in ast.walk(tree)), \
        'geometry probe must not actuate the robot'


def test_crossing_scene_probe_checks_wheel_envelope_clearance_against_live_bounds():
    path = Path(__file__).parents[1] / 'scripts/probe_m1_wbc_crossing_scene.py'
    source = path.read_text()
    tree = ast.parse(source)
    assert 'single_wheel_swing_reference' in source, \
        'the live USD obstacle probe must exercise the actual swing reference'
    assert 'predicted_wheel_clearance_m' in source
    assert 'wheel_envelope_overlap_m' in source
    assert 'obstacle_far_x' in source
    assert any(isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'single_wheel_swing_reference'
        for node in ast.walk(tree)), \
        'swing samples must be generated from measured obstacle bounds'
