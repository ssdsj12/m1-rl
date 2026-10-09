from types import SimpleNamespace
import torch
import pytest
from extension.parallelism.kinematics import rpy_to_rotation_matrix
from extension.batch_mpc_planner.adapter import mpc_result_to_reference_cache, standstill_cache_from_state


@pytest.mark.parametrize('standstill', [False, True])
def test_training_reference_foot_is_in_body_axes(standstill):
    root = torch.tensor([[2., 3., .5]])
    rpy = torch.tensor([[.1, -.2, .7]])
    body = torch.tensor([[[.3,.2,-.4],[.3,-.2,-.4],[-.3,.2,-.4],[-.3,-.2,-.4]]])
    rot = rpy_to_rotation_matrix(rpy)
    world = root[:, None] + torch.einsum('bij,blj->bli', rot, body)
    state = SimpleNamespace(root_pos=root, root_rpy=rpy, foot_pos=world, joint_angles=torch.zeros(1,12))
    if standstill:
        cache = standstill_cache_from_state(state, horizon=2)
    else:
        result = SimpleNamespace(**{k:v[:,None].expand(-1,2,*v.shape[1:]) for k,v in vars(state).items()})
        result.contact_state = torch.ones(1,2,4,dtype=torch.bool)
        result.planned_touchdown_w = result.foot_pos
        cache = mpc_result_to_reference_cache(result)
    torch.testing.assert_close(cache.foot_pos_root, body[:,None].expand(-1,2,-1,-1))
