"""Physical episode evidence for the flat-first PPO terrain curriculum.

The reward hook samples live state before Isaac's automatic scene reset. No
reward value or commanded action is used as evidence of locomotion success.
"""
from __future__ import annotations

import torch
import math


class LearningCurriculumGate:
    def __init__(self, num_envs, device, *, window_size=2048):
        if num_envs < 1 or window_size < 2048:
            raise ValueError('positive environments and at least 2048 episodes required')
        self.device = torch.device(device)
        self.window_size = int(window_size)
        self.stage = 0
        self.streak = 0
        self.steps = torch.zeros(num_envs, dtype=torch.long, device=device)
        self.episode_stage = torch.zeros_like(self.steps)
        self.error = torch.zeros(num_envs, device=device)
        self.duration = torch.zeros_like(self.error)
        self.command_distance = torch.zeros_like(self.error)
        self.start_x = torch.zeros_like(self.error)
        self.end_x = torch.zeros_like(self.error)
        self.finite = torch.ones(num_envs, dtype=torch.bool, device=device)
        self.window_count = 0
        self.window_pass = 0
        self.window_error = 0.
        self.window_duration = 0.
        self.window_attempts = 0
        self.window_successes = 0
        self.last = dict(sample_count=0., pass_rate=0., velocity_error=0.,
                         strict_attempts=0., strict_successes=0., strict_success_rate=0.)

    @torch.no_grad()
    def accumulate(self, vx, command_x, root_pos_w, finite, dt):
        first = self.steps == 0
        valid = (finite & torch.isfinite(vx) & torch.isfinite(command_x)
                 & torch.isfinite(root_pos_w).all(-1))
        self.finite &= valid
        self.start_x[first] = torch.nan_to_num(root_pos_w[first, 0])
        self.end_x.copy_(torch.nan_to_num(root_pos_w[:, 0]))
        self.error += torch.nan_to_num((vx-command_x).abs(), nan=1.e6, posinf=1.e6) * dt
        self.command_distance += torch.nan_to_num(command_x.clamp_min(0), nan=0., posinf=0.) * dt
        self.duration += dt
        self.steps += 1

    @torch.no_grad()
    def reset(self, env_ids, terminated, timeout, max_episode_steps,
              *, strict_attempts=None, strict_successes=None):
        ids = torch.as_tensor(env_ids, device=self.device, dtype=torch.long)
        observed = self.steps[ids] > 0
        eligible = observed & (self.episode_stage[ids] == self.stage)
        take = ids[eligible]
        if take.numel():
            full = self.steps[take] >= int(max_episode_steps)
            progress = self.end_x[take] - self.start_x[take]
            passed = (self.finite[take] & ~terminated[take].bool() & timeout[take].bool()
                      & full & (self.command_distance[take] > 0)
                      & (progress > 0) & (progress >= .7*self.command_distance[take]))
            self.window_count += take.numel()
            self.window_pass += int(passed.sum())
            self.window_error += float(self.error[take].sum())
            self.window_duration += float(self.duration[take].sum())
            if strict_attempts is not None and strict_successes is not None:
                attempts = strict_attempts[take].clamp_min(0)
                successes = strict_successes[take].clamp_min(0).minimum(attempts)
                self.window_attempts += int(attempts.sum())
                self.window_successes += int(successes.sum())
            if self.window_count >= self.window_size:
                self.last = self._window_metrics()
                strict_ok = (self.stage == 0 or
                             (self.window_attempts > 0 and self.last['strict_success_rate'] >= .5))
                # Speed error remains telemetry, not a promotion requirement.
                good = self.last['pass_rate'] >= .9 and strict_ok
                self.streak = min(self.streak + 1, 3) if good else 0
                if self.streak >= 3 and self.stage < 4:
                    self.stage += 1
                    self.streak = 0
                self.window_count = self.window_pass = self.window_attempts = self.window_successes = 0
                self.window_error = self.window_duration = 0.
        self.steps[ids] = 0
        self.error[ids] = self.duration[ids] = self.command_distance[ids] = 0
        self.finite[ids] = True
        self.episode_stage[ids] = self.stage
        return self.metrics()

    def _window_metrics(self):
        return dict(sample_count=float(self.window_count),
                    pass_rate=self.window_pass / max(self.window_count, 1),
                    velocity_error=self.window_error / max(self.window_duration, 1.e-12),
                    strict_attempts=float(self.window_attempts),
                    strict_successes=float(self.window_successes),
                    strict_success_rate=self.window_successes / max(self.window_attempts, 1))

    def metrics(self):
        result = self._window_metrics() if self.window_count else self.last.copy()
        result.update(stage=float(self.stage), qualifying_streak=float(self.streak))
        return result

    def state_dict(self):
        names = ('stage', 'streak', 'window_count', 'window_pass', 'window_error',
                 'window_duration', 'window_attempts', 'window_successes')
        return {'version': 1, **{name: getattr(self, name) for name in names}, 'last': self.last.copy()}

    def load_state_dict(self, state):
        expected = self.state_dict()
        if not isinstance(state, dict) or state.keys() != expected.keys() or state['version'] != 1:
            raise ValueError('invalid or missing learning curriculum checkpoint metadata')
        for name in expected.keys() - {'version', 'last'}:
            value = state[name]
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'invalid curriculum {name}')
        for name in ('stage', 'streak', 'window_count', 'window_pass', 'window_attempts', 'window_successes'):
            if not isinstance(state[name], int):
                raise ValueError(f'curriculum {name} must be integer')
        if (state['stage'] > 4 or state['streak'] > 3 or state['window_count'] >= self.window_size
                or state['window_pass'] > state['window_count']
                or state['window_successes'] > state['window_attempts']):
            raise ValueError('invalid curriculum checkpoint bounds')
        last = state['last']
        if (not isinstance(last, dict) or last.keys() != self.last.keys()
                or not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in last.values())):
            raise ValueError('invalid curriculum checkpoint metrics')
        for name in expected.keys() - {'version', 'last'}:
            setattr(self, name, state[name])
        self.last = last.copy()
        self.steps.zero_()
        self.error.zero_()
        self.duration.zero_()
        self.command_distance.zero_()
        self.finite.fill_(True)
        self.episode_stage.fill_(self.stage)


