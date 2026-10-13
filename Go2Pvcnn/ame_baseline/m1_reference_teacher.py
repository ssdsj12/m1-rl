"""Independent tensor teacher; no simulator, old teacher or reference imports.

Algorithm provenance (not a vendored source/license claim):
https://github.com/ssdsj12/m1/blob/8aeb845f73e39fd1e121758522ef05ee2378150f/Go2Pvcnn/go2_pvcnn/tasks/m1_curriculum.py
https://github.com/ssdsj12/m1/blob/8aeb845f73e39fd1e121758522ef05ee2378150f/Go2Pvcnn/go2_pvcnn/tasks/m1_rsl_rl_wrapper.py
Independently expressed phase scheduling and DLS; no source blocks copied.
Reference FAR/FBL/RAR/RBL -> current FBL/FAR/RBL/RAR is [1,0,3,2].
We deliberately use componentwise .25 rad DLS clipping, not reference L2
clipping, and the live 1.50 action decoder, not reference .8 scaling.

30/10/20/20 are interpolation horizons, NEVER minimum dwell or success
timers. Measured gates may advance earlier. The five stable RESTORE samples
overlap its interpolation and still require an existing strict receipt.
This controller's phase is never a crossing-success certificate.
Native revision 1: LIFT additionally requires the complete transported body
shift to be measured within 1cm, root speed <=.05m/s and recovered tilt/rate.
These are preparation gates, not a new dwell time or a physical success claim.
Native revision 2: BALANCE first brakes at live nominal joints. Only measured
four-wheel bearing and stable motion lock the body reference and start the
unchanged ramp. Braking time never advances interpolation or certifies success.
"""
from dataclasses import asdict, dataclass, fields
from enum import IntEnum
import hashlib
import json

import torch

from extension.parallelism.m1_kinematics import (
    M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES,
    M1_WHEEL_RADIUS_M, M1_WHEEL_HORIZONTAL_ENVELOPE_M, m1_joint_limit_mask,
)
from extension.parallelism.kinematics import rpy_to_rotation_matrix
from extension.parallelism.rl_adapter import resolve_named_indices
from .m1_ame_contract import (M1_LEG_ACTION_SCALE_RAD, M1_WHEEL_ACTION_SCALE_RAD_S,
    M1_WHEEL_SPEED_LIMIT_RAD_S, m1_action_targets)
from .m1_reference_geometry import cylinder_bottom
from .m1_crossing_landing import crossing_touchdown_safe
from .m1_teacher_ik import body_feet, body_jacobian, dls_step

LEG_COLUMNS = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_PLANNER_JOINT_NAMES))
WHEEL_COLUMNS = list(resolve_named_indices(M1_ASSET_JOINT_NAMES, M1_WHEEL_JOINT_NAMES))
REFERENCE_COMMIT = '8aeb845f73e39fd1e121758522ef05ee2378150f'


class Phase(IntEnum):
    APPROACH = 0
    BALANCE = 1
    LIFT = 2
    PASS = 3
    RESTORE = 4


class Reason(IntEnum):
    OK = 0
    RESET = 1
    COLLISION = 2
    SUPPORT_LOST = 3
    NONFINITE = 4
    IK_INVALID = 5
    ACTION_INVALID = 6
    TARGET_CHANGED = 7
    STALE_STEP = 8


