"""Clock contract from Isaac's per-step timer callback, without actuation."""
from types import SimpleNamespace

import numpy as np
import pytest

from ame_baseline.m1_wbc_execution_adapter import _validate_native_clock


def clock(step, elapsed, native_dt=.001):
    return SimpleNamespace(sim=SimpleNamespace(current_time_step_index=step,
        current_time=elapsed, get_physics_dt=lambda: native_dt))


@pytest.mark.parametrize('step', [294, 2000, 100000])
def test_float32_callback_tick_accumulation_is_not_a_stale_step(step):
    # Recorded native witness at294:0.2940000139642507, dt config0.001.
    elapsed = step*float(np.float32(.001))
    env = clock(step, elapsed)
    assert _validate_native_clock(env, step, step, .001) == (env.sim, elapsed)


def test_configured_native_timestep_must_match_caller_even_at_zero_step():
    with pytest.raises(ValueError, match='simulation time'):
        _validate_native_clock(clock(0, 0., .002), 0, 0, .001)


@pytest.mark.parametrize('step_delta,time_delta', [(1, 0.), (0, .001), (0, -.001)])
def test_quantized_clock_does_not_accept_one_step_staleness(step_delta, time_delta):
    env = clock(294+step_delta, 294*float(np.float32(.001))+time_delta)
    with pytest.raises(ValueError, match='simulation time'):
        _validate_native_clock(env, 294, 294, .001)


def test_arbitrary_drift_is_not_accepted_as_float32_quantization():
    with pytest.raises(ValueError, match='simulation time'):
        _validate_native_clock(clock(294, .2940002), 294, 294, .001)
