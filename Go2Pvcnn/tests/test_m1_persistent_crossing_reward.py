"""Required-route rewards cannot be recovered by bypass or retreat."""
import torch
import pytest
import ast
from pathlib import Path
from types import SimpleNamespace
from ame_baseline import m1_required_crossing as reward_module


def course():
    return dict(centers_top=torch.tensor([[[2.9, .215, .03], [4.7, -.215, .03]]]),
                half_extents=torch.tensor([[[.05, .09], [.05, .09]]]),
                valid=torch.ones(1, 2, dtype=torch.bool), ids=torch.tensor([[11, 12]]))


def mask(c):
    return reward_module.progressive_required_wheels(c, torch.zeros(1))


def test_required_wheels_follow_authored_tracks_not_policy_drift():
    c = course()
    assert mask(c).tolist() == [[[True, False, True, False], [False, True, False, True]]]
    c['centers_top'][:, :, 1] += 120.
    assert torch.equal(reward_module.progressive_required_wheels(c, torch.tensor([120.])), mask(course()))


def test_valid_obstacle_without_required_track_is_rejected_not_auto_complete():
    c = course(); c['centers_top'][0, 0, 1] = 2.
    with pytest.raises(ValueError, match='wheel track'):
        mask(c)


def test_unrecovered_bypass_stays_blocked_after_final_slab_and_retreat():
    gate = reward_module.RequiredCrossingRewardGate(1, 2, 'cpu')
    c = course(); receipts = torch.zeros(1, 2, 4, dtype=torch.bool)
    for x, blocked in ((0., False), (2., True), (6., True), (1., True)):
        assert gate.update(torch.tensor([[x, -1., .537]]), c, mask(c), receipts).item() == blocked


def test_both_required_wheels_and_every_started_obstacle_must_recover():
    gate = reward_module.RequiredCrossingRewardGate(1, 2, 'cpu')
    c = course(); receipts = torch.zeros(1, 2, 4, dtype=torch.bool)
    pos = torch.tensor([[3., .0, .45]])
    assert gate.update(pos, c, mask(c), receipts).item()
    receipts[0, 0, 0] = True
    assert gate.update(pos, c, mask(c), receipts).item()
    receipts[0, 0, 2] = True
    assert not gate.update(pos, c, mask(c), receipts).item()  # next block not reached
    pos[:, 0] = 6.
    assert gate.update(pos, c, mask(c), receipts).item()
    receipts[0, 1, [1, 3]] = True
    assert not gate.update(pos, c, mask(c), receipts).item()


def test_attempts_wrong_wheels_and_one_obstacle_cannot_unlock_another():
    gate = reward_module.RequiredCrossingRewardGate(1, 2, 'cpu')
    c = course(); receipts = torch.zeros(1, 2, 4, dtype=torch.bool)
    receipts[0, 0, [1, 3]] = True
    receipts[0, 1] = True
    assert gate.update(torch.tensor([[6., 0., .45]]), c, mask(c), receipts).item()


def test_episode_reset_and_course_identity_clear_started_latches():
    gate = reward_module.RequiredCrossingRewardGate(1, 2, 'cpu')
    c = course(); receipts = torch.zeros(1, 2, 4, dtype=torch.bool)
    assert gate.update(torch.tensor([[6., 0., .45]]), c, mask(c), receipts).item()
    gate.reset(torch.tensor([True]))
    assert not gate.update(torch.tensor([[0., 0., .45]]), c, mask(c), receipts).item()
    gate.update(torch.tensor([[6., 0., .45]]), c, mask(c), receipts)
    c['ids'] += 30
    assert not gate.update(torch.tensor([[0., 0., .45]]), c, mask(c), receipts).item()


def test_padding_and_inactive_stage_cannot_create_obligations():
    gate = reward_module.RequiredCrossingRewardGate(1, 2, 'cpu')
    c = course(); c['valid'].zero_()
    assert not gate.update(torch.tensor([[6., 0., .45]]), c, mask(c), torch.zeros(1, 2, 4, dtype=torch.bool)).item()


