import numpy as np
from pathlib import Path

from ame_baseline.m1_wbc_contact_diagnostics import contact_diagnostics
from ame_baseline.m1_wbc_contact_diagnostics import jacobian_velocity_consistency
from ame_baseline.m1_wbc_contact_diagnostics import contact_acceleration_consistency
from ame_baseline.m1_wbc_contact_diagnostics import (
    generalized_acceleration_consistency, wheel_contact_force_consistency,
    wheel_contact_force_vector_consistency)


def test_reports_material_slip_and_geometric_rolling_velocity_per_contact():
    result = contact_diagnostics(
        points=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        normals=np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]),
        owners=np.array([0, 1]),
        com_positions=np.zeros((4, 3)),
        com_velocity=np.array([
            [0.2, 0.0, 0.0, 0.0, -2.0, 0.0],
            [0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ]),
        surface_velocity=np.zeros((2, 3)),
    )

    assert result["scope"] == "diagnostic_only_not_crossing_or_contact_acceptance"
    assert [row["wheel_owner"] for row in result["contacts"]] == [0, 1]
    np.testing.assert_allclose(result["contacts"][0]["material_velocity_mps"], [0.2, 0.0, 0.0])
    np.testing.assert_allclose(result["contacts"][0]["slip_speed_mps"], 0.2)
    np.testing.assert_allclose(result["contacts"][1]["slip_speed_mps"], 0.1)
    np.testing.assert_allclose(result["geometry_velocity_by_wheel_mps"][0], [0.2, 0.0, 0.0])


def test_reports_native_gap_for_each_contact_without_conflating_it_with_slip():
    result = contact_diagnostics(
        points=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        normals=np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]),
        owners=np.array([0, 1]), com_positions=np.zeros((4, 3)),
        com_velocity=np.zeros((4, 6)), surface_velocity=np.zeros((2, 3)),
        gaps=np.array([0.0004, -0.0002]),
    )
    assert [row["gap_m"] for row in result["contacts"]] == [0.0004, -0.0002]


def test_rejects_owner_outside_m1_four_wheel_order():
    with np.testing.assert_raises(ValueError):
        contact_diagnostics(
            points=np.zeros((1, 3)), normals=np.array([[0.0, 0.0, 1.0]]),
            owners=np.array([4]), com_positions=np.zeros((4, 3)),
            com_velocity=np.zeros((4, 6)), surface_velocity=np.zeros((1, 3)),
        )


def test_pd_handoff_probe_logs_contact_diagnostics_before_crossing_control():
    source = (Path(__file__).parents[1] / "scripts/probe_m1_wbc_pd_handoff.py").read_text()
    assert "contact_diagnostics(" in source
    assert '"M1_WBC_CONTACT_DIAGNOSTICS "' in source
    assert 'contact_points_world_xyz=points.tolist()' in source
    assert 'gaps_before_m' in source and 'gaps_after_m' in source
    assert 'contact_dedup=contact_dedup_audit.copy()' in source
    assert "report.update(identity=identity" in source
    assert "if tick == 0:" in source
    assert "jacobian_velocity_consistency(" in source
    assert '"M1_WBC_JACOBIAN_VELOCITY "' in source
    assert "contact_acceleration_consistency(" in source
    assert '"M1_WBC_CONTACT_ACCELERATION "' in source
    assert "contact_point_velocity_fd" in source
    assert "generalized_acceleration_consistency(" in source
    assert '"M1_WBC_GENERALIZED_ACCELERATION "' in source
    assert "generalized_coordinate_order=[" in source
    assert "wheel_contact_force_consistency(" in source
    assert '"M1_WBC_CONTACT_FORCE "' in source
    assert "get_friction_data(" in source
    assert "wheel_contact_force_vector_consistency(" in source
    assert 'predicted_contact_force = solution["force"]' in source


def test_jacobian_velocity_consistency_compares_wheel_and_contact_points():
    wheel_jac = np.zeros((4, 6, 22))
    wheel_jac[:, :, :6] = np.eye(6)
    qdot = np.zeros(22)
    qdot[:6] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    wheel_expected = np.tile(qdot[:6], (4, 1))
    contact_jac = np.zeros((2, 3, 22))
    contact_jac[:, :, :3] = np.eye(3)
    contact_jac[1, :, 3:6] = np.eye(3)
    contact_expected = np.array([[0.1, 0.2, 0.3], [0.5, 0.7, 0.9]])

    result = jacobian_velocity_consistency(
        wheel_com_jacobians=wheel_jac,
        generalized_velocity=qdot,
        wheel_com_velocity=wheel_expected,
        contact_jacobians=contact_jac,
        material_contact_velocity=contact_expected,
    )

    assert result["max_wheel_velocity_error_mps"] == 0.0
    assert result["max_contact_velocity_error_mps"] < 1e-12
    np.testing.assert_allclose(result["contact_predicted_velocity_mps"], contact_expected)


