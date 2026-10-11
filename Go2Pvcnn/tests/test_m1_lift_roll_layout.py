"""CPU candidate invariants, not a native/deployment certificate."""
import importlib
import importlib.util
from dataclasses import FrozenInstanceError
import math

import pytest
from ame_baseline.m1_mixed_course import progressive_positions, progressive_row


def get_layout():
    name = 'ame_baseline.m1_lift_roll_layout'
    assert importlib.util.find_spec(name) is not None, 'candidate layout is not implemented'
    return importlib.import_module(name)


def test_all_obstacle_stages_identical_in_count_and_xy_only_height_changes():
    layout = get_layout()
    stages = [layout.candidate_blocks(row,fill_gap=.20) for row in (1,2,3)]
    horizontal = lambda bs: [(b.x,b.y,b.length,b.width,b.required_crossing) for b in bs]
    assert [progressive_row(row)[0] for row in (1,2,3)] == [8,8,8]
    assert all(len(bs)==78 for bs in stages)
    assert horizontal(stages[0]) == horizontal(stages[1]) == horizontal(stages[2])
    for bs,height in zip(stages,(.03,.06,.10)):
        assert all(b.height==height for b in bs)
    assert [(b.x,b.y) for b in stages[0][:8]] == [(-1.2+1.1*i,.215 if i%2==0 else -.215) for i in range(8)]


def overlaps(a, b):
    return (abs(a.x-b.x) < (a.length+b.length)/2-1e-10
            and abs(a.y-b.y) < (a.width+b.width)/2-1e-10)


@pytest.mark.parametrize('row', [1, 2, 3])
def test_deterministic_targets_follow_existing_curriculum(row):
    layout = get_layout()
    blocks = layout.candidate_blocks(row)
    assert blocks == layout.candidate_blocks(row)
    count, height, _ = progressive_row(row)
    targets = blocks[:count]
    assert all(b.required_crossing for b in targets)
    assert all(not b.required_crossing for b in blocks[count:])
    assert [(b.x,b.y) for b in targets] == list(progressive_positions(count,0,row=row)['small'])
    assert all((b.length,b.width,b.height) == (.10,.18,height) for b in targets)
    assert len(blocks) > count + 60
    assert all(b.height == height for b in blocks)
    with pytest.raises(FrozenInstanceError):
        targets[0].x = 2


@pytest.mark.parametrize('row', [1, 2, 3])
def test_fill_preserves_both_rolling_strips_spawn_and_tile(row):
    layout = get_layout()
    fill = [b for b in layout.candidate_blocks(row) if not b.required_crossing]
    reserved = [layout.Block(0,y,15.9,.26,.1,False) for y in (-.215,.215)]
    reserved += [layout.Block(-2,0,1.1,1.6,.1,False)]
    for b in fill:
        assert abs(b.x)+b.length/2 <= 7.95+1e-10
        assert abs(b.y)+b.width/2 <= 7.95+1e-10
        assert not any(overlaps(b, hole) for hole in reserved)
    for i, a in enumerate(fill):
        for b in fill[i+1:]:
            # Separated tops: at least one positive XY gap, not merely disjoint interiors.
            assert max(abs(a.x-b.x)-(a.length+b.length)/2,
                       abs(a.y-b.y)-(a.width+b.width)/2) > 1e-8


def test_stage0_and_unsupported_rows():
    layout = get_layout()
    assert layout.candidate_blocks(0) == ()
    for row in (-1,4,10,True,1.5):
        with pytest.raises(ValueError):
            layout.candidate_blocks(row)


@pytest.mark.parametrize('changes', [dict(x=math.nan),dict(y=math.inf),dict(length=0),
    dict(width=-1),dict(height=0),dict(required_crossing=1)])
def test_invalid_block_fails_closed(changes):
    layout = get_layout()
    data = dict(x=0.,y=0.,length=.1,width=.18,height=.03,required_crossing=True)
    data.update(changes)
    with pytest.raises(ValueError):
        layout.Block(**data)


def test_interval_subtraction():
    layout = get_layout()
    assert layout.subtract_interval((0,4),(1,3)) == ((0,1),(3,4))
    assert layout.subtract_interval((0,4),(-1,5)) == ()
    assert layout.subtract_interval((0,4),(5,6)) == ((0,4),)
    assert layout.subtract_interval((0,4),(-1,1)) == ((1,4),)
    for bounds in ((1,1),(2,1),(0,math.inf)):
        with pytest.raises(ValueError):
            layout.subtract_interval(bounds,(0,1))


def test_gap_sweep_is_explicit_candidate_only_and_does_not_move_targets():
    layout = get_layout()
    import inspect
    assert 'fill_gap' in inspect.signature(layout.candidate_blocks).parameters
    default = layout.candidate_blocks(1)
    wider = layout.candidate_blocks(1,fill_gap=.20)
    assert [b for b in wider if b.required_crossing] == [b for b in default if b.required_crossing]
    assert len(wider) < len(default)
    for gap in (0.,-.1,math.nan,math.inf,True):
        with pytest.raises(ValueError):
            layout.candidate_blocks(1,fill_gap=gap)
