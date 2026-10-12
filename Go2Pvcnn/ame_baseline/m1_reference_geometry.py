"""Measured reference Y-cylinders; conservative separation certificates, not IK."""
import torch
from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M, M1_WHEEL_THICKNESS_M


def cylinder_axis(pos, quat):
    if (pos.shape[-1]!=3 or quat.shape!=pos.shape[:-1]+(4,)
            or not torch.isfinite(pos).all() or not torch.isfinite(quat).all()):
        raise ValueError('finite aligned cylinder poses required')
    norm=quat.norm(dim=-1,keepdim=True)
    if (norm<1e-8).any(): raise ValueError('nonzero cylinder quaternion required')
    w,x,y,z=(quat/norm).unbind(-1)
    return torch.stack((2*(x*y-w*z),1-2*(x*x+z*z),2*(y*z+w*x)),-1)


def cylinder_bottom(pos, quat, radius=M1_WHEEL_RADIUS_M, thickness=M1_WHEEL_THICKNESS_M):
    axis=cylinder_axis(pos,quat)
    az=axis[...,2].abs().clamp(0.,1.)
    return pos[...,2]-(thickness/2*az+radius*(1-az.square()).clamp_min(0).sqrt())


def cylinder_clears_box(pos, quat, centers_top, half_extents,
                        radius=M1_WHEEL_RADIUS_M, thickness=M1_WHEEL_THICKNESS_M):
    """Certify a cylinder disjoint from an axis-aligned, downward solid box.

    Exact cylinder support function, tested on finitely many separating planes.
    True proves separation; False may be conservative for arbitrary tilt.
    Unlike whole-bottom gating this certifies the common round-leading-edge gap.
    It is not a replacement for simulator collision/termination measurements.
    """
    axis=cylinder_axis(pos,quat)
    if (centers_top.shape!=(pos.shape[0],3) or half_extents.shape!=(pos.shape[0],2)
            or not torch.isfinite(centers_top).all() or not torch.isfinite(half_extents).all()
            or (half_extents<=0).any()): raise ValueError('finite positive box geometry required')
    delta=pos-centers_top[:,None]
    closest=delta.clone()
    closest[...,:2]=delta[...,:2].clamp(-half_extents[:,None],half_extents[:,None])
    closest[...,2]=0.
    nearest=delta-closest
    signs=pos.new_tensor([[-1,-1],[1,-1],[-1,1],[1,1]])
    corners=torch.cat((half_extents[:,None]*signs[None],pos.new_zeros(pos.shape[0],4,1)),-1)
    normals=torch.cat((nearest[:,:,None],delta[:,:,None]-corners[:,None],
        pos.new_tensor([[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1]])[None,None].expand(pos.shape[0],pos.shape[1],-1,-1)),2)
    length=normals.norm(dim=-1)
    usable=(normals[...,2]>=0)&(length>1e-8)
    normals=normals/length.clamp_min(1e-8)[...,None]
    axial=(normals*axis[:,:,None]).sum(-1)
    support=thickness/2*axial.abs()+radius*(1-axial.square()).clamp_min(0).sqrt()
    box_support=(normals[...,:2].abs()*half_extents[:,None,None]).sum(-1)
    separation=(normals*delta[:,:,None]).sum(-1)-support-box_support
    return ((separation>=0.)&usable).any(-1)
