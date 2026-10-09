import importlib.util
from pathlib import Path
import numpy as np
import pytest


def coefficient():
    p=Path(__file__).parents[1]/'ame_baseline/m1_wbc_materials.py'
    assert p.exists(), 'measured material combination adapter missing'
    spec=importlib.util.spec_from_file_location('materials',p)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.conservative_friction


@pytest.mark.parametrize('mode,expected',[
    ('average',.65),('min',.3),('multiply',.3),('max',1.)])
def test_modes_apply_to_measured_static_and_dynamic_values(mode,expected):
    fn=coefficient()
    assert fn(np.array([[.8,.3,0.]]),['average'],[1.,1.,0.],mode)==pytest.approx(expected)


def test_priority_is_not_minimum_or_alphabetical():
    fn=coefficient()
    assert fn([[.8,.4,0.]],['multiply'],[.5,.5,0.],'min')==pytest.approx(.2)
    assert fn([[.8,.4,0.]],['max'],[.5,.5,0.],'multiply')==pytest.approx(.5)


def test_lowest_of_all_shapes_and_both_coefficients_bounds_unknown_patch():
    fn=coefficient()
    assert fn([[.8,.9,0.],[.6,.2,.1]],['average','average'],[1.,1.,0.],'multiply')==pytest.approx(.2)


@pytest.mark.parametrize('fault',['empty','nan','negative','unknown','count'])
def test_invalid_or_unmapped_materials_reject(fault):
    fn=coefficient(); mat=np.array([[.8,.3,0.]]); modes=['average']
    if fault=='empty': mat=np.zeros((0,3)); modes=[]
    elif fault=='nan': mat[0,0]=np.nan
    elif fault=='negative': mat[0,1]=-.1
    elif fault=='unknown': modes=['unknown']
    else: modes=[]
    with pytest.raises(ValueError): fn(mat,modes,[1.,1.,0.],'multiply')
