"""M1 AME-AMP observation and reference contract."""
from __future__ import annotations
from dataclasses import dataclass
from isaaclab.utils import configclass
from .m1_ame_env_cfg import M1AmeCrossLargeComplexEnvCfg
from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES, M1_WHEEL_JOINT_NAMES

@dataclass(frozen=True)
class M1AmpObservationSchema:
    window_frames: int = 24
    joint_pos_dim: int = 12
    joint_vel_dim: int = 12
    action_dim: int = 16
    joint_names: tuple[str, ...] = M1_PLANNER_JOINT_NAMES

M1_AME_AMP_ENV_ID = "Isaac-M1-Cross-Large-Complex-AME-AMP-v0"
M1_AME_AMP_EXPERIMENT_NAME = "m1_cross_large_complex_ame_amp"
@configclass
class M1AmeAmpCrossLargeComplexEnvCfg(M1AmeCrossLargeComplexEnvCfg):
    experiment_name: str = "m1_cross_large_complex_ame_amp"
    planner_owned_reference_cache: bool = True
    parallelism_plan_batch_size: int = 1024
    amp_window_frames: int = 24
    amp_dt: float = 0.02
    amp_observation_schema: M1AmpObservationSchema = M1AmpObservationSchema()
    def __post_init__(self):
        super().__post_init__()
        self.experiment_name = "m1_cross_large_complex_ame_amp"
        self.planner_owned_reference_cache = True
        self.parallelism_plan_batch_size = 1024
        self.amp_window_frames = 24
        self.amp_dt = 0.02
        self.amp_observation_schema = M1AmpObservationSchema()
        if set(self.amp_observation_schema.joint_names) & set(M1_WHEEL_JOINT_NAMES):
            raise ValueError("M1 AMP schema must exclude wheel joints")

def make_m1_reference_cache(batch: int, frames: int):
    import torch
    if frames != 24:
        raise ValueError("M1 AMP reference cache requires 24 frames")
    return type("M1ReferenceCache", (), {"joint_pos": torch.zeros(batch, frames, 12)})()

__all__ = ["M1AmeAmpCrossLargeComplexEnvCfg", "M1AmpObservationSchema", "make_m1_reference_cache"]
