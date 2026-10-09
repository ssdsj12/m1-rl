import importlib.util
from pathlib import Path
import torch


def guard():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_effort_guard.py'
    assert path.exists(), 'M1 effort lifecycle guard missing'
    spec = importlib.util.spec_from_file_location('effort_guard', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.guarded_effort


def inputs():
    return dict(target=torch.full((2, 16), 20.), previous=torch.zeros(2, 16),
                pd_effort=torch.zeros(2, 16), limits=torch.full((2, 16), 150.),
                leg_mask=torch.tensor([True]*12+[False]*4),
                enabled=torch.ones(2, dtype=torch.bool),
                reset=torch.zeros(2, dtype=torch.bool), dt=.02)


def test_ramp_and_wheel_exclusion():
    out = guard()(**inputs())
    assert out['valid'].all()
    torch.testing.assert_close(out['effort'][:, :12], torch.full((2, 12), .4))
    assert (out['effort'][:, 12:] == 0).all()


def test_reset_and_disabled_clear_without_slew_delay():
    args = inputs()
    args['previous'][:, :12] = 12.
    args['reset'][0] = True
    args['enabled'][1] = False
    out = guard()(**args)
    assert (out['effort'] == 0).all()
    assert not out['valid'].any()


def test_total_pd_plus_feedforward_rejected_not_clipped():
    args = inputs()
    args['pd_effort'][0, 0] = 149.9
    out = guard()(**args)
    assert not out['valid'][0] and out['valid'][1]
    assert (out['effort'][0] == 0).all()


def test_nan_and_excessive_request_fail_closed_per_row():
    args = inputs()
    args['target'][0, 0] = float('nan')
    args['target'][1, 0] = 200.
    out = guard()(**args)
    assert not out['valid'].any()
    assert (out['effort'] == 0).all()


def test_arbitrary_named_leg_order_and_previous_wheel_leak_rejected():
    args = inputs()
    args['leg_mask'] = torch.tensor([True, True, True, False]*4)
    args['previous'][0, 3] = 1.
    out = guard()(**args)
    assert not out['valid'][0] and out['valid'][1]
    assert (out['effort'][:, ~args['leg_mask']] == 0).all()


def test_new_position_target_pd_used_before_feedforward_limit_check():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_effort_guard.py'
    spec = importlib.util.spec_from_file_location('effort_guard', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'position_pd_effort'), 'fresh target PD helper missing'
    q = torch.zeros(2, 16)
    result = mod.position_pd_effort(q+.2, q, q, q+.1, q+100., q+2.)
    torch.testing.assert_close(result, q+19.8)
