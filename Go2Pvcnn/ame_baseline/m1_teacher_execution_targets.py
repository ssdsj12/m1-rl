"""Per-leg execution geometry, separate from physical trajectory intent."""
from dataclasses import dataclass
import torch
from ame_baseline.m1_teacher_ik import body_feet
from ame_baseline.m1_teacher_support_heading import support_heading_goal
from ame_baseline.m1_teacher_pose import BodyPose, PoseReference, _check_pose_like, _tensor, world_to_goal_body, _rotation


@dataclass(frozen=True)
class ExecutionTarget:
    body_goal: torch.Tensor
    body_step: torch.Tensor
    mode: torch.Tensor
    fraction: torch.Tensor
    active_fraction: torch.Tensor = None
    intent_fraction: torch.Tensor = None
    heading_delta: torch.Tensor = None

    def __post_init__(self):
        if self.active_fraction is None:
            object.__setattr__(self,'active_fraction',self.fraction.clone())
        if self.intent_fraction is None:
            object.__setattr__(self,'intent_fraction',self.fraction.clone())
        if self.heading_delta is None:
            object.__setattr__(self,'heading_delta',torch.zeros_like(self.fraction))


def execution_targets(command, measured, active_wheel, last_applied_q, fraction, mode, *, support_offset_w_z=None, support_reference_w_z=None, support_heave_w_z=None, support_capture_root_z=None):
    if not isinstance(command, PoseReference):
        raise ValueError('command must be PoseReference')
    _check_pose_like(measured, command.body, 'measured')
    pos=command.body.pos_w; batch=pos.shape[0]
    _tensor(last_applied_q,(batch,12),pos,'last_applied_q')
    _tensor(fraction,(batch,),pos,'fraction')
    for value,name,upper in ((active_wheel,'active_wheel',3),(mode,'mode',2)):
        if (not isinstance(value,torch.Tensor) or value.shape!=(batch,) or value.dtype!=torch.long
                or value.device!=pos.device or bool(((value<0)|(value>upper)).any())):
            raise ValueError(f'{name} must be valid long [B] on reference device')
    if not bool((torch.isfinite(fraction)&(fraction>0)&(fraction<=1)).all()):
        raise ValueError('fraction must be finite in (0,1]')
    if support_capture_root_z is not None:
        _tensor(support_capture_root_z,(batch,),pos,'support capture root Z')
        if (support_reference_w_z is None or bool((mode==0).any())
                or not bool(torch.isfinite(support_capture_root_z).all())):
            raise ValueError('support capture root requires finite crossing/restore height context')
    goal=world_to_goal_body(command)
    measured_goal=world_to_goal_body(PoseReference(measured,command.wheels_w))
    selected=(torch.arange(4,device=pos.device)[None]==active_wheel[:,None])&(mode[:,None]==1)
    goal=torch.where(selected[:,:,None],measured_goal,goal)
    if support_reference_w_z is not None:
        _tensor(support_reference_w_z,(batch,4),pos,'support_reference_w_z')
        if not bool(torch.isfinite(support_reference_w_z).all()) or bool((mode==0).any()):
            raise ValueError('support reference requires finite crossing/restore heights')
        support=torch.arange(4,device=pos.device)[None]!=active_wheel[:,None]
        translation=world_to_goal_body(PoseReference(BodyPose(command.body.pos_w,measured.quat_w),command.wheels_w))
        # Keep attitude control in the bounded load-aware Z channel during
        # crossing. A full pose rotation in XY otherwise opposes translation.
        # Preserve invalid original command poses rather than masking them.
        use_translation=support&(mode[:,None]==1)&torch.isfinite(goal).all(-1)
        goal=torch.where(use_translation[:,:,None],translation,goal)
        rotation=_rotation(measured.quat_w)
        world=measured.pos_w[:,None]+torch.einsum('bij,bkj->bki',rotation,goal)
        support=torch.arange(4,device=pos.device)[None]!=active_wheel[:,None]
        vertical=torch.zeros_like(goal)
        reference=support_reference_w_z
        if support_capture_root_z is not None:
            # Stored heights use the captured root origin. A measured vertical
            # body displacement is a frame change, not a request to shorten legs.
            reference=reference+(measured.pos_w[:,2]-support_capture_root_z)[:,None]
        vertical[:,:,2]=torch.where(support,reference-world[:,:,2],torch.zeros_like(reference))
        goal=goal+torch.einsum('bij,bkj->bki',rotation.transpose(-1,-2),vertical)
    if support_heave_w_z is not None:
        _tensor(support_heave_w_z,(batch,),pos,'support_heave_w_z')
        if (support_reference_w_z is None or not bool(torch.isfinite(support_heave_w_z).all())
                or bool((support_heave_w_z.abs()>.020000001).any())):
            raise ValueError('heave requires bounded finite correction and support reference')
        world=torch.zeros_like(goal)
        support=torch.arange(4,device=pos.device)[None]!=active_wheel[:,None]
        world[:,:,2]=torch.where(support,support_heave_w_z[:,None],0.)
        goal=goal+torch.einsum('bij,bkj->bki',_rotation(measured.quat_w).transpose(-1,-2),world)
    if support_offset_w_z is not None:
        _tensor(support_offset_w_z,(batch,4),pos,'support_offset_w_z')
        off=support_offset_w_z
        if (not bool(torch.isfinite(off).all()) or bool((off.abs()>.015000001).any())
                or bool((off.sum(-1).abs()>1e-8).any())
                or bool((off.gather(1,active_wheel[:,None])!=0).any())
                or bool(((mode==0)&(off.abs().amax(-1)>0)).any())):
            raise ValueError('invalid support offset')
        world=torch.zeros_like(goal);world[:,:,2]=off
        goal=goal+torch.einsum('bij,bkj->bki',_rotation(measured.quat_w).transpose(-1,-2),world)
    heading_delta=torch.zeros_like(fraction)
    if support_reference_w_z is not None:
        goal,heading_delta=support_heading_goal(goal,measured.quat_w,command.body.quat_w,
                                               active_wheel,mode==1)
    start=body_feet(last_applied_q)
    step=start+fraction[:,None,None]*(goal-start)
    step=torch.where((mode==0)[:,None,None],goal,step)
    return ExecutionTarget(goal,step,mode.clone(),fraction.clone(),heading_delta=heading_delta)
