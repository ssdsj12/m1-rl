from types import SimpleNamespace
from pathlib import Path
import torch
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES, M1_WHEEL_RADIUS_M


def test_m1_actor_sees_all_action_channels_including_wheel_commands():
    from ame_baseline import m1_ame_contract as contract
    assert hasattr(contract, 'm1_last_action'), 'M1 actor is missing four wheel action channels'
    a = torch.arange(16.).reshape(1, 16)
    env = SimpleNamespace(cfg=SimpleNamespace(asset_joint_names=M1_ASSET_JOINT_NAMES), action_manager=SimpleNamespace(action=a))
    torch.testing.assert_close(contract.m1_last_action(env), a)


def test_wheel_surface_velocity_is_named_and_independent_of_wrapped_angle():
    from ame_baseline import m1_ame_contract as contract
    assert hasattr(contract, 'm1_wheel_surface_velocity'), 'M1 actor cannot observe wheel speed'
    names = tuple(reversed(M1_ASSET_JOINT_NAMES))
    velocity = torch.arange(16.).reshape(1, 16)
    robot = SimpleNamespace(joint_names=names, data=SimpleNamespace(joint_vel=velocity))
    env = SimpleNamespace(scene={'robot': robot})
    expected = velocity[:, [names.index(n) for n in M1_WHEEL_JOINT_NAMES]] * M1_WHEEL_RADIUS_M
    torch.testing.assert_close(contract.m1_wheel_surface_velocity(env), expected)


def test_production_policy_group_has_wheel_velocity_and_full_action_history():
    import ast
    path = Path(__file__).parents[1] / 'ame_baseline/m1_ame_env_cfg.py'
    tree = ast.parse(path.read_text())
    cfg = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'M1AmeObservationsCfg')
    policy = next(n for n in cfg.body if isinstance(n, ast.ClassDef) and n.name == 'PolicyStateCfg')
    terms = {n.targets[0].id: n.value for n in policy.body if isinstance(n, ast.Assign)}
    assert 'wheel_vel' in terms
    actions_func = next(k.value for k in terms['actions'].keywords if k.arg == 'func')
    assert actions_func.id == 'm1_last_action'
