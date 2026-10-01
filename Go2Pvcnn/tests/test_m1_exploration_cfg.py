from ame_baseline.ame_train_cfg import get_ame_train_cfg
from ame_baseline.m1_ame_train_cfg import get_m1_ame_train_cfg


def test_m1_initial_exploration_does_not_exhaust_tracking_reward_on_action_rate_alone():
    cfg = get_m1_ame_train_cfg()
    std = cfg["policy"]["init_noise_std"]
    # Independent per-step Gaussian actions: E[||a_t-a_(t-1)||²] = 2*d*sigma².
    # M1 has 12 leg action units and 4 wheel surface-speed units; the current
    # action-rate weight is 0.1 and maximum linear+yaw tracking is 1.5+0.75.
    expected_rate_cost = .1 * 2 * 16 * std**2
    assert expected_rate_cost < .1 * (1.5 + .75)
    assert 0 < std <= .25


def test_m1_exploration_change_does_not_mutate_go2_defaults():
    get_m1_ame_train_cfg()
    assert get_ame_train_cfg()["policy"]["init_noise_std"] == 1.0
