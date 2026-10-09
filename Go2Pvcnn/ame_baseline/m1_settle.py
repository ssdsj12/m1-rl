"""Admission for contacted four-wheel SETTLE, not stable-landing success.

Caller owns fresh identity, completed LAND deadline, pose/collision guards,
effort convergence and five-frame stable-contact gate. At20ms max100steps=2s.
The optional evidence mode tolerates low-load contact after confirmed touchdown;
it never permits additional descent or treats >1N as stable-landing success.
"""
import torch


def settle_allowed(force,elapsed_steps,max_steps,*,selected=None,touchdown_seen=None):
    if type(elapsed_steps) is not int or elapsed_steps<0 or type(max_steps) is not int or not 1<=max_steps<=100:
        raise ValueError('settle budget must be1..100steps with nonnegative elapsed')
    if force.ndim!=2 or force.shape[1]!=4 or not force.is_floating_point():
        raise ValueError('force must be floating [B,4]')
    finite=torch.isfinite(force).all(-1)
    if selected is None and touchdown_seen is None:
        return finite & (force>10.).all(-1) & (elapsed_steps<max_steps)
    batch=force.shape[0]
    if (selected is None or touchdown_seen is None or selected.shape!=(batch,)
        or selected.dtype!=torch.long or touchdown_seen.shape!=(batch,)
        or touchdown_seen.dtype!=torch.bool or selected.device!=force.device
        or touchdown_seen.device!=force.device):
        raise ValueError('selected and touchdown_seen must be row-aligned typed evidence')
    selected_ok=(selected>=0)&(selected<4)
    mask=torch.arange(4,device=force.device)[None]==selected[:,None]
    # >1N is contact persistence only; final PrepareGate still requires >10N
    # for five frames. Caller must freeze height and stop wheels in SETTLE.
    contact=((force>1.)|~mask).all(-1)
    supports=((force>=30.)|mask).all(-1)
    return finite & selected_ok & touchdown_seen & contact & supports & (elapsed_steps<max_steps)