def _gate(env):
    if not hasattr(env, '_m1_learning_gate'):
        env._m1_learning_gate = LearningCurriculumGate(env.num_envs, env.device)
    return env._m1_learning_gate


def _strict_counts(env, gate):
    if not hasattr(env, '_m1_curriculum_attempts'):
        return torch.zeros_like(gate.steps), torch.zeros_like(gate.steps)
    return env._m1_curriculum_attempts, env._m1_curriculum_successes


@torch.no_grad()
def accumulate_curriculum(env, command_name='base_velocity'):
    gate = _gate(env)
    # Some reward configurations evaluate a term more than once per step.
    stamp = int(env.common_step_counter)
    if getattr(env, '_m1_learning_last_step', None) == stamp:
        return
    env._m1_learning_last_step = stamp
    data = env.scene['robot'].data
    finite = torch.isfinite(data.root_state_w).all(-1) & torch.isfinite(data.joint_pos).all(-1)
    finite &= torch.isfinite(data.joint_vel).all(-1)
    gate.accumulate(data.root_lin_vel_b[:, 0], env.command_manager.get_command(command_name)[:, 0],
                    data.root_pos_w, finite, float(env.step_dt))


def track_velocity_and_accumulate(env, command_name, std, asset_cfg=None):
    """Unchanged Isaac tracking reward, plus separate pre-reset measurements."""
    from go2_pvcnn.mdp.rewards import track_lin_vel_xy_exp
    accumulate_curriculum(env, command_name)
    kwargs = {} if asset_cfg is None else {'asset_cfg': asset_cfg}
    return track_lin_vel_xy_exp(env, command_name=command_name, std=std, **kwargs)


@torch.no_grad()
def curriculum_reset(env, env_ids):
    """Called by the curriculum manager before scene reset, including init."""
    gate = _gate(env)
    ids = (torch.arange(env.num_envs, device=env.device) if env_ids is None else
           torch.arange(env.num_envs, device=env.device)[env_ids] if isinstance(env_ids, slice) else
           torch.as_tensor(env_ids, device=env.device, dtype=torch.long))
    attempts, successes = _strict_counts(env, gate)
    if not hasattr(env, '_m1_learning_strict_baseline'):
        env._m1_learning_strict_baseline = (torch.zeros_like(attempts), torch.zeros_like(successes))
    old_a, old_s = env._m1_learning_strict_baseline
    manager = getattr(env, 'termination_manager', None)
    zeros = torch.zeros(env.num_envs, device=env.device, dtype=torch.bool)
    metrics = gate.reset(ids, getattr(manager, 'terminated', zeros),
                         getattr(manager, 'time_outs', zeros), env.max_episode_length,
                         strict_attempts=(attempts-old_a).clamp_min(0),
                         strict_successes=(successes-old_s).clamp_min(0))
    old_a[ids] = attempts[ids]
    old_s[ids] = successes[ids]
    terrain = env.scene.terrain
    if gate.stage < 4:
        if not hasattr(env, '_m1_learning_flat_column'):
            generator = getattr(getattr(terrain, 'cfg', None), 'terrain_generator', None)
            if generator is not None:
                from extension.semantic_course import terrain_column_names_from_generator
                names = terrain_column_names_from_generator(generator)
                if names is None or 'flat' not in names:
                    raise ValueError('flat-first curriculum requires an actual flat terrain column')
                env._m1_learning_flat_column = names.index('flat')
            else:
                # Minimal tensor fixtures have no generator configuration.
                env._m1_learning_flat_column = 0
        terrain.terrain_levels[ids] = gate.stage
        terrain.terrain_types[ids] = env._m1_learning_flat_column
    else:
        rows, cols = terrain.terrain_origins.shape[:2]
        terrain.terrain_levels[ids] = torch.randint(4, rows, (ids.numel(),), device=env.device)
        terrain.terrain_types[ids] = torch.randint(cols, (ids.numel(),), device=env.device)
    terrain.env_origins[ids] = terrain.terrain_origins[terrain.terrain_levels[ids], terrain.terrain_types[ids]]
    if gate.stage < 4:
        # 20 s at 0.45 m/s needs 9 m; a centered 16 m tile offers only 8 m.
        terrain.env_origins[ids, 0] -= 2.
    return metrics