def test_full_height_increment_is_not_clipped_back_to_two_centimeters():
    z = torch.zeros(1); no = torch.zeros(1, dtype=torch.bool)
    _, _, bonus = reward_module.required_crossing_reward(z, z[:, None], .02,
        blocked=~no, collision=no, done=no, prelift=no, recovery=no,
        prelift_progress_delta=torch.tensor([2.]))
    assert bonus.item() == pytest.approx(.6)


def _wrapper_blocks():
    source = Path(__file__).parents[1] / 'ame_baseline/ame_env_wrapper.py'
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'AmeRslRlEnvWrapper')
    step = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'step')
    start = next(i for i, n in enumerate(step.body) if isinstance(n, ast.ImportFrom)
                 and n.module == 'm1_required_crossing')
    end = next(i for i, n in enumerate(step.body) if isinstance(n, ast.Assign)
               and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
               and n.value.func.attr == 'step')
    resets = [n for n in step.body if isinstance(n, ast.If)
              and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                      and call.func.attr == 'reset' and isinstance(call.func.value, ast.Attribute)
                      and call.func.value.attr == '_m1_required_gate' for call in ast.walk(n))]
    assert len(resets) == 1
    def execute(nodes, scope):
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(source), 'exec'), scope)
    return lambda scope: execute(step.body[start:end], scope), lambda scope: execute(resets, scope)


def test_actual_wrapper_pre_step_gate_keeps_failed_bypass_blocked():
    pre_step, _ = _wrapper_blocks()
    c = course(); receipt = torch.zeros(1, 2, 4, dtype=torch.bool)
    class Scene(dict):
        env_origins = torch.zeros(1, 3)
        terrain = SimpleNamespace(terrain_levels=torch.ones(1, dtype=torch.long))
    scene = Scene(robot=SimpleNamespace(data=SimpleNamespace(root_pos_w=torch.tensor([[6., -1., .537]]))))
    gate = reward_module.RequiredCrossingRewardGate(1, 2, 'cpu')
    wrapper = SimpleNamespace(num_envs=1, device='cpu',
        unwrapped=SimpleNamespace(cfg=SimpleNamespace(m1_flat_first=True), scene=scene),
        _m1_current_course=lambda: c, _m1_required_gate=gate,
        _m1_strict_crossing=SimpleNamespace(recovered_for_course=lambda _: receipt))
    scope = dict(self=wrapper, torch=torch, __package__='ame_baseline')
    pre_step(scope)
    assert scope['required_zone'].item(), 'actual wrapper must consume strict receipts after the slab'


def test_wrapper_mixed_stages_terminal_snapshot_and_next_episode_do_not_leak():
    pre_step, terminal_reset = _wrapper_blocks()
    registry = {k: v.repeat(3, *([1]*(v.ndim-1))) for k, v in course().items()}
    receipt = torch.zeros(3, 2, 4, dtype=torch.bool)
    class Scene(dict):
        env_origins = torch.zeros(3, 3)
        terrain = SimpleNamespace(terrain_levels=torch.tensor([0, 1, 4]))
    roots = torch.tensor([[6., -1., .537]]).repeat(3, 1)
    scene = Scene(robot=SimpleNamespace(data=SimpleNamespace(root_pos_w=roots)))
    gate = reward_module.RequiredCrossingRewardGate(3, 2, 'cpu')
    wrapper = SimpleNamespace(num_envs=3, device='cpu',
        unwrapped=SimpleNamespace(cfg=SimpleNamespace(m1_flat_first=True), scene=scene),
        _m1_current_course=lambda: {k: v.clone() for k, v in registry.items()},
        _m1_required_gate=gate, _m1_strict_crossing=SimpleNamespace(recovered_for_course=lambda _: receipt))
    scope = dict(self=wrapper, torch=torch, __package__='ame_baseline')
    pre_step(scope)
    snapshot = scope['required_zone']
    assert snapshot.tolist() == [False, True, False]
    assert registry['valid'].all()  # stage masking must not alter the registry
    # Isaac auto-reset happens between the snapshot and reward calculation.
    roots[:, 0] = 0.
    scope['done'] = torch.tensor([False, True, False])
    terminal_reset(scope)
    assert snapshot.tolist() == [False, True, False]
    pre_step(scope)
    assert not scope['required_zone'].any()
    roots[:, 0] = 6.
    pre_step(scope)
    assert scope['required_zone'].tolist() == [False, True, False]