@dataclass(frozen=True)
class TeacherConfig:
    balance_steps: int = 30
    balance_position_tolerance_m: float = .01
    balance_speed_limit_m_s: float = .05
    lift_steps: int = 10
    pass_steps: int = 20
    restore_steps: int = 20
    front_max_lift_m: float = .22
    rear_max_lift_m: float = .20
    body_shift_lateral_m: float = .06
    body_shift_longitudinal_m: float = .04
    far_margin_m: float = .15
    approach_gap_m: float = .06
    approach_capture_m: float = .01
    flat_speed_m_s: float = .30
    cruise_speed_m_s: float = 1.0
    pass_speed_m_s: float = .8
    approach_gain_s_inv: float = 3.0
    yaw_gain_s_inv: float = 1.0
    damping: float = .05
    fd_epsilon: float = 1e-4
    dq_component_limit_rad: float = .25
    ik_iterations: int = 32
    ik_tolerance_m: float = .002
    support_min_force_n: float = 30.
    support_max_tangential_ratio: float = 1.
    target_min_force_n: float = 10.
    recovery_tilt_rad: float = .15
    recovery_rate_rad_s: float = .20
    recovery_pose_rad: float = .15
    recovery_height_m: float = .08
    stable_samples: int = 5

    def __post_init__(self):
        if any(not isinstance(v, (int, float)) or not 0 < v < float('inf') for v in asdict(self).values()):
            raise ValueError('teacher configuration values must be positive and finite')
        for name in ('balance_steps', 'lift_steps', 'pass_steps', 'restore_steps', 'ik_iterations', 'stable_samples'):
            if not isinstance(getattr(self, name), int):
                raise ValueError(f'{name} must be an integer')
        if self.body_shift_lateral_m > .06 or self.body_shift_longitudinal_m > .04:
            raise ValueError('body shift exceeds approved envelope')

    @property
    def fingerprint(self):
        payload = dict(config=asdict(self), algorithm=REFERENCE_COMMIT,
                       implementation='independent-dls-components-v4-native2-brake-before-anchor',
                       asset_order=M1_ASSET_JOINT_NAMES, leg_scale=M1_LEG_ACTION_SCALE_RAD,
                       wheel_scale=M1_WHEEL_ACTION_SCALE_RAD_S)
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class TeacherState:
    """Named-order measurements; metres, seconds, radians, N, wxyz quaternions.

    course fields contain required boxes only; no landing/fill table. Callers
    provide episode identity and the same control-step/reset snapshot as the
    observation; reset rows never consume terminal receipts.
    """
    root_pos_w: torch.Tensor
    com_pos_w: torch.Tensor
    measurement_valid: torch.Tensor
    last_applied_leg_target: torch.Tensor
    applied_target_valid: torch.Tensor
    root_quat_w: torch.Tensor
    root_lin_vel_w: torch.Tensor
    root_ang_vel_w: torch.Tensor
    leg_pos: torch.Tensor
    default_joint_pos: torch.Tensor
    wheel_pos_w: torch.Tensor
    wheel_quat_w: torch.Tensor
    wheel_force_w: torch.Tensor
    centers_top: torch.Tensor
    half_extents: torch.Tensor
    ground_z: torch.Tensor
    course_valid: torch.Tensor
    course_ids: torch.Tensor
    required_wheels: torch.Tensor
    recovered: torch.Tensor
    nominal_root_z_w: torch.Tensor
    dt: torch.Tensor
    reset_mask: torch.Tensor
    episode_id: torch.Tensor
    control_step: torch.Tensor
    collision: torch.Tensor

    def validate(self):
        b = self.root_pos_w.shape[0]
        c = self.centers_top.shape[1]
        shapes = dict(root_pos_w=(b,3), root_quat_w=(b,4), root_lin_vel_w=(b,3),
            com_pos_w=(b,3), last_applied_leg_target=(b,12),
            root_ang_vel_w=(b,3), leg_pos=(b,12), default_joint_pos=(b,16),
            wheel_pos_w=(b,4,3), wheel_quat_w=(b,4,4), wheel_force_w=(b,4,3),
            centers_top=(b,c,3), half_extents=(b,c,2), ground_z=(b,c),
            course_valid=(b,c), course_ids=(b,c), required_wheels=(b,c,4), recovered=(b,c,4))
        boolean = {'course_valid','required_wheels','recovered','reset_mask','collision',
                   'measurement_valid','applied_target_valid'}
        integer = {'course_ids','episode_id','control_step'}
        for f in fields(self):
            value = getattr(self, f.name)
            if not isinstance(value, torch.Tensor) or value.shape != shapes.get(f.name, (b,)):
                raise ValueError(f'{f.name} has invalid tensor shape')
            if value.device != self.root_pos_w.device:
                raise ValueError(f'{f.name} has inconsistent device')
            if f.name in boolean and value.dtype != torch.bool:
                raise ValueError(f'{f.name} must be bool')
            if f.name in integer and value.dtype != torch.long:
                raise ValueError(f'{f.name} must be int64')
            if f.name not in boolean | integer and not value.is_floating_point():
                raise ValueError(f'{f.name} must be floating point')
        if not torch.isfinite(self.dt).all() or (self.dt <= 0).any():
            raise ValueError('dt must be finite and positive')


@dataclass(frozen=True)
class TeacherOutput:
    """action is executable finite fallback when valid=False; never a label then."""
    action: torch.Tensor
    valid: torch.Tensor
    phase: torch.Tensor
    active_wheel: torch.Tensor
    active_target: torch.Tensor
    reason: torch.Tensor


