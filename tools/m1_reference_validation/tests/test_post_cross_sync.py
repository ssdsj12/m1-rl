"""CPU contract tests; the toy plants are not Isaac stability evidence."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parents[1]


def controller(n=2):
    path = HERE / "post_cross_sync.py"
    assert path.is_file(), "Missing isolated post-cross synchronizer"
    spec = importlib.util.spec_from_file_location("post_cross_sync_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PostCrossSync(n)


def current(step, n=2):
    return {
        "wheel_velocity": torch.ones((n, 4), dtype=torch.float64),
        "root_pos": torch.tensor([[1.5, 0.0, 0.57]] * n, dtype=torch.float64),
        "wave_gate": torch.zeros(n, dtype=torch.bool),
        "drive_allowed": torch.ones(n, dtype=torch.bool),
        "episode_length": torch.full((n,), step + 1, dtype=torch.int64),
    }


def actions(n=2):
    result = torch.zeros((n, 16), dtype=torch.float64)
    result[:, 12:] = torch.tensor([1.0, 1.0, 1.4, 1.4])
    return result


def packet(step, n=2):
    x = (0.72, 0.85, 1.0, 1.02)[min(step, 3)]
    z = 0.17 if step < 3 else 0.0959
    return {
        "root_pos": torch.tensor([[1.5, 0.0, 0.57]] * n, dtype=torch.float64),
        "gravity": torch.tensor([[0.0, 0.0, -1.0]] * n, dtype=torch.float64),
        "wheel_pos": torch.tensor([[[x, -0.2, z]] * 4] * n, dtype=torch.float64),
        "wheel_contact_force": torch.full((n, 4), 2.0 if step >= 3 else 0.0, dtype=torch.float64),
        "wheel_bar_force_peak": torch.zeros((n, 4), dtype=torch.float64),
        "nonwheel_bar_force_peak": torch.zeros((n, 13), dtype=torch.float64),
        "wheel_velocity": torch.ones((n, 4), dtype=torch.float64),
        "prepared_actions": torch.zeros((n, 12), dtype=torch.float64),
        "applied_actions": actions(n),
        "wave_gate": torch.full((n,), step < 3, dtype=torch.bool),
        "phase": torch.full((n,), 11 if step >= 3 else 1, dtype=torch.int64),
        "terminated": torch.zeros(n, dtype=torch.bool),
        "timeout": torch.zeros(n, dtype=torch.bool),
        "reference_collision": torch.zeros((n, 4), dtype=torch.bool),
        "episode_id": torch.zeros(n, dtype=torch.int64),
        "env_id": torch.arange(n),
    }


def advance(sync, step, value=None, curr=None, original=None):
    n = sync.num_envs
    out, diag = sync.prepare(step, actions(n) if original is None else original,
                             current(step, n) if curr is None else curr)
    value = packet(step, n) if value is None else value
    value["episode_id"] = sync.episode_id.clone()
    value["applied_actions"] = out.clone()
    sync.observe(step, value)
    return out, diag


def qualify(sync, applied=None):
    for step in range(8):
        advance(sync, step)
    if applied is not None:
        # Exercise the actual packet path instead of changing controller state.
        other = controller(sync.num_envs)
        for step in range(8):
            value = packet(step, sync.num_envs)
            other.prepare(step, actions(sync.num_envs), current(step, sync.num_envs))
            if step == 7:
                value["applied_actions"][:, 12:] = applied
            other.observe(step, value)
        return other
    return sync


def test_inactive_action_and_snapshot_bitwise_parity():
    sync = controller()
    original = torch.arange(32, dtype=torch.float32).reshape(2, 16)
    original[0, 0] = -0.0
    saved = original.clone()
    out, diag = sync.prepare(0, original, current(0))
    assert torch.equal(out.view(torch.int32), saved.view(torch.int32))
    assert out.dtype == original.dtype and out.device == original.device
    out.fill_(42)
    original.fill_(13)
    assert torch.equal(diag["original_actions"], saved)
    assert torch.equal(diag["final_actions"], saved)
    diag["active"].fill_(True)
    assert not sync.active.any()


def test_activation_is_next_prepare_after_five_complete_samples_and_actual_hold():
    sync = qualify(controller(), applied=torch.tensor([2.0, 3.0, 4.0, 5.0]))
    assert not sync.active.any()
    assert sync.ready_count.tolist() == [5, 5]
    curr = current(8)
    curr["wheel_velocity"][:] = torch.tensor([0.2, 0.8, 1.4, 2.0])
    out, diag = sync.prepare(8, actions(), curr)
    assert sync.activation_step.tolist() == [8, 8]
    assert diag["hold"].all() and diag["integral_paused"].all()
    assert torch.equal(out[:, 12:], torch.tensor([[2., 3., 4., 5.]] * 2, dtype=out.dtype))
    assert torch.equal(diag["filtered_velocity"], curr["wheel_velocity"])
    assert not diag["bias"].any()
    assert torch.equal(sync.events, torch.tensor([[[0, 1, 2, 3]] * 2] * 2))


@pytest.mark.parametrize("case", ["initial_minus_one", "phase5", "no_prelift", "no_overbar",
    "out_of_order", "one_wheel", "wave", "legs", "wheel_x", "wheel_z", "ground_force",
    "root_equal", "height_low", "height_high", "tilt", "reference", "wheel_bar", "nonwheel_bar",
    "terminated", "timeout"])
def test_each_gate_blocks_activation(case):
    sync = controller()
    for step in range(16):
        value = packet(step)
        if case == "initial_minus_one":
            value = packet(9)
            value["phase"].fill_(-1)
        elif case == "phase5":
            value["phase"].fill_(5)
        elif case == "no_prelift" and step == 0:
            value["wheel_pos"][:, :, 2] = 0.0959
        elif case == "no_overbar" and step == 1:
            value["wheel_pos"][:, :, 2] = 0.0959
        elif case == "out_of_order" and step < 2:
            value = packet(1 - step)
        elif case == "one_wheel" and step < 3:
            value["wheel_pos"][:, 2, 2] = 0.0959
        elif step >= 3:
            if case == "wave": value["wave_gate"].fill_(True)
            if case == "legs": value["prepared_actions"][:, 0] = 1e-10
            if case == "wheel_x": value["wheel_pos"][:, 0, 0] = 0.9758
            if case == "wheel_z": value["wheel_pos"][:, 2, 2] = 0.101
            if case == "ground_force": value["wheel_contact_force"][:, 2] = 1.0
            if case == "root_equal": value["root_pos"][:, 0] = 1.15
            if case == "height_low": value["root_pos"][:, 2] = 0.5299
            if case == "height_high": value["root_pos"][:, 2] = 0.6101
            if case == "tilt": value["gravity"][:, 2] = -np.cos(0.4501)
            if case == "reference": value["reference_collision"][:, 1] = True
            if case == "wheel_bar": value["wheel_bar_force_peak"][:, 1] = 1.0001
            if case == "nonwheel_bar": value["nonwheel_bar_force_peak"][:, 7] = 1.0001
            if case == "terminated": value["terminated"].fill_(True)
            if case == "timeout": value["timeout"].fill_(True)
        _, diag = advance(sync, step, value)
        assert not diag["active"].any(), case
    assert sync.gate_reasons.ne(0).all()


def test_ready_streak_breaks_and_phase11_latches():
    sync = controller()
    for step in range(12):
        value = packet(step)
        if step > 3: value["phase"].fill_(-1)
        if step == 5: value["wheel_contact_force"].fill_(0)
        _, diag = advance(sync, step, value)
        assert diag["active"].all().item() == (step >= 11)


def test_readiness_and_integrator_are_per_environment():
    sync = controller()
    for step in range(11):
        value = packet(step)
        value["phase"][1] = 5
        out, diag = advance(sync, step, value)
    assert diag["active"].tolist() == [True, False]
    assert torch.equal(out[1], actions()[1])
    assert torch.equal(out[:, :12], actions()[:, :12])


def test_observe_deep_copies_packet_and_diagnostics_do_not_alias_state():
    sync = controller()
    for step in range(8):
        sync.prepare(step, actions(), current(step))
        value = packet(step)
        sync.observe(step, value)
        for tensor in value.values(): tensor.fill_(0)
    out, diag = sync.prepare(8, actions(), current(8))
    assert diag["active"].all()
    assert torch.equal(out, actions())
    diag["bias"].fill_(123)
    assert not sync.bias.any()


@pytest.mark.parametrize("scenario", ["observe_before_prepare", "repeat_prepare", "missing_observe",
    "repeat_observe", "skip_prepare", "future_observe", "wrong_env", "duplicate_env", "wrong_episode"])
def test_packet_sequence_and_identity_reject(scenario):
    sync = controller()
    if scenario == "observe_before_prepare":
        with pytest.raises(ValueError): sync.observe(0, packet(0))
        return
    sync.prepare(0, actions(), current(0))
    if scenario in ("repeat_prepare", "missing_observe", "skip_prepare"):
        step = {"repeat_prepare": 0, "missing_observe": 1, "skip_prepare": 2}[scenario]
        with pytest.raises(ValueError): sync.prepare(step, actions(), current(step))
        return
    value = packet(0)
    if scenario == "wrong_env": value["env_id"] = torch.tensor([1, 0])
    if scenario == "duplicate_env": value["env_id"] = torch.tensor([0, 0])
    if scenario == "wrong_episode": value["episode_id"][1] = 1
    if scenario == "repeat_observe":
        sync.observe(0, value)
    with pytest.raises(ValueError): sync.observe(1 if scenario == "future_observe" else 0, value)


def test_partial_reset_clears_all_state_and_invalidates_old_packet():
    sync = qualify(controller())
    advance(sync, 8)
    env1_events = sync.events[1].clone()
    sync.reset(torch.tensor([0]))
    assert sync.episode_id.tolist() == [1, 0]
    assert sync.active.tolist() == [False, True]
    assert sync.activation_step.tolist() == [-1, 8]
    assert (sync.events[0] == -1).all()
    assert torch.equal(sync.events[1], env1_events)
    assert sync.ready_count[0] == 0
    curr = current(9)
    curr["episode_length"][0] = 0
    original = actions()
    original[0] = torch.arange(16)
    out, diag = sync.prepare(9, original, curr)
    assert torch.equal(out[0], original[0])
    assert not diag["bias"][0].any() and not diag["filtered_velocity"][0].any()
    stale = packet(9)
    with pytest.raises(ValueError, match="episode"): sync.observe(9, stale)
    stale["episode_id"] = sync.episode_id.clone()
    sync.observe(9, stale)
    sync.reset(torch.tensor([0, 1]))
    assert sync.episode_id.tolist() == [2, 1]
    assert not sync.active.any()


def test_episode_length_regression_requires_explicit_reset():
    sync = controller()
    advance(sync, 0)
    curr = current(1)
    curr["episode_length"][1] = 0
    with pytest.raises(ValueError, match="episode_length"): sync.prepare(1, actions(), curr)
    sync.reset([1])
    out, _ = sync.prepare(1, actions(), curr)
    assert torch.equal(out, actions())


@pytest.mark.parametrize("field", ["wave_gate", "drive_allowed", "root_pos", "legs"])
def test_active_current_controller_reentry_fails_before_override(field):
    sync = qualify(controller())
    curr, original = current(8), actions()
    if field == "wave_gate": curr[field][0] = True
    if field == "drive_allowed": curr[field][0] = False
    if field == "root_pos": curr[field][0, 0] = 1.15
    if field == "legs": original[0, 3] = 1e-30
    saved = original.clone()
    with pytest.raises(ValueError, match="applicability"): sync.prepare(8, original, curr)
    assert torch.equal(original, saved)
    assert not sync.active.any()


@pytest.mark.parametrize("where", ["actions", "velocity", "root", "packet", "state"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_inputs_and_state_rejected(where, bad):
    sync, curr, original = controller(), current(0), actions()
    if where == "actions": original[0, 1] = bad
    if where == "velocity": curr["wheel_velocity"][0, 1] = bad
    if where == "root": curr["root_pos"][0, 1] = bad
    if where == "state": sync.bias[0, 1] = bad
    if where == "packet":
        sync.prepare(0, original, curr)
        value = packet(0)
        value["wheel_pos"][0, 0, 1] = bad
        with pytest.raises(ValueError, match="finite"): sync.observe(0, value)
    else:
        with pytest.raises(ValueError, match="finite"): sync.prepare(0, original, curr)


@pytest.mark.parametrize("field", ["phase", "wave_gate", "wheel_contact_force", "wheel_pos", "env_id"])
def test_malformed_packets_fail_without_consuming_step(field):
    sync = controller()
    sync.prepare(0, actions(), current(0))
    value = packet(0)
    if field in ("phase", "wave_gate", "env_id"): value[field] = value[field].double()
    elif field == "wheel_contact_force": value[field][0, 0] = -1
    else: value[field] = value[field][:, :3]
    with pytest.raises(ValueError): sync.observe(0, value)
    assert sync.last_observed_step == -1
    sync.observe(0, packet(0))


def test_equal_velocity_has_no_bias_and_first_hold_pauses_following_integral():
    sync = qualify(controller())
    for step in range(8, 13):
        _, diag = advance(sync, step)
        assert not diag["bias"].any()
        assert diag["integral_paused"].all().item() == (step <= 9)
        assert diag["hold"].all().item() == (step == 8)


def test_fixed_error_direction_ema_projection_and_slew():
    sync = qualify(controller(), applied=torch.tensor([5., 0., 3., 0.]))
    previous = None
    for step in range(8, 750):
        curr = current(step)
        curr["wheel_velocity"][:] = torch.tensor([-10., 0., 10., 20.])
        out, diag = advance(sync, step, curr=curr)
        assert torch.max(torch.abs(diag["bias"])) <= 1 + 1e-12
        assert torch.max(torch.abs(diag["bias"].sum(dim=1))) < 1e-12
        assert ((out[:, 12:] >= 0) & (out[:, 12:] <= 20)).all()
        if previous is not None:
            assert torch.max(torch.abs(out[:, 12:] - previous)) <= 0.02 + 1e-12
        previous = out[:, 12:].clone()
    assert diag["bias"][0, 0] > 0 and diag["bias"][0, 3] < 0
    assert diag["bias_limited"].all()


def test_filter_equation_and_per_environment_previous_slew_support_pause():
    sync = qualify(controller(), applied=torch.tensor([[5., 5., 5., 5.], [1., 1., 1.4, 1.4]]))
    advance(sync, 8)
    for step in (9, 10):
        curr = current(step)
        curr["wheel_velocity"][:] = torch.tensor([0., 1., 1., 2.])
        out, diag = advance(sync, step, curr=curr)
        if step == 9:
            expected = torch.ones(4) + (1 - np.exp(-0.02 / 0.20)) * torch.tensor([-1., 0., 0., 1.])
            assert torch.allclose(diag["filtered_velocity"][0], expected.double(), atol=1e-7)
        else:
            assert diag["integral_paused"].tolist() == [True, False]
            assert not diag["bias"][0].any() and diag["bias"][1, 0] > 0
    # Loss of support on env1 pauses only its integrator; output/filter continue.
    value = packet(11)
    value["wheel_contact_force"][1] = 0
    advance(sync, 11, value)
    before = sync.bias.clone()
    _, diag = advance(sync, 12)
    assert diag["integral_paused"][1]
    assert torch.equal(diag["bias"][1], before[1])
    assert diag["active"].all()


def test_every_diagnostic_is_independent_finite_cpu_tensor():
    sync = qualify(controller())
    _, diagnostic = sync.prepare(8, actions(), current(8))
    expected = {
        "episode_id", "active", "activation_step", "events", "ready_count", "gate_reasons",
        "support_ok", "original_actions", "final_actions", "velocity", "filtered_velocity",
        "error", "bias", "slew_limited", "bias_limited", "physical_limited", "hold", "integral_paused",
    }
    assert set(diagnostic) == expected
    for name, value in diagnostic.items():
        assert isinstance(value, torch.Tensor) and value.device.type == "cpu"
        assert torch.isfinite(value).all()
        if hasattr(sync, name):
            assert value.data_ptr() != getattr(sync, name).data_ptr()
    assert diagnostic["original_actions"].data_ptr() != diagnostic["final_actions"].data_ptr()


def test_boundaries_use_only_double_roundoff_and_strict_ground_force():
    sync = controller()
    for step in range(8):
        value = packet(step)
        if step == 0:
            value["wheel_pos"][:, :, 0] = 0.7241
            value["wheel_pos"][:, :, 1] = -0.2 + 0.08 + 0.0959
            value["wheel_pos"][:, :, 2] = 0.1609
        if step == 1:
            value["wheel_pos"][:, :, 0] = 0.88
            value["wheel_pos"][:, :, 2] = 0.1609
            value["wheel_contact_force"].fill_(1.0)
        if step >= 2: value["wheel_pos"][:, :, 0] = 0.9759
        if step >= 3:
            value["wheel_pos"][:, :, 2] = 0.0959 + 0.005
            value["root_pos"][:, 2] = torch.tensor([0.53, 0.61])
            # Explicit float64 avoids treating float32 representation as roundoff.
            value["root_pos"][0, 2] = 0.53
            value["root_pos"][1, 2] = 0.61
            value["gravity"][:, 2] = -np.cos(0.45)
            value["wheel_bar_force_peak"].fill_(1.0)
            value["nonwheel_bar_force_peak"].fill_(1.0)
        advance(sync, step, value)
    _, diag = sync.prepare(8, actions(), current(8))
    assert diag["active"].all()
    assert torch.equal(diag["events"], torch.tensor([[[0, 1, 2, 3]] * 2] * 2))


def test_gate_reason_is_distinct_per_failed_predicate():
    sync = controller()
    value = packet(0)
    value["root_pos"][0, 0] = 1.15
    advance(sync, 0, value)
    # Every other field is identical, so only the root bit differs.
    assert int(sync.gate_reasons[0] ^ sync.gate_reasons[1]) == 1 << 8


def test_ended_packet_never_grants_or_recovers_qualification_without_reset():
    sync = controller()
    for step in range(13):
        value = packet(step)
        if step == 7: value["terminated"].fill_(True)
        _, diag = advance(sync, step, value)
        assert not diag["active"].any()
    assert not sync.ready_count.any()


def test_initial_reset_allows_initial_original_step_and_old_packet_is_rejected():
    sync = controller()
    sync.reset([0])
    out, diag = sync.prepare(0, actions(), current(0))
    assert torch.equal(out, actions())
    assert diag["episode_id"].tolist() == [1, 0]
    with pytest.raises(ValueError, match="episode"): sync.observe(0, packet(0))
    value = packet(0)
    value["episode_id"] = sync.episode_id.clone()
    sync.observe(0, value)


def test_reset_between_prepare_and_observe_rejects_both_old_and_new_packet_generations():
    sync = controller()
    sync.prepare(0, actions(), current(0))
    sync.reset([0])
    value = packet(0)
    with pytest.raises(ValueError, match="episode|generation"): sync.observe(0, value)
    value["episode_id"] = sync.episode_id.clone()
    with pytest.raises(ValueError, match="generation"): sync.observe(0, value)


@pytest.mark.parametrize("bad_ids", [[-1], [2], [0, 0], [True], [0.0], [[0]]])
def test_reset_ids_are_validated_without_partial_mutation(bad_ids):
    sync = qualify(controller())
    before = sync.episode_id.clone()
    with pytest.raises(ValueError): sync.reset(bad_ids)
    assert torch.equal(sync.episode_id, before)
    assert sync.ready_count.tolist() == [5, 5]


@pytest.mark.parametrize("field", list(packet(0)))
def test_every_required_packet_field_is_mandatory(field):
    sync = controller()
    sync.prepare(0, actions(), current(0))
    value = packet(0)
    del value[field]
    with pytest.raises(ValueError, match="Missing field"): sync.observe(0, value)
    assert sync.last_observed_step == -1


def test_packet_step_metadata_matches_call_and_extras_are_ignored():
    sync = controller()
    sync.prepare(0, actions(), current(0))
    value = packet(0)
    value["step"] = torch.tensor(1)
    with pytest.raises(ValueError, match="packet step"): sync.observe(0, value)
    value["step"] = torch.tensor(0)
    value["unrelated_recorder_diagnostic"] = "not a controller input"
    sync.observe(0, value)


def test_previous_physical_clamp_flag_pauses_only_its_environment():
    sync = qualify(controller())
    advance(sync, 8)
    advance(sync, 9)
    sync.physical_limited[0, 2] = True
    curr = current(10)
    curr["wheel_velocity"][:] = torch.tensor([0., 1., 1., 2.])
    _, diag = advance(sync, 10, curr=curr)
    assert diag["integral_paused"].tolist() == [True, False]
    assert not diag["bias"][0].any()
    assert diag["bias"][1, 0] > 0


def test_active_float32_preserves_leg_bits_and_slew_with_representation_roundoff():
    sync = qualify(controller(), applied=torch.tensor([5., 5., 5., 5.]))
    previous = None
    for step in range(8, 25):
        original = actions().float()
        original[:, :12] = -0.0
        out, _ = advance(sync, step, original=original)
        assert torch.equal(out[:, :12].view(torch.int32), original[:, :12].view(torch.int32))
        if previous is not None:
            now = out[:, 12:]
            before_ulp = (torch.nextafter(previous, torch.full_like(previous, float("inf"))) - previous).double()
            now_ulp = (torch.nextafter(now, torch.full_like(now, float("inf"))) - now).double()
            rounding = (before_ulp + now_ulp) / 2
            assert ((now.double() - previous.double()).abs() <= 0.02 + rounding + 1e-12).all()
        previous = out[:, 12:].clone()


def test_finite_values_that_overflow_intermediate_state_fail_before_returning_actions():
    sync = qualify(controller())
    curr = current(8)
    curr["wheel_velocity"].fill_(1e308)
    with pytest.raises(ValueError, match="finite"):
        sync.prepare(8, actions(), curr)


def test_state_is_cpu_even_if_host_changes_torch_default_device():
    try:
        torch.set_default_device("meta")
        sync = controller()
    finally:
        torch.set_default_device("cpu")
    for value in vars(sync).values():
        if isinstance(value, torch.Tensor): assert value.device.type == "cpu"


@pytest.mark.parametrize("delay", [0, 1])
def test_cpu_unit_response_plant_fixed_disturbance_converges_without_two_step_cycle(delay):
    sync = qualify(controller(1))
    disturbance = torch.tensor([[0.15, -0.1, -0.3, -0.55]], dtype=torch.float64)
    velocity = actions(1)[:, 12:] + disturbance
    prior = actions(1)[:, 12:].clone()
    history = []
    for step in range(8, 1608):
        curr = current(step, 1)
        curr["wheel_velocity"] = velocity
        out, _ = advance(sync, step, curr=curr)
        wheel = out[:, 12:]
        velocity = (prior if delay else wheel) + disturbance
        prior = wheel.clone()
        history.append(velocity[0].clone())
    trace = torch.stack(history)
    tail = trace[-200:]
    assert (tail.max(dim=1).values - tail.min(dim=1).values).max() < 1e-5
    assert (tail[1:] - tail[:-1]).abs().max() < 1e-6
    assert (tail[::2].mean(dim=0) - tail[1::2].mean(dim=0)).abs().max() < 1e-7


@pytest.mark.parametrize("run_name, expected", [
    ("20260918_gpu7_8x1600_12_normal_clone", [249, 253, 248, 251, 245, 248, 248, 247]),
    ("20260918_gpu7_8x1600_13_equalizer_off", None),
])
def test_frozen_run_event_parity_and_first_episode_gate_replay(run_name, expected):
    folder = Path("/home/hexinkun/m1_rl/run_logs/m1_reference_validation") / run_name
    if not folder.is_dir(): pytest.skip("Frozen remote CPU replay data unavailable")
    files = sorted(folder.glob("samples_*.npz"))
    data = {}
    for path in files:
        with np.load(path, allow_pickle=False) as chunk:
            for key in chunk.files: data.setdefault(key, []).append(chunk[key])
    data = {key: np.concatenate(parts) for key, parts in data.items()}
    metric_spec = importlib.util.spec_from_file_location("frozen_parity_metrics", HERE / "metrics.py")
    metric_module = importlib.util.module_from_spec(metric_spec)
    metric_spec.loader.exec_module(metric_module)
    metrics = metric_module.FirstEpisodeMetrics(8, 1600, np.zeros((8, 3)))
    sync = controller(8)
    first = [-1] * 8
    ended = np.zeros(8, dtype=bool)
    for step in range(1600):
        value = {key: item[step].copy() for key, item in data.items() if key != "step"}
        metrics.update(step, value)
        curr = current(step, 8)
        # Replay identifies candidate readiness; synthetic current obeys the flat contract.
        sync.prepare(step, actions(8), curr)
        for env in range(8):
            if first[env] < 0 and sync.active[env] and not ended[env]: first[env] = step
        value["env_id"] = np.arange(8, dtype=np.int64)
        value["episode_id"] = sync.episode_id.clone()
        value["applied_actions"] = actions(8)
        sync.observe(step, value)
        ended |= value["terminated"] | value["timeout"]
        assert np.array_equal(sync.events.numpy(), metrics.clearance_events["strict"])
    if expected is not None:
        assert first == expected
    else:
        assert [first[i] for i in (1, 2, 5)] == [-1, -1, -1]
