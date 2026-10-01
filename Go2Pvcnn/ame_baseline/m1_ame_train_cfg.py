from __future__ import annotations
import copy
import os
from .ame_train_cfg import get_ame_train_cfg
from .ame_amp_train_cfg import get_ame_amp_train_cfg

def get_m1_ame_train_cfg():
    cfg = copy.deepcopy(get_ame_train_cfg())
    cfg["experiment_name"] = "m1_cross_large_complex_ame"
    # M1's stronger leg servos and velocity-driven wheels cannot use the
    # 1.0 action noise safely: expected action-rate cost alone is 3.2/s,
    # exceeding the maximum 2.25/s tracking reward. At 0.2 it is 0.128/s,
    # with 0.05 rad leg and 0.2 m/s wheel-surface initial exploration.
    cfg["policy"]["init_noise_std"] = float(os.environ.get("M1_INIT_NOISE_STD", "0.05"))
    cfg["policy"]["zero_actor_output"] = os.environ.get("M1_ZERO_ACTOR_OUTPUT", "1").strip().lower() not in {"0", "false", "no"}
    # The AME CNN/attention policy is more sensitive than the legacy MLP.
    # Use a conservative fixed step and let only valid teacher rows provide
    # a bounded leg-target imitation signal.
    # The AME attention policy is sensitive during the first gait adaptation;
    # a 2e-4 step destroys the standing limit cycle within a few rollouts.
    # Use a small fixed step so obstacle curriculum can add difficulty without
    # erasing the stabilising policy.
    # Keep the adaptation step externally tunable.  The M1 obstacle teacher
    # can provide a physically safe action while the AME policy is still
    # settling; a large PPO update at that boundary destroys the locomotion
    # limit cycle within a few rollouts.  The default preserves the previous
    # value, while smoke/production jobs can lower it without editing code.
    cfg["algorithm"]["learning_rate"] = float(
        os.environ.get("M1_LEARNING_RATE", "2.0e-5")
    )
    cfg["algorithm"]["schedule"] = "fixed"
    cfg["algorithm"]["imitation_coef"] = float(
        os.environ.get("M1_IMITATION_COEF", "0.25")
    )
    cfg["algorithm"]["ppo_log_ratio_clip"] = 5.0
    return cfg

def get_m1_ame_amp_train_cfg():
    cfg = copy.deepcopy(get_ame_amp_train_cfg())
    cfg["experiment_name"] = "m1_cross_large_complex_ame_amp"
    return cfg
