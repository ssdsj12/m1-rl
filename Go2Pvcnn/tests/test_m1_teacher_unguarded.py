"""Diagnostic gate removal must not modify raw measurements or hard validity."""
from dataclasses import replace
import pytest
import torch
from ame_baseline import m1_reference_teacher as m
from test_m1_teacher_coherent_support import coherent_teacher

@pytest.mark.parametrize('value',[1,None,'yes'])
def test_unguarded_flag_is_explicit_bool(value):
    with pytest.raises(ValueError,match='unguarded'):
        m.TeacherConfig(unguarded_diagnostic=value)

def test_unguarded_requires_coherent_mode():
    with pytest.raises(ValueError,match='unguarded'):
        m.TeacherConfig(unguarded_diagnostic=True)

@pytest.mark.parametrize('condition',['collision','weak_support','com_outside'])
def test_unguarded_continues_real_transaction_without_faking_measurement(condition):
    t,s=coherent_teacher()
    t.cfg=replace(t.cfg,unguarded_diagnostic=True)
    if condition=='collision': s.collision[:]=True
    elif condition=='weak_support': s.wheel_force_w[:,3,2]=20.
    else: s.com_pos_w[:,1]+=.4
    raw=s.wheel_force_w.clone();collision=s.collision.clone()
    old=t._rows[0]['lift_age']
    out=t.step(s)
    assert out.valid.item() and not out.failure_locked.item()
    assert t._rows[0]['lift_age']==old+1
    assert torch.equal(s.wheel_force_w,raw) and torch.equal(s.collision,collision)
    d=dict(zip(m.TEACHER_DIAGNOSTIC_FIELDS,out.diagnostic[0].tolist()))
    assert d['dynamic_increment_m']>0

def test_unguarded_still_rejects_nan():
    t,s=coherent_teacher();t.cfg=replace(t.cfg,unguarded_diagnostic=True)
    s.root_pos_w[0,0]=float('nan')
    out=t.step(s)
    assert not out.valid.item()

def test_default_still_locks_weak_support():
    t,s=coherent_teacher();s.wheel_force_w[:,3,2]=20.
    out=t.step(s)
    assert not out.valid.item() and out.failure_locked.item()