def quaternion_rpy(quat):
    q = quat / quat.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    w,x,y,z = q.unbind(-1)
    return torch.stack((torch.atan2(2*(w*x+y*z), 1-2*(x*x+y*y)),
        torch.asin((2*(w*y-z*x)).clamp(-1,1)),
        torch.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))), -1)


def solve_ik_body(current_q, target_body, cfg=None):
    """Current-pose branch continuation; invalid rows return finite held joints."""
    cfg = cfg or TeacherConfig()
    finite = torch.isfinite(current_q).all(-1) & torch.isfinite(target_body).all(dim=(-1,-2))
    q = torch.nan_to_num(current_q).clone()
    target = torch.where(finite[:,None,None], target_body, body_feet(q))
    initial = q.clone()
    for _ in range(cfg.ik_iterations):
        error = target-body_feet(q)
        if bool((error.norm(dim=-1).amax(-1) <= cfg.ik_tolerance_m).all()):
            break
        dq = dls_step(body_jacobian(q, cfg.fd_epsilon), error,
                      cfg.damping, cfg.dq_component_limit_rad)
        q = q + dq.flatten(1)  # FK's explicit planner-order 4 legs x 3 joints.
    residual = (target-body_feet(q)).norm(dim=-1).amax(-1)
    # Keep the observed knee branch; crossing straight singularity is not a
    # license to silently swap the front knees to positive-acos solutions.
    knees = [M1_PLANNER_JOINT_NAMES.index(f'{p}_KNEE_JOINT') for p in ('FBL','FAR','RBL','RAR')]
    branch = ((initial[:,knees]*q[:,knees] >= 0) | (initial[:,knees].abs() < 1e-6)).all(-1)
    valid = finite & torch.isfinite(q).all(-1) & m1_joint_limit_mask(q) & branch & (residual <= cfg.ik_tolerance_m)
    return torch.where(valid[:,None], q, initial), valid


def encode_targets(q_target, surface_speed, live_default):
    """Validate against actual decoder; do not clip and pretend reachability."""
    action = torch.zeros_like(live_default)
    action[:,LEG_COLUMNS] = (q_target-live_default[:,LEG_COLUMNS])/M1_LEG_ACTION_SCALE_RAD
    action[:,WHEEL_COLUMNS] = surface_speed/(M1_WHEEL_RADIUS_M*M1_WHEEL_ACTION_SCALE_RAD_S)
    actual = m1_action_targets(action, live_default)
    valid = (torch.isfinite(action).all(-1) & torch.isfinite(live_default).all(-1)
        & m1_joint_limit_mask(q_target)
        & (surface_speed.abs() <= M1_WHEEL_RADIUS_M*M1_WHEEL_SPEED_LIMIT_RAD_S).all(-1)
        & ((actual[:,LEG_COLUMNS]-q_target).abs() <= 1e-5).all(-1)
        & ((actual[:,WHEEL_COLUMNS]*M1_WHEEL_RADIUS_M-surface_speed).abs() <= 1e-5).all(-1))
    return torch.where(valid[:,None], action, torch.zeros_like(action)), valid


def body_shift_error(anchor, actual, yaw, active_wheel, fraction, cfg):
    """Desired-root minus actual-root, expressed in the locked heading frame."""
    shift = torch.zeros_like(actual)
    shift[:,0] = torch.where(active_wheel < 2, -cfg.body_shift_longitudinal_m, cfg.body_shift_longitudinal_m)*fraction
    shift[:,1] = torch.where(active_wheel.remainder(2) == 0, -cfg.body_shift_lateral_m, cfg.body_shift_lateral_m)*fraction
    c,s = yaw.cos(), yaw.sin()
    delta = anchor-actual
    delta_body = torch.stack((c*delta[:,0]+s*delta[:,1], -s*delta[:,0]+c*delta[:,1], delta[:,2]),-1)
    return delta_body+shift


