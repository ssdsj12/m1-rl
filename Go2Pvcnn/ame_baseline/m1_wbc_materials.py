"""Conservative friction bound from measured coefficients and known modes."""
import numpy as np


def conservative_friction(materials, modes, ground, ground_mode):
    """Each material row has a corresponding known combine mode.

    Unknown active collision shape: bound by the minimum across all rows and
    both static/dynamic values. Caller may explicitly enumerate all coefficient/
    mode pairs if native shape ordering is unavailable. No guessed defaults.
    """
    values=np.asarray(materials,dtype=np.float64)
    ground=np.asarray(ground,dtype=np.float64)
    priority=('average','min','multiply','max')
    if (values.ndim!=2 or values.shape[1]!=3 or len(values)==0
            or ground.shape!=(3,) or len(modes)!=len(values)
            or ground_mode not in priority or any(m not in priority for m in modes)
            or not np.isfinite(values).all() or not np.isfinite(ground).all()
            or (values<0).any() or (ground<0).any()):
        raise ValueError('finite nonnegative measured properties and known mapped modes required')
    bounds=[]
    for row,mode in zip(values,modes):
        choice=max(priority.index(mode),priority.index(ground_mode))
        a,b=row[:2],ground[:2]
        combined=((a+b)/2,np.minimum(a,b),a*b,np.maximum(a,b))[choice]
        bounds.append(float(combined.min()))
    return min(bounds)
