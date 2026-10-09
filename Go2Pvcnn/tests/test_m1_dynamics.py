import importlib.util
from pathlib import Path
import pytest
import torch


def converter():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_dynamics.py'
    assert path.exists(), 'verified point Jacobian conversion missing'
    spec = importlib.util.spec_from_file_location('m1_dynamics', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.point_linear_jacobian


def test_translation_and_rotation_at_offset_point():
    jac = torch.zeros(2, 4, 6, 22)
    jac[:, :, :3, :3] = torch.eye(3)
    jac[:, :, 5, 6] = 1.
    com = torch.zeros(2, 4, 3)
    point = com.clone()
    point[..., 0] = 1.
    result = converter()(jac, com, point)
    torch.testing.assert_close(result[..., :3], jac[:, :, :3, :3])
    torch.testing.assert_close(result[..., 6], torch.tensor([0., 1., 0.]).expand(2, 4, 3))


def test_same_point_is_identity_and_translation_invariant():
    jac = torch.randn(2, 4, 6, 22)
    com = torch.randn(2, 4, 3)
    fn = converter()
    torch.testing.assert_close(fn(jac, com, com), jac[:, :, :3])
    point = com + .1
    torch.testing.assert_close(fn(jac, com, point), fn(jac, com+10., point+10.), atol=2e-6, rtol=1e-4)


def test_missing_or_malformed_geometry_is_not_silently_broadcast():
    fn = converter()
    jac = torch.zeros(2, 4, 6, 22)
    com = torch.zeros(2, 4, 3)
    with pytest.raises(ValueError):
        fn(jac, com[:, :1], com)
    com[0, 0, 0] = float('nan')
    with pytest.raises(ValueError):
        fn(jac, com, com)
