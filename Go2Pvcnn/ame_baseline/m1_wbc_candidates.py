"""Bounded geometric contact candidates for an explicitly at-rest oracle.

Does not determine validity for moving/slipping/impacting states. Every original
force slot is preserved; coincident point slots share the same attached mode.
"""
from itertools import product
import numpy as np


def rest_contact_candidates(points, owners, *, groups=4, max_candidates=32):
    points=np.asarray(points,dtype=np.float64); owners=np.asarray(owners)
    if (points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all()
            or owners.shape!=(len(points),) or owners.dtype.kind not in 'iu'
            or type(groups) is not int or groups<1
            or type(max_candidates) is not int or max_candidates<1
            or np.any(owners<0) or np.any(owners>=groups)):
        raise ValueError('finite named point ownership and positive integer budget required')
    choices=[]; count=1
    for group in range(groups):
        indices=np.flatnonzero(owners==group)
        if not len(indices):
            raise ValueError('support group has no measured contact location')
        unique,inverse=np.unique(points[indices],axis=0,return_inverse=True)
        n=len(unique)
        if n>max_candidates.bit_length() or count*((1<<n)-1)>max_candidates:
            raise ValueError('contact mode budget exceeded; no silent truncation')
        count*=((1<<n)-1)
        options=[]
        for bits in range((1<<n)-1,0,-1):
            mask=np.zeros(len(points),dtype=bool)
            mask[indices]=[(bits>>int(i))&1 for i in inverse]
            options.append(mask)
        choices.append(options)
    return [np.logical_or.reduce(combo) for combo in product(*choices)]
