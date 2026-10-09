"""Exact opposite-face cancellation for diagnostics, not general mesh repair.

Preserves authored points and surviving indices. Requires closed, oriented
two-manifold edges afterward; does not establish freedom from self-intersection.
"""
import numpy as np


def clean_opposite_pairs(points,indices):
    p=np.asarray(points);idx=np.asarray(indices)
    if (p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all()
            or idx.ndim!=1 or len(idx)%3 or idx.dtype.kind not in 'iu'
            or len(idx)==0 or idx.min()<0 or idx.max()>=len(p)):
        raise ValueError('invalid triangle arrays')
    _,inverse=np.unique(p,axis=0,return_inverse=True)
    tri=inverse[idx.reshape(-1,3)]
    a,b,c=tri.T
    sign=np.sign((a-b)*(b-c)*(c-a))
    if (sign==0).any():raise ValueError('degenerate triangle')
    _,group,count=np.unique(np.sort(tri,axis=1),axis=0,return_inverse=True,return_counts=True)
    balance=np.bincount(group,weights=sign)
    if ((count>2)|((count==2)&(balance!=0))).any():
        raise ValueError('ambiguous or same-winding coincident faces')
    keep=count[group]==1
    remaining=tri[keep]
    if not len(remaining):raise ValueError('empty surface')
    edges=np.concatenate((remaining[:,[0,1]],remaining[:,[1,2]],remaining[:,[2,0]]))
    _,ei,ec=np.unique(np.sort(edges,axis=1),axis=0,return_inverse=True,return_counts=True)
    eb=np.bincount(ei,weights=np.where(edges[:,0]<edges[:,1],1,-1))
    if (ec!=2).any() or (eb!=0).any():raise ValueError('remaining surface is not closed oriented manifold')
    return idx.reshape(-1,3)[keep].reshape(-1).copy()
