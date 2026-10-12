import importlib.util
import torch
import pytest


def module():
    assert importlib.util.find_spec('ame_baseline.m1_reference_geometry') is not None
    from ame_baseline import m1_reference_geometry
    return m1_reference_geometry


def test_cylinder_bottom_uses_measured_orientation_not_old_mesh():
    g=module(); p=torch.tensor([[[0.,0.,.2]]]); q=torch.tensor([[[1.,0.,0.,0.]]])
    torch.testing.assert_close(g.cylinder_bottom(p,q),torch.tensor([[.1041]]))
    q=torch.tensor([[[2**-.5,2**-.5,0.,0.]]])
    torch.testing.assert_close(g.cylinder_bottom(p,q),torch.tensor([[.2-.0465/2]]))
    with pytest.raises(ValueError): g.cylinder_bottom(p,torch.zeros_like(q))


def test_round_leading_edge_clearance_not_whole_bottom():
    g=module()
    # Box near x=-.05/top=.03. Circle overlaps in XY, but its curved tip is above top.
    p=torch.tensor([[[-.13,0.,.105],[0.,0.,.105],[0.,0.,.14]]])
    q=torch.tensor([[[1.,0.,0.,0.]]]).expand(1,3,4)
    result=g.cylinder_clears_box(p,q,torch.tensor([[0.,0.,.03]]),torch.tensor([[.05,.09]]))
    assert result.tolist()==[[True,False,True]]
    assert (g.cylinder_bottom(p,q)[0,:2]<.03).all()


def test_separation_certificate_invariant_to_translation_and_rejects_invalid_pose():
    g=module(); p=torch.tensor([[[-.13,0.,.105]]]);q=torch.tensor([[[1.,0.,0.,0.]]])
    box=torch.tensor([[0.,0.,.03]]); ext=torch.tensor([[.05,.09]])
    off=torch.tensor([5.,3.,.9])
    assert torch.equal(g.cylinder_clears_box(p,q,box,ext),g.cylinder_clears_box(p+off,q,box+off,ext))
    with pytest.raises(ValueError):g.cylinder_clears_box(p,q*float('nan'),box,ext)


def test_runtime_cylinder_measurement_is_wired():
    from pathlib import Path
    root=Path(__file__).parents[1]/'ame_baseline'
    assert 'cylinder_bottom(' in (root/'ame_env_wrapper.py').read_text()
    assert 'cylinder_geometry=True' in (root/'ame_env_wrapper.py').read_text()
    assert 'clearance_safe=' in (root/'m1_dynamic_crossing.py').read_text()
