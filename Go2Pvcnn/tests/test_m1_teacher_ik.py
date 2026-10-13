"""CPU numerical contracts; no simulator or teacher scheduling."""
from dataclasses import replace

import pytest
import torch

from ame_baseline import m1_teacher_ik as ik
from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS
from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, m1_joint_limit_mask,
)


def nominal(batch=1, dtype=torch.float64):
    ids = [M1_ASSET_JOINT_NAMES.index(name) for name in M1_PLANNER_JOINT_NAMES]
    return torch.tensor(M1_TRAINING_JOINT_POS, dtype=dtype)[ids].repeat(batch, 1)


def solve(q, target=None, branch=None, cfg=None):
    return ik.solve_constrained_ik(q, ik.body_feet(q) if target is None else target,
                                   q if branch is None else branch, cfg or ik.IKConfig())


def test_all_four_legs_must_be_valid():
    q = nominal()
    target = ik.body_feet(q)
    target[:, 2, 2] = -2.  # Support leg unreachable, active front leg unchanged.
    result = solve(q, target)
    assert not result.valid.item()
    assert result.reason[0, 0] == ik.IKReason.OK
    assert not result.workspace_ok[0, 2]
    assert result.reason[0, 2] == ik.IKReason.WORKSPACE


def test_iterates_do_not_cross_limits_or_knee_branch(monkeypatch):
    q = nominal()
    q[:, 2] = -.12
    goal = q.clone()
    goal[:, 2] = .5
    goal[:, 3] = 1.2  # Outside right ABAD limit.
    target = ik.body_feet(goal)
    recorded = []
    original = ik.body_jacobian

    def record(current, epsilon):
        recorded.append(current.clone())
        return original(current, epsilon)

    monkeypatch.setattr(ik, 'body_jacobian', record)
    result = solve(q, target)
    recorded.append(result.q)
    previous = q
    for current in recorded:
        assert m1_joint_limit_mask(current).all()
        assert (current[:, 2::3] * q[:, 2::3] > 0).all()
        assert (current[:, 2::3].abs() >= .10).all()
        assert ((current - previous).abs() <= .25 + 1e-12).all()
        assert ((target - ik.body_feet(current)).norm(dim=-1)
                <= (target - ik.body_feet(previous)).norm(dim=-1) + 1e-12).all()
        previous = current


@pytest.mark.parametrize('knee,valid', [(.099, False), (.100, True), (-.099, False), (-.100, True)])
def test_near_straight_is_rejected_at_point_one(knee, valid):
    q = nominal()
    q[:, 2] = knee
    result = solve(q)
    assert result.valid.item() is valid
    assert result.reason[0, 0] == (ik.IKReason.OK if valid else ik.IKReason.NEAR_STRAIGHT)
    assert result.extension_margin_rad[0, 0].item() == pytest.approx(abs(knee) - .10)


def test_residual_and_budget_are_not_relaxed():
    q = nominal(2)
    target = ik.body_feet(q)
    target[0, :, 2] += .02
    # Geometrically possible but deliberately extreme within the true workspace.
    goal = nominal()[0].clone()
    goal[1] = 2.4
    target[1, 0] = ik.body_feet(goal[None])[0, 0]
    result = solve(q, target)
    assert result.valid[0], result
    assert not result.valid[1]
    assert result.reason[1, 0] == ik.IKReason.RESIDUAL
    assert result.residual_m[1, 0] > .002
    assert result.iterations[1, 0] == 32
    assert (result.residual_m[result.valid] <= .002).all()
    assert (result.iterations <= 32).all()
    assert ik.IKConfig().ik_iterations == 32
    assert ik.IKConfig().ik_tolerance_m == .002


def test_monotonic_solver_can_reject_workspace_reachable_target():
    q = nominal()
    target = ik.body_feet(q)
    target[..., 2] += .07
    result = solve(q, target)
    # Component clipping makes this initial DLS step increase the error;
    # workspace reachability alone cannot authorize accepting it.
    assert result.workspace_ok.all()
    assert not result.valid.any()
    assert torch.equal(result.q, q)
    assert (result.reason == ik.IKReason.RESIDUAL).all()
    assert (result.iterations == 32).all()


def test_fk_offsets_not_root_radius_shortcut():
    q = nominal()
    q[:, 1::3] = 0
    q[:, 2::3] = torch.tensor([-.10, -.10, .10, .10])
    target = ik.body_feet(q)
    assert (target.norm(dim=-1) > .54).all()
    result = solve(q, target)
    assert result.workspace_ok.all()
    assert result.valid.all()


def test_nan_row_does_not_poison_batch():
    q = nominal(3)
    target = ik.body_feet(q)
    target[:, :, 2] += .04
    target[1, 0, 0] = float('nan')
    q[2, 7] = float('nan')
    result = solve(q, target)
    assert result.valid.tolist() == [True, False, False]
    assert result.reason[1, 0] == ik.IKReason.NONFINITE
    assert result.reason[2, 2] == ik.IKReason.NONFINITE
    assert torch.isfinite(result.q).all()
    clean = solve(nominal(), target[:1])
    assert torch.equal(result.q[:1], clean.q)


def test_jacobian_matches_autograd():
    q = nominal()[0].requires_grad_()
    exact = torch.autograd.functional.jacobian(lambda a: ik.body_feet(a[None])[0], q)
    measured = ik.body_jacobian(q[None])[0]
    for leg in range(4):
        assert torch.allclose(measured[leg], exact[leg, :, 3*leg:3*leg+3], atol=1e-8)


