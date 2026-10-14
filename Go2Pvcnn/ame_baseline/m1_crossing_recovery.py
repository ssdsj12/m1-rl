"""Pure measured crossing/recovery outcome, with no control or simulator access.

Quaternions use wxyz; the wheel is the authored Y-axis cylinder (radius
0.0959 m, full width 0.0465 m). ``recovered`` is already explicitly mapped to
the frozen ``scope.course_ids`` by the caller; tensor positions cannot prove
receipt identity. Structural/identity mistakes raise, numeric bad rows clear
their recovery window. Only explicit ``reset`` clears unsafe history.
"""
from dataclasses import dataclass, fields
import math

import torch


RECOVERY_CONTRACT = 'crossing-recovery-0p3-v1'


@dataclass(frozen=True)
class RecoveryScope:
    env_id: torch.Tensor
    episode_id: torch.Tensor
    scope_id: torch.Tensor
    course_ids: torch.Tensor
    required: torch.Tensor
    centers_w: torch.Tensor
    half_extents: torch.Tensor
    forward_w: torch.Tensor


@dataclass(frozen=True)
class RecoveryFrame:
    env_id: torch.Tensor
    episode_id: torch.Tensor
    scope_id: torch.Tensor
    frame: torch.Tensor
    sim_time_s: torch.Tensor
    dt_s: torch.Tensor
    root_state_w: torch.Tensor
    leg_pos: torch.Tensor
    default_leg_pos: torch.Tensor
    wheel_pos_w: torch.Tensor
    wheel_quat_w: torch.Tensor
    wheel_force_w: torch.Tensor
    nominal_root_z_w: torch.Tensor
    recovered: torch.Tensor
    valid: torch.Tensor
    collision: torch.Tensor
    penetration: torch.Tensor
    base_contact: torch.Tensor
    physical_failure: torch.Tensor
    reset: torch.Tensor
    ended: torch.Tensor


@dataclass(frozen=True)
class RecoveryResult:
    eligible: torch.Tensor
    stable: torch.Tensor
    success: torch.Tensor
    vetoed: torch.Tensor
    interval_count: torch.Tensor
    start_frame: torch.Tensor
    last_frame: torch.Tensor
    elapsed_s: torch.Tensor
    start_time_s: torch.Tensor
    net_forward_m: torch.Tensor
    reason: tuple[str, ...]


_IDS = ('env_id', 'episode_id', 'scope_id')
_UNSAFE = ('collision', 'penetration', 'base_contact', 'physical_failure')
_FLOAT_FRAME = ('sim_time_s', 'dt_s', 'root_state_w', 'leg_pos', 'default_leg_pos',
                'wheel_pos_w', 'wheel_quat_w', 'wheel_force_w', 'nominal_root_z_w')


def _tensor(value, shape, dtype, device, name):
    if (not isinstance(value, torch.Tensor) or value.shape != shape
            or value.dtype != dtype or value.device != device):
        raise ValueError(f'{name} must have shape {shape}, dtype {dtype}, device {device}')


def _scope_shape(scope):
    if not isinstance(scope, RecoveryScope):
        raise TypeError('scope must be RecoveryScope')
    if (not isinstance(scope.centers_w, torch.Tensor) or scope.centers_w.ndim != 3
            or scope.centers_w.shape[-1] != 3
            or scope.centers_w.dtype not in (torch.float32, torch.float64)):
        raise ValueError('centers_w must be float32/float64 [B,C,3]')
    batch, courses, _ = scope.centers_w.shape
    dtype, device = scope.centers_w.dtype, scope.centers_w.device
    for name in _IDS:
        _tensor(getattr(scope, name), (batch,), torch.long, device, name)
    _tensor(scope.course_ids, (batch, courses), torch.long, device, 'course_ids')
    _tensor(scope.required, (batch, courses, 4), torch.bool, device, 'required')
    _tensor(scope.half_extents, (batch, courses, 2), dtype, device, 'half_extents')
    _tensor(scope.forward_w, (batch, 3), dtype, device, 'forward_w')
    if scope.env_id.unique().numel() != batch:
        raise ValueError('env_id must uniquely identify each row')
    if any(bool((getattr(scope, name) < 0).any()) for name in _IDS):
        raise ValueError('scope identity must be nonnegative')
    if courses > 1:
        ordered = scope.course_ids.sort(dim=-1).values
        if bool((ordered[:, 1:] == ordered[:, :-1]).any()):
            raise ValueError('course_ids must be unique within each scope row')
    if (not all(bool(torch.isfinite(getattr(scope, name)).all()) for name in
                ('centers_w', 'half_extents', 'forward_w'))
            or bool((scope.half_extents <= 0).any())):
        raise ValueError('scope geometry must be finite with positive half_extents')
    forward = scope.forward_w.double()
    tol = 8*torch.finfo(dtype).eps
    if bool(((forward[:, 2].abs() > tol) | ((forward.norm(dim=-1)-1).abs() > tol)).any()):
        raise ValueError('forward_w must be a fixed horizontal unit vector')
    return batch, courses, dtype, device


