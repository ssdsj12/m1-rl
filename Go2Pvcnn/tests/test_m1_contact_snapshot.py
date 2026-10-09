def test_contact_snapshot_respects_buffer_offsets_and_zero_count():
    from ame_baseline.m1_contact_snapshot import pair_records
    result=pair_records([99.,12.,0.],[[9,9,9],[1,2,3],[4,5,6]],[9.,-.001,.0002],[2,0],[1,0])
    assert result==[{'normal':[12.,0.],'points':[[1,2,3],[4,5,6]],'separation':[-.001,.0002]},
                    {'normal':[],'points':[],'separation':[]}]


def test_contact_snapshot_rejects_truncated_buffers():
    import pytest
    from ame_baseline.m1_contact_snapshot import pair_records
    with pytest.raises(ValueError):
        pair_records([1.],[[0,0,0]],[0.],[2],[0])


def test_friction_wrench_uses_pair_offsets_and_origin():
    from ame_baseline.m1_contact_snapshot import friction_wrenches
    result=friction_wrenches([[99,99,99],[2,0,0],[0,3,0]],
        [[0,0,0],[1,1,0],[2,0,0]],[2,0],[1,0],[1,0,0])
    assert result == [{'force':[2,3,0],'moment':[0,0,1],'count':2},
                      {'force':[0,0,0],'moment':[0,0,0],'count':0}]


def test_friction_wrench_rejects_truncated_and_nonfinite_active_data():
    import pytest
    from ame_baseline.m1_contact_snapshot import friction_wrenches
    with pytest.raises(ValueError):
        friction_wrenches([[1,0,0]],[[0,0,0]],[2],[0],[0,0,0])
    with pytest.raises(ValueError):
        friction_wrenches([[float('nan'),0,0]],[[0,0,0]],[1],[0],[0,0,0])
