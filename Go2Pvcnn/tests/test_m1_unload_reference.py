import importlib.util
from pathlib import Path
import torch
import pytest


def proposal():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_unload_reference.py'
    assert path.exists(), 'measured unload reference missing'
    spec = importlib.util.spec_from_file_location('unload_ref', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.unload_height


def test_force_feedback_is_bounded_and_stops_when_unloaded():
    result = proposal()(torch.tensor([0., .01, .0199]), torch.tensor([50., 2., 100.]), .02)
    torch.testing.assert_close(result['height'], torch.tensor([.00018, .01, .02]))
    assert result['valid'].all()


def test_invalid_evidence_never_advances():
    result = proposal()(torch.tensor([0., .01]), torch.tensor([float('nan'), -1.]), .02)
    assert not result['valid'].any()
    torch.testing.assert_close(result['height'], torch.tensor([0., .01]))


def test_height_cap_with_persistent_contact_is_not_success():
    result = proposal()(torch.tensor([.02]), torch.tensor([50.]), .02)
    assert result['at_limit'].item()
    assert result['height'].item() <= .020001


def test_unsettled_effort_holds_reference_per_row():
    result = proposal()(torch.tensor([0., 0.]), torch.tensor([50., 50.]), .02,
                        effort_settled=torch.tensor([False, True]))
    torch.testing.assert_close(result['height'], torch.tensor([0., .00018]))


def test_zero_target_keeps_unloading_at_acceptance_boundary():
    result = proposal()(torch.zeros(3), torch.tensor([5., 0., 100.]), .02,
                        target_force=0.)
    torch.testing.assert_close(result['height'], torch.tensor([.00002, 0., .0002]))
    assert result['valid'].all()


@pytest.mark.parametrize('target', [-1., 6., float('nan')])
def test_invalid_force_target_rejected(target):
    with pytest.raises(ValueError):
        proposal()(torch.zeros(1), torch.ones(1), .02, target_force=target)


def test_contact_speed_floor_advances_only_with_remaining_contact():
    result=proposal()(torch.zeros(4),torch.tensor([0.,2.,10.,100.]),.02,
                      target_force=0.,min_contact_speed=.003)
    torch.testing.assert_close(result['height'],torch.tensor([0.,.00006,.00006,.0002]))


def test_speed_floor_cannot_bypass_effort_settle_or_height_cap():
    result=proposal()(torch.tensor([0.,.01999]),torch.tensor([10.,10.]),.02,
                      target_force=0.,min_contact_speed=.003,effort_settled=torch.tensor([False,True]))
    torch.testing.assert_close(result['height'],torch.tensor([0.,.02]))
