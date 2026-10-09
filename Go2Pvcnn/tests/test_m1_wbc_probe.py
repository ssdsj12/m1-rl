"""Opt-in wiring check; physics semantics are verified by native audit separately."""
import ast
from pathlib import Path


def test_full_snapshot_is_opt_in_and_stops_before_prepare():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert "parser.add_argument('--wbc_snapshot', action='store_true')" in source
    tree = ast.parse(source)
    blocks = [n for n in ast.walk(tree) if isinstance(n, ast.If)
              and ast.unparse(n.test) == 'args.wbc_snapshot']
    assert len(blocks) == 1
    block = ast.get_source_segment(source, blocks[0])
    assert 'generalized_snapshot(' in block
    assert 'get_jacobians()' in block
    assert "stopped = 'wbc_read_only_complete'" in block
    assert 'write_' not in block and 'set_' not in block
    assert source.index(block) < source.index('for step in range(args.num_steps')


def test_installed_inertia_uses_measured_actor_frame_not_com_principal_frame():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assignments = [node for node in ast.walk(ast.parse(source))
                   if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'inertia_world' for t in node.targets)]
    assert len(assignments) == 1
    assert ast.unparse(assignments[0].value) == 'link_rotation @ inertia_local @ link_rotation.transpose(-1, -2)'
    assert 'com_inertia_mass_error=' in source  # Keep the rejected hypothesis visible.


def test_wbc_snapshot_reads_true_contact_points_before_control():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'wbc_contact_views' in source
    assert 'contact_geometry(' in source
    assert 'M1_WBC_CONTACTS ' in source
    assert 'contact force closure rejected' in source


def test_material_audit_reads_live_wheel_shapes_and_bound_material_modes():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    for token in ('wbc_material_views','get_material_properties()',
                  'ComputeBoundMaterial', 'GetFrictionCombineModeAttr',
                  'conservative_friction(', 'M1_WBC_MATERIALS '):
        assert token in source, f'material observation missing: {token}'


def test_diagnostic_prints_exception_before_simulator_shutdown():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'traceback.print_exc()' in source
    assert 'except BaseException:' in source


def test_absent_physics_schema_uses_registered_fallback_not_invented_mode():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'FindAppliedAPIPrimDefinition' in source
    assert "GetAttributeFallbackValue('physxMaterial:frictionCombineMode')" in source
    assert 'mode_source' in source


def test_shadow_static_qp_uses_live_geometry_friction_limits_without_actuation():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    for token in ('solve_wbc(', 'M1_WBC_STATIC_QP ', 'get_dof_max_forces()',
                  "material_records[int(owner)]['conservative_mu']"):
        assert token in source, f'missing physical static QP input: {token}'


def test_native_rest_rolling_counterfactual_evaluates_all_bounded_point_modes():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    for token in ('rest_contact_candidates(', 'contact_mode_constraints(',
                  'M1_WBC_ROLL_SHADOW ', 'zero_velocity_counterfactual_not_applied'):
        assert token in source
    imports=[alias.name for node in ast.walk(ast.parse(source))
             if isinstance(node,ast.ImportFrom)
             and node.module=='extension.parallelism.m1_kinematics' for alias in node.names]
    assert 'M1_WHEEL_RADIUS_M' in imports


def test_shadow_records_exact_qp_inputs_for_cpu_reproduction():
    source=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'M1_WBC_REPLAY_INPUT ' in source
    assert 'result=solve_wbc(**qp_input)' in source
