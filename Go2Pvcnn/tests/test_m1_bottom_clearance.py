"""User contract: measured wheel bottom clears the obstacle by 3--5 cm."""
import pytest
import torch

from ame_baseline.m1_crossing_clearance import (
    MIN_BOTTOM_CLEARANCE_M, wheel_center_target_z,
)


@pytest.mark.parametrize('clearance', [0.03, 0.04, 0.05])
def test_world_top_and_radius_are_counted_once(clearance):
    # Nonzero terrain elevation must survive conversion to a wheel-center target.
    top = torch.tensor([0.10, 1.10], dtype=torch.float64)
    center = wheel_center_target_z(top, wheel_radius=0.095958,
                                   bottom_clearance=clearance)
    torch.testing.assert_close(center - 0.095958 - top,
                               torch.full_like(top, clearance))


def test_default_targets_middle_of_user_band():
    assert wheel_center_target_z(0.10, wheel_radius=0.095958) == pytest.approx(0.235958)
    assert MIN_BOTTOM_CLEARANCE_M == 0.03


@pytest.mark.parametrize('clearance', [0.029, 0.051, float('nan')])
def test_outside_requested_target_band_is_rejected(clearance):
    with pytest.raises(ValueError):
        wheel_center_target_z(0.10, wheel_radius=0.095958,
                              bottom_clearance=clearance)
