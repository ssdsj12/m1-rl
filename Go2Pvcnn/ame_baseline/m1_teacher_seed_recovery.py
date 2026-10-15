"""Bounded numerical initialization for pose IK; never rewrite measurements."""
import torch
from extension.parallelism.m1_kinematics import m1_joint_limit_mask
from .m1_teacher_ik import IKConfig,solve_constrained_ik


def recovered_pose_seed(seed,target,branch,cfg):
    if not isinstance(cfg,IKConfig):raise TypeError('cfg must be IKConfig')
    if seed.ndim!=2 or seed.shape[1]!=12 or target.shape!=(seed.shape[0],4,3) or branch.shape!=seed.shape:
        raise ValueError('seed/target/branch must be [B,12]/[B,4,3]/[B,12]')
    if seed.dtype not in (torch.float32,torch.float64) or any(x.dtype!=seed.dtype or x.device!=seed.device for x in (target,branch)):
        raise ValueError('matching float32/float64 tensors required')
    joints=seed.reshape(-1,4,3);knees=seed[:,2::3]
    finite=torch.isfinite(joints).all(-1)&torch.isfinite(target).all(-1)&torch.isfinite(branch.reshape(-1,4,3)).all(-1)
    legal=m1_joint_limit_mask(joints,torch.arange(4,device=seed.device))
    same=(knees.sign()==branch[:,2::3].sign())&(knees!=0)&(branch[:,2::3]!=0)
    deficit=cfg.min_knee_abs_rad-knees.abs()
    recover=finite&legal&same&(deficit>0)&(deficit<=.01)
    result=seed.clone()
    result[:,2::3]=torch.where(recover,knees.sign()*cfg.min_knee_abs_rad,knees)
    return result


def solve_pose_ik(q_seed,target_b,branch_q,cfg=None,*,tolerance_m=None):
    cfg=cfg or IKConfig()
    initialized=recovered_pose_seed(q_seed,target_b,branch_q,cfg)
    return solve_constrained_ik(initialized,target_b,branch_q,cfg,tolerance_m=tolerance_m)
