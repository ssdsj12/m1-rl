"""Static grounded obstacle tables indexed by the live terrain row/column.

No per-step USD traversal and no fixed course coordinates. Padding is invalid;
table IDs are stable within a scene and must not be reused after scene rebuild.
"""
from __future__ import annotations
import math
import torch


def shape_half_extents(kind, params):
    if kind == 'cuboid':
        dims = tuple(float(v)/2 for v in params['size'])
    elif kind == 'sphere':
        dims = (float(params['radius']),)*3
    elif kind in ('cylinder','cone','capsule'):
        if params.get('axis','Z') != 'Z':
            raise ValueError('course registry requires Z-axis primitives')
        r=float(params['radius'])
        z=float(params['height'])/2 + (r if kind=='capsule' else 0)
        dims=(r,r,z)
    else:
        raise ValueError(f'unsupported course shape {kind!r}')
    if len(dims)!=3 or not all(math.isfinite(x) and x>0 for x in dims):
        raise ValueError('shape dimensions must be finite and positive')
    return dims


class CourseRegistry:
    def __init__(self, obstacles, *, rows: int, cols: int, device, _all_geometry=False):
        if min(rows,cols)<1:
            raise ValueError('rows/cols must be positive')
        obstacles=tuple(obstacles)
        self.landing_registry = (None if _all_geometry else CourseRegistry(
            obstacles, rows=rows, cols=cols, device=device, _all_geometry=True))
        grouped={}
        seen=set()
        for obj in obstacles:
            if not _all_geometry and obj.semantic_class!='small':
                continue
            if not (0<=obj.row<rows and 0<=obj.col<cols):
                raise ValueError('obstacle tile index outside registry')
            identity=(obj.row,obj.col,obj.semantic_class,obj.slot_index)
            if identity in seen:
                raise ValueError(f'duplicate obstacle identity {identity}')
            seen.add(identity)
            center=tuple(float(v) for v in obj.world_center)
            if len(center)!=3 or not all(math.isfinite(v) for v in center):
                raise ValueError('obstacle world center must be finite XYZ')
            extent=shape_half_extents(obj.shape_kind,obj.shape_params)
            grouped.setdefault((obj.row,obj.col),[]).append(((obj.semantic_class,obj.slot_index),center,extent))
        self.capacity=max(1,max((len(x) for x in grouped.values()),default=0))
        shape=(rows,cols,self.capacity)
        self.centers_top=torch.zeros((*shape,3),device=device)
        self.half_extents=torch.zeros((*shape,2),device=device)
        self.ground_z=torch.zeros(shape,device=device)
        self.valid=torch.zeros(shape,dtype=torch.bool,device=device)
        self.ids=torch.full(shape,-1,dtype=torch.long,device=device)
        for (row,col),values in sorted(grouped.items()):
            for index,(_,center,extent) in enumerate(sorted(values)):
                self.centers_top[row,col,index]=torch.tensor((center[0],center[1],center[2]+extent[2]),device=device)
                self.half_extents[row,col,index]=torch.tensor(extent[:2],device=device)
                self.ground_z[row,col,index]=center[2]-extent[2]
                self.valid[row,col,index]=True
                self.ids[row,col,index]=(row*cols+col)*self.capacity+index

    def for_envs(self, levels: torch.Tensor, types: torch.Tensor):
        if levels.ndim!=1 or types.shape!=levels.shape:
            raise ValueError('terrain levels/types must be aligned [B]')
        for values,limit in ((levels,self.valid.shape[0]),(types,self.valid.shape[1])):
            if values.dtype not in (torch.int32,torch.int64) or values.device!=self.valid.device:
                raise ValueError('terrain indices must be integer tensors on registry device')
            if ((values<0)|(values>=limit)).any():
                raise ValueError('terrain indices outside registry')
        result = {name:getattr(self,name)[levels,types] for name in
                ('centers_top','half_extents','ground_z','valid','ids')}
        if self.landing_registry is not None:
            landing=self.landing_registry.for_envs(levels,types)
            result.update({'landing_'+name:landing[name] for name in
                           ('centers_top','half_extents','valid')})
        return result
