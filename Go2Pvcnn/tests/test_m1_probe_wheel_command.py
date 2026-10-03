"""Exercise the actual probe assignment without importing Isaac Sim."""
import ast
from pathlib import Path

import pytest
import torch


@pytest.mark.parametrize("speed", [0.0, 0.05, 0.10])
def test_probe_wheels_follow_requested_speed_and_stop_invalid_rows(speed):
    path = Path(__file__).resolve().parents[1] / 'scripts/probe_m1_teacher_physx.py'
    tree = ast.parse(path.read_text())
    assignment = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.Assign)
                      and ast.unparse(node.targets[0]) == 'action[:, 3::4]')
    action = torch.zeros(2, 16)
    scope = dict(torch=torch, action=action, valid=torch.tensor([True, False]), probe_speed=speed)
    exec(compile(ast.Module(body=[assignment], type_ignores=[]), str(path), 'exec'), scope)
    assert torch.allclose(action[0, 3::4], torch.full((4,), speed))
    assert torch.equal(action[1, 3::4], torch.zeros(4))


def test_probe_reports_measured_single_leg_verification():
    source = (Path(__file__).resolve().parents[1] / 'scripts/probe_m1_teacher_physx.py').read_text()
    assert 'verified_legs' in source
    assert 'physical_single_leg_swing_verified = (' in source
    assert '"physical_single_leg_swing_verified": physical_single_leg_swing_verified' in source
