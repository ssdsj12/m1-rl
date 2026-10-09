import importlib.util
from pathlib import Path
import torch


def solver():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_support_effort.py'
    assert path.exists(), 'bounded support effort solver missing'
    spec = importlib.util.spec_from_file_location('support_effort', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.vertical_support_solution


def inputs():
    jac = torch.zeros(2, 4, 3, 22)
    jac[:, :, 2, 2] = 1.
    jac[:, :, 2, 3] = torch.tensor([1., -1., 1., -1.])
    jac[:, :, 2, 4] = torch.tensor([-1., -1., 1., 1.])
    for i in range(4): jac[:, i, 2, 6+i] = .2
    gravity = torch.zeros(2, 22)
    gravity[:, 2] = 400.
    gravity[:, 6:10] = 1.
    return dict(point_jacobian=jac, gravity=gravity,
                support_mask=torch.ones(2, 4, dtype=torch.bool),
                effort_limits=torch.full((2, 16), 150.), min_force=10.)


def test_four_support_equilibrium_and_effort_sign():
    args = inputs()
    result = solver()(**args)
    assert result['valid'].all()
    torch.testing.assert_close(result['normal_force'], torch.full((2, 4), 100.))
    torch.testing.assert_close(result['effort'][:, :4], torch.full((2, 4), -19.))
    assert result['base_residual'].abs().max() < 1e-3


def test_three_support_requires_com_inside_and_zero_inactive_force():
    args = inputs()
    args['support_mask'][:, 0] = False
    args['gravity'][0, 3:5] = torch.tensor([-80., 80.])
    result = solver()(**args)
    assert result['valid'][0]
    assert not result['valid'][1]  # on triangle boundary: third load is zero
    torch.testing.assert_close(result['normal_force'][0], torch.tensor([0., 160., 160., 80.]))


def test_torque_limit_is_rejection_not_clipping():
    args = inputs()
    args['effort_limits'][0] = 5.
    result = solver()(**args)
    assert not result['valid'][0]
    assert result['valid'][1]
    assert (result['effort'][0] == 0).all()


def test_unbalanced_horizontal_wrench_and_nan_rejected_per_row():
    args = inputs()
    args['gravity'][0, 0] = 10.
    args['gravity'][1, 0] = float('nan')
    result = solver()(**args)
    assert not result['valid'].any()
    assert torch.isfinite(result['effort']).all()


def test_no_support_cannot_produce_effort_command():
    args = inputs()
    args['support_mask'][0] = False
    result = solver()(**args)
    assert not result['valid'][0]
    assert result['valid'][1]
