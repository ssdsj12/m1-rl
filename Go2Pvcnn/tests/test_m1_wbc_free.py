import ast
import importlib.util
from pathlib import Path
import pytest
import torch


def residual_fn():
    path = Path(__file__).parents[1]/'ame_baseline/m1_wbc_dynamics.py'
    spec = importlib.util.spec_from_file_location('dynamics', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert hasattr(m, 'free_dynamics_residual'), 'free-body residual missing'
    return m.free_dynamics_residual


def test_exact_inverse_dynamics_residual():
    fn = residual_fn()
    matrix = torch.eye(22, dtype=torch.float64)[None]*2
    bias = torch.arange(22, dtype=torch.float64)[None]/20
    tau = torch.ones(1, 16, dtype=torch.float64)*.01
    force = torch.cat((torch.zeros(1, 6, dtype=torch.float64), tau), dim=1)
    v0 = torch.zeros(1, 22, dtype=torch.float64)
    v1 = (force-bias)*.001/2
    torch.testing.assert_close(fn(matrix, bias, v0, v1, tau, .001), torch.zeros_like(v0))
    with pytest.raises(ValueError):
        fn(matrix, bias, v0, v1, tau, 0.)
    with pytest.raises(ValueError):
        fn(matrix, bias, v0[:, :16], v1, tau, .001)


def test_diagnostic_is_separate_bounded_and_zero_drive():
    path = Path(__file__).parents[1]/'scripts/probe_m1_wbc_free.py'
    assert path.exists(), 'isolated free-body probe missing'
    source = path.read_text()
    ast.parse(source)
    for statement in ('actuator.stiffness = 0.', 'actuator.damping = 0.',
                      'root[:, 2] = 2.', 'for sign in (0., 1., -1.):',
                      'get_dof_stiffnesses()', 'get_dof_dampings()',
                      'get_dof_actuation_forces()', 'free_dynamics_residual('):
        assert statement in source
    assert 'env.step(' not in source and 'train(' not in source


def test_kinematic_oracle_is_opt_in_and_compares_native_link_acceleration():
    source = (Path(__file__).parents[1]/'scripts/probe_m1_wbc_free.py').read_text()
    for statement in ("'--kinematic_bias'", 'if args.kinematic_bias:',
                      'kinematic_bias(', 'body_com_vel_w.clone()',
                      'get_jacobians()', 'kinematic_error', 'M1_KINEMATIC_SAMPLE'):
        assert statement in source, f'missing independent native acceleration oracle: {statement}'
