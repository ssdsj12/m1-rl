import math
import pytest


@pytest.mark.parametrize('seed', range(5))
def test_dense_front_is_reserved_and_background_cannot_block_landing(seed):
    from ame_baseline.m1_mixed_course import dense_forward_positions
    out = dense_forward_positions(165, 3, seed=seed, tile_size=(16., 8.))
    assert len(out['small']) == 165
    assert len(out['large']) == 3
    front = out['small'][:8]
    assert front == tuple((.9 + .9*i, .215 if i % 2 == 0 else -.215) for i in range(8))
    for x,y in out['small'][8:] + out['large']:
        assert not (x > .5 and abs(y) < .8)
    for x,y in front:
        assert x > 0 and abs(y) == .215
        assert x + .05/math.sqrt(2) < 7.5
    # Nominal front/rear contact events do not overlap wheel+block envelopes.
    events=sorted([x+offset for x,_ in front for offset in (0.,.544)])
    assert min(b-a for a,b in zip(events,events[1:])) > 2*.095958+.05+.05


def test_dense_requires_enough_space_and_eight_obstacles():
    from ame_baseline.m1_mixed_course import dense_forward_positions
    with pytest.raises(ValueError):
        dense_forward_positions(7,0,seed=0,tile_size=(16.,8.))
    with pytest.raises(ValueError):
        dense_forward_positions(8,0,seed=0,tile_size=(8.,8.))


def test_dense_runtime_configuration_has_square_tiles_and_fixed_commands():
    from pathlib import Path
    text=(Path(__file__).parents[1]/'ame_baseline/m1_mixed_course.py').read_text()
    assert 'terrain_generator.size = (16., 16.)' in text
    for field in ('ranges','limit_ranges'):
        for axis in ('lin_vel_y','ang_vel_z'):
            assert f'cfg.commands.base_velocity.{field}.{axis}=(0.,0.)' in text
