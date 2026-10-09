import pytest
from scripts.m1_support_geometry import triangle_margin


@pytest.mark.parametrize('vertices', [((0,0),(1,0),(0,1)), ((0,1),(1,0),(0,0))])
def test_signed_triangle_margin(vertices):
    assert triangle_margin((.2,.2), vertices) == pytest.approx(.2)
    assert triangle_margin((.8,.8), vertices) == pytest.approx(-.6 / 2**.5)
    assert triangle_margin((.5,.5), vertices) == pytest.approx(0.)


def test_degenerate_or_missing_support_is_not_valid():
    assert triangle_margin((0,0), ((0,0),(1,0),(2,0))) is None
    assert triangle_margin((0,0), ((0,0),(1,0))) is None
    assert triangle_margin((float('nan'),0), ((0,0),(1,0),(0,1))) is None
