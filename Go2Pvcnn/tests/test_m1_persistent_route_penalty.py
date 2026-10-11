"""Authored-route costs survive scanner loss without commanding any action."""
from types import SimpleNamespace
import ast
from pathlib import Path
import pytest
import torch

from ame_baseline.m1_required_crossing import RequiredCrossingRewardGate, progressive_required_wheels


def fixture():
    course = dict(centers_top=torch.tensor([[[2.9, .215, .03], [4.7, -.215, .03]]]),
                  half_extents=torch.tensor([[[.05, .09], [.05, .09]]]),
                  valid=torch.ones(1, 2, dtype=torch.bool), ids=torch.tensor([[11, 12]]))
    required = progressive_required_wheels(course, torch.zeros(1))
    recovered = torch.zeros(1, 2, 4, dtype=torch.bool)
    wheels = torch.tensor([[[2.3, .215, .096], [2.3, -.215, .096],
                            [1.7, .215, .096], [1.7, -.215, .096]]])
    width = torch.full((1, 4), .02325)
    return RequiredCrossingRewardGate(1, 2, 'cpu'), course, required, recovered, wheels, width


def cost(gate, course, required, recovered, wheels, width, x=2.):
    gate.update(torch.tensor([[x, 0., .456]]), course, required, recovered)
    return gate.route_penalty(wheels, width, course, required, recovered)


def test_lateral_bypass_cost_survives_beyond_last_obstacle_and_retreat():
    gate, c, req, rec, wheels, width = fixture()
    wheels[..., 1] -= .4
    assert cost(gate, c, req, rec, wheels, width, x=0.).item() == 0
    for x in (2., 6., 0.):
        assert cost(gate, c, req, rec, wheels, width, x=x).item() == pytest.approx(1.)


def test_free_band_is_actual_wheel_footprint_not_twenty_two_cm_root_band():
    gate, c, req, rec, wheels, width = fixture()
    wheels[0, 0, 1] -= .06
    assert cost(gate, c, req, rec, wheels, width).item() == 0
    wheels[0, 0, 1] -= .02  # .08 offset: (.08 + .02325 - .09) / .30
    assert cost(gate, c, req, rec, wheels, width).item() == pytest.approx(.0441666667)


def test_front_receipt_does_not_release_unrecovered_rear_and_wrong_side_is_ignored():
    gate, c, req, rec, wheels, width = fixture()
    wheels[0, [0, 2], 1] -= .2
    before = cost(gate, c, req, rec, wheels, width).item()
    rec[0, 0, 0] = True
    assert cost(gate, c, req, rec, wheels, width).item() == pytest.approx(before)
    rec[0, 0, 2] = True
    wheels[0, 1, 1] = -2.  # next obstacle is not approached yet
    assert cost(gate, c, req, rec, wheels, width).item() == 0
    assert cost(gate, c, req, rec, wheels, width, x=4.).item() == 1


def test_rotation_cannot_hide_footprint_overhang_and_cost_is_max_not_sum():
    gate, c, req, rec, wheels, width = fixture()
    width[0, [0, 2]] = .12  # centered but wider than block
    assert cost(gate, c, req, rec, wheels, width).item() == pytest.approx(.1)
    wheels[0, 0, 1] = 5.
    assert cost(gate, c, req, rec, wheels, width).item() == 1


def test_actual_lift_in_lane_is_not_penalized_or_counted_as_recovery():
    gate, c, req, rec, wheels, width = fixture()
    wheels[0, 0, 2] = .5
    assert cost(gate, c, req, rec, wheels, width).item() == 0
    assert not rec.any()


def test_reset_identity_padding_and_inactive_stage_clear_obligations():
    gate, c, req, rec, wheels, width = fixture()
    wheels[..., 1] += .4
    assert cost(gate, c, req, rec, wheels, width).item() > 0
    gate.reset(torch.tensor([True]))
    assert cost(gate, c, req, rec, wheels, width, x=0.).item() == 0
    cost(gate, c, req, rec, wheels, width)
    c['ids'] += 10
    assert cost(gate, c, req, rec, wheels, width, x=0.).item() == 0
    c['valid'].zero_()
    assert cost(gate, c, req, rec, wheels, width, x=6.).item() == 0


def _reward_function():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_obstacle_rewards.py'
    fn = next(n for n in ast.parse(path.read_text()).body
              if isinstance(n, ast.FunctionDef) and n.name == 'm1_small_obstacle_corridor_penalty')
    namespace = dict(torch=torch, Tensor=torch.Tensor,
                     m1_obstacle_presence=lambda *args: (torch.zeros(3, dtype=torch.bool), torch.zeros(3, dtype=torch.bool)))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), str(path), 'exec'), namespace)
    return namespace[fn.name], namespace


def test_reward_term_consumes_snapshot_when_scan_lost_and_preserves_stage_zero_and_mixed():
    fn, namespace = _reward_function()
    class Scene(dict):
        env_origins = torch.zeros(3, 3)
    env = SimpleNamespace(scene=Scene(robot=SimpleNamespace(data=SimpleNamespace(
        root_pos_w=torch.tensor([[0., .5, .456]]).repeat(3, 1)))),
        _m1_required_route_snapshot=(torch.tensor([False, True, False]), torch.tensor([0., .8, 0.])))
    assert fn(env).tolist() == pytest.approx([0., .8, 0.])
    namespace['m1_obstacle_presence'] = lambda *args: (torch.ones(3, dtype=torch.bool), torch.zeros(3, dtype=torch.bool))
    assert fn(env).tolist() == pytest.approx([.28/.30, .8, .28/.30])
    # A terminal reset pose must not replace this pre-step penalty.
    env.scene['robot'].data.root_pos_w.zero_()
    assert fn(env)[1].item() == pytest.approx(.8)
