"""Audit coherent execution independently of producer/replay agreement."""
import argparse
import copy
import pytest
from test_m1_teacher_coherent_support import coherent_teacher
from test_m1_teacher_probe_contract import probe

def record(monkeypatch):
    import test_m1_teacher_load_feedback_evidence as factory
    t,state=coherent_teacher()
    monkeypatch.setattr(factory,'load_teacher',lambda:(t,state))
    return factory.sample()

def test_cli_coherent_config_is_explicit():
    p=probe();parser=argparse.ArgumentParser();p.add_teacher_motion_options(parser)
    args=parser.parse_args(['--slow-rolling','--load-feedback','--bounded-crossing-attitude','--coherent-support-pose'])
    cfg=p.probe_teacher_config(**vars(args))
    assert cfg.coherent_support_pose
    assert not p.probe_teacher_config(**vars(parser.parse_args([]))).coherent_support_pose
    with pytest.raises(ValueError):
        p.probe_teacher_config(coherent_support_pose=True)

def test_coherent_full_audit_roundtrip(monkeypatch):
    p,t,s=record(monkeypatch)
    assert s['dynamic_support']['valid']
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]

def test_coherent_audit_does_not_reuse_producer_rotation(monkeypatch):
    import torch
    from ame_baseline import m1_teacher_pose
    p,t,s=record(monkeypatch)
    monkeypatch.setattr(m1_teacher_pose,'_rotation',lambda q:torch.eye(3,dtype=q.dtype,device=q.device).expand(len(q),3,3))
    p.verify_execution_geometry(s,t.cfg)

@pytest.mark.parametrize('field',['execution_body_goal_1_z','execution_body_goal_1_x','execution_heading_delta','height_enabled','heave_enabled','attitude_enabled'])
def test_independent_coherent_geometry_rejects_mutation(monkeypatch,field):
    p,t,s=record(monkeypatch)
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    s['teacher_diagnostic'][field]+=.02 if field.startswith('execution_') else 1
    with pytest.raises(ValueError):
        if field=='height_enabled':p.verify_support_height(s,t.cfg)
        elif field=='heave_enabled':p.verify_support_heave(s,t.cfg)
        elif field=='attitude_enabled':p.verify_load_feedback(s,t.cfg)
        else:p.verify_execution_geometry(s,t.cfg)