class ReferenceTeacher:
    """One locked required box/wheel per row. No environment mutations."""
    def __init__(self, cfg=None):
        self.cfg = cfg or TeacherConfig()
        self._rows = None

    @torch.no_grad()
    def step(self, state):
        state.validate()
        b = state.root_pos_w.shape[0]
        if self._rows is None:
            self._rows = [None]*b
        if len(self._rows) != b:
            raise ValueError('batch size changed; use a new teacher')
        outputs = []
        for i in range(b):
            outputs.append(self._step_row(state, i))
        return TeacherOutput(*(torch.cat([getattr(o,f.name) for o in outputs],0) for f in fields(TeacherOutput)))

    def _step_row(self, s, i):
        cfg = self.cfg
        row = self._rows[i]
        episode, step = int(s.episode_id[i]), int(s.control_step[i])
        reset = bool(s.reset_mask[i])
        identity_changed = row is not None and row['episode'] != episode
        if row is None or row['episode'] != episode or (reset and row['step'] != step):
            row = dict(episode=episode, step=-1, reset=False, target=-1, wheel=-1,
                       phase=Phase.APPROACH, age=0, stable=0, failure=Reason.OK)
            self._rows[i] = row
        if row['step'] == step and row['reset'] == reset:
            # Clone cache so callers cannot mutate the stored label/phase.
            return TeacherOutput(*(getattr(row['output'],f.name).clone() for f in fields(TeacherOutput)))
        if step < row['step']:
            row['failure'] = Reason.STALE_STEP
        if step != row['step'] + 1:
            # Unobserved control steps cannot establish consecutive recovery.
            # The duplicate-step cache above neither clears nor advances it.
            row['stable'] = 0
        row['step'], row['reset'] = step, reset
        q = s.leg_pos[i:i+1]
        defaults = s.default_joint_pos[i:i+1]
        reason = row['failure']
        finite = all(bool(torch.isfinite(getattr(s,f.name)[i]).all()) for f in fields(s)
                     if getattr(s,f.name).is_floating_point())
        finite = finite and bool(s.root_quat_w[i].norm() > 1e-8) and bool((s.wheel_quat_w[i].norm(dim=-1)>1e-8).all())
        if reset or identity_changed:
            row.update(target=-1, wheel=-1, phase=Phase.APPROACH, stable=0, age=0, failure=Reason.OK)
            reason = Reason.RESET
        elif not finite:
            reason = Reason.NONFINITE
        elif bool(s.collision[i]):
            reason = row['failure'] = Reason.COLLISION
        if reason != Reason.OK:
            return self._output(s, i, row, torch.zeros_like(defaults), False, reason)

        rpy = quaternion_rpy(s.root_quat_w[i:i+1])
        rotation = rpy_to_rotation_matrix(rpy)
        force = s.wheel_force_w[i:i+1].norm(dim=-1)
        pending = s.required_wheels[i] & s.course_valid[i,:,None] & ~s.recovered[i]
        if row['target'] < 0 and bool(pending.any()):
            candidates = pending.nonzero()
            # Ordered world-X boxes; within each box the front wheel precedes rear.
            choice = (s.centers_top[i,candidates[:,0],0]*8 + candidates[:,1]*1e-4).argmin()
            target, wheel = candidates[choice].tolist()
            row.update(target=target, wheel=wheel, target_id=int(s.course_ids[i,target]),
                       phase=Phase.APPROACH, age=0, stable=0)
        target, wheel = row['target'], row['wheel']
        q_target = defaults[:,LEG_COLUMNS].clone()
        speed = q.new_full((1,4), cfg.flat_speed_m_s)
        ik_valid = True
        restore_complete = False
        if target >= 0:
            if (not bool(s.course_valid[i,target]) or int(s.course_ids[i,target]) != row['target_id']
                    or not bool(s.required_wheels[i,target,wheel])):
                row['failure'] = Reason.TARGET_CHANGED
                return self._output(s,i,row,torch.zeros_like(defaults),False,row['failure'])
            center, half = s.centers_top[i,target], s.half_extents[i,target]
            if bool((half <= 0).any()):
                return self._output(s,i,row,torch.zeros_like(defaults),False,Reason.NONFINITE)
            measured = s.wheel_pos_w[i:i+1]
            bottom = cylinder_bottom(measured, s.wheel_quat_w[i:i+1])[0,wheel]
            support = [k for k in range(4) if k != wheel]
            upward = s.wheel_force_w[i,:,2]
            horizontal = s.wheel_force_w[i,:,:2].norm(dim=-1)
            bearing = (upward > cfg.support_min_force_n) & (horizontal <= cfg.support_max_tangential_ratio*upward)
            support_ready = bool(bearing[support].all())
            phase = row['phase']
            if phase >= Phase.LIFT and not support_ready:
                row['failure'] = Reason.SUPPORT_LOST
                return self._output(s,i,row,torch.zeros_like(defaults),False,row['failure'])
            near_x = center[0]-half[0]-M1_WHEEL_HORIZONTAL_ENVELOPE_M-cfg.approach_gap_m
            far_x = center[0]+half[0]+M1_WHEEL_HORIZONTAL_ENVELOPE_M+cfg.far_margin_m
            if phase == Phase.APPROACH:
                distance = near_x-measured[0,wheel,0]
                speed[:] = min(cfg.cruise_speed_m_s, max(0., float(distance)*cfg.approach_gain_s_inv))
                if distance <= cfg.approach_capture_m:
                    row.update(phase=Phase.BALANCE, age=0, prepared=False,
                               body_age=0, lift_age=0)
                    # A new target must not inherit the previous target's anchor.
                    for key in ('anchor','yaw','support_origin','lift_start_z','restore_q'):
                        row.pop(key, None)
            elif phase == Phase.BALANCE and not row['prepared']:
                # Stop at live nominal before capturing a body-height/pose
                # reference. This separates braking from body-shift IK; it
                # does not impose a timed dwell or modify the LIFT gate below.
                ready = bool(bearing.all())
                ready &= bool(s.root_lin_vel_w[i].norm() <= cfg.balance_speed_limit_m_s)
                ready &= bool(rpy[:,:2].abs().amax() <= cfg.recovery_tilt_rad)
                ready &= bool(s.root_ang_vel_w[i,:2].abs().amax() <= cfg.recovery_rate_rad_s)
                if ready:
                    row.update(prepared=True,
                        anchor=s.root_pos_w[i:i+1].clone(), yaw=rpy[:,2].clone(),
                        support_origin=measured[:,support,:].mean(1).clone(),
                        lift_start_z=measured[0,wheel,2].clone(),
                        restore_q=q.clone(), body_age=0, lift_age=0)
            elif phase == Phase.BALANCE:
                # Three loaded wheels alone did not establish a prepared
                # support transfer in native run1. Test the *full* shifted
                # root goal, not the near-zero beginning of its ramp.
                transported = row['anchor'].clone()
                transported[:,:2] += (measured[:,support].mean(1)-row['support_origin'])[:,:2]
                full_error = body_shift_error(transported, s.root_pos_w[i:i+1], row['yaw'],
                    torch.tensor([wheel],device=q.device), q.new_ones(1), cfg)
                ready = support_ready
                ready &= bool(full_error[:,:2].norm(dim=-1)[0] <= cfg.balance_position_tolerance_m)
                ready &= bool(s.root_lin_vel_w[i].norm() <= cfg.balance_speed_limit_m_s)
                ready &= bool(rpy[:,:2].abs().amax() <= cfg.recovery_tilt_rad)
                ready &= bool(s.root_ang_vel_w[i,:2].abs().amax() <= cfg.recovery_rate_rad_s)
                if ready:
                    row.update(phase=Phase.LIFT, age=0)
            elif phase == Phase.LIFT and bottom > center[2]:
                row.update(phase=Phase.PASS, age=0)
            elif phase == Phase.PASS and measured[0,wheel,0] > far_x:
                row.update(phase=Phase.RESTORE, age=0, restore_q=q.clone())
            elif phase == Phase.RESTORE:
                safe = crossing_touchdown_safe(support_contact=force > cfg.target_min_force_n,
                    support_force=force, target_wheel=torch.tensor([wheel],device=q.device),
                    target_min_force=cfg.target_min_force_n, support_min_force=cfg.support_min_force_n)
                stable = bool(safe[0]) and bool(rpy[:,:2].abs().amax() <= cfg.recovery_tilt_rad)
                stable &= bool((horizontal <= cfg.support_max_tangential_ratio*upward).all())
                stable &= bool(upward[wheel] > cfg.target_min_force_n)
                stable &= bool(s.root_ang_vel_w[i,:2].abs().amax() <= cfg.recovery_rate_rad_s)
                stable &= bool((q-defaults[:,LEG_COLUMNS]).abs().amax() <= cfg.recovery_pose_rad)
                stable &= bool((s.root_pos_w[i,2]-s.nominal_root_z_w[i]).abs() <= cfg.recovery_height_m)
                stable &= bool(measured[0,wheel,0] > far_x)
                row['stable'] = row['stable']+1 if stable else 0
                if row['stable'] >= cfg.stable_samples and bool(s.recovered[i,target,wheel]):
                    # Defer release until the final action is validated; a
                    # clipped/invalid label cannot finish this observation.
                    restore_complete = True
                    speed.zero_()
            phase = row['phase']
            if phase == Phase.BALANCE and not row['prepared']:
                # q_target is the live nominal pose; no IK and no clock advance.
                speed.zero_()
            elif row['target'] >= 0 and phase != Phase.APPROACH:
                row['age'] += 1
                age = row['age']
                if phase == Phase.RESTORE:
                    alpha = min(1., age/cfg.restore_steps)
                    q_target = row['restore_q']*(1-alpha)+defaults[:,LEG_COLUMNS]*alpha
                    speed.zero_()
                else:
                    # Reference interpolation clocks continue across measured
                    # transitions; early LIFT/PASS never jump to full offsets.
                    row['body_age'] += 1
                    alpha = min(1., row['body_age']/cfg.balance_steps)
                    # Transport contact reference with measured rolling supports.
                    # It is never a world-fixed stance-foot anchor.
                    transported = row['anchor'].clone()
                    transported[:,:2] += (measured[:,support].mean(1)-row['support_origin'])[:,:2]
                    error = body_shift_error(transported, s.root_pos_w[i:i+1], row['yaw'],
                        torch.tensor([wheel],device=q.device), q.new_tensor([alpha]), cfg)
                    target_body = torch.einsum('bij,bkj->bki', rotation.transpose(-1,-2), measured-s.root_pos_w[i:i+1,None])
                    # Opposite wheel displacement produces the requested body shift.
                    target_body -= error[:,None]
                    if phase >= Phase.LIFT:
                        row['lift_age'] += 1
                        lift_alpha = min(1., row['lift_age']/cfg.lift_steps)
                        max_lift = cfg.front_max_lift_m if wheel < 2 else cfg.rear_max_lift_m
                        desired_z = s.ground_z[i,target]+M1_WHEEL_RADIUS_M+max_lift
                        desired_z = row['lift_start_z']+(desired_z-row['lift_start_z'])*lift_alpha
                        # swing_with_body: the body rolls across; no forced far-X IK.
                        nominal = body_feet(defaults[:,LEG_COLUMNS])[:,wheel]
                        target_body[:,wheel,:2] = nominal[:,:2]-error[:,:2]
                        desired_world = measured[:,wheel].clone()
                        desired_world[:,2] = desired_z
                        local = torch.einsum('bij,bj->bi', rotation.transpose(-1,-2), desired_world-s.root_pos_w[i:i+1])
                        target_body[:,wheel,2] = local[:,2]
                    q_target, ok = solve_ik_body(q, target_body, cfg)
                    ik_valid = bool(ok[0])
                    speed.zero_()
                    if phase == Phase.PASS:
                        speed[:] = cfg.pass_speed_m_s*min(1., age/cfg.pass_steps)
        # Gentle heading correction is bounded by the same action contract.
        if bool((speed != 0).any()):
            speed += -cfg.yaw_gain_s_inv*rpy[:,2,None]*q.new_tensor([-.215,.215,-.215,.215])
        if restore_complete:
            q_target = defaults[:,LEG_COLUMNS].clone()
        action, encoded = encode_targets(q_target, speed, defaults)
        valid = ik_valid and bool(encoded[0])
        reason = Reason.OK if valid else (Reason.IK_INVALID if not ik_valid else Reason.ACTION_INVALID)
        if not valid:
            # Hold current finite/legal joints when possible, stop all wheels.
            action, _ = encode_targets(torch.nan_to_num(q), torch.zeros_like(speed), defaults)
        elif restore_complete:
            row.update(target=-1, wheel=-1, phase=Phase.APPROACH, age=0, stable=0)
        return self._output(s,i,row,action,valid,reason)

    @staticmethod
    def _output(s, i, row, action, valid, reason):
        if not valid:
            # All early returns and final encoding/IK failures break the same
            # consecutive-measurement run, including transient NONFINITE.
            row['stable'] = 0
        device = s.root_pos_w.device
        out = TeacherOutput(action.clone(), torch.tensor([valid],device=device),
            torch.tensor([int(row['phase'])],device=device), torch.tensor([row['wheel']],device=device),
            torch.tensor([row['target']],device=device), torch.tensor([int(reason)],device=device))
        row['output'] = out
        return TeacherOutput(*(getattr(out,f.name).clone() for f in fields(TeacherOutput)))