def test_config_cannot_relax_approved_bounds():
    for kwargs in ({'ik_iterations': 33}, {'ik_tolerance_m': .0021},
                   {'dq_component_limit_rad': .26}, {'min_knee_abs_rad': .099}):
        with pytest.raises(ValueError):
            replace(ik.IKConfig(), **kwargs)


def test_accepted_steps_move_and_strictly_reduce_error(monkeypatch):
    q = nominal()
    target = ik.body_feet(q)
    target[..., 2] += .02
    recorded = [q.clone()]
    original = ik.body_jacobian

    def record(current, epsilon):
        recorded.append(current.clone())
        return original(current, epsilon)

    monkeypatch.setattr(ik, 'body_jacobian', record)
    result = solve(q, target)
    assert result.valid.all()
    assert not torch.equal(result.q, q)
    recorded.append(result.q)
    for before, after in zip(recorded, recorded[1:]):
        changed = (before.reshape(1, 4, 3) != after.reshape(1, 4, 3)).any(-1)
        before_error = (target - ik.body_feet(before)).norm(dim=-1)
        after_error = (target - ik.body_feet(after)).norm(dim=-1)
        assert (after_error[changed] < before_error[changed]).all()
        assert ((after - before).abs() <= .25).all()


@pytest.mark.parametrize('bad', ['limit', 'branch', 'straight', 'nonfinite', 'no_improvement'])
def test_rejected_proposals_hold_pre_iteration_joints(monkeypatch, bad):
    q = nominal()
    q[:, 2] = -.12
    target = ik.body_feet(q)
    target[:, 0, 2] += .02

    def proposal(jacobian, error, damping, component_limit):
        step = torch.zeros_like(error)
        if bad == 'limit':
            # Seed already at limit: any positive step must be refused.
            step[:, 0, 0] = .1
        elif bad == 'branch':
            step[:, 0, 2] = .25
        elif bad == 'straight':
            step[:, 0, 2] = .03
        elif bad == 'nonfinite':
            step[:, 0, 1] = float('nan')
        return step

    if bad == 'limit':
        q[:, 0] = .697
        target = ik.body_feet(q)
        target[:, 0, 2] += .02
    monkeypatch.setattr(ik, 'dls_step', proposal)
    result = solve(q, target)
    assert torch.equal(result.q, q)
    assert result.iterations[0, 0] == 32
    assert not result.valid[0]
    assert result.reason[0, 0] == ik.IKReason.RESIDUAL


@pytest.mark.parametrize('bad,reason', [('limit', ik.IKReason.JOINT_LIMIT),
                                     ('branch', ik.IKReason.BRANCH),
                                     ('nonfinite_branch', ik.IKReason.NONFINITE)])
def test_invalid_seed_or_branch_is_not_repaired(bad, reason):
    q = nominal()
    branch = q.clone()
    if bad == 'limit':
        q[:, 3] = .524
    elif bad == 'branch':
        branch[:, 5] *= -1
    else:
        branch[:, 4] = float('nan')
    result = solve(q, branch=branch)
    assert result.reason[0, 1] == reason
    assert not result.valid[0]
    assert not result.iterations.any()
    assert torch.equal(result.q, q)


def test_workspace_rejects_inner_hole_and_excess_planar_reach():
    q = nominal(2)
    target = ik.body_feet(q)
    # Actual front-left ABAD mount is (.272,.065,0); lateral sum is .1424.
    target[0, 0] = torch.tensor([.3295, .065, -.05], dtype=q.dtype)
    # Account for mounting offsets, then ask for .55m planar extension.
    target[1, 0] = torch.tensor([.3295, .2074, -.55], dtype=q.dtype)
    result = solve(q, target)
    assert not result.workspace_ok[:, 0].any()
    assert (result.reason[:, 0] == ik.IKReason.WORKSPACE).all()
    assert not result.iterations.any()


def test_geometry_exports_and_result_shapes_remain_compatible():
    from ame_baseline import m1_reference_teacher as old
    assert old.body_feet is ik.body_feet
    assert old.body_jacobian is ik.body_jacobian
    assert old.dls_step is ik.dls_step
    result = solve(nominal(2, torch.float32))
    assert result.valid.all()
    assert result.q.shape == (2, 12)
    assert result.valid.dtype == torch.bool
    for name in ('residual_m', 'joint_limit_ok', 'branch_ok', 'extension_margin_rad',
                 'workspace_ok', 'iterations', 'reason'):
        assert getattr(result, name).shape == (2, 4)
    assert result.reason.dtype == result.iterations.dtype == torch.long


@pytest.mark.parametrize('field,value', [('damping', float('nan')), ('fd_epsilon', 0),
                                       ('ik_iterations', 1.5), ('ik_iterations', True)])
def test_invalid_numeric_configuration_is_rejected(field, value):
    with pytest.raises(ValueError):
        replace(ik.IKConfig(), **{field: value})


def test_stricter_guard_keeps_margin_at_spec_boundary():
    q = nominal()
    q[:, 2] = -.15
    result = solve(q, cfg=replace(ik.IKConfig(), min_knee_abs_rad=.20))
    assert result.extension_margin_rad[0, 0].item() == pytest.approx(.05)
    assert result.reason[0, 0] == ik.IKReason.NEAR_STRAIGHT
