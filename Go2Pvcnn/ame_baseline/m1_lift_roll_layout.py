"""Undeployed lift-and-roll geometry candidate. Not a safety certificate.

Production intentionally does not import this module. Geometry, real source
mesh envelopes, anti-bypass and native gates must pass before selection.
"""
from dataclasses import dataclass
import math

from .m1_mixed_course import progressive_positions, progressive_row


@dataclass(frozen=True)
class Block:
    x: float
    y: float
    length: float
    width: float
    height: float
    required_crossing: bool

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.x,self.y,self.length,self.width,self.height)):
            raise ValueError('block geometry must be finite')
        if min(self.length,self.width,self.height) <= 0:
            raise ValueError('block dimensions must be positive')
        if type(self.required_crossing) is not bool:
            raise ValueError('required_crossing must be bool')


def subtract_interval(bounds, hole):
    """Subtract a closed interval, returning positive-length pieces only."""
    a,b = bounds
    c,d = hole
    if not all(math.isfinite(v) for v in (a,b,c,d)) or not (a < b and c < d):
        raise ValueError('intervals must be finite and increasing')
    if d <= a or c >= b:
        return ((a,b),)
    return tuple((lo,hi) for lo,hi in ((a,min(b,c)),(max(a,d),b)) if hi > lo)


def candidate_blocks(row, *, fill_gap=.02):
    """Initial .13m half-strip candidate, preserving existing target positions."""
    if type(row) is not int or row not in range(4):
        raise ValueError('candidate row must be an integer in [0,3]')
    if isinstance(fill_gap,bool) or not math.isfinite(fill_gap) or fill_gap <= 0:
        raise ValueError('fill_gap must be finite and positive')
    if row == 0:
        return ()
    count,height,_ = progressive_row(row)
    blocks = [Block(x,y,.10,.18,height,True)
              for x,y in progressive_positions(count,0,row=row)['small']]
    # Separate longitudinal tops by .02m, including cuts at spawn boundaries.
    # This is not proof that wheels cannot bridge these gaps while riding tops.
    pitch = .5+fill_gap
    for i in range(math.ceil(15.9/pitch)):
        a = -7.95 + i*pitch
        b = min(a+.5,7.95)
        intervals = ((a,b),)
        for edge in (-2.55,-1.45):
            intervals = tuple(part for interval in intervals
                              for part in subtract_interval(interval,(edge-fill_gap/2,edge+fill_gap/2)))
        for x0,x1 in intervals:
            ys = ((-7.95,7.95),)
            holes = [(-.345,-.085),(.085,.345)]
            if x0 < -1.45 and x1 > -2.55:
                holes.append((-.8,.8))
            for hole in holes:
                ys = tuple(part for interval in ys for part in subtract_interval(interval,hole))
            for y0,y1 in ys:
                blocks.append(Block((x0+x1)/2,(y0+y1)/2,x1-x0,y1-y0,height,False))
    return tuple(blocks)
