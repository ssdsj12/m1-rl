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
Support-IK revision: explicit world references, real measured COM and loads,
bounded four-leg IK and actual executed-target continuity precede every commit.
Legacy solve_ik_body/body_shift_error remain compatibility math only; live
teacher execution uses the constrained pose path in every phase.
"""
from dataclasses import asdict, dataclass, fields, field, replace
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
from .m1_teacher_ik import body_feet, body_jacobian, dls_step, IKConfig
from .m1_teacher_pose import (BodyPose, PoseReference, world_to_goal_body,
    choose_support_pose, backtrack_feedback_reference, feedback_command, support_margin)
from .m1_teacher_feedback import (FeedbackConfig, FeedbackState, propose_feedback,
    select_integral, recompute_feedback)

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
    MEASUREMENT_INVALID = 9
    APPLIED_TARGET_INVALID = 10


class FreezeReason(IntEnum):
    NONE = 0
    BRAKING = 1
    TRACKING = 2
    IK = 3
    ACTION = 4
    SAFETY = 5
    RESET = 6
    LOCKED = 7
    PREPARATION = 8


# Columns have stable names. Discrete columns are explicitly declared below;
# consumers must resolve names, never infer meanings from numeric positions.
TEACHER_DIAGNOSTIC_FIELDS = tuple(
    [f'{kind}_root_{axis}' for kind in ('measured', 'requested', 'attempted', 'accepted')
     for axis in ('x', 'y', 'z', 'qw', 'qx', 'qy', 'qz')]
    + [f'{kind}_wheel_{leg}_{axis}' for kind in ('requested_world', 'attempted_world',
       'attempted_body', 'accepted_world', 'accepted_body')
       for leg in range(4) for axis in ('x', 'y', 'z')]
    + [f'com_{axis}' for axis in ('x', 'y', 'z')]
    + ['measured_com_margin_m', 'predicted_com_margin_m', 'candidate_com_margin_m']
    + [f'ik_{name}_{leg}' for name in ('residual_m', 'joint_limit_ok', 'branch_ok',
       'extension_margin_rad', 'workspace_ok', 'iterations', 'reason') for leg in range(4)]
    + [f'{kind}_q_{joint}' for kind in ('attempted', 'accepted', 'last_applied') for joint in range(12)]
    + [f'support_slip_{leg}_{axis}' for leg in range(4) for axis in ('x', 'y')]
    + ['candidate_index', 'candidate_count', 'backtrack_index', 'invalid_streak',
       'freeze_reason', 'reference_valid', 'diagnostic_only', 'age', 'body_age', 'lift_age']
    + [f'preparation_{kind}_root_{axis}' for kind in ('prior', 'goal')
       for axis in ('x', 'y', 'z', 'qw', 'qx', 'qy', 'qz')]
    + ['preparation_ready']
    + [f'command_{kind}_root_{axis}' for kind in ('requested','attempted','accepted')
       for axis in ('x','y','z','qw','qx','qy','qz')]
    + [f'command_{kind}_world_wheel_{leg}_{axis}' for kind in ('requested','attempted','accepted')
       for leg in range(4) for axis in ('x','y','z')]
    + [f'nominal_ik_{name}_{leg}' for name in ('residual_m','joint_limit_ok','branch_ok',
       'extension_margin_rad','workspace_ok','iterations','reason') for leg in range(4)]
    + [f'feedback_{kind}_{axis}' for kind in ('error_h','integral_before','integral_candidate',
       'integral_selected','integral_committed','raw_output','proposed_output','output_before',
       'output_committed','limited','integral_limited','amplitude_limited','slew_limited',
       'final_proposed_output') for axis in ('x','y','z')]
    + [f'wheel_{kind}_surface_speed_{leg}' for kind in ('nominal','final') for leg in range(4)]
    + ['feedback_passes','wheel_headroom_limited','feedback_active',
       'feedback_first_backtrack_index','feedback_first_transaction_valid'])
TEACHER_DIAGNOSTIC_INTEGER_FIELDS = tuple(
    [f'ik_{name}_{leg}' for name in ('joint_limit_ok', 'branch_ok', 'workspace_ok',
       'iterations', 'reason') for leg in range(4)]
    + ['candidate_index', 'candidate_count', 'backtrack_index', 'invalid_streak',
       'freeze_reason', 'reference_valid', 'diagnostic_only', 'age', 'body_age', 'lift_age', 'preparation_ready']
    + [f'nominal_ik_{name}_{leg}' for name in ('joint_limit_ok','branch_ok','workspace_ok',
       'iterations','reason') for leg in range(4)]
    + [f'feedback_{kind}_{axis}' for kind in ('limited','integral_limited','amplitude_limited','slew_limited')
       for axis in ('x','y','z')]
    + ['feedback_passes','wheel_headroom_limited','feedback_active',
       'feedback_first_backtrack_index','feedback_first_transaction_valid'])


@dataclass(frozen=True)
class TeacherConfig:
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
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
    body_lowering_max_m: float = .08
    com_margin_m: float = .01
    min_knee_abs_rad: float = .10
    joint_target_rate_rad_s: float = 2.5
    backtrack_steps: int = 8
    candidate_limit: int = 126
    invalid_lock_steps: int = 5

    def __post_init__(self):
        if not isinstance(self.feedback, FeedbackConfig):
            raise ValueError('feedback must be FeedbackConfig')
        self.feedback.__post_init__()
        if any(not isinstance(v, (int, float)) or not 0 < v < float('inf')
               for k,v in asdict(self).items() if k != 'feedback'):
            raise ValueError('teacher configuration values must be positive and finite')
        for name in ('balance_steps', 'lift_steps', 'pass_steps', 'restore_steps', 'ik_iterations',
                     'stable_samples', 'backtrack_steps', 'candidate_limit', 'invalid_lock_steps'):
            if type(getattr(self, name)) is not int:
                raise ValueError(f'{name} must be an integer')
        if self.body_shift_lateral_m > .06 or self.body_shift_longitudinal_m > .04:
            raise ValueError('body shift exceeds approved envelope')
        IKConfig(**{f.name: getattr(self, f.name) for f in fields(IKConfig)})
        fixed = dict(body_shift_lateral_m=.06, body_shift_longitudinal_m=.04,
                     body_lowering_max_m=.08, com_margin_m=.01, joint_target_rate_rad_s=2.5,
                     backtrack_steps=8, candidate_limit=126, invalid_lock_steps=5)
        if any(getattr(self, k) != v for k, v in fixed.items()):
            raise ValueError('pose search, continuity and failure bounds are fixed by the approved design')

    @property
    def fingerprint(self):
        payload = dict(config=asdict(self), algorithm=REFERENCE_COMMIT,
                       implementation='support-ik-transaction-v8', diagnostic_fields=TEACHER_DIAGNOSTIC_FIELDS,
                       diagnostic_integer_fields=TEACHER_DIAGNOSTIC_INTEGER_FIELDS,
                       asset_order=M1_ASSET_JOINT_NAMES, leg_scale=M1_LEG_ACTION_SCALE_RAD,
                       wheel_scale=M1_WHEEL_ACTION_SCALE_RAD_S,
                       wheel_radius_m=M1_WHEEL_RADIUS_M, wheel_speed_limit_rad_s=M1_WHEEL_SPEED_LIMIT_RAD_S)
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
    """Only executable=True authorizes action application, independently of labels.

    A non-executable action is a NaN non-command placeholder. Callers must stop
    the entire batch before process/apply/physics, retaining the failed decision.
    """
    action: torch.Tensor
    valid: torch.Tensor
    phase: torch.Tensor
    active_wheel: torch.Tensor
    active_target: torch.Tensor
    reason: torch.Tensor
    diagnostic: torch.Tensor
    failure_locked: torch.Tensor
    executable: torch.Tensor


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
    """Per-episode transactional references; only validated execution commits."""
    def __init__(self, cfg=None):
        self.cfg = cfg or TeacherConfig()
        self.ik_cfg = IKConfig(**{f.name: getattr(self.cfg, f.name) for f in fields(IKConfig)})
        self._rows = None
        self._mode = None

    @torch.no_grad()
    def step(self, state):
        return self._batch(state, None)

    @torch.no_grad()
    def diagnostic_step(self, state, *, active_wheel, lift):
        """Local fixture only: never emits course/BC labels or creates receipts."""
        if type(active_wheel) is not int or active_wheel not in range(4) or type(lift) is not bool:
            raise ValueError('diagnostic wheel must be 0..3 and lift must be bool')
        return self._batch(state, (active_wheel, lift))

    def _batch(self, state, diagnostic):
        state.validate()
        mode = ('course',) if diagnostic is None else ('diagnostic', diagnostic[0])
        if self._mode is not None and self._mode != mode:
            raise ValueError('use a separate teacher for course and each diagnostic wheel')
        self._mode = mode
        b = state.root_pos_w.shape[0]
        if self._rows is None:
            self._rows = [None]*b
        if len(self._rows) != b:
            raise ValueError('batch size changed; use a new teacher')
        outputs = [self._step_row(state, i, diagnostic) for i in range(b)]
        return TeacherOutput(*(torch.cat([getattr(o, f.name) for o in outputs], 0)
                               for f in fields(TeacherOutput)))

    @staticmethod
    def _reference(s, i):
        return PoseReference(BodyPose(s.root_pos_w[i:i+1].clone(), s.root_quat_w[i:i+1].clone()),
                             s.wheel_pos_w[i:i+1].clone())

    @staticmethod
    def _clone_output(out):
        return TeacherOutput(*(getattr(out, f.name).clone() for f in fields(TeacherOutput)))

    def _tracked(self, s, i, ref):
        cfg = self.cfg
        position = (s.root_pos_w[i:i+1]-ref.body.pos_w).norm(dim=-1)
        a = quaternion_rpy(s.root_quat_w[i:i+1])
        b = quaternion_rpy(ref.body.quat_w)
        angular = torch.atan2((a-b).sin(), (a-b).cos()).abs().amax()
        return bool(position[0] <= cfg.balance_position_tolerance_m and angular <= cfg.recovery_pose_rad)

    def _quiet(self, s, i):
        cfg = self.cfg
        rpy = quaternion_rpy(s.root_quat_w[i:i+1])
        return bool(s.root_lin_vel_w[i].norm() <= cfg.balance_speed_limit_m_s
                    and rpy[:, :2].abs().amax() <= cfg.recovery_tilt_rad
                    and s.root_ang_vel_w[i].norm() <= cfg.recovery_rate_rad_s)

    def _fallback(self, s, i, row):
        # Certify a hold using executed-target evidence, independently of other
        # invalid measurements. Never replace an uncertifiable hold by nominal.
        defaults = s.default_joint_pos[i:i+1]
        last = row.get('last_q')
        if last is None:
            last = s.last_applied_leg_target[i:i+1]
        action, encoded = encode_targets(last, last.new_zeros(1, 4), defaults)
        actual = m1_action_targets(action, defaults)[:, LEG_COLUMNS]
        knees = [M1_PLANNER_JOINT_NAMES.index(f'{p}_KNEE_JOINT') for p in ('FBL','FAR','RBL','RAR')]
        legal = bool((actual[:, knees].abs() >= self.cfg.min_knee_abs_rad).all())
        branch = row.get('branch_q')
        if branch is not None:
            legal &= bool(torch.isfinite(branch).all() and (actual[:, knees]*branch[:, knees] > 0).all())
        continuous = bool(s.applied_target_valid[i] and
            torch.isfinite(s.last_applied_leg_target[i]).all() and
            ((actual-s.last_applied_leg_target[i:i+1]).abs() <= self.cfg.joint_target_rate_rad_s*float(s.dt[i])).all())
        executable = bool(encoded[0]) and legal and continuous
        return (action if executable else torch.full_like(defaults, float('nan'))), executable

    def _feedback_transaction(self, s, i, work, accepted, requested, q, branch,
                              nominal_speed, evidence):
        """Two passes maximum. No proposed reference/integral is committed here."""
        cfg=self.cfg.feedback
        previous=work['feedback']
        active=torch.tensor([work['prepared'] and work['phase'] != Phase.APPROACH],device=q.device)
        yaw=work.get('yaw',q.new_zeros(1))
        dt=s.dt[i:i+1].to(q.dtype)
        proposal=propose_feedback(requested.body.pos_w,s.root_pos_w[i:i+1],yaw,previous,dt,cfg,active=active)
        integral_limit=q.new_tensor([cfg.integral_limit_x,cfg.integral_limit_yz,cfg.integral_limit_yz])
        ki=q.new_tensor([cfg.ki_x,cfg.ki_yz,cfg.ki_yz])
        limit=q.new_tensor([cfg.output_limit_x,cfg.output_limit_yz,cfg.output_limit_yz])
        slew=dt[:,None]*q.new_tensor([cfg.slew_rate_x,cfg.slew_rate_yz,cfg.slew_rate_yz])
        increment=previous.integral+torch.where(active[:,None],ki*proposal.error_h*dt[:,None],torch.zeros_like(q[:,:3]))
        evidence.update(feedback_active=int(active[0]),feedback_error_h=proposal.error_h,
            feedback_integral_before=previous.integral,feedback_integral_candidate=proposal.integral_candidate,
            feedback_raw_output=proposal.raw_output,feedback_output_before=previous.output,
            feedback_proposed_output=proposal.output,
            feedback_integral_limited=(increment.abs()>integral_limit)&active[:,None],
            feedback_amplitude_limited=proposal.raw_output.abs()>limit,
            feedback_slew_limited=(proposal.raw_output.clamp(-limit,limit)-previous.output).abs()>slew,
            wheel_nominal=nominal_speed.clone())
        wheel_limit=M1_WHEEL_RADIUS_M*M1_WHEEL_SPEED_LIMIT_RAD_S
        # Fixed nominal/yaw wheel values: intersect total headroom with the
        # approved correction amplitude and actual prior correction slew.
        lower=torch.maximum((-wheel_limit-nominal_speed).amax(-1),previous.output[:,0]-slew[:,0])
        upper=torch.minimum((wheel_limit-nominal_speed).amin(-1),previous.output[:,0]+slew[:,0])
        lower=torch.maximum(lower,q.new_full((1,),-cfg.output_limit_x))
        upper=torch.minimum(upper,q.new_full((1,),cfg.output_limit_x))
        headroom_ok=lower <= upper
        def wheel_bound(p):
            output=p.output.clone()
            output[:,0]=torch.maximum(lower,torch.minimum(upper,output[:,0]))
            # Keep a finite bounded diagnostic proposal even for empty intersections.
            output[:,0]=torch.where(headroom_ok,output[:,0],p.output[:,0])
            limited=p.limited.clone(); limited[:,0] |= (output[:,0] != p.output[:,0]) | ~headroom_ok
            return replace(p,output=output,limited=limited)
        proposal=wheel_bound(proposal)
        evidence.update(feedback_limited=proposal.limited,
            wheel_headroom_limited=int(bool(proposal.limited[0,0] and
                ((proposal.output[0,0] != evidence['feedback_proposed_output'][0,0]) or not headroom_ok[0]))))
        def execution_valid(ik,output):
            speed=nominal_speed+output[:,0,None]
            action,encoded=encode_targets(ik.q,speed,s.default_joint_pos[i:i+1])
            actual=m1_action_targets(action,s.default_joint_pos[i:i+1])[:,LEG_COLUMNS]
            continuous=((actual-s.last_applied_leg_target[i:i+1]).abs() <= self.cfg.joint_target_rate_rad_s*float(dt[0])).all(-1)
            correction_slew=((output-previous.output).abs() <= slew+torch.finfo(q.dtype).eps).all(-1)
            return encoded & continuous & headroom_ok & correction_slew
        def solve(p):
            return backtrack_feedback_reference(accepted,requested,previous.output,p.output,yaw,q,branch,
                s.last_applied_leg_target[i:i+1],float(dt[0]),self.ik_cfg,execution_valid=execution_valid)
        solved=solve(proposal)
        evidence.update(feedback_first_backtrack_index=int(solved.backtrack_index[0]),
                        feedback_first_transaction_valid=int(solved.valid[0]))
        selected=select_integral(previous,proposal,safe=torch.ones_like(active),
            transaction_valid=solved.valid,backtracked=solved.backtrack_index>0)
        # Inactive successful transitions clear I while only slewing outputs.
        if not bool(active[0]) and bool(solved.valid[0]): selected=torch.zeros_like(selected)
        evidence['feedback_passes']=1
        final=proposal
        if not torch.equal(selected,proposal.integral_candidate):
            final=wheel_bound(recompute_feedback(proposal.error_h,previous,dt,cfg,active=active,integral=selected))
            solved=solve(final); evidence['feedback_passes']=2
        evidence.update(feedback_integral_selected=selected,feedback_final_proposed_output=final.output,
            command_requested=feedback_command(requested,final.output,yaw),command_attempted=solved.command,
            attempted=solved.physical,ik=solved.command_ik,nominal_ik=solved.nominal_ik,
            backtrack_index=int(solved.backtrack_index[0]),wheel_final=nominal_speed+solved.output[:,0,None])
        return solved,selected

    def _diagnostics(self, s, i, row, evidence, valid, freeze, diagnostic):
        data = s.root_pos_w.new_full((1, len(TEACHER_DIAGNOSTIC_FIELDS)), float('nan'))
        values = dict(zip(TEACHER_DIAGNOSTIC_INTEGER_FIELDS, [-1]*len(TEACHER_DIAGNOSTIC_INTEGER_FIELDS)))
        def put(prefix, tensor, suffixes):
            if tensor is not None:
                values.update(zip((prefix+x for x in suffixes), tensor.reshape(-1).tolist()))
        pose_fields = ('x', 'y', 'z', 'qw', 'qx', 'qy', 'qz')
        for kind in ('prior', 'goal'):
            ref = evidence.get('preparation_'+kind)
            if ref is not None:
                put('preparation_'+kind+'_root_', torch.cat((ref.body.pos_w, ref.body.quat_w), -1), pose_fields)
        put('measured_root_', torch.cat((s.root_pos_w[i], s.root_quat_w[i])), pose_fields)
        for kind in ('requested', 'attempted', 'accepted'):
            ref = row.get('accepted') if kind == 'accepted' else evidence.get(kind)
            if ref is not None:
                put(kind+'_root_', torch.cat((ref.body.pos_w, ref.body.quat_w), -1), pose_fields)
                put(kind+'_world_wheel_', ref.wheels_w,
                    tuple(f'{leg}_{axis}' for leg in range(4) for axis in ('x', 'y', 'z')))
                if kind != 'requested':
                    put(kind+'_body_wheel_', world_to_goal_body(ref),
                        tuple(f'{leg}_{axis}' for leg in range(4) for axis in ('x', 'y', 'z')))
            command = row.get('accepted_command') if kind == 'accepted' else evidence.get('command_'+kind)
            if command is not None:
                put('command_'+kind+'_root_',torch.cat((command.body.pos_w,command.body.quat_w),-1),pose_fields)
                put('command_'+kind+'_world_wheel_',command.wheels_w,
                    tuple(f'{leg}_{axis}' for leg in range(4) for axis in ('x','y','z')))
        put('com_', s.com_pos_w[i], ('x', 'y', 'z'))
        put('last_applied_q_', s.last_applied_leg_target[i], tuple(str(j) for j in range(12)))
        put('accepted_q_', row.get('last_q'), tuple(str(j) for j in range(12)))
        result = evidence.get('ik')
        if result is not None:
            for field in ('residual_m', 'joint_limit_ok', 'branch_ok', 'extension_margin_rad',
                          'workspace_ok', 'iterations', 'reason'):
                put('ik_'+field+'_', getattr(result, field), tuple(str(j) for j in range(4)))
            put('attempted_q_', result.q, tuple(str(j) for j in range(12)))
        nominal=evidence.get('nominal_ik')
        if nominal is not None:
            for name in ('residual_m','joint_limit_ok','branch_ok','extension_margin_rad','workspace_ok','iterations','reason'):
                put('nominal_ik_'+name+'_',getattr(nominal,name),tuple(str(j) for j in range(4)))
        for kind in ('error_h','integral_before','integral_candidate','integral_selected','raw_output',
                     'proposed_output','output_before','limited','integral_limited','amplitude_limited',
                     'slew_limited','final_proposed_output'):
            put('feedback_'+kind+'_',evidence.get('feedback_'+kind),('x','y','z'))
        put('feedback_integral_committed_',row['feedback'].integral,('x','y','z'))
        put('feedback_output_committed_',row['feedback'].output,('x','y','z'))
        for kind in ('nominal','final'):
            put('wheel_'+kind+'_surface_speed_',evidence.get('wheel_'+kind),tuple(str(j) for j in range(4)))
        for name in ('feedback_passes','wheel_headroom_limited','feedback_active',
                     'feedback_first_backtrack_index','feedback_first_transaction_valid'):
            values[name]=evidence.get(name,-1 if name == 'feedback_first_backtrack_index' else 0)
        put('support_slip_', evidence.get('slip'), tuple(f'{j}_{a}' for j in range(4) for a in ('x', 'y')))
        for name in ('measured_com_margin_m', 'predicted_com_margin_m', 'candidate_com_margin_m', 'candidate_index',
                     'candidate_count', 'backtrack_index'):
            if name in evidence:
                values[name] = evidence[name]
        values.update(invalid_streak=row['invalid_streak'], freeze_reason=int(freeze),
                      reference_valid=int(valid), diagnostic_only=int(diagnostic is not None),
                      age=row['age'], body_age=row['body_age'], lift_age=row['lift_age'],
                      preparation_ready=int(valid and evidence.get('preparation_ready', False)))
        for name, value in values.items():
            data[0, TEACHER_DIAGNOSTIC_FIELDS.index(name)] = value
        return data

    def _output(self, s, i, row, action, valid, reason, evidence, freeze, diagnostic, executable=True):
        if not valid:
            row['stable'] = 0
        device = s.root_pos_w.device
        out = TeacherOutput(action.clone(), torch.tensor([valid and diagnostic is None], device=device),
            torch.tensor([int(row['phase'])], device=device), torch.tensor([row['wheel']], device=device),
            torch.tensor([row['target'] if diagnostic is None else -1], device=device),
            torch.tensor([int(reason)], device=device),
            self._diagnostics(s, i, row, evidence, valid, freeze, diagnostic),
            torch.tensor([row['failure'] != Reason.OK], device=device),
            torch.tensor([executable], dtype=torch.bool, device=device))
        row['output'] = out
        return self._clone_output(out)

    def _step_row(self, s, i, diagnostic):
        cfg, evidence = self.cfg, {}
        row = self._rows[i]
        episode, step, reset = int(s.episode_id[i]), int(s.control_step[i]), bool(s.reset_mask[i])
        changed = row is not None and row['episode'] != episode
        if row is None or changed or (reset and (row['step'] != step or not row['reset'])):
            row = dict(episode=episode, step=-1, reset=False, target=-1, wheel=-1,
                       phase=Phase.APPROACH, age=0, body_age=0, lift_age=0, stable=0,
                       prepared=False, failure=Reason.OK, invalid_streak=0,
                       feedback=FeedbackState(s.root_pos_w.new_zeros(1,3),s.root_pos_w.new_zeros(1,3)))
            self._rows[i] = row
        if row['step'] == step and row['reset'] == reset:
            return self._clone_output(row['output'])
        if step < row['step']:
            row['failure'] = Reason.STALE_STEP
        if step != row['step']+1:
            row['stable'] = 0
            row['invalid_streak'] = 0
        row['step'], row['reset'] = step, reset

        def fail(reason, freeze, lock=False, count=False):
            if count:
                row['invalid_streak'] += 1
                lock |= row['invalid_streak'] >= cfg.invalid_lock_steps
            if lock:
                row['failure'] = reason
            action, executable = self._fallback(s, i, row)
            return self._output(s, i, row, action, False, reason,
                                evidence, freeze, diagnostic, executable)

        if reset or changed:
            return fail(Reason.RESET, FreezeReason.RESET)
        if row['failure'] != Reason.OK:
            return fail(row['failure'], FreezeReason.LOCKED)
        finite = all(bool(torch.isfinite(getattr(s, f.name)[i]).all()) for f in fields(s)
                     if getattr(s, f.name).is_floating_point())
        finite &= bool((s.root_quat_w[i].norm()-1).abs() <= 1e-3)
        finite &= bool(((s.wheel_quat_w[i].norm(dim=-1)-1).abs() <= 1e-3).all())
        if not finite:
            return fail(Reason.NONFINITE, FreezeReason.SAFETY, lock=row['prepared'], count=True)
        if not bool(s.measurement_valid[i]):
            return fail(Reason.MEASUREMENT_INVALID, FreezeReason.SAFETY, lock=row['prepared'], count=True)
        if not bool(s.applied_target_valid[i]):
            return fail(Reason.APPLIED_TARGET_INVALID, FreezeReason.SAFETY, count=True)
        if bool(s.collision[i]):
            return fail(Reason.COLLISION, FreezeReason.SAFETY, lock=True)

        # Scratch state: tensors already stored on the row are immutable here.
        # No phase, reference, anchor or age change escapes a rejected transaction.
        work = dict(row)
        decaying = row['phase'] == Phase.APPROACH and bool(row['feedback'].output.any())
        q, defaults = s.leg_pos[i:i+1], s.default_joint_pos[i:i+1]
        measured = self._reference(s, i)
        rpy = quaternion_rpy(measured.body.quat_w)
        upward = s.wheel_force_w[i, :, 2]
        horizontal = s.wheel_force_w[i, :, :2].norm(dim=-1)
        bearing = (upward > cfg.support_min_force_n) & (horizontal <= cfg.support_max_tangential_ratio*upward)
        if diagnostic is not None:
            work.update(wheel=diagnostic[0], target=-1)
            if work['phase'] == Phase.APPROACH:
                work.update(phase=Phase.BALANCE, age=0)
        elif work['target'] < 0:
            pending = s.required_wheels[i] & s.course_valid[i, :, None] & ~s.recovered[i]
            if bool(pending.any()):
                candidates = pending.nonzero()
                selected = (s.centers_top[i, candidates[:, 0], 0]*8+candidates[:, 1]*1e-4).argmin()
                target, wheel = candidates[selected].tolist()
                work.update(target=target, wheel=wheel, target_id=int(s.course_ids[i, target]),
                            phase=Phase.APPROACH, age=0, body_age=0, lift_age=0, stable=0, prepared=False)
                if not decaying:
                    for key in ('anchor', 'anchor_pose', 'wheel_anchor', 'support_origin', 'lift_start_z', 'goal'):
                        work.pop(key, None)
        target, wheel, phase = work['target'], work['wheel'], work['phase']
        active = wheel >= 0
        support = [k for k in range(4) if k != wheel]
        support_ready = active and bool(bearing[support].all())
        if active:
            margin, margin_valid = support_margin(s.com_pos_w[i:i+1], measured.wheels_w,
                                                  torch.tensor([wheel], device=q.device))
            evidence['measured_com_margin_m'] = float(margin[0])
            measured_com_ok = bool(margin_valid[0] and margin[0] >= cfg.com_margin_m)
        else:
            measured_com_ok = False
        if row['prepared'] and not support_ready:
            return fail(Reason.SUPPORT_LOST, FreezeReason.SAFETY, lock=True)
        near_x = far_x = bottom = None
        if diagnostic is None and active:
            if (target >= s.course_valid.shape[1] or not bool(s.course_valid[i, target])
                    or int(s.course_ids[i, target]) != work['target_id']
                    or not bool(s.required_wheels[i, target, wheel])):
                return fail(Reason.TARGET_CHANGED, FreezeReason.SAFETY, lock=True)
            center, half = s.centers_top[i, target], s.half_extents[i, target]
            if bool((half <= 0).any()):
                return fail(Reason.NONFINITE, FreezeReason.SAFETY, lock=row['prepared'], count=True)
            near_x = center[0]-half[0]-M1_WHEEL_HORIZONTAL_ENVELOPE_M-cfg.approach_gap_m
            far_x = center[0]+half[0]+M1_WHEEL_HORIZONTAL_ENVELOPE_M+cfg.far_margin_m
            bottom = cylinder_bottom(measured.wheels_w, s.wheel_quat_w[i:i+1])[0, wheel]
        speed = q.new_full((1, 4), cfg.flat_speed_m_s)
        freeze, finish = FreezeReason.NONE, False
        accepted = work.get('accepted', measured)
        branch = work.get('branch_q', q)
        tracked = self._tracked(s, i, accepted)
        if phase == Phase.APPROACH and active:
            distance = near_x-measured.wheels_w[0, wheel, 0]
            speed[:] = min(cfg.cruise_speed_m_s, max(0., float(distance)*cfg.approach_gain_s_inv))
            if distance <= cfg.approach_capture_m and not decaying:
                work.update(phase=Phase.BALANCE, age=0)
                phase = Phase.BALANCE
                speed.zero_()
                # The next measured sample, not the capture transition itself,
                # decides whether braking has finished.
        if phase == Phase.BALANCE and not work['prepared']:
            speed.zero_()
            freeze = FreezeReason.BRAKING
            was_balancing = row['phase'] == Phase.BALANCE or diagnostic is not None
            if was_balancing and bool(bearing.all()) and self._quiet(s, i):
                yaw = rpy[:, 2]
                work.update(prepared=True, anchor=measured.body.pos_w.clone(), anchor_pose=measured.body,
                            yaw=yaw.clone(), wheel_anchor=measured.wheels_w.clone(),
                            support_origin=measured.wheels_w[:, support].mean(1).clone(),
                            support_previous=measured.wheels_w.clone(),
                            lift_start_z=measured.wheels_w[0, wheel, 2].clone(),
                            branch_q=q.clone(), body_age=0, lift_age=0)
                accepted, branch, tracked = measured, q, True
        if not work['prepared']:
            # Rolling and braking have the same constrained IK/slew transaction.
            # Re-express the previous commanded joint geometry at measured root;
            # this does not capture a world support anchor during motion.
            rotation = rpy_to_rotation_matrix(rpy)
            last = work.get('last_q', s.last_applied_leg_target[i:i+1])
            accepted = (work['accepted'] if decaying else
                PoseReference(measured.body, measured.body.pos_w[:, None]
                    +torch.einsum('bij,bkj->bki', rotation, body_feet(last))))
            requested = PoseReference(measured.body, measured.body.pos_w[:, None]
                                      +torch.einsum('bij,bkj->bki', rotation, body_feet(defaults[:, LEG_COLUMNS])))
        else:
            speed.zero_()
            goal = work.get('goal', accepted)
            if phase == Phase.BALANCE:
                choice = choose_support_pose(measured.body, work['anchor_pose'], accepted.body,
                    s.com_pos_w[i:i+1], work['wheel_anchor'], torch.tensor([wheel], device=q.device),
                    s.nominal_root_z_w[i:i+1], q, branch, self.ik_cfg)
                evidence.update(requested=choice.reference, attempted=choice.reference, ik=choice.ik,
                    predicted_com_margin_m=float(choice.predicted_margin_m[0]),
                    candidate_com_margin_m=float(choice.predicted_margin_m[0]),
                    candidate_index=int(choice.candidate_index[0]), candidate_count=int(choice.candidate_count[0]))
                if not bool(choice.valid[0]):
                    return fail(Reason.IK_INVALID, FreezeReason.IK, count=True)
                # Explicit level attitude; the accepted-pose search candidate
                # may retain captured tilt, which must not become a new goal.
                yaw = work['yaw']
                level = torch.stack((torch.cos(yaw/2), torch.zeros_like(yaw),
                                     torch.zeros_like(yaw), torch.sin(yaw/2)), -1)
                goal = PoseReference(BodyPose(choice.reference.body.pos_w, level), choice.reference.wheels_w)
                work['goal'] = goal
                ready = tracked and self._tracked(s, i, goal) and measured_com_ok and support_ready and self._quiet(s, i)
                # Same decision, before the accepted reference is replaced. Capture
                # alone is not readiness; rejected transactions cannot certify it.
                evidence.update(preparation_prior=accepted, preparation_goal=goal,
                                preparation_ready=ready and row['prepared'])
                if ready and row['prepared'] and (diagnostic is None or diagnostic[1]):
                    work.update(phase=Phase.LIFT, age=0)
                    phase = Phase.LIFT
                else:
                    freeze = FreezeReason.PREPARATION
            elif phase == Phase.LIFT:
                if diagnostic is None:
                    clear = bool(bottom > center[2])
                else:
                    height = cfg.front_max_lift_m if wheel < 2 else cfg.rear_max_lift_m
                    clear = bool(measured.wheels_w[0, wheel, 2] >= work['lift_start_z']+height-cfg.ik_tolerance_m)
                if clear and tracked:
                    work.update(phase=Phase.PASS if diagnostic is None else Phase.RESTORE, age=0)
                    phase = work['phase']
            elif phase == Phase.PASS and tracked and measured.wheels_w[0, wheel, 0] > far_x:
                work.update(phase=Phase.RESTORE, age=0)
                phase = Phase.RESTORE

            if tracked:
                work['age'] += 1
                if phase != Phase.RESTORE:
                    work['body_age'] += 1
                if phase in (Phase.LIFT, Phase.PASS):
                    work['lift_age'] += 1
            else:
                freeze = FreezeReason.TRACKING

            # Progress advances only from measured previous accepted root pose.
            # Wheel/body targets are all world coordinates until the one full
            # desired-body transform in backtrack_reference.
            root_goal = goal.body.pos_w
            quat_goal = goal.body.quat_w
            wheels_goal = work['wheel_anchor'].clone()
            if phase == Phase.PASS:
                displacement = measured.wheels_w[:, support, :2]-work['support_previous'][:, support, :2]
                common = displacement.mean(1)
                slip = q.new_zeros(1, 4, 2)
                slip[:, support] = displacement-common[:, None]
                evidence['slip'] = slip
                anchor_w = work['wheel_anchor'].clone()
                anchor_w[:, :, :2] += common[:, None]
                work['wheel_anchor'] = anchor_w
                work['support_previous'] = measured.wheels_w.clone()
                root_goal = goal.body.pos_w.clone()
                root_goal[:, :2] += common
                goal = PoseReference(BodyPose(root_goal, quat_goal), anchor_w)
                work['goal'] = goal
                # Transport both ends by the same common rolling displacement;
                # this introduces no artificial support-joint motion or tilt.
                p = accepted.body.pos_w.clone()
                p[:, :2] += common
                w = accepted.wheels_w.clone()
                w[:, :, :2] += common[:, None]
                accepted = PoseReference(BodyPose(p, accepted.body.quat_w), w)
                wheels_goal = anchor_w.clone()
                speed[:] = cfg.pass_speed_m_s*min(1., work['age']/cfg.pass_steps)
            if phase in (Phase.LIFT, Phase.PASS):
                maximum = cfg.front_max_lift_m if wheel < 2 else cfg.rear_max_lift_m
                end_z = (work['lift_start_z']+maximum if diagnostic is not None
                         else s.ground_z[i, target]+M1_WHEEL_RADIUS_M+maximum)
                wheels_goal[0, wheel, 2] = work['lift_start_z']+(end_z-work['lift_start_z'])*min(1., work['lift_age']/cfg.lift_steps)
            if phase == Phase.RESTORE:
                root_goal = work['anchor'].clone()
                # Preserve rolling displacement in XY while restoring captured
                # height and heading through the very same world reference IK.
                root_goal[:, :2] += work['wheel_anchor'][:, support, :2].mean(1)-work['support_origin'][:, :2]
                quat_goal = goal.body.quat_w
                wheels_goal = work['wheel_anchor'].clone()
            horizon = cfg.restore_steps if phase == Phase.RESTORE else cfg.balance_steps
            remaining = max(1, horizon-work['age']+1) if phase == Phase.RESTORE else max(1, horizon-work['body_age']+1)
            alpha = 1./remaining if tracked else 0.
            position = accepted.body.pos_w+alpha*(root_goal-accepted.body.pos_w)
            # Short-arc normalized interpolation is sufficient for <=.15rad
            # captured tilt; backtracking itself uses exact shortest-arc SLERP.
            end = torch.where((accepted.body.quat_w*quat_goal).sum(-1, keepdim=True) < 0, -quat_goal, quat_goal)
            quat = accepted.body.quat_w+alpha*(end-accepted.body.quat_w)
            quat = quat/quat.norm(dim=-1, keepdim=True)
            if not tracked:
                wheels_goal = accepted.wheels_w
            if phase == Phase.RESTORE:
                wheels_goal = accepted.wheels_w+alpha*(wheels_goal-accepted.wheels_w)
            requested = PoseReference(BodyPose(position, quat), wheels_goal)

            if phase == Phase.RESTORE:
                safe = crossing_touchdown_safe(support_contact=s.wheel_force_w[i:i+1].norm(dim=-1) > cfg.target_min_force_n,
                    support_force=s.wheel_force_w[i:i+1].norm(dim=-1),
                    target_wheel=torch.tensor([wheel], device=q.device),
                    target_min_force=cfg.target_min_force_n, support_min_force=cfg.support_min_force_n)
                stable = bool(safe[0]) and tracked
                stable &= bool(rpy[:, :2].abs().amax() <= cfg.recovery_tilt_rad)
                stable &= bool(s.root_ang_vel_w[i].norm() <= cfg.recovery_rate_rad_s)
                stable &= bool((horizontal <= cfg.support_max_tangential_ratio*upward).all() and upward[wheel] > cfg.target_min_force_n)
                stable &= bool((q-defaults[:, LEG_COLUMNS]).abs().amax() <= cfg.recovery_pose_rad)
                stable &= bool((s.root_pos_w[i, 2]-s.nominal_root_z_w[i]).abs() <= cfg.recovery_height_m)
                stable &= diagnostic is not None or bool(measured.wheels_w[0, wheel, 0] > far_x)
                work['stable'] = work['stable']+1 if stable else 0
                finish = (work['stable'] >= cfg.stable_samples
                          and diagnostic is None and bool(s.recovered[i, target, wheel]))

        evidence['requested'] = requested
        if bool((speed != 0).any()):
            heading = work['yaw'] if work['prepared'] else rpy.new_zeros(1)
            yaw_error = rpy[:, 2]-heading
            yaw_error = torch.atan2(yaw_error.sin(), yaw_error.cos())
            speed += -cfg.yaw_gain_s_inv*yaw_error[:, None]*q.new_tensor([-.215, .215, -.215, .215])
        solved,selected_integral=self._feedback_transaction(s,i,work,accepted,requested,q,branch,speed,evidence)
        if active:
            measured_rotation = rpy_to_rotation_matrix(rpy)
            com_offset = torch.einsum('bij,bj->bi', measured_rotation.transpose(-1, -2),
                                     s.com_pos_w[i:i+1]-measured.body.pos_w)
            goal_rotation = rpy_to_rotation_matrix(quaternion_rpy(solved.physical.body.quat_w))
            predicted = solved.physical.body.pos_w+torch.einsum('bij,bj->bi', goal_rotation, com_offset)
            predicted_margin, _ = support_margin(predicted, solved.physical.wheels_w,
                                                  torch.tensor([wheel], device=q.device))
            evidence['predicted_com_margin_m'] = float(predicted_margin[0])
        if not bool(solved.valid[0]):
            return fail(Reason.IK_INVALID, FreezeReason.IK, count=True)
        action, encoded = encode_targets(solved.command_ik.q, speed+solved.output[:,0,None], defaults)
        actual = m1_action_targets(action, defaults)[:, LEG_COLUMNS]
        continuous = bool(((actual-s.last_applied_leg_target[i:i+1]).abs() <= cfg.joint_target_rate_rad_s*float(s.dt[i])).all())
        if not bool(encoded[0]) or not continuous:
            return fail(Reason.ACTION_INVALID, FreezeReason.ACTION, count=True)
        work.update(accepted=solved.physical,accepted_command=solved.command,
                    feedback=FeedbackState(selected_integral.clone(),solved.output.clone()),
                    last_q=actual.clone(), branch_q=branch.clone(), invalid_streak=0)
        if work['prepared'] and phase != Phase.PASS:
            # Baseline for the next measured rolling increment, without moving
            # any preparation anchor. Old preparation slip is not PASS motion.
            work['support_previous'] = measured.wheels_w.clone()
        if finish:
            work.update(target=-1, wheel=-1, phase=Phase.APPROACH, age=0, body_age=0,
                        lift_age=0, stable=0, prepared=False,
                        feedback=FeedbackState(torch.zeros_like(selected_integral),solved.output.clone()))
        row.update(work)
        return self._output(s, i, row, action, True, Reason.OK, evidence, freeze, diagnostic)
