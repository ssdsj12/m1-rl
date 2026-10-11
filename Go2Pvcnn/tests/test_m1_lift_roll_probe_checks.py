"""Counterexamples for native placement measurements, not reward changes."""
import importlib
import torch
import pytest


def checker():
    name = 'ame_baseline.m1_lift_roll_probe_checks'
    assert importlib.util.find_spec(name) is not None, 'placement evidence checker missing'
    return importlib.import_module(name)


def frame(**overrides):
    values = dict(wheel_force=torch.tensor([[[0., 0., 100.]] * 4]),
                  bottom=torch.zeros(1, 4), ground=torch.zeros(1),
                  margin=torch.full((1, 4), .01), expected=torch.ones(1, 4, dtype=torch.bool),
                  nonwheel_force=torch.zeros(1, 3, 3), clearance=torch.tensor([.04]),
                  root_error=torch.zeros(1), angle_error=torch.zeros(1), joint_error=torch.zeros(1))
    values.update(overrides)
    return checker().assess_frame(**values)


def test_horizontal_side_contact_is_not_ground_support():
    result = frame(wheel_force=torch.tensor([[[100., 0., 0.]] * 4]))
    assert not result['ground_support']


@pytest.mark.parametrize('kwargs', [dict(bottom=torch.full((1, 4), .03)),
                                  dict(margin=torch.full((1, 4), -.001))])
def test_obstacle_top_or_side_is_not_flat_ground_support(kwargs):
    assert not frame(**kwargs)['ground_support']


def test_initial_collision_cannot_be_erased_by_later_clear_frames():
    history = checker().PlacementEvidence()
    history.record(frame(nonwheel_force=torch.ones(1, 3, 3)))
    for _ in range(8):
        history.record(frame())
    assert not history.result()['geometry_verified']


def test_pose_extruded_away_from_requested_sample_is_unverified():
    assert not frame(root_error=torch.tensor([.021]))['pose_verified']
    assert not frame(angle_error=torch.tensor([.10]))['pose_verified']
    assert not frame(joint_error=torch.tensor([.041]))['pose_verified']


def test_settling_support_failure_is_not_geometry_impossibility():
    history = checker().PlacementEvidence()
    for _ in range(8):
        history.record(frame(wheel_force=torch.zeros(1, 4, 3)))
    result = history.result()
    assert result['geometry_verified'] and not result['support_verified']
    assert not result['verified']


def test_ground_supported_pose_passes_after_settling():
    history = checker().PlacementEvidence()
    history.record(frame(wheel_force=torch.zeros(1, 4, 3)))
    for _ in range(5):
        history.record(frame())
    assert history.result()['verified']
