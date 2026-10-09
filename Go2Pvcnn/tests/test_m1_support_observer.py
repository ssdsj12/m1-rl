"""Runtime-shaped fixtures exercise the real observer, not a simulator claim."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
import torch
from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES


def module():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_support_observer.py'
    assert path.exists(), 'M1 support observer missing'
    spec = importlib.util.spec_from_file_location('support_observer', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def fixture():
    names = tuple(n.replace('_JOINT', '_LINK') for n in M1_WHEEL_JOINT_NAMES)
    wheel = torch.tensor([[[1., 1., 0.], [1., -1., 0.], [-1., 1., 0.], [-1., -1., 0.]]]).repeat(8, 1, 1)
    bodies = torch.cat([torch.tensor([[[-.4, -.4, .5]]]).repeat(8, 1, 1), wheel], dim=1)
    masses = torch.tensor([[4., 1., 1., 1., 1.]]).repeat(8, 1)
    robot = NS(body_names=('base', *names), data=NS(
        body_com_pos_w=bodies.clone(), body_pos_w=bodies.clone(),
        root_quat_w=torch.tensor([[1., 0., 0., 0.]]).repeat(8, 1),
        root_ang_vel_b=torch.zeros(8, 3)),
        root_physx_view=NS(get_masses=lambda: masses))
    force = torch.zeros(8, 4, 3)
    force[:, :, 2] = torch.tensor([11., 12., 13., 14.])
    sensor = NS(body_names=tuple(reversed(names)), data=NS(net_forces_w=force.flip(1)))
    return robot, sensor, masses


def test_named_mass_weighted_observations_and_positive_support_margin():
    robot, sensor, _ = fixture()
    result = module().observe_support(robot, sensor, torch.zeros(8, dtype=torch.long))
    torch.testing.assert_close(result['com_w'], torch.tensor([[-.2, -.2, .25]]).repeat(8, 1))
    torch.testing.assert_close(result['force'], torch.tensor([[11., 12., 13., 14.]]).repeat(8, 1))
    assert result['margin'].tolist() == pytest.approx([.4 / 2**.5] * 8)
    assert result['valid'].all()


def test_excluding_different_leg_changes_margin_not_other_rows():
    robot, sensor, _ = fixture()
    result = module().observe_support(robot, sensor, torch.tensor([3, 0, 0, 0, 0, 0, 0, 0]))
    assert result['margin'][0] < 0
    assert (result['margin'][1:] > 0).all()


def test_side_impact_not_support_and_negative_force_not_rectified():
    robot, sensor, _ = fixture()
    sensor.data.net_forces_w[0] = torch.tensor([[500., 0., 0.]]).repeat(4, 1)
    sensor.data.net_forces_w[1, :, 2] = -20
    result = module().observe_support(robot, sensor, torch.zeros(8, dtype=torch.long))
    assert (result['force'][0] == 0).all()
    assert (result['force'][1] == -20).all()


@pytest.mark.parametrize('damage', ['mass', 'quat', 'geometry', 'nan'])
def test_bad_row_fails_closed_without_poisoning_other_rows(damage):
    robot, sensor, masses = fixture()
    if damage == 'mass': masses[0, 0] = -1
    if damage == 'quat': robot.data.root_quat_w[0] = 0
    if damage == 'geometry': robot.data.body_pos_w[0, 1:] = 0
    if damage == 'nan': sensor.data.net_forces_w[0, 0, 0] = float('nan')
    result = module().observe_support(robot, sensor, torch.zeros(8, dtype=torch.long))
    assert not result['valid'][0]
    assert torch.isnan(result['margin'][0])
    assert result['valid'][1:].all()


def test_missing_support_name_rejected():
    robot, sensor, _ = fixture()
    sensor.body_names = ('wrong', *sensor.body_names[1:])
    with pytest.raises(ValueError, match='support'):
        module().observe_support(robot, sensor, torch.zeros(8, dtype=torch.long))


def test_observer_values_drive_prepare_gate_and_reject_side_impact():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_prepare_gate.py'
    spec = importlib.util.spec_from_file_location('prepare_gate', path)
    gate_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate_module)
    gate = gate_module.PrepareGate(8)
    robot, sensor, _ = fixture()
    sensor.data.net_forces_w[0] = torch.tensor([[500., 0., 0.]]).repeat(4, 1)
    for frame in range(5):
        leg = torch.zeros(8, dtype=torch.long)
        observed = module().observe_support(robot, sensor, leg)
        ready = gate.update(
            episode=torch.zeros(8, dtype=torch.long), obstacle=torch.ones(8, dtype=torch.long),
            leg=leg, step=torch.full((8,), frame, dtype=torch.long),
            force=observed['force'], tilt=observed['tilt'], tilt_rate=observed['tilt_rate'],
            margin=observed['margin'], ik_valid=torch.ones(8, dtype=torch.bool),
            collision=torch.zeros(8, dtype=torch.bool))
    assert ready.tolist() == [False, True, True, True, True, True, True, True]


def test_tilt_rates_include_yaw_coupling_for_tilted_body():
    from extension.convention import euler_to_quat_batch
    robot, sensor, _ = fixture()
    robot.data.root_quat_w = euler_to_quat_batch(torch.full((8,), .1), torch.full((8,), .12), torch.full((8,), .7))
    robot.data.root_ang_vel_b[:] = torch.tensor([.01, .02, .3])
    out = module().observe_support(robot, sensor, torch.zeros(8, dtype=torch.long))
    import math
    expected = [.01 + (.02 * math.sin(.1) + .3 * math.cos(.1)) * math.tan(.12),
                .02 * math.cos(.1) - .3 * math.sin(.1)]
    torch.testing.assert_close(out['tilt_rate'], torch.tensor([expected]).repeat(8, 1))


def test_mass_randomization_is_read_fresh_not_cached():
    robot, sensor, masses = fixture()
    observer = module()
    first = observer.observe_support(robot, sensor, torch.zeros(8, dtype=torch.long))
    masses[0, 0] = 12
    second = observer.observe_support(robot, sensor, torch.zeros(8, dtype=torch.long))
    assert second['com_w'][0, 0].item() == pytest.approx(-.3)
    torch.testing.assert_close(first['com_w'][1:], second['com_w'][1:])
