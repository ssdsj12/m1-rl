"""Flat-ground pre-action support measurements for M1, without control writes.

Wheel-center projection is a diagnostic approximation, not a dynamic stability
certificate. Collision evidence and obstacle identity remain caller obligations.
"""
import torch
from extension.parallelism.m1_kinematics import M1_WHEEL_JOINT_NAMES
from extension.convention import extract_roll_pitch_batch


def observe_support(robot, sensor, selected_leg):
    """Read current articulation/contact buffers before advancing simulation.

    Return named force [B,4], tilt/rate [B,2], COM [B,3], signed margin [B]
    and validity [B]. Invalid numeric rows get NaN margin so PrepareGate refuses
    advancement; missing names/shapes fail explicitly. No root-position COM proxy.
    """
    names = tuple(n.replace('_JOINT', '_LINK') for n in M1_WHEEL_JOINT_NAMES)
    body_names, sensor_names = tuple(robot.body_names), tuple(sensor.body_names)
    if any(body_names.count(n) != 1 or sensor_names.count(n) != 1 for n in names):
        raise ValueError('missing or duplicate M1 support body name')
    body_ids = [body_names.index(n) for n in names]
    sensor_ids = [sensor_names.index(n) for n in names]
    pos = robot.data.body_com_pos_w
    masses = robot.root_physx_view.get_masses().to(pos)
    link_pos = robot.data.body_pos_w
    forces = sensor.data.net_forces_w
    quat = robot.data.root_quat_w
    omega = robot.data.root_ang_vel_b
    batch = pos.shape[0]
    expected = [
        (pos, (batch, len(body_names), 3)),
        (masses, (batch, len(body_names))),
        (link_pos, (batch, len(body_names), 3)),
        (forces, (batch, len(sensor_names), 3)),
        (quat, (batch, 4)), (omega, (batch, 3)),
    ]
    if any(x.shape != shape or x.device != pos.device or not x.is_floating_point()
           for x, shape in expected):
        raise ValueError('invalid M1 support observation shape, device or dtype')
    if (selected_leg.shape != (batch,) or selected_leg.dtype != torch.long
            or selected_leg.device != pos.device):
        raise ValueError('selected_leg must be long [B] on observation device')
    valid = torch.ones(batch, dtype=torch.bool, device=pos.device)
    for value, _ in expected:
        valid &= torch.isfinite(value).reshape(batch, -1).all(-1)
    mass_sum = masses.sum(-1)
    valid &= (masses >= 0).all(-1) & (mass_sum > 0)
    valid &= (quat.norm(dim=-1) - 1).abs() <= 1e-3
    valid &= (selected_leg >= 0) & (selected_leg < 4)
    com = (pos * masses[..., None]).sum(1) / mass_sum.clamp_min(1e-12)[:, None]
    wheel = link_pos[:, body_ids]
    supports = torch.tensor([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]],
                            device=pos.device)[selected_leg.clamp(0, 3)]
    triangle = wheel.gather(1, supports[..., None].expand(-1, -1, 3))[..., :2]
    edge = triangle.roll(-1, dims=1) - triangle
    relative = com[:, None, :2] - triangle
    ab, ac = triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0]
    area = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]
    length = edge.norm(dim=-1)
    valid &= (area.abs() > 1e-10) & (length > 1e-10).all(-1)
    margin = ((edge[..., 0] * relative[..., 1] - edge[..., 1] * relative[..., 0])
              * area.sign()[:, None] / length.clamp_min(1e-12)).amin(-1)
    roll, pitch = extract_roll_pitch_batch(quat)
    p, q, r = omega.unbind(-1)
    tilt = torch.stack([roll, pitch], dim=-1)
    tilt_rate = torch.stack([p + (q * roll.sin() + r * roll.cos()) * pitch.tan(),
                             q * roll.cos() - r * roll.sin()], dim=-1)
    valid &= torch.isfinite(tilt_rate).all(-1) & (pitch.cos().abs() > 1e-3)
    return dict(com_w=com, wheel_pos_w=wheel,
                force=forces[:, sensor_ids, 2].clone(), tilt=tilt,
                tilt_rate=tilt_rate, valid=valid,
                margin=torch.where(valid, margin, torch.full_like(margin, float('nan'))))
