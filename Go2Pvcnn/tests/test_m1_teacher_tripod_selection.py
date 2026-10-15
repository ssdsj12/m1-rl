"""Load selection independent triangle examples; IK isolated by existing fixture."""
import pytest
import torch
from ame_baseline import m1_teacher_pose as pose
from ame_baseline.m1_teacher_ik import IKConfig
from test_m1_teacher_pose import triangle_setup, fixed_solver


def choose(monkeypatch, total=300., com_xy=None, measured_shift=0., **kwargs):
    fixed_solver(pose, monkeypatch)
    q, body, ref, com = triangle_setup(pose)
    if com_xy is not None:
        com[:, :2] = q.new_tensor(com_xy)
    return pose.choose_support_pose(body, body, body, com, ref.wheels_w,
        torch.tensor([0]), body.pos_w[:, 2], q, q, IKConfig(),
        measured_wheels_w=ref.wheels_w+q.new_tensor([measured_shift, 0., 0.]),
        tripod_total_load_n=None if total is None else q.new_tensor([total]), **kwargs)


def test_geometry_pass_but_load_fail(monkeypatch):
    assert choose(monkeypatch, None).valid.item()
    assert not choose(monkeypatch, 90.).valid.item()


def test_maximin_before_motion_cost(monkeypatch):
    out = choose(monkeypatch)
    assert out.valid.item()
    assert out.reference.body.pos_w[0, :2].tolist() == pytest.approx([.04, .03])
    # Literal barycentrics, not the implementation helper: min(.33,.34,.33)*300.
    assert out.candidate_index.item() == 115


def test_ties_keep_cost_then_index(monkeypatch):
    out = choose(monkeypatch)
    assert out.reference.body.pos_w[0, 2].item() == pytest.approx(.62)
    assert out.candidate_index.item() == 115


@pytest.mark.parametrize('total', [0., -1., float('nan'), 90.])
def test_no_eligible_returns_invalid(monkeypatch, total):
    out = choose(monkeypatch, total)
    assert not out.valid.item() and out.candidate_index.item() == -1


def test_default_legacy_unchanged(monkeypatch):
    out = choose(monkeypatch, None)
    assert out.valid.item() and out.candidate_index.item() == 60


def test_negative_fraction_never_eligible(monkeypatch):
    assert not choose(monkeypatch, 300., com_xy=[.8, .8]).valid.item()


def test_both_triangles_required(monkeypatch):
    # Geometric clearance remains possible, but measured triangle can carry
    # at most (.34-.25)*300=27N on its x-side support.
    assert choose(monkeypatch, None, measured_shift=.25).valid.item()
    assert not choose(monkeypatch, 300., measured_shift=.25).valid.item()


def test_sort_conflict_rejected(monkeypatch):
    with pytest.raises(ValueError):
        choose(monkeypatch, desired_com_xy=torch.tensor([[.3, .3]], dtype=torch.float64))


def test_partial_reserve_candidate_remains_available(monkeypatch):
    # Independent triangle: weakest .33 * 130 = 42.9N, below full45N.
    out = choose(monkeypatch, 130.)
    assert out.valid.item()
    assert out.candidate_index.item() == 115


def test_exact_floor_is_not_a_safe_candidate(monkeypatch):
    # Explicit floor equals the hand-computed maximin99N for this fixture.
    assert not choose(monkeypatch, 300., tripod_min_load_n=99.).valid.item()
