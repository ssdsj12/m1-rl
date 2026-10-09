import ast
from pathlib import Path
from types import SimpleNamespace
import torch
import pytest


@pytest.mark.parametrize('rpy', [[0.,0.,0.], [0.,0.,1.57079632679], [.1,-.2,.7]])
def test_root_foot_target_roundtrips_world_coordinates(rpy):
    from extension.parallelism.m1_kinematics import rpy_to_rotation_matrix
    path = Path(__file__).with_name('viewer_adapter.py')
    if not path.exists():
        path = Path(__file__).resolve().parents[1] / 'extension/parallelism/viewer_adapter.py'
    tree = ast.parse(path.read_text())
    expr = next(n.value for n in ast.walk(tree) if isinstance(n, ast.keyword) and n.arg == 'foot_pos_root')
    rotation_rpy = torch.tensor([[rpy]])
    root = torch.tensor([[[2.,3.,.5]]])
    body = torch.tensor([[[[.3,.2,-.4],[.3,-.2,-.4],[-.3,.2,-.4],[-.3,-.2,-.4]]]])
    rot = rpy_to_rotation_matrix(rotation_rpy)
    world = root.unsqueeze(-2) + torch.einsum('...ij,...lj->...li', rot, body)
    trajectory = SimpleNamespace(root_pos_w=root, root_rpy_w=rotation_rpy, foot_pos_w=world)
    actual = eval(compile(ast.Expression(expr), '<frame>', 'eval'),
                  dict(torch=torch, trajectory=trajectory, rpy_to_rotation_matrix=rpy_to_rotation_matrix))
    assert torch.allclose(actual, body, atol=1e-6)

    # Exercise the complete adapter too, including its real imports and M1 FK.
    from extension.parallelism.viewer_adapter import parallelism_trajectory_to_viewer_result
    from extension.parallelism.robot_backend import get_robot_backend
    trajectory.joint_pos = torch.zeros(1, 1, 12)
    trajectory.contact_state = torch.ones(1, 1, 4, dtype=torch.bool)
    trajectory.selected_foothold_w = world[:, 0]
    trajectory.valid = torch.ones(1, dtype=torch.bool)
    trajectory.diagnostics = SimpleNamespace(candidate_center_w=world[:, 0], candidate_radius_m=.4)
    result = parallelism_trajectory_to_viewer_result(trajectory, get_robot_backend('m1'))
    torch.testing.assert_close(result.foot_pos_root, body, atol=1e-6, rtol=0.)
