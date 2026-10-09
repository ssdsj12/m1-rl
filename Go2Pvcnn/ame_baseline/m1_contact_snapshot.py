"""Compact read-only contact-buffer records, preserving pair offsets."""
import math


def pair_records(normal,points,separation,counts,starts):
    if len(counts)!=len(starts) or not(len(normal)==len(points)==len(separation)):
        raise ValueError('inconsistent contact buffers')
    records=[]
    for count,start in zip(counts,starts):
        if count<0 or start<0 or start+count>len(normal):
            raise ValueError('truncated contact buffer')
        records.append(dict(normal=normal[start:start+count],points=points[start:start+count],
                            separation=separation[start:start+count]))
    return records


def friction_wrenches(forces, points, counts, starts, origin):
    """Sum world-frame patch forces and moments about a supplied world point."""
    if len(forces)!=len(points) or len(counts)!=len(starts):
        raise ValueError('inconsistent friction buffers')
    if len(origin)!=3 or not all(math.isfinite(v) for v in origin):
        raise ValueError('invalid wrench origin')
    result=[]
    for count,start in zip(counts,starts):
        if count<0 or start<0 or start+count>len(forces):
            raise ValueError('truncated friction buffer')
        force=[0.,0.,0.]
        moment=[0.,0.,0.]
        for f,p in zip(forces[start:start+count],points[start:start+count]):
            if len(f)!=3 or len(p)!=3 or not all(math.isfinite(v) for v in (*f,*p)):
                raise ValueError('invalid active friction patch')
            r=[p[i]-origin[i] for i in range(3)]
            for i in range(3):
                force[i]+=f[i]
                moment[i]+=r[(i+1)%3]*f[(i+2)%3]-r[(i+2)%3]*f[(i+1)%3]
        result.append(dict(force=force,moment=moment,count=count))
    return result
