"""Pure support attitude preference; never a physical support certificate."""
from dataclasses import dataclass
import torch
from .m1_teacher_pose import PoseReference,_check_pose_like,_rotation,_pose_valid


@dataclass(frozen=True)
class SupportAttitudeError:
    error_m: torch.Tensor
    valid: torch.Tensor


def centered_support_attitude_error(command,measured,active_wheel):
    if not isinstance(command,PoseReference):
        raise ValueError('command must be PoseReference')
    _check_pose_like(measured,command.body,'measured')
    pos=command.body.pos_w;b=pos.shape[0]
    if (not isinstance(active_wheel,torch.Tensor) or active_wheel.shape!=(b,)
            or active_wheel.dtype!=torch.long or active_wheel.device!=pos.device
            or bool(((active_wheel<0)|(active_wheel>3)).any())):
        raise ValueError('active wheel contract mismatch')
    safe=_pose_valid(command.body)&_pose_valid(measured)&torch.isfinite(command.wheels_w).all(dim=(-1,-2))
    # Double precision prevents loss of a small attitude signal at world offsets.
    p=command.wheels_w.double()-pos.double()[:,None]
    rm=_rotation(measured.quat_w.double());rd=_rotation(command.body.quat_w.double())
    raw=(torch.einsum('bij,bkj->bki',rm@rd.transpose(-1,-2),p)-p)[:,:,2]
    ids=torch.arange(4,device=pos.device).expand(b,4)
    support=ids[ids!=active_wheel[:,None]].reshape(b,3)
    error=raw.gather(1,support);error=error-error.mean(-1,keepdim=True)
    error=torch.where(safe[:,None],error,torch.zeros_like(error)).to(pos.dtype)
    # Preserve the input contract after the float32 cast.
    error=torch.cat((error[:,:2],-error[:,:2].sum(-1,keepdim=True)),-1)
    return SupportAttitudeError(torch.zeros_like(pos.new_zeros(b,4)).scatter(1,support,error),safe)
