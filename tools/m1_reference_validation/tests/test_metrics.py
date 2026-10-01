"""Synthetic first-episode metrics tests; no simulator or tensor runtime."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


def collector(num_envs=2, requested_steps=1600, initial_root_pos=None):
    implementation = Path(__file__).resolve().parents[1] / "metrics.py"
    assert implementation.is_file(), "Missing first-episode metrics implementation"
    spec = importlib.util.spec_from_file_location("m1_metrics_under_test", implementation)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if initial_root_pos is None:
        initial_root_pos = np.tile([0.0, 0.0, 0.57], (num_envs, 1))
    return module.FirstEpisodeMetrics(num_envs, requested_steps, initial_root_pos)


def sample(step, n=2):
    wheel_x = (0.72, 0.85, 1.0, 1.02)[min(step, 3)]
    wheel_z = 0.17 if step < 3 else 0.0959
    wave = step < 4
    return {
        "root_pos": np.tile([1.55 if step >= 4 else 0.8, 0.0, 0.57], (n, 1)),
        "gravity": np.tile([0.0, 0.0, -1.0], (n, 1)),
        "wheel_pos": np.tile([wheel_x, -0.2, wheel_z], (n, 4, 1)),
        "wheel_contact_force": np.full((n, 4), 2.0 if step >= 3 else 0.0),
        "wheel_bar_force_peak": np.zeros((n, 4)),
        "nonwheel_bar_force_peak": np.zeros((n, 13)),
        "wheel_velocity": np.full((n, 4), 1.0),
        "raw_actions": np.zeros((n, 16)),
        "prepared_actions": np.full((n, 12), 0.03 if wave else 0.0),
        "joint_posture_error": np.full((n, 12), 0.06 if wave else 0.0),
        "wave_gate": np.full(n, wave, dtype=bool),
        "phase": np.full(n, 11 if step >= 3 else 1, dtype=np.int64),
        "terminated": np.zeros(n, dtype=bool),
        "timeout": np.zeros(n, dtype=bool),
        "reference_collision": np.zeros((n, 4), dtype=bool),
    }


def run(metrics, count=1600, mutate=None):
    for step in range(count):
        value = sample(step, metrics.num_envs)
        if mutate is not None:
            mutate(step, value)
        metrics.update(step, value)
    return metrics.report(process_finalized=True)


def test_full_budget_and_process_finalization_are_both_required():
    metrics = collector()
    result = run(metrics)
    assert result["completed"] is True
    assert result["passed"] is True
    assert result["validation_kind"] == "strict"
    assert result["passed_envs"] == 2
    assert result["num_envs"] == 2
    assert result["received_steps"] == result["requested_steps"] == 1600
    assert metrics.report()["completed"] is False
    assert metrics.report()["passed"] is False
    env = result["per_env"][0]
    assert all(env["flags"].values())
    assert env["first_failure_step"] is None
    assert env["active_sample_count"] == 1600
    assert env["reset_count"] == 0
    assert env["strict_clearance"] == {
        "FAR": {"prelift_step": 0, "overbar_step": 1, "passed_step": 2, "touchdown_step": 3},
        "RAR": {"prelift_step": 0, "overbar_step": 1, "passed_step": 2, "touchdown_step": 3},
    }
    assert env["wheel_mean_angular_speed"] == {
        "min": [1.0] * 4, "max": [1.0] * 4, "mean": [1.0] * 4,
        "spread": 0.0, "count": 1600,
    }
    json.dumps(result, allow_nan=False)


def test_partial_and_empty_reports_are_incomplete_and_json_safe():
    metrics = collector()
    empty = metrics.report(process_finalized=True)
    assert empty["completed"] is False
    assert empty["passed"] is False
    assert empty["per_env"][0]["root_final_x"] is None
    json.dumps(empty, allow_nan=False)
    result = run(metrics, count=8)
    assert result["passed"] is False
    assert result["completed"] is False
    json.dumps(result, allow_nan=False)


def test_32_step_smoke_cannot_be_behavior_acceptance():
    result = run(collector(requested_steps=32), count=32)
    assert result["validation_kind"] == "startup"
    assert result["completed"] is True
    assert result["passed"] is False
    assert result["passed_envs"] == 2


@pytest.mark.parametrize("field", list(sample(0)))
def test_missing_fields_fail_without_consuming_step(field):
    metrics = collector()
    value = sample(0)
    del value[field]
    with pytest.raises(ValueError, match=field):
        metrics.update(0, value)
    assert metrics.report()["received_steps"] == 0


@pytest.mark.parametrize("field", list(sample(0)))
def test_wrong_shapes_fail_without_consuming_step(field):
    metrics = collector()
    value = sample(0)
    value[field] = value[field][:1]
    with pytest.raises(ValueError, match=field):
        metrics.update(0, value)
    assert metrics.report()["received_steps"] == 0


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_nonfinite_samples_fail_closed(bad):
    metrics = collector()
    value = sample(0)
    value["wheel_pos"][0, 0, 0] = bad
    with pytest.raises(ValueError, match="wheel_pos.*finite"):
        metrics.update(0, value)


@pytest.mark.parametrize("field", ["wave_gate", "terminated", "timeout", "reference_collision"])
def test_boolean_fields_do_not_silently_coerce_numeric_inputs(field):
    metrics = collector()
    value = sample(0)
    value[field] = value[field].astype(float)
    with pytest.raises(ValueError, match=field):
        metrics.update(0, value)


def test_phase_requires_integer_dtype():
    metrics = collector()
    value = sample(0)
    value["phase"] = value["phase"].astype(float)
    with pytest.raises(ValueError, match="phase"):
        metrics.update(0, value)


def test_steps_must_be_consecutive_and_within_budget():
    metrics = collector(requested_steps=2)
    with pytest.raises(ValueError, match="step"):
        metrics.update(1, sample(1))
    metrics.update(0, sample(0))
    with pytest.raises(ValueError, match="step"):
        metrics.update(0, sample(0))
    metrics.update(1, sample(1))
    with pytest.raises(ValueError, match="step"):
        metrics.update(2, sample(2))


def test_first_termination_freezes_evidence_and_failure_through_auto_reset():
    def mutate(step, value):
        if step == 2:
            value["terminated"][0] = True
        if step >= 3:
            value["root_pos"][0, 0] = 99.0
            value["nonwheel_bar_force_peak"][0, 0] = 100.0
    result = run(collector(), mutate=mutate)
    env = result["per_env"][0]
    assert result["passed"] is False
    assert result["passed_envs"] == 1
    assert env["active_sample_count"] == 3
    assert env["root_max_x"] == 0.8
    assert env["nonwheel_bar_force_peak_max"] == 0.0
    assert env["reset_count"] == 1
    assert env["first_failure_step"] == 2
    assert env["flags"]["no_termination"] is False


def test_goal_then_late_fall_still_fails():
    def mutate(step, value):
        if step == 1200:
            value["gravity"][0] = [0.0, 0.0, 1.0]
    result = run(collector(), mutate=mutate)
    assert result["passed_envs"] == 1
    assert result["per_env"][0]["first_failure_step"] == 1200
    assert result["per_env"][0]["max_tilt_rad"] == pytest.approx(np.pi)


def test_timeout_is_failure_and_ends_first_episode():
    def mutate(step, value):
        if step == 20:
            value["timeout"][0] = True
    result = run(collector(), mutate=mutate)
    env = result["per_env"][0]
    assert result["passed"] is False
    assert env["flags"]["no_timeout"] is False
    assert env["active_sample_count"] == 21
    assert env["first_failure_step"] == 20


@pytest.mark.parametrize("missing", ["prelift", "overbar", "touchdown", "recovery"])
def test_missing_required_evidence_fails(missing):
    def mutate(step, value):
        if missing == "prelift" and step == 0:
            value["wheel_pos"][:, :, 0] = 0.75
        if missing == "overbar" and step == 1:
            value["wheel_pos"][:, :, 0] = 0.95
        if missing == "touchdown" and step >= 3:
            value["wheel_contact_force"][:] = 0.0
        if missing == "recovery":
            value["root_pos"][:, 0] = 1.0
    result = run(collector(), mutate=mutate)
    assert result["passed_envs"] == 0
    assert result["passed"] is False


def test_actual_radius_clearance_is_stricter_than_reference_diagnostic():
    def mutate(step, value):
        if step < 3:
            value["wheel_pos"][:, :, 2] = 0.1605
    result = run(collector(), mutate=mutate)
    env = result["per_env"][0]
    assert result["passed"] is False
    assert env["strict_clearance"]["FAR"]["overbar_step"] is None
    assert env["reference_radius_ordered_clearance"]["FAR"]["touchdown_step"] == 3


@pytest.mark.parametrize("field", ["wheel_bar_force_peak", "nonwheel_bar_force_peak"])
def test_own_bar_contacts_latch_and_include_every_body(field):
    def mutate(step, value):
        if step == 500:
            value[field][1, -1] = 1.01
    result = run(collector(), mutate=mutate)
    assert result["passed_envs"] == 1
    assert result["per_env"][1]["first_failure_step"] == 500


def test_reference_collision_latches_failure():
    def mutate(step, value):
        if step == 7:
            value["reference_collision"][0, 3] = True
    result = run(collector(), mutate=mutate)
    assert result["passed_envs"] == 1
    assert result["per_env"][0]["flags"]["no_reference_collision"] is False


def test_nonzero_raw_policy_residual_is_failure_without_mutating_input():
    metrics = collector()
    value = sample(0)
    value["raw_actions"][0, 15] = 1e-12
    metrics.update(0, value)
    assert value["raw_actions"][0, 15] == 1e-12
    env = metrics.report()["per_env"][0]
    assert env["flags"]["zero_raw_actions"] is False
    assert env["first_failure_step"] == 0


@pytest.mark.parametrize("failure", ["speed", "wave_delta", "nonwave", "wave_small", "posture_small"])
def test_control_activity_and_stability_gates(failure):
    def mutate(step, value):
        if failure == "speed":
            value["wheel_velocity"][0, 3] = 1.081
        if failure == "wave_delta" and step == 1:
            value["prepared_actions"][0, 0] = 2.1
        if failure == "nonwave" and step == 9:
            value["prepared_actions"][0, 0] = 0.001
        if failure == "wave_small" and step < 4:
            value["prepared_actions"][0] = 0.01
        if failure == "posture_small":
            value["joint_posture_error"][0] = 0.01
    result = run(collector(), mutate=mutate)
    assert result["passed"] is False
    assert result["passed_envs"] == 1


def test_action_delta_excludes_current_nonwave_samples():
    metrics = collector(requested_steps=3)
    first = sample(0)
    first["prepared_actions"][:] = 3.0
    metrics.update(0, first)
    second = sample(1)
    second["wave_gate"][:] = False
    second["prepared_actions"][:] = 0.0
    metrics.update(1, second)
    env = metrics.report()["per_env"][0]
    assert env["wave_action_delta_max"] is None
    assert env["flags"]["wave_action_delta"] is False


@pytest.mark.parametrize("case", ["mean", "last", "tilt", "phase", "root_final"])
def test_height_tilt_phase_and_final_progress_gates(case):
    def mutate(step, value):
        if case == "mean" and 4 <= step < 1400:
            value["root_pos"][0, 2] = 0.63
        if case == "last" and step == 1599:
            value["root_pos"][0, 2] = 0.62
        if case == "tilt" and step == 100:
            value["gravity"][0] = [np.sin(0.46), 0.0, -np.cos(0.46)]
        if case == "phase":
            value["phase"][0] = 10
        if case == "root_final" and step == 1599:
            value["root_pos"][0, 0] = 1.49
    result = run(collector(), mutate=mutate)
    assert result["passed_envs"] == 1
    assert result["passed"] is False


def test_lateral_clearance_and_ground_force_threshold_are_required():
    def mutate(step, value):
        if step == 1:
            value["wheel_pos"][0, 0, 1] = 0.1
            value["wheel_contact_force"][1, 2] = 1.01
    assert run(collector(), mutate=mutate)["passed_envs"] == 0


def test_all_environment_denominator_includes_a_failing_last_environment():
    def mutate(step, value):
        value["phase"][-1] = 0
    result = run(collector(num_envs=8), mutate=mutate)
    assert result["num_envs"] == 8
    assert len(result["per_env"]) == 8
    assert result["passed_envs"] == 7
    assert result["success_rate"] == 7 / 8
    assert result["passed"] is False


def test_wheel_speed_gate_uses_four_signed_time_means_not_temporal_range():
    def mutate(step, value):
        value["wheel_velocity"][0] = 0.0 if step < 800 else 2.0
        value["wheel_velocity"][1] = [-1.0, 1.0, -1.0, 1.0]
    result = run(collector(), mutate=mutate)
    first, second = result["per_env"]
    assert first["passed"] is True
    assert first["wheel_mean_angular_speed"]["spread"] == 0.0
    assert first["wheel_mean_angular_speed"]["min"] == [0.0] * 4
    assert first["wheel_mean_angular_speed"]["max"] == [2.0] * 4
    assert second["flags"]["wheel_mean_angular_speed_spread"] is False
    assert second["wheel_mean_angular_speed"]["spread"] == 2.0


def test_progress_is_relative_to_actual_nonzero_initial_root():
    initial = np.array([[0.2, 0.0, 0.57], [0.4, 0.0, 0.57]])
    metrics = collector(initial_root_pos=initial)
    initial[:] = 99.0  # The collector owns a snapshot, not an alias.
    def mutate(step, value):
        if step >= 4:
            value["root_pos"][1, 0] = 1.95
    result = run(metrics, mutate=mutate)
    first, second = result["per_env"]
    assert first["root_initial_pos"] == [0.2, 0.0, 0.57]
    assert first["root_final_dx"] == pytest.approx(1.35)
    assert first["flags"]["root_progress"] is False
    assert second["root_final_dx"] == pytest.approx(1.55)
    assert second["passed"] is True
    assert "new diagnostic" in result["diagnostic_definitions"]["touchdown"]


@pytest.mark.parametrize("initial", [np.zeros((2, 2)), np.full((2, 3), np.nan), None])
def test_invalid_initial_root_is_rejected(initial):
    # Load through the helper, then exercise the constructor without its test default.
    cls = type(collector())
    with pytest.raises(ValueError, match="initial_root_pos"):
        cls(2, 1600, initial)


def test_event_order_rejects_earlier_overbar_and_same_step_touchdown():
    def mutate(step, value):
        if step == 0:
            value["wheel_pos"][0, :, 0] = 0.85  # overbar before prelift
        if step == 1:
            value["wheel_pos"][0, :, 0] = 0.72
        if step == 2:
            value["wheel_pos"][1, :, 2] = 0.0959
            value["wheel_contact_force"][1] = 2.0  # passed and grounded same sample
        if step >= 3:
            value["wheel_pos"][1, :, 2] = 0.17
    result = run(collector(requested_steps=4), count=4, mutate=mutate)
    first, second = result["per_env"]
    assert first["strict_clearance"]["FAR"]["overbar_step"] is None
    assert first["source_reference_flags"]["FAR"] == {"prelift": True, "overbar": True}
    assert second["strict_clearance"]["FAR"]["passed_step"] == 2
    assert second["strict_clearance"]["FAR"]["touchdown_step"] is None


def test_exact_inclusive_thresholds_are_not_rejected_by_float_roundoff():
    def mutate(step, value):
        value["root_pos"][:, 2] = 0.61
        value["gravity"][:] = [np.sin(0.45), 0.0, -np.cos(0.45)]
        value["wheel_velocity"][:, 3] = 1.08
        value["wheel_bar_force_peak"][:] = 1.0
        value["nonwheel_bar_force_peak"][:] = 1.0
        if step < 4:
            value["prepared_actions"][:] = 0.02
            value["joint_posture_error"][:] = 0.05
        if step == 0:
            value["wheel_pos"][:, :, 0] = 0.7241
        if step == 1:
            value["wheel_pos"][:, :, 0] = 0.88
            value["wheel_contact_force"][:] = 1.0
        if step < 2:
            value["wheel_pos"][:, :, 2] = 0.1609
        if step == 2:
            value["wheel_pos"][:, :, 0] = 0.9759
        if step >= 3:
            value["wheel_pos"][:, :, 2] = 0.1009
    result = run(collector(), mutate=mutate)
    assert result["passed"] is True, result["per_env"][0]["failed_gates"]


def test_touchdown_cannot_be_counted_after_retreating_in_front_of_bar():
    def mutate(step, value):
        if step >= 3:
            value["wheel_pos"][:, :, 0] = 0.70
    result = run(collector(requested_steps=4), count=4, mutate=mutate)
    events = result["per_env"][0]["strict_clearance"]["FAR"]
    assert events["passed_step"] == 2
    assert events["touchdown_step"] is None


def test_all_wave_trajectory_cannot_pass_without_nonwave_evidence():
    def mutate(step, value):
        value["wave_gate"][:] = True
        value["prepared_actions"][:] = 0.03
        value["joint_posture_error"][:] = 0.06
    result = run(collector(), mutate=mutate)
    assert result["completed"] is True
    assert result["passed"] is False
    for env in result["per_env"]:
        assert env["failed_gates"] == ["nonwave_prepared_zero"]
        assert env["nonwave_sample_count"] == 0
        assert env["nonwave_prepared_abs_max"] is None


def test_recovery_gate_uses_absolute_mean_height_error_not_mean_absolute_error():
    def mutate(step, value):
        if 4 <= step < 1599:
            value["root_pos"][:, 2] = 0.52 if step % 2 == 0 else 0.62
        if step == 1599:
            value["root_pos"][:, 2] = 0.57
    result = run(collector(), mutate=mutate)
    assert result["passed"] is True
    for env in result["per_env"]:
        assert env["flags"]["height_recovery_mean"] is True
        assert env["height_recovery_mean_height"] == pytest.approx(0.57, abs=0.001)
        assert env["height_recovery_abs_mean_error"] < 0.001
        assert env["height_recovery_mean_abs_error"] > 0.04
        assert env["last_active_height_abs_error"] == 0.0
