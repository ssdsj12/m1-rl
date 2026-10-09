import importlib.util
from pathlib import Path
import numpy as np
import pytest


def candidates():
    p=Path(__file__).parents[1]/'ame_baseline/m1_wbc_candidates.py'
    assert p.exists(), 'bounded point-mode enumeration missing'
    s=importlib.util.spec_from_file_location('candidates',p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m.rest_contact_candidates


def test_preserves_duplicate_force_slots_and_enumerates_release_choices():
    p=np.array([[0,0,0],[0,0,0],[1,0,0],[2,0,0],[3,0,0]],float)
    owners=np.array([0,0,0,1,2])
    modes=candidates()(p,owners,groups=3,max_candidates=8)
    assert len(modes)==3
    assert all(m[0]==m[1] and m[3] and m[4] for m in modes)
    assert {tuple(m.tolist()) for m in modes}=={
        (True,True,True,True,True),(True,True,False,True,True),
        (False,False,True,True,True)}


def test_budget_rejects_instead_of_silently_dropping_modes():
    p=np.arange(9).reshape(3,3)
    with pytest.raises(ValueError): candidates()(p,np.zeros(3,int),groups=1,max_candidates=4)


def test_missing_support_group_rejects():
    with pytest.raises(ValueError): candidates()(np.zeros((1,3)),np.array([0]),groups=2)


def test_nonfinite_points_reject():
    with pytest.raises(ValueError): candidates()(np.full((1,3),np.nan),np.array([0]),groups=1)
