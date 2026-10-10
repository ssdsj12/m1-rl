import torch

from ame_baseline.m1_learning_curriculum import LearningCurriculumGate


def episode(gate, *, steps=4, speed=.3, progress=.3, terminated=False, attempts=0, successes=0, ids=None):
    n = gate.steps.numel()
    for i in range(steps):
        gate.accumulate(torch.full((n,), float(speed)), torch.full((n,), .3),
                        torch.full((n, 3), float(i * progress)), torch.ones(n, dtype=torch.bool), 1.)
    ids = torch.arange(n) if ids is None else ids
    return gate.reset(ids, torch.full((n,), terminated), torch.full((n,), not terminated),
                      4, strict_attempts=torch.full((n,), attempts),
                      strict_successes=torch.full((n,), successes))


def test_requires_three_qualifying_windows():
    gate = LearningCurriculumGate(2048, 'cpu')
    episode(gate)
    assert gate.stage == 0 and gate.streak == 1
    episode(gate)
    assert gate.stage == 0 and gate.streak == 2
    episode(gate)
    assert gate.stage == 1 and gate.streak == 0


def test_initial_reset_excluded_but_early_failures_count():
    gate = LearningCurriculumGate(2048, 'cpu')
    gate.reset(torch.arange(2048), torch.zeros(2048, dtype=torch.bool),
               torch.zeros(2048, dtype=torch.bool), 4)
    assert gate.metrics()['sample_count'] == 0
    episode(gate, steps=1, terminated=True)
    assert gate.metrics()['sample_count'] == 2048
    assert gate.metrics()['pass_rate'] == 0
    assert gate.streak == 0


def test_stationary_reward_proxy_cannot_qualify():
    gate = LearningCurriculumGate(2048, 'cpu')
    episode(gate, progress=0)
    assert gate.streak == 0
    episode(gate, speed=0, progress=0)
    assert gate.streak == 0


def test_speed_error_is_diagnostic_only_for_promotion():
    gate = LearningCurriculumGate(2048, 'cpu')
    for _ in range(3):
        episode(gate, speed=.5, progress=.5)
    assert gate.metrics()['velocity_error'] > .08
    assert gate.stage == 1
    for _ in range(3):
        episode(gate, speed=.5, progress=.5, attempts=2, successes=1)
    assert gate.stage == 2


def test_failed_window_breaks_streak_and_strict_attempts_required():
    gate = LearningCurriculumGate(2048, 'cpu')
    episode(gate)
    episode(gate, terminated=True)
    assert gate.streak == 0
    for _ in range(3):
        episode(gate)
    for _ in range(3):
        episode(gate)
    assert gate.stage == 1 and gate.streak == 0
    for _ in range(3):
        episode(gate, attempts=2, successes=1)
    assert gate.stage == 2


def test_old_stage_episodes_do_not_leak():
    gate = LearningCurriculumGate(4096, 'cpu')
    ids = torch.arange(2048)
    for _ in range(3):
        episode(gate, ids=ids)
    assert gate.stage == 1
    episode(gate, ids=torch.arange(2048, 4096), attempts=1, successes=1)
    assert gate.window_count == 0
    assert (gate.episode_stage == 1).all()


def test_nonfinite_fails_closed_and_metrics_finite():
    gate = LearningCurriculumGate(2048, 'cpu')
    episode(gate, speed=float('nan'))
    assert gate.streak == 0
    assert all(torch.isfinite(torch.as_tensor(value)) for value in gate.metrics().values())


def test_short_timeout_is_not_success():
    gate = LearningCurriculumGate(2048, 'cpu')
    episode(gate, steps=2)
    assert gate.metrics()['pass_rate'] == 0


def test_checkpoint_restores_gate_but_not_inflight_episodes():
    gate = LearningCurriculumGate(2048, 'cpu')
    for _ in range(4):
        episode(gate, attempts=2, successes=1)
    restored = LearningCurriculumGate(2048, 'cpu')
    restored.load_state_dict(gate.state_dict())
    assert restored.stage == 1 and restored.streak == 1
    assert restored.steps.sum() == 0 and (restored.episode_stage == 1).all()
    for _ in range(2):
        episode(restored, attempts=2, successes=1)
    assert restored.stage == 2


def test_hooks_count_strict_deltas_once_and_keep_terrain_bounded():
    from types import SimpleNamespace
    from ame_baseline.m1_learning_curriculum import curriculum_reset
    n = 2048
    terrain = SimpleNamespace(terrain_origins=torch.zeros(10, 6, 3),
                              terrain_levels=torch.ones(n, dtype=torch.long),
                              terrain_types=torch.ones(n, dtype=torch.long),
                              env_origins=torch.zeros(n, 3))
    env = SimpleNamespace(num_envs=n, device='cpu', max_episode_length=4,
                          scene=SimpleNamespace(terrain=terrain),
                          termination_manager=SimpleNamespace(terminated=torch.zeros(n, dtype=torch.bool),
                                                              time_outs=torch.ones(n, dtype=torch.bool)),
                          _m1_curriculum_attempts=torch.zeros(n, dtype=torch.long),
                          _m1_curriculum_successes=torch.zeros(n, dtype=torch.long))
    curriculum_reset(env, None)
    assert (terrain.terrain_levels == 0).all() and (terrain.terrain_types == 0).all()
    assert (terrain.env_origins[:, 0] == -2).all()
    curriculum_reset(env, None)
    assert (terrain.env_origins[:, 0] == -2).all()  # never accumulate the offset
    gate = env._m1_learning_gate
    gate.stage = 1
    gate.episode_stage.fill_(1)
    for i in range(4):
        gate.accumulate(torch.full((n,), .3), torch.full((n,), .3),
                        torch.full((n, 3), i*.3), torch.ones(n, dtype=torch.bool), 1.)
    env._m1_curriculum_attempts += 2
    env._m1_curriculum_successes += 1
    metrics = curriculum_reset(env, None)
    assert metrics['strict_attempts'] == 4096 and metrics['strict_successes'] == 2048
    assert gate.streak == 1
    assert (terrain.env_origins[:, 0] == -2).all()
    for i in range(4):
        gate.accumulate(torch.full((n,), .3), torch.full((n,), .3),
                        torch.full((n, 3), i*.3), torch.ones(n, dtype=torch.bool), 1.)
    assert curriculum_reset(env, None)['strict_attempts'] == 0
    assert gate.streak == 0
    for stage in (1, 2, 3):
        gate.stage = stage
        curriculum_reset(env, None)
        curriculum_reset(env, None)
        assert (terrain.terrain_levels == stage).all()
        assert (terrain.env_origins[:, 0] == -2).all()
    gate.stage = 4
    curriculum_reset(env, None)
    assert (terrain.terrain_levels >= 4).all() and (terrain.terrain_levels < 10).all()
    assert (terrain.terrain_types >= 0).all() and (terrain.terrain_types < 6).all()
    assert (terrain.env_origins[:, 0] == 0).all()
