import pytest


@pytest.mark.parametrize('selected',range(4))
def test_airborne_control_drives_only_selected_and_default_only_supports(selected):
    from ame_baseline.m1_rolling_speed import drive_columns
    assert drive_columns(selected,True)==(selected,)
    assert drive_columns(selected,False)==tuple(i for i in range(4) if i!=selected)


@pytest.mark.parametrize('selected,mode',[(-1,True),(4,True),(1.,True),(True,True),(0,1)])
def test_invalid_selection_rejected(selected,mode):
    from ame_baseline.m1_rolling_speed import drive_columns
    with pytest.raises(ValueError): drive_columns(selected,mode)