def _same(left, right):
    equal = left == right
    if left.is_floating_point():
        equal = equal | (torch.isnan(left) & torch.isnan(right))
    return bool(equal.all())


def _unit_quaternion(quat):
    value = quat.double()
    return value / value.norm(dim=-1, keepdim=True).clamp_min(torch.finfo(torch.float64).tiny)


class CrossingRecoveryTracker:
    """Consume a full batch; freeze scope and isolate each environment window.

    ``stable`` means this observation qualifies. Success additionally requires
    at least 0.3 s of adjacent qualifying intervals and 0.01 m net forward root
    displacement. Neither flag is latched; unsafe and terminal history is.
    ``last_frame`` is the window's final observation, -1 without a window.
    """

    def __init__(self, scope: RecoveryScope):
        self._batch, self._courses, self._dtype, self._device = _scope_shape(scope)
        self._scope = RecoveryScope(**{f.name: getattr(scope, f.name).detach().clone() for f in fields(scope)})
        self._previous = [None] * self._batch
        self._unsafe = [[] for _ in range(self._batch)]
        self._terminal = [''] * self._batch
        self._reason = ['pending'] * self._batch
        self._state = {}
        for name in ('eligible', 'stable', 'success', 'vetoed'):
            self._state[name] = torch.zeros(self._batch, dtype=torch.bool, device=self._device)
        for name in ('interval_count', 'start_frame', 'last_frame'):
            self._state[name] = torch.full((self._batch,), 0 if name == 'interval_count' else -1,
                                            dtype=torch.long, device=self._device)
        for name in ('elapsed_s', 'start_time_s', 'net_forward_m'):
            self._state[name] = torch.full((self._batch,), 0. if name == 'elapsed_s' else math.nan,
                                            dtype=torch.float64, device=self._device)
        self._start_pos = torch.full((self._batch, 3), math.nan, dtype=torch.float64, device=self._device)
        self._min_dt = torch.full((self._batch,), math.inf, dtype=torch.float64, device=self._device)

    def _clear_window(self, index):
        for name in ('interval_count', 'elapsed_s'):
            self._state[name][index] = 0
        for name in ('start_frame', 'last_frame'):
            self._state[name][index] = -1
        for name in ('start_time_s', 'net_forward_m'):
            self._state[name][index] = math.nan
        self._start_pos[index] = math.nan
        self._min_dt[index] = math.inf

    def reset(self, rows: torch.Tensor, scope: RecoveryScope) -> None:
        """Replace selected rows using a scope subbatch in selection order.

        A bool [B] mask selects rows in increasing order; a long [N] tensor
        specifies the order. C/device/state dtype and environment IDs are fixed.
        """
        if not isinstance(rows, torch.Tensor) or rows.device != self._device or rows.ndim != 1:
            raise ValueError('rows must be a one-dimensional tensor on the scope device')
        if rows.dtype == torch.bool:
            if rows.shape != (self._batch,):
                raise ValueError('bool rows must have shape [B]')
            indices = rows.nonzero().flatten()
        elif rows.dtype == torch.long:
            indices = rows
        else:
            raise ValueError('rows must have long indices or a bool mask')
        if (indices.unique().numel() != indices.numel()
                or bool(((indices < 0) | (indices >= self._batch)).any())):
            raise ValueError('rows must be unique valid indices')
        expected = (indices.numel(), self._courses, self._dtype, self._device)
        if _scope_shape(scope) != expected:
            raise ValueError('reset scope must be a matching selected-row subbatch')
        if not torch.equal(scope.env_id, self._scope.env_id[indices]):
            raise ValueError('reset scope environment identity must match selected rows')
        # Complete validation precedes any mutation, including the frozen scope.
        for f in fields(scope):
            getattr(self._scope, f.name)[indices] = getattr(scope, f.name).detach().clone()
        for index in indices.tolist():
            self._previous[index] = None
            self._unsafe[index] = []
            self._terminal[index] = ''
            self._reason[index] = 'pending'
            for name in ('eligible', 'stable', 'success', 'vetoed'):
                self._state[name][index] = False
            self._clear_window(index)

    def _validate_frame(self, frame):
        if not isinstance(frame, RecoveryFrame):
            raise TypeError('frame must be RecoveryFrame')
        batch, courses = self._batch, self._courses
        for name in (*_IDS, 'frame'):
            _tensor(getattr(frame, name), (batch,), torch.long, self._device, name)
        shapes = {'sim_time_s': (batch,), 'dt_s': (batch,), 'root_state_w': (batch, 13),
                  'leg_pos': (batch, 12), 'default_leg_pos': (batch, 12),
                  'wheel_pos_w': (batch, 4, 3), 'wheel_quat_w': (batch, 4, 4),
                  'wheel_force_w': (batch, 4, 3), 'nominal_root_z_w': (batch,)}
        for name, shape in shapes.items():
            _tensor(getattr(frame, name), shape, self._dtype, self._device, name)
        _tensor(frame.recovered, (batch, courses, 4), torch.bool, self._device, 'recovered')
        for name in ('valid', *_UNSAFE, 'reset', 'ended'):
            _tensor(getattr(frame, name), (batch,), torch.bool, self._device, name)
        if any(not torch.equal(getattr(frame, name), getattr(self._scope, name)) for name in _IDS):
            raise ValueError('frame identity must match frozen env/episode/scope identity')

    def _conditions(self, frame):
        scope = self._scope
        finite = torch.ones(self._batch, dtype=torch.bool, device=self._device)
        for name in _FLOAT_FRAME:
            finite &= torch.isfinite(getattr(frame, name)).reshape(self._batch, -1).all(-1)
        root = frame.root_state_w.double()
        root_norm = root[:, 3:7].norm(dim=-1)
        wheel_norm = frame.wheel_quat_w.double().norm(dim=-1)
        finite &= ((root_norm-1).abs() <= 1.e-3) & ((wheel_norm-1).abs() <= 1.e-3).all(-1)
        w, x, y, z = _unit_quaternion(frame.wheel_quat_w).unbind(-1)
        # The world-space local-Y axle; cylinder support along d is
        # width/2*|a.d| + radius*sqrt(1-(a.d)^2), exact for every direction.
        axle = torch.stack((2*(x*y-w*z), 1-2*(x*x+z*z), 2*(y*z+w*x)), -1)
        forward = scope.forward_w.double()
        axial_dot = (axle*forward[:, None]).sum(-1).abs().clamp(0, 1)
        extent = .02325*axial_dot + .0959*torch.sqrt((1-axial_dot.square()).clamp_min(0))
        wheel_rear = (frame.wheel_pos_w.double()*forward[:, None]).sum(-1)-extent
        has_obligations = scope.required.flatten(1).any(-1)
        receipts = (~scope.required | frame.recovered).flatten(1).all(-1)
        if self._courses:
            obstacle_far = ((scope.centers_w.double()*forward[:, None]).sum(-1)
                            + (scope.half_extents.double()*forward[:, None, :2].abs()).sum(-1)).amax(-1)
            far_side = (wheel_rear > obstacle_far[:, None]).all(-1)
        else:
            far_side = torch.zeros_like(has_obligations)
        eligible = finite & has_obligations & receipts & far_side
        w, x, y, z = _unit_quaternion(frame.root_state_w[:, 3:7]).unbind(-1)
        roll = torch.atan2(2*(w*x+y*z), 1-2*(x*x+y*y))
        pitch = torch.asin((2*(w*y-z*x)).clamp(-1, 1))
        yaw = torch.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
        course_yaw = torch.atan2(forward[:, 1], forward[:, 0])
        yaw_error = torch.atan2(torch.sin(yaw-course_yaw), torch.cos(yaw-course_yaw)).abs()
        force = frame.wheel_force_w.double()
        gates = {
            'invalid_data': finite & frame.valid,
            'incomplete_scope': has_obligations & receipts,
            'not_far_side': far_side,
            'tilt': torch.maximum(roll.abs(), pitch.abs()) <= .15,
            'angular_rate': root[:, 10:13].norm(dim=-1) <= .20,
            'leg_error': (frame.leg_pos.double()-frame.default_leg_pos.double()).abs().amax(-1) <= .15,
            'height_error': (root[:, 2]-frame.nominal_root_z_w.double()).abs() <= .08,
            'wheel_load': ((force[:, :, 2] > 10.) & (force[:, :, :2].norm(dim=-1) <= force[:, :, 2])).all(-1),
            'yaw_error': yaw_error <= .15,
            'forward_velocity': (root[:, 7:10]*forward).sum(-1) > 0.,
        }
        return eligible, gates

    def _time_tolerance(self, time, dt):
        # Bound representation allowance to 1/10000 of a step. Large or coarse
        # clocks that cannot prove adjacent dt must reject evidence, not round
        # an absent control interval up to a complete recovery window.
        return min(8*torch.finfo(self._dtype).eps*max(1., abs(time)), dt*1.e-4)

    @torch.no_grad()
    def update(self, frame: RecoveryFrame) -> RecoveryResult:
        self._validate_frame(frame)
        duplicates = []
        for index, previous in enumerate(self._previous):
            same_frame = previous is not None and int(frame.frame[index]) == int(previous['frame'])
            if same_frame and any(not _same(getattr(frame, f.name)[index], previous[f.name]) for f in fields(frame)):
                raise ValueError(f'conflicting duplicate frame in row {index}')
            duplicates.append(same_frame)
        eligible, gates = self._conditions(frame)
        for index, previous in enumerate(self._previous):
            if duplicates[index]:
                continue
            for name in _UNSAFE:
                if bool(getattr(frame, name)[index]) and name not in self._unsafe[index]:
                    self._unsafe[index].append(name)
            if bool(frame.reset[index]) or bool(frame.ended[index]):
                self._terminal[index] = 'reset' if bool(frame.reset[index]) else 'ended'
            self._state['vetoed'][index] = bool(self._unsafe[index])
            self._state['eligible'][index] = eligible[index]
            number = int(frame.frame[index])
            time, dt = float(frame.sim_time_s[index]), float(frame.dt_s[index])
            temporal = number >= 0 and math.isfinite(time) and time >= 0 and math.isfinite(dt) and dt > 0
            if previous is not None:
                prev_number, prev_time = int(previous['frame']), float(previous['sim_time_s'])
                temporal = temporal and number == prev_number+1
                if math.isfinite(prev_time) and temporal:
                    delta = time-prev_time
                    temporal = delta > 0 and abs(delta-dt) <= self._time_tolerance(time, dt)
            reason = ''
            if self._unsafe[index]:
                reason = 'veto:'+','.join(self._unsafe[index])
            elif self._terminal[index]:
                reason = self._terminal[index]
            elif not temporal:
                reason = 'invalid_interval'
            else:
                reason = next((name for name, ok in gates.items() if not bool(ok[index])), '')
            stable = not reason
            self._state['stable'][index] = stable
            self._state['success'][index] = False
            if not stable:
                self._clear_window(index)
            elif int(self._state['start_frame'][index]) < 0:
                self._state['start_frame'][index] = number
                self._state['start_time_s'][index] = time
                self._state['last_frame'][index] = number
                self._state['net_forward_m'][index] = 0.
                self._start_pos[index] = frame.root_state_w[index, :3].double()
                self._min_dt[index] = dt
                reason = 'pending_window'
            else:
                self._state['interval_count'][index] += 1
                self._state['elapsed_s'][index] += time-float(previous['sim_time_s'])
                self._state['last_frame'][index] = number
                self._min_dt[index] = min(float(self._min_dt[index]), dt)
                displacement = frame.root_state_w[index, :3].double()-self._start_pos[index]
                net = (displacement*self._scope.forward_w[index].double()).sum()
                self._state['net_forward_m'][index] = net
                tolerance = self._time_tolerance(.3, float(self._min_dt[index]))
                duration_ok = float(self._state['elapsed_s'][index])+tolerance >= .3
                success = duration_ok and float(net) >= .01
                self._state['success'][index] = success
                reason = 'success' if success else ('insufficient_progress' if duration_ok else 'pending_window')
            self._reason[index] = reason
            # Keep the high-water frame after out-of-order observations so
            # rejected old samples cannot make replayed history count anew.
            if previous is None or number > int(previous['frame']):
                self._previous[index] = {f.name: getattr(frame, f.name)[index].detach().clone() for f in fields(frame)}
        return RecoveryResult(**{name: value.clone() for name, value in self._state.items()},
                              reason=tuple(self._reason))
