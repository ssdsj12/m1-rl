import ast
from pathlib import Path


def test_grounded_initial_contact_probe_is_single_env_and_advances_bounded_raw_ticks():
    path = Path(__file__).parents[1] / 'scripts/probe_m1_wbc_ground_init.py'
    assert path.exists(), 'fresh grounded WBC initialization probe is missing'
    source = path.read_text()
    tree = ast.parse(source)
    assert 'cfg.scene.num_envs = 1' in source
    assert 'choices=range(1, 33), default=32' in source
    assert 'actuator.stiffness = 0.' in source
    assert 'actuator.damping = 0.' in source
    assert 'create_rigid_contact_view(' in source
    assert 'M1_WBC_GROUND_INIT ' in source
    sim_steps = [node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'step' and isinstance(node.func.value, ast.Attribute)
        and ast.unparse(node.func.value) == 'env.sim']
    assert len(sim_steps) == 1, 'probe may only advance through one bounded raw-step call site'
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'step' and ast.unparse(node.func.value) == 'env'
        for node in ast.walk(tree)), 'manager action step must not run implicit controllers'
    assert 'initial_contact_observability_not_stance_or_crossing' in source


def test_pd_to_wbc_probe_hands_off_same_tick_and_uses_raw_steps_afterward():
    path = Path(__file__).parents[1] / 'scripts/probe_m1_wbc_pd_handoff.py'
    assert path.exists(), 'same-state PD-to-WBC handoff probe is missing'
    source = path.read_text()
    tree = ast.parse(source)
    assert 'cfg.scene.num_envs = 1' in source
    assert 'capture_pd_handoff(' in source and 'handoff=handoff' in source
    assert 'joint_names=tuple(robot.joint_names)' in source
    assert 'same_state_handoff_and_closed_loop_flat_support_not_crossing' in source
    assert 'M1_WBC_PD_HANDOFF_ERROR' in source
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    apply_lines = [node.lineno for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == 'apply_wbc_command']
    assert len(apply_lines) == 2, 'handoff is followed by one feedback command site in the control loop'
    manager_step_lines = [node.lineno for node in calls
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'step'
        and ast.unparse(node.func.value) == 'env']
    assert manager_step_lines and max(manager_step_lines) < apply_lines[0]
    assert "env.sim.step(render=False)" in source


def test_pd_wbc_support_smoke_re_solves_and_rate_limits_every_physics_tick():
    path = Path(__file__).parents[1] / 'scripts/probe_m1_wbc_pd_handoff.py'
    tree = ast.parse(path.read_text())
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For)
        and isinstance(node.target, ast.Name) and node.target.id == 'tick']
    assert len(loops) == 1
    loop_calls = [node for node in ast.walk(loops[0]) if isinstance(node, ast.Call)]
    assert any(isinstance(node.func, ast.Name) and node.func.id == 'solve_wbc'
        for node in loop_calls), 'support hold must be a receding-horizon WBC loop'
    assert any(isinstance(node.func, ast.Name) and node.func.id == 'apply_wbc_command'
        for node in loop_calls), 'each tick must write a freshly validated torque command'
    assert any(isinstance(node.func, ast.Name) and node.func.id == 'effort_step_bounds'
        for node in loop_calls), 'each tick must retain the fixed measured effort slew bound'


def test_wbc_takeover_allows_only_bounded_transient_then_requires_recovered_speed():
    path = Path(__file__).parents[1] / 'scripts/probe_m1_wbc_pd_handoff.py'
    tree = ast.parse(path.read_text())
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For)
        and isinstance(node.target, ast.Name) and node.target.id == 'tick']
    loop_calls = [node for node in ast.walk(loops[0]) if isinstance(node, ast.Call)]
    assert any(isinstance(node.func, ast.Name) and node.func.id == 'require_support_gate'
        and any(keyword.arg == 'speed_limit' and isinstance(keyword.value, ast.Constant)
            and keyword.value.value == .08 for keyword in node.keywords)
        for node in loop_calls), 'only a bounded transition envelope is allowed during takeover'
    assert 'require_support_gate(trace[-1], speed_limit=0.04)' in ast.unparse(tree)


def test_closed_loop_contact_acceleration_constraint_uses_live_kinematic_bias():
    path = Path(__file__).parents[1] / 'scripts/probe_m1_wbc_pd_handoff.py'
    source = path.read_text()
    tree = ast.parse(source)
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For)
        and isinstance(node.target, ast.Name) and node.target.id == 'tick']
    assignments = [node for node in ast.walk(loops[0]) if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'solution'
                for target in node.targets)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name) and node.value.func.id == 'solve_wbc']
    assert len(assignments) == 1
    solve = assignments[0].value
    rhs = next(keyword.value for keyword in solve.keywords if keyword.arg == 'contact_rhs')
    assert isinstance(rhs, ast.Subscript)
    assert ast.unparse(rhs.value) == 'contact_mode'
    assert ast.literal_eval(rhs.slice) == 'contact_rhs'
    assert 'contact_step_constraints(' in source
    assert 'kinematic_bias(' in source
    assert 'contact_motion(' in source


def test_closed_loop_probe_records_root_com_velocity_finite_difference():
    source=(Path(__file__).parents[1]/'scripts/probe_m1_wbc_pd_handoff.py').read_text()
    assert 'root_com_velocity_before' in source
    assert 'root_com_velocity_after' in source
    assert 'qdd_root_com_fd' in source
    assert 'qdd_model_minus_root_com_fd' in source
