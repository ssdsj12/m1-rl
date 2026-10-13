"""CPU world references; independent geometry and real four-leg IK."""
from dataclasses import fields
import importlib
import importlib.util
import math

import pytest
import torch
from ame_baseline import m1_teacher_ik as ik


@pytest.fixture
def pose():
    assert importlib.util.find_spec('ame_baseline.m1_teacher_pose') is not None, 'new pure pose API is absent'
    return importlib.import_module('ame_baseline.m1_teacher_pose')


def nominal(batch=1, dtype=torch.float64):
    return torch.tensor([[0., .3, -.6, 0., .3, -.6, 0., -.3, .6, 0., -.3, .6]], dtype=dtype).repeat(batch, 1)


def quat(r=0., p=0., y=0., dtype=torch.float64):
    cr, sr, cp, sp, cy, sy = math.cos(r/2), math.sin(r/2), math.cos(p/2), math.sin(p/2), math.cos(y/2), math.sin(y/2)
    return torch.tensor([[cr*cp*cy+sr*sp*sy, sr*cp*cy-cr*sp*sy,
                          cr*sp*cy+sr*cp*sy, cr*cp*sy-sr*sp*cy]], dtype=dtype)


def rotation(r, p, y, dtype=torch.float64):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return torch.tensor([[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
                         [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr],
                         [-sp, cp*sr, cp*cr]], dtype=dtype)


def setup(pose, batch=1, dtype=torch.float64):
    q = nominal(batch, dtype)
    body = pose.BodyPose(q.new_tensor([[0., 0., .62]]).repeat(batch, 1), quat(dtype=dtype).repeat(batch, 1))
    return q, body, pose.PoseReference(body, ik.body_feet(q)+body.pos_w[:, None])


def search(pose, body, ref, q, com=None, accepted=None, nominal_z=None):
    return pose.choose_support_pose(body, body, body if accepted is None else accepted,
        ref.wheels_w[:, 1:].mean(1) if com is None else com, ref.wheels_w,
        torch.zeros(q.shape[0], dtype=torch.long), body.pos_w[:, 2] if nominal_z is None else nominal_z,
        q, q, ik.IKConfig())


def test_full_world_body_transform_with_roll_pitch_yaw(pose):
    q, r, p, y = nominal(), .13, -.11, .71
    pos, local, rot = q.new_tensor([[1., 2., .62]]), ik.body_feet(q), rotation(r, p, y)
    world = local @ rot.T+pos[:, None]
    body = pose.BodyPose(pos, quat(r, p, y))
    assert torch.allclose(pose.world_to_goal_body(pose.PoseReference(body, world)), local, atol=1e-12)
    delta = q.new_tensor([[-.04, -.06, 0.]]) @ rotation(0., 0., y).T
    goal = pose.PoseReference(pose.BodyPose(pos+delta, body.quat_w), world)
    target = pose.world_to_goal_body(goal)
    assert torch.allclose(target @ rot.T+goal.body.pos_w[:, None], world, atol=1e-12)
    assert not torch.allclose(target, local-q.new_tensor([[[-.04, -.06, 0.]]]), atol=1e-4)


def record_solver(pose, monkeypatch):
    recorded, original = [], pose.solve_constrained_ik
    def record(seed, target, branch, cfg):
        result = original(seed, target, branch, cfg)
        recorded.append((target.clone(), result))
        return result
    monkeypatch.setattr(pose, 'solve_constrained_ik', record)
    return recorded


def test_origin_relative_height_floor(pose, monkeypatch):
    q, body, _ = setup(pose, 2)
    body.pos_w[:, 2] = q.new_tensor([.60, 7.60])
    ref = pose.PoseReference(body, ik.body_feet(q)+body.pos_w[:, None])
    recorded = record_solver(pose, monkeypatch)
    result = search(pose, body, ref, q, nominal_z=q.new_tensor([.62, 7.62]))
    assert result.valid.all() and result.candidate_count.tolist() == [101, 101]
    target = recorded[0][0].reshape(2, 126, 4, 3)
    finite = torch.isfinite(target).all(dim=(-1, -2))
    assert torch.equal(finite[0], finite[1])
    assert torch.allclose(target[0, finite[0]], target[1, finite[1]], atol=1e-12)


def test_triangle_degenerate_and_com_margin(pose):
    wheel = torch.tensor([[[9., 9., 0.], [0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]], dtype=torch.float64).repeat(5, 1, 1)
    com = wheel.new_tensor([[.01, .2, .4], [0., .2, .4], [-.02, .2, .4], [.2, .2, .4], [.2, .2, .4]])
    wheel[3, 3] = wheel.new_tensor([2., 0., 0.])
    wheel[4, [2, 3]] = wheel[4, [3, 2]]
    margin, valid = pose.support_margin(com, wheel, torch.zeros(5, dtype=torch.long))
    assert valid.tolist() == [True, True, True, False, True]
    assert torch.allclose(margin[[0, 1, 2, 4]], wheel.new_tensor([.01, 0., -.02, .2]), atol=1e-12)
    assert torch.isnan(margin[3])


def test_search_envelope_and_stable_tie_order(pose, monkeypatch):
    q, body, _ = setup(pose)
    y = .83
    body = pose.BodyPose(body.pos_w, quat(.12, -.08, y))
    accepted = pose.BodyPose(body.pos_w.clone(), quat(0., 0., y))
    wheels = ik.body_feet(q) @ rotation(0., 0., y).T+body.pos_w[:, None]
    ref = pose.PoseReference(body, wheels)
    com = ik.body_feet(q)[:, 1:].mean(1) @ rotation(.12, -.08, y).T+body.pos_w
    recorded = record_solver(pose, monkeypatch)
    result = search(pose, body, ref, q, com=com, accepted=accepted)
    assert result.valid.item() and result.candidate_count.item() == 126
    assert result.candidate_index.item() == 60  # x=0,y=0,z=0 before duplicate125.
    assert torch.equal(result.reference.wheels_w, wheels)
    target = recorded[0][0].reshape(126, 4, 3)
    finite = torch.isfinite(target).all(dim=(-1, -2))
    positions = wheels[0, 0]-target[finite, 0] @ rotation(0., 0., y).T
    delta = (positions-body.pos_w) @ rotation(0., 0., y)
    assert delta[:, 0].abs().amax() <= .04+1e-12
    assert delta[:, 1].abs().amax() <= .06+1e-12
    assert delta[:, 2].amin() >= -.08-1e-12 and delta[:, 2].amax() <= 1e-12
    assert torch.allclose(result.reference.body.quat_w, accepted.quat_w)


def test_candidate_cost_uses_heading_normalized_displacement(pose, monkeypatch):
    q, body, ref = setup(pose)
    accepted = pose.BodyPose(body.pos_w-q.new_tensor([[0., 0., .07]]), body.quat_w)
    recorded = record_solver(pose, monkeypatch)
    result = search(pose, body, ref, q, accepted=accepted)
    assert result.valid.item()
    targets, solves = recorded[0]
    positions = ref.wheels_w[0, 0]-targets[:, 0]
    predicted = positions+(ref.wheels_w[:, 1:].mean(1)-body.pos_w)
    margins, geometric = pose.support_margin(predicted, ref.wheels_w.expand(126, -1, -1), torch.zeros(126, dtype=torch.long))
    costs = ((positions-accepted.pos_w)/q.new_tensor([.04, .06, .08])).square().sum(-1)
    eligible = solves.valid & geometric & (margins >= .01)
    expected = torch.where(eligible, costs, torch.full_like(costs, float('inf'))).argmin()
    assert result.candidate_index.item() == expected.item()


@pytest.mark.parametrize('dt', [.01, .02, .04])
def test_backtrack_not_joint_clipping(pose, dt):
    q, body, accepted = setup(pose)
    requested = pose.PoseReference(pose.BodyPose(body.pos_w-q.new_tensor([[0., 0., .07]]), body.quat_w), accepted.wheels_w)
    full = ik.solve_constrained_ik(q, pose.world_to_goal_body(requested), q)
    assert not full.valid.item() and full.workspace_ok.all()
    result = pose.backtrack_reference(accepted, requested, q, q, q, dt, ik.IKConfig())
    assert result.valid.item() and result.slew_ok.item()
    index = result.backtrack_index.item()
    assert 0 < index < 8 and (result.ik.q-q).abs().amax() <= 2.5*dt
    assert result.ik.residual_m.amax() <= .002
    assert torch.allclose(ik.body_feet(result.ik.q), pose.world_to_goal_body(result.reference), atol=.002)
    alpha = 2.**(-index)
    assert torch.allclose(result.reference.body.pos_w, body.pos_w+alpha*(requested.body.pos_w-body.pos_w))
    replay = ik.solve_constrained_ik(q, pose.world_to_goal_body(result.reference), q)
    assert torch.equal(result.ik.q, replay.q)


def test_shortest_arc_and_world_wheel_interpolation(pose):
    q, body, _ = setup(pose)
    y = math.pi-.03
    old = pose.BodyPose(body.pos_w, quat(.08, -.06, y))
    wheels = ik.body_feet(q) @ rotation(.08, -.06, y).T+old.pos_w[:, None]
    accepted = pose.PoseReference(old, wheels)
    end = pose.BodyPose(old.pos_w+q.new_tensor([[.005, -.004, -.02]]), quat(-.04, .03, -math.pi+.03))
    requested = pose.PoseReference(end, wheels+q.new_tensor([[[.01, -.005, .02]]]))
    result = pose.backtrack_reference(accepted, requested, q, q, q, .02, ik.IKConfig())
    assert result.valid.item()
    assert (old.quat_w*end.quat_w).sum() < 0
    alpha = 2.**(-result.backtrack_index.item())
    theta = torch.acos((old.quat_w*(-end.quat_w)).sum(-1))
    expected = (torch.sin((1-alpha)*theta)[:, None]*old.quat_w+torch.sin(alpha*theta)[:, None]*(-end.quat_w))/torch.sin(theta)[:, None]
    assert torch.allclose(result.reference.body.quat_w, expected, atol=1e-12)
    assert torch.allclose(result.reference.body.quat_w.norm(dim=-1), q.new_ones(1))
    assert torch.allclose(result.reference.wheels_w, wheels+alpha*(requested.wheels_w-wheels), atol=1e-12)


def test_backtrack_rejection_is_bounded_and_cannot_commit(pose, monkeypatch):
    q, body, accepted = setup(pose)
    requested = pose.PoseReference(pose.BodyPose(body.pos_w-q.new_tensor([[0., 0., .07]]), body.quat_w), accepted.wheels_w)
    recorded = record_solver(pose, monkeypatch)
    last_applied = q+q.new_tensor([[.2, 0., 0.]*4])
    result = pose.backtrack_reference(accepted, requested, q, q, last_applied, .02, ik.IKConfig())
    assert len(recorded) == 8 and result.backtrack_index.item() == -1
    assert not result.valid.item() and not result.slew_ok.item() and result.ik.valid.item()
    assert torch.allclose(result.reference.body.pos_w, body.pos_w+1/128*(requested.body.pos_w-body.pos_w))
    assert torch.allclose(recorded[-1][0], pose.world_to_goal_body(result.reference), atol=1e-12)
    assert result.ik.residual_m.amax() <= .002
    assert torch.equal(accepted.body.pos_w, body.pos_w)  # Pure API never mutates accepted state.


def test_predicted_com_does_not_certify_measured_support(pose):
    q, body, ref = setup(pose)
    com = body.pos_w+q.new_tensor([[-.009, .009, -.05]])
    margin, valid = pose.support_margin(com, ref.wheels_w, torch.tensor([0]))
    assert valid.item() and margin.item() < .01
    result = search(pose, body, ref, q, com=com)
    assert result.valid.item() and result.predicted_margin_m.item() >= .01
    assert not {'success', 'phase', 'measured_support_ok'} & {f.name for f in fields(result)}


def test_invalid_row_isolation_and_accepted_envelope(pose):
    q, body, ref = setup(pose, 3)
    accepted = pose.BodyPose(body.pos_w.clone(), body.quat_w.clone())
    accepted.pos_w[1, 0] += .041
    body.quat_w[2] = 0.
    result = search(pose, body, ref, q, accepted=accepted)
    assert result.valid.tolist() == [True, True, False]
    assert result.candidate_count[1].item() == 125 and result.candidate_index[1].item() < 125
    assert result.candidate_index[2].item() == -1


@pytest.mark.parametrize('bad', ['active', 'com', 'wheel'])
def test_invalid_support_data_fails_closed(pose, bad):
    q, _, ref = setup(pose, 2)
    com, wheel, active = ref.wheels_w[:, 1:].mean(1), ref.wheels_w.clone(), torch.zeros(2, dtype=torch.long)
    if bad == 'active':
        active[1] = -1
    elif bad == 'com':
        com[1, 2] = float('nan')
    else:
        wheel[1, 0, 2] = float('nan')
    margin, valid = pose.support_margin(com, wheel, active)
    assert valid.tolist() == [True, False] and torch.isnan(margin[1])


@pytest.mark.parametrize('dtype', [torch.float32, torch.float64])
def test_batch_shortest_arc_sign_and_dtype(pose, dtype):
    q, body, accepted = setup(pose, 2, dtype)
    requested = pose.PoseReference(pose.BodyPose(body.pos_w.clone(), -body.quat_w), accepted.wheels_w.clone())
    result = pose.backtrack_reference(accepted, requested, q, q, q, .02, ik.IKConfig())
    assert result.valid.all() and result.backtrack_index.tolist() == [0, 0]
    assert result.ik.q.dtype == dtype and torch.equal(result.reference.body.quat_w, body.quat_w)


@pytest.mark.parametrize('dt', [0., -.01, float('nan'), float('inf')])
def test_invalid_dt_is_contract_error(pose, dt):
    q, _, accepted = setup(pose)
    with pytest.raises(ValueError, match='dt'):
        pose.backtrack_reference(accepted, accepted, q, q, q, dt, ik.IKConfig())


def test_bad_input_quaternion_is_not_repaired_into_finite_reference(pose):
    q, body, accepted = setup(pose, 2)
    bad = body.quat_w.clone()
    bad[1] *= 2
    requested = pose.PoseReference(pose.BodyPose(body.pos_w.clone(), bad), accepted.wheels_w.clone())
    result = pose.backtrack_reference(accepted, requested, q, q, q, .02, ik.IKConfig())
    assert result.valid.tolist() == [True, False]
    assert result.backtrack_index.tolist() == [0, -1]
    targets = pose.world_to_goal_body(result.reference)
    assert torch.isfinite(targets[0]).all() and torch.isnan(targets[1]).all()
    assert (result.ik.reason[1] == ik.IKReason.NONFINITE).all()


def test_mixed_rows_preserve_first_accepted_step(pose):
    q, body, accepted = setup(pose, 3)
    positions = body.pos_w.clone()
    positions[1, 2] -= .07
    requested = pose.PoseReference(pose.BodyPose(positions, body.quat_w.clone()), accepted.wheels_w.clone())
    last = q.clone()
    last[2, 0] += .2
    result = pose.backtrack_reference(accepted, requested, q, q, last, .02, ik.IKConfig())
    assert result.valid.tolist() == [True, True, False]
    assert result.backtrack_index[0].item() == 0 and 0 < result.backtrack_index[1].item() < 8
    assert result.backtrack_index[2].item() == -1
    assert torch.equal(result.ik.q[0], q[0])
    assert torch.equal(result.reference.body.pos_w[0], body.pos_w[0])
    replay = ik.solve_constrained_ik(q, pose.world_to_goal_body(result.reference), q)
    assert torch.equal(result.ik.q, replay.q)


def test_no_support_candidate_does_not_expand_envelope(pose):
    q, body, ref = setup(pose)
    result = search(pose, body, ref, q, com=body.pos_w+q.new_tensor([[2., 2., 0.]]))
    assert not result.valid.item() and result.candidate_index.item() == -1
    assert result.candidate_count.item() == 126
    assert torch.equal(result.reference.body.pos_w, body.pos_w)
    assert result.predicted_margin_m.item() < 0
    assert result.ik.valid.item()  # Reachable geometry alone cannot permit commit.


def test_structural_input_errors_are_explicit(pose):
    q, body, ref = setup(pose)
    with pytest.raises(ValueError, match='quat_w'):
        pose.BodyPose(body.pos_w, body.quat_w.float())
    with pytest.raises(ValueError, match='wheels_w'):
        pose.PoseReference(body, ref.wheels_w[:, :3])
    with pytest.raises(ValueError, match='active_wheel'):
        pose.support_margin(body.pos_w, ref.wheels_w, torch.zeros(1))
    with pytest.raises(ValueError, match='q_seed'):
        pose.backtrack_reference(ref, ref, q[:, :11], q, q, .02, ik.IKConfig())
