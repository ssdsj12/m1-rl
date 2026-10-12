"""Real FK and semantic terrain tests for the user-approved fresh-training contract."""
from types import SimpleNamespace
from pathlib import Path
import torch
import pytest
from ame_baseline import m1_ame_contract as contract
from ame_baseline import m1_ame_terminations as terms
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, m1_fk
from extension.parallelism.rl_adapter import select_named_joint_state


def test_front_and_rear_knees_fold_inward_not_in_the_same_direction():
    q = torch.tensor(contract.M1_TRAINING_JOINT_POS)[None]
    legs = select_named_joint_state(q, source_names=M1_ASSET_JOINT_NAMES, selected_names=M1_PLANNER_JOINT_NAMES)
    geometry = m1_fk(torch.tensor([[0., 0., contract.M1_TRAINING_ROOT_Z_M]]), torch.zeros(1, 3), legs)
    dx = geometry.knee_pos_w[0, :, 0] - geometry.hip_pos_w[0, :, 0]
    assert (dx[:2] < -.05).all(), dx
    assert (dx[2:] > .05).all(), dx


def _env():
    # Only front-left wheel column has terrain: ordinary ground, small top
    # contact, wheel-side overlap, 1cm air gap, body-height obstacle, unknown.
    count, side, res = 6, 201, .01
    axis = torch.arange(side) * res - 1.
    yy, xx = torch.meshgrid(axis, axis, indexing='ij')
    hits = torch.stack((xx, yy, torch.zeros_like(xx)), -1)[None].repeat(count, 1, 1, 1)
    semantic = torch.zeros(count, side, side, dtype=torch.long)
    mask = ((xx - .3295).abs() < .075) & ((yy - .2074).abs() < .06)
    for row in (1, 2, 3, 4, 5):
        hits[row, :, :, 2][mask] = .03 if row != 4 else .8
        semantic[row, mask] = 1 if row != 4 else 2
    valid = torch.ones_like(semantic, dtype=torch.bool)
    valid[5] = False
    root = torch.tensor([[0., 0., contract.M1_TRAINING_ROOT_Z_M]]).repeat(count, 1)
    root[1, 2] += .029  # small top contact, no legacy support exemption allowed
    root[3, 2] += .04  # only 1cm gap, not strict-success 3cm, yet NOT collision
    data = SimpleNamespace(root_pos_w=root, root_quat_w=torch.tensor([[1.,0.,0.,0.]]).repeat(count,1),
                           joint_pos=torch.tensor(contract.M1_TRAINING_JOINT_POS)[None].repeat(count,1))
    scanner = SimpleNamespace(cfg=SimpleNamespace(pattern_cfg=SimpleNamespace(resolution=res)),
                              data=SimpleNamespace(ray_hits_w=hits.reshape(count,-1,3), semantic_map=semantic, valid_mask=valid))
    return SimpleNamespace(device='cpu', scene={'robot':SimpleNamespace(data=data,joint_names=M1_ASSET_JOINT_NAMES),
                                                'semantic_height_scanner':scanner})


def test_collision_terminates_only_hit_rows_without_ground_or_clearance_false_positive():
    assert hasattr(terms, 'obstacle_collision'), 'missing current-step obstacle termination'
    result = terms.obstacle_collision(_env())
    assert result.dtype == torch.bool
    assert result.tolist() == [False, True, True, False, True, False]


def test_obstacle_termination_is_wired_as_physical_failure_not_timeout():
    source = (Path(__file__).parents[1]/'ame_baseline/m1_ame_env_cfg.py').read_text()
    assert 'func=obstacle_collision' in source


def test_new_stance_contract_rejects_missing_or_old_metadata():
    assert hasattr(contract, 'm1_training_contract'), 'missing versioned pose/reset contract'
    assert hasattr(contract, 'validate_training_contract')
    expected = contract.m1_training_contract()
    assert expected['obstacle_collision_reset'] is True
    contract.validate_training_contract({'m1_training_contract':expected}, expected)
    with pytest.raises(ValueError, match='training contract'):
        contract.validate_training_contract({}, expected)
    stale = dict(expected, joint_pos=[0.] * 16)
    with pytest.raises(ValueError, match='training contract'):
        contract.validate_training_contract({'m1_training_contract':stale}, expected)


def test_runtime_runner_and_evaluation_validate_pose_contract_before_loading():
    root = Path(__file__).parents[1]
    runner = (root/'ame_baseline/ame_runner.py').read_text()
    evaluation = (root/'scripts/evaluate_m1_ame.py').read_text()
    assert 'validate_training_contract(checkpoint' in runner
    assert "checkpoint['m1_training_contract']" in runner
    assert 'validate_training_contract(checkpoint' in evaluation


def test_runner_rejects_old_pose_before_changing_model_or_optimizer(tmp_path):
    from copy import deepcopy
    from ame_baseline.ame_runner import AmeOnPolicyRunner
    from ame_baseline.actor_critic_ame import ActorCriticAME
    actor = ActorCriticAME(1589,1592,12,actor_hidden_dims=(8,),critic_hidden_dims=(8,))
    runner = object.__new__(AmeOnPolicyRunner)
    runner.device = 'cpu'
    runner.alg = SimpleNamespace(actor_critic=actor,optimizer=torch.optim.Adam(actor.parameters()))
    runner.env = SimpleNamespace(unwrapped=SimpleNamespace(cfg=SimpleNamespace(
        m1_training_contract=contract.m1_training_contract(),m1_fixed_wheel_speed_m_s=.3)))
    before = deepcopy(actor.state_dict())
    old = tmp_path/'old.pt'
    torch.save({}, old)
    with pytest.raises(ValueError,match='training contract'):
        runner.load(old)
    for key,value in before.items():
        torch.testing.assert_close(actor.state_dict()[key],value)
    assert not runner.alg.optimizer.state
