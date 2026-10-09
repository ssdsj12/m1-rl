import importlib.util
from pathlib import Path
import numpy as np
import pytest


def motion():
    p=Path(__file__).parents[1]/'ame_baseline/m1_wbc_motion.py'
    assert p.exists(), 'measured contact motion decomposition missing'
    spec=importlib.util.spec_from_file_location('motion',p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.contact_motion


def test_material_velocity_relative_to_ground_not_wheel_center():
    # Circle rolling at .2m/s with radius.1: bottom material point is stationary.
    r=motion()(points=[[0,0,0]], normals=[[0,0,1]], owners=[0],
        com_positions=[[0,0,.1]], com_velocity=[[.2,0,0,0,2,0]],
        surface_velocity=[[0,0,0]])
    np.testing.assert_allclose(r['relative_velocity'],0,atol=1e-12)
    np.testing.assert_allclose(r['slip_speed'],0,atol=1e-12)


def test_separation_slip_and_moving_surface_are_distinct():
    r=motion()(points=[[0,0,0]], normals=[[0,0,1]], owners=[0],
        com_positions=[[0,0,0]], com_velocity=[[.3,.4,.02,0,0,0]],
        surface_velocity=[[.3,0,0]])
    np.testing.assert_allclose(r['normal_speed'],[.02])
    np.testing.assert_allclose(r['slip_speed'],[.4])


def test_invalid_normals_and_nonfinite_motion_rejected():
    data=dict(points=[[0,0,0]],normals=[[0,0,2]],owners=[0],
        com_positions=[[0,0,0]],com_velocity=[[0,0,0,0,0,0]],surface_velocity=[[0,0,0]])
    with pytest.raises(ValueError): motion()(**data)
    data['normals']=[[0,0,1]];data['com_velocity']=[[float('nan'),0,0,0,0,0]]
    with pytest.raises(ValueError): motion()(**data)


def test_probe_records_unloaded_contacts_and_native_separations():
    source=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert 'M1_WBC_CONTACT_MOTION ' in source
    assert 'native_separation' in source
    assert source.index('raw_contacts.append(')<source.index('if strength > 0:')
