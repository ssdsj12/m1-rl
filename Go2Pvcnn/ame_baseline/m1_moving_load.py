"""Diagnostic COM proposal in a measured translating frame, not acceptance.

The caller must keep real-joint slew/world-foot feedback and actual30N guards.
Only commit offset after executing the accepted final world-corrected action.
"""
import torch
from extension.parallelism.m1_kinematics import m1_ik
from .m1_load_transfer import transfer_target


def support_center(wheels,selected):
    mask=torch.arange(4,device=wheels.device)[None]!=selected[:,None]
    return torch.where(mask[...,None],wheels,0.).sum(1)/3.


def moving_load_target(*,entry_root,prepared_root,rpy,anchor,shift,offset,height,
                       support,live_root,com,selected,force,dt,root_speed=.04,max_root_shift=.08):
    root=prepared_root+shift+offset
    held=anchor+shift[:,None]
    held=held.clone()
    held[torch.arange(len(root),device=root.device),selected,2]+=height
    nominal,reachable=m1_ik(root,rpy,held)
    result=transfer_target(entry_root=entry_root+shift,entry_rpy=rpy,
        anchor_w=held,support_w=support,live_root=live_root,live_com=com,
        selected_leg=selected,previous_root=root,previous_joint=nominal.reshape(-1,12),
        wheel_force=force,support_floor=35.,dt=dt,root_speed=root_speed,max_root_shift=max_root_shift)
    result['valid'] &= reachable.all(-1)
    result['reason']=torch.where(reachable.all(-1),result['reason'],4)
    result['offset']=result['root']-prepared_root-shift
    return result
