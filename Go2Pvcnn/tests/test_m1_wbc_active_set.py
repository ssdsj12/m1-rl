import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest


def fallback():
    p=Path(__file__).parents[1]/'ame_baseline/m1_wbc_active_set.py'
    assert p.exists(), 'independent equality-reduced active-set oracle missing'
    s=importlib.util.spec_from_file_location('active',p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m.solve_active_set


def test_duplicate_equalities_are_reduced_without_dropping_original_checks():
    a=np.array([[1.,1.],[2.,2.],[1.,0.],[0.,1.]])
    r=fallback()(np.eye(2),np.zeros(2),a,np.array([1.,2.,0.,0.]),
                 np.array([1.,2.,np.inf,np.inf]),time_limit=.05)
    assert r['valid'],r['reason']
    np.testing.assert_allclose(r['x'],[.5,.5],atol=1e-8)
    assert r['max_violation']<1e-8


def test_inconsistent_equalities_return_no_command():
    r=fallback()(np.eye(2),np.zeros(2),np.array([[1.,1.],[2.,2.]]),
                 np.array([1.,3.]),np.array([1.,3.]),time_limit=.05)
    assert not r['valid'] and r['x'] is None


def test_fully_fixed_equalities_and_zero_time_budget():
    args=(np.eye(2),np.zeros(2),np.eye(2),np.array([1.,2.]),np.array([1.,2.]))
    r=fallback()(*args,time_limit=.05)
    assert r['valid']; np.testing.assert_allclose(r['x'],[1.,2.])
    r=fallback()(*args,time_limit=0.)
    assert not r['valid'] and r['x'] is None


def test_captured_native_all_attached_case_passes_unchanged_physical_constraints():
    from test_m1_wbc_qp import solver
    data=json.loads((Path(__file__).parent/'fixtures/m1_wbc_rest_fixture.json').read_text())['kwargs']
    for key in ('contact_matrix','separation_matrix'):
        data[key]=np.asarray(data[key],float).reshape(-1,22)
    r=solver()(**data)
    assert r['valid'],r
    assert r['max_violation']<=1e-5
    assert any(s.get('fallback_status')=='solved' for s in r['stages'])
