"""Explicit diagnostic bounded start/brake profile, not a distance planner."""
import math


def hold_effort(speed, velocity, damping, limit, scale):
    """Predict zero-stiffness/zero-feedforward wheel drive effort before write."""
    import torch
    if (speed.ndim != 2 or speed.shape[1] != 4 or not math.isfinite(scale) or scale <= 0
            or any(v.shape != speed.shape or not torch.isfinite(v).all()
                   for v in (speed,velocity,damping,limit))
            or (damping < 0).any() or (limit <= 0).any()):
        raise ValueError('invalid wheel hold effort input')
    effort=damping*(speed*scale-velocity)
    if not torch.isfinite(effort).all() or (effort.abs()>limit).any():
        raise ValueError('wheel hold effort exceeds limit')
    return effort


def anchor_hold_speed(anchor, position, yaw, previous, dt):
    """Diagnostic PREPARE servo in m/s; not a rigid wheel lock or roll controller.

    Fixed entry anchors must be supplied, never reset to the measured drift.
    Longitudinal-only P feedback (2/s), 0.04m/s cap, 0.2m/s2 slew.
    Runtime remains responsible for contact, effort and phase-handoff guards.
    """
    import torch
    if (position.ndim != 3 or position.shape[1:] != (4,3)
            or anchor.shape != position.shape or yaw.shape != position.shape[:1]
            or previous.shape != position.shape[:2]
            or not math.isfinite(dt) or not 0 < dt <= .1):
        raise ValueError('invalid wheel hold shape or timestep')
    values=(anchor,position,yaw,previous)
    if (any(not v.is_floating_point() or v.device != position.device
            or v.dtype != position.dtype or not torch.isfinite(v).all() for v in values)
            or (previous.abs() > .040001).any()):
        raise ValueError('invalid wheel hold state')
    error=anchor-position
    longitudinal=error[:,:,0]*yaw.cos()[:,None]+error[:,:,1]*yaw.sin()[:,None]
    desired=(2.*longitudinal).clamp(-.04,.04)
    return previous+(desired-previous).clamp(-.2*dt,.2*dt)


def phase_hold_speed(anchor,position,yaw,previous,dt,phase,selected,roll_speed=0.):
    """Continuous wheel command ownership; selected wheel brakes before lifting.

    During rolling use feedforward, not fixed-anchor feedback opposing motion.
    LAND uses transported anchors; selected wheel stays stopped until SETTLE.
    """
    import torch
    if (phase not in ('prepare','unload','lift','roll','land','settle')
            or not math.isfinite(roll_speed) or not 0<=roll_speed<=.1
            or (phase!='roll' and roll_speed!=0)
            or selected.shape!=position.shape[:1] or selected.dtype!=torch.long
            or selected.device!=position.device or ((selected<0)|(selected>3)).any()
            or not torch.isfinite(previous).all() or (previous.abs()>.100001).any()):
        raise ValueError('invalid phase wheel state')
    # Reuse the strict geometry/state validator; desired projection below is
    # unslewed so there is exactly one slew limiter across phase boundaries.
    anchor_hold_speed(anchor,position,yaw,previous.clamp(-.04,.04),dt)
    error=anchor-position
    desired=(2*(error[:,:,0]*yaw.cos()[:,None]+error[:,:,1]*yaw.sin()[:,None])).clamp(-.04,.04)
    if phase=='roll':desired=torch.full_like(previous,roll_speed)
    if phase not in ('prepare','settle'):
        desired[torch.arange(len(selected),device=selected.device),selected]=0.
    return previous+(desired-previous).clamp(-.2*dt,.2*dt)


def rolling_torque(step,total,dt,target):
    """Opt-in explicit wheel effort, <=3Nm and <=20Nm/s, zero endpoints."""
    if target not in (0.,3.):raise ValueError('diagnostic torque must be 0 or 3Nm')
    rolling_speed(step,total,dt,0.)
    return min(target,20.*dt*step,20.*dt*(total-1-step))


def selected_legs(leg):
    """Eight-row diagnostic selection; None keeps four-leg coverage."""
    if leg is None:return [i%4 for i in range(8)]
    if type(leg) is not int or not 0<=leg<4:raise ValueError('invalid selected leg')
    return [leg]*8


def drive_columns(selected, lifted_only):
    """Planner-order wheel columns for contact versus free-DOF isolation."""
    if type(selected) is not int or not 0<=selected<4 or type(lifted_only) is not bool:
        raise ValueError('invalid wheel selection or diagnostic mode')
    return (selected,) if lifted_only else tuple(i for i in range(4) if i!=selected)


def refine_timestep(cfg, factor):
    """Diagnostic resolution comparison preserving physical control/render periods."""
    if type(factor) is not int or factor not in (1,2):
        raise ValueError('diagnostic timestep refinement must be 1 or 2')
    cfg.sim.dt /= factor
    cfg.decimation *= factor
    cfg.sim.render_interval *= factor


def rolling_damping(phase, gain):
    """Diagnostic only: restore baseline before lowering, no torque-limit change."""
    if phase not in ('prepare','unload','lift','roll','land','settle') or gain not in (5.,20.):
        raise ValueError('invalid phase or diagnostic wheel damping')
    return gain if phase == 'roll' else 5.


def solver_comparison(standing,iterations):
    if type(iterations) is not int or iterations not in (0,4) or (iterations and not standing):
        raise ValueError('solver comparison requires standing rolling and 0 or 4 iterations')
    return iterations


def standing_window(budget):
    if type(budget) is not int or budget not in (100,180):
        raise ValueError('standing rolling budget must be 100 or 180')
    return 60,budget-80


def rolling_speed(step,total,dt,target,*,initial=0.):
    if not isinstance(step,int) or not isinstance(total,int) or not 0<=step<total:
        raise ValueError('step must index the finite rolling window')
    if not math.isfinite(dt) or not 0<dt<=.1 or not math.isfinite(target) or not 0<=target<=.1:
        raise ValueError('invalid rolling dt or target')
    if (not math.isfinite(initial) or not 0<=initial<=target
            or initial>.2*dt*(total-1)):
        raise ValueError('incoming speed cannot meet bounded braking deadline')
    return min(target,initial+.2*dt*step,.2*dt*(total-1-step))


def window_speed(step,start,total,dt,target):
    if type(step) is not int or type(start) is not int or step<0 or start<0:
        raise ValueError('window indices must be nonnegative integers')
    rolling_speed(0,total,dt,target)  # validate even outside active window
    return rolling_speed(step-start,total,dt,target) if start<=step<start+total else 0.
