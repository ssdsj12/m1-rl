import numpy as np
import pytest
from ame_baseline import m1_wbc_contacts


def inventory(**values):
    function=getattr(m1_wbc_contacts, 'contact_inventory', None)
    assert callable(function), 'near-contact geometry must survive zero measured force'
    return function(**values)


def data():
    return dict(points=np.array([[.33,0,0],[.28,0,0],[.28,0,0],[.33,0,0]]),
        normals=np.tile([0.,0.,1.],(4,1)),owners=np.array([1,1,1,1]),
        gaps=np.array([2e-7,28e-6,28e-6,2e-7]),
        normal_forces=np.array([110.,0.,0.,2.4]))


def test_preserves_approaching_zero_force_point_as_distinct_geometry():
    result=inventory(**data())
    assert len(result['points'])==2
    assert result['measured_loaded'].tolist()==[True,False]
    np.testing.assert_allclose(result['normal_forces'],[112.4,0.])
    np.testing.assert_allclose(result['gaps'],[2e-7,28e-6])
    assert result['source_indices']==[[0,3],[1,2]]


def test_zero_force_never_fakes_support_and_loaded_mask_is_not_attach_mode():
    values=data();values['normal_forces'][:]=0.
    result=inventory(**values)
    assert len(result['points'])==2 and not result['measured_loaded'].any()
    assert 'attached' not in result


def test_duplicate_merge_preserves_total_normal_force_and_wrench():
    values=data();values['normal_forces'][1:3]=[12.,3.]
    result=inventory(**values)
    raw_f=values['normal_forces'][:,None]*values['normals']
    new_f=result['normal_forces'][:,None]*result['normals']
    np.testing.assert_allclose(raw_f.sum(0),new_f.sum(0))
    np.testing.assert_allclose(np.cross(values['points'],raw_f).sum(0),
                               np.cross(result['points'],new_f).sum(0))


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1.])
def test_invalid_normal_force_is_rejected_even_when_not_loaded(bad):
    values=data();values['normal_forces'][1]=bad
    with pytest.raises(ValueError,match='normal force'):
        inventory(**values)


def test_empty_inventory_has_aligned_shapes():
    result=inventory(points=np.empty((0,3)),normals=np.empty((0,3)),
        owners=np.empty(0,dtype=int),gaps=np.empty(0),normal_forces=np.empty(0))
    assert result['normal_forces'].shape==(0,)
    assert result['measured_loaded'].shape==(0,)
