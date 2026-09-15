from __future__ import annotations
import copy
from .ame_amp_train_cfg import get_ame_amp_train_cfg

def get_m1_ame_amp_train_cfg():
    cfg = copy.deepcopy(get_ame_amp_train_cfg())
    cfg["experiment_name"] = "m1_cross_large_complex_ame_amp"
    return cfg