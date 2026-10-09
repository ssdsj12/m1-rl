import pytest


def test_default_covers_every_leg_and_override_isolates_one_leg():
    from ame_baseline.m1_rolling_speed import selected_legs
    assert selected_legs(None)==[0,1,2,3,0,1,2,3]
    for leg in range(4):assert selected_legs(leg)==[leg]*8


@pytest.mark.parametrize('leg',[-1,4,2.,True])
def test_bad_leg_rejected(leg):
    from ame_baseline.m1_rolling_speed import selected_legs
    with pytest.raises(ValueError):selected_legs(leg)