def test_contact_acceleration_consistency_compares_model_to_next_physics_frame():
    result = contact_acceleration_consistency(
        predicted_acceleration=np.array([[1.0, -2.0, 0.5]]),
        velocity_before=np.array([[0.01, 0.02, 0.03]]),
        velocity_after=np.array([[0.015, 0.01, 0.0325]]),
        dt=0.005,
    )
    np.testing.assert_allclose(result["predicted_acceleration_mps2"], [[1.0, -2.0, 0.5]])
    np.testing.assert_allclose(result["finite_difference_acceleration_mps2"], [[1.0, -2.0, 0.5]])
    assert result["max_abs_model_error_mps2"] < 1e-12


def test_generalized_acceleration_consistency_separates_base_and_joint_residuals():
    before = np.zeros(22)
    after = np.arange(22, dtype=np.float64) * 0.002
    predicted = np.arange(22, dtype=np.float64)
    result = generalized_acceleration_consistency(
        predicted_acceleration=predicted,
        velocity_before=before,
        velocity_after=after,
        dt=0.002,
    )
    np.testing.assert_allclose(result["predicted_acceleration"], predicted)
    np.testing.assert_allclose(result["finite_difference_acceleration"], predicted)
    assert result["max_abs_model_error"] < 1e-12
    assert result["max_abs_base_linear_error_mps2"] < 1e-12
    assert result["max_abs_base_angular_error_rad_s2"] < 1e-12
    assert result["max_abs_joint_error_rad_s2"] < 1e-12


def test_wheel_contact_force_consistency_aggregates_world_forces_by_owner():
    result = wheel_contact_force_consistency(
        predicted_world_force=np.array([[1.0, 2.0, 30.0], [3.0, 4.0, 35.0]]),
        contact_normals=np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]),
        owners=np.array([0, 0]),
        measured_wheel_normal_load=np.array([65.0, 0.0, 0.0, 0.0]),
    )
    np.testing.assert_allclose(result["predicted_wheel_normal_load_n"], [65.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(result["normal_load_error_n"], 0.0, atol=1e-12)
    assert result["max_abs_normal_load_error_n"] == 0.0
    assert result["tangential_force_observed"] is False


def test_wheel_contact_force_vector_consistency_aggregates_normal_and_friction():
    result = wheel_contact_force_vector_consistency(
        predicted_world_force=np.array([[1.0, 2.0, 30.0], [3.0, 4.0, 35.0]]),
        owners=np.array([0, 0]),
        measured_wheel_normal_force=np.array([[0.0, 0.0, 65.0], [0.0, 0.0, 0.0],
                                              [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
        raw_wheel_friction_force=np.array([[4.0, 6.0, 0.0], [0.0, 0.0, 0.0],
                                           [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
    )
    np.testing.assert_allclose(result["predicted_wheel_force_n"],
        [[4.0, 6.0, 65.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    np.testing.assert_allclose(result["force_error_if_friction_on_sensor_n"], 0.0, atol=1e-12)
    np.testing.assert_allclose(
        result["force_error_if_friction_on_filter_n"][0], [-8.0, -12.0, 0.0])
    assert result["max_abs_force_error_n"] == 0.0


def test_snapshot_only_probe_exits_before_any_explicit_wbc_application():
    import ast
    from pathlib import Path
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_wbc_pd_handoff.py').read_text())
    guards=[n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='args.snapshot_only']
    assert len(guards)==1, 'read-only WBC snapshot needs an explicit guarded exit'
    guard=guards[0]
    assert any(isinstance(n,ast.Raise) and ast.unparse(n.exc)=='_SnapshotComplete()' for n in ast.walk(guard))
    applies=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and ast.unparse(n.func)=='apply_wbc_command']
    assert all(guard.end_lineno<n.lineno for n in applies)
    handlers=[n for n in ast.walk(tree) if isinstance(n,ast.ExceptHandler) and n.type and ast.unparse(n.type)=='_SnapshotComplete']
    assert len(handlers)==1
