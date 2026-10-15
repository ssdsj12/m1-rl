import copy
from dataclasses import replace
import pytest
import torch
import json
from pathlib import Path
from test_m1_teacher_dynamic_support_evidence import sample


def test_native_float32_world_coordinate_receipt():
    from test_m1_teacher_probe_contract import probe
    from ame_baseline.m1_reference_teacher import TeacherConfig,ReferenceTeacher,TeacherState
    record=json.loads((Path(__file__).parent/'fixtures/reconciliation_v17_native.json').read_text())
    p=probe(); cfg=TeacherConfig(slow_rolling=True); teacher=ReferenceTeacher(cfg)
    old=record['contexts'][0]  # Complete real input; old scalar-only fixture is retained unchanged.
    state=TeacherState(**p._dynamic_unpack(old['input'],'cpu'))
    teacher._rows=[p._dynamic_unpack(old['pre'],'cpu')]
    p.observe_dynamic_support(teacher)
    out=teacher.step(state)
    current=dict(dynamic_support=p.dynamic_context_for(teacher,state,0),
        teacher_diagnostic=p.diagnostic_json(out.diagnostic[0].tolist()))
    assert out.valid.item()
    assert p.verify_tripod_sample(current,cfg)==[]


def test_valid_tripod_receipt_passes():
    p,t,s=sample()
    assert p.verify_tripod_sample(s,t.cfg)==[]


@pytest.mark.parametrize('field',['tripod_min_load_n','tripod_captured_total_n'])
def test_tampered_capture_or_minimum_rejected(field):
    p,t,s=sample()
    s['teacher_diagnostic'][field]+=20.
    assert p.verify_tripod_sample(s,t.cfg)


def test_reset_identity_mismatch():
    p,t,s=sample()
    s['dynamic_support']['pre']['tripod_capture_identity'][0]+=1
    assert p.verify_tripod_sample(s,t.cfg)


def test_joint_producer_replay_corruption_rejected(monkeypatch):
    import ame_baseline.m1_reference_teacher as producer
    real=producer.tripod_load
    def wrong(*args):
        out=real(*args)
        return replace(out,min_load_n=out.min_load_n+10.)
    monkeypatch.setattr(producer,'tripod_load',wrong)
    p,t,s=sample()
    assert p.verify_tripod_sample(s,t.cfg)


def test_joint_increment_corruption_rejected(monkeypatch):
    import ame_baseline.m1_reference_teacher as producer
    real=producer.measured_lift_step
    def wrong(*args,**kwargs):
        out=real(*args,**kwargs)
        inc=torch.full_like(out.increment,.0004)
        return replace(out,increment=inc,next_z=args[0]+inc)
    monkeypatch.setattr(producer,'measured_lift_step',wrong)
    p,t,s=sample()
    assert p.verify_tripod_sample(s,t.cfg)


def test_successful_restore_clears_capture_and_validates_terminal_input():
    from test_m1_teacher_reference_commit import prepared_teacher,feedback
    from test_m1_teacher_probe_contract import probe
    from test_m1_reference_teacher import api
    p=probe(); t,s,_=prepared_teacher(rolling=True)
    t._rows[0]['phase']=api().Phase.RESTORE
    s.centers_top[:,0,0]=s.wheel_pos_w[:,0,0]-.5
    s.recovered[:,0,0]=True
    p.observe_dynamic_support(t)
    for _ in range(30):
        out=t.step(s)
        if t._rows[0]['wheel']==-1:
            record=dict(dynamic_support=p.dynamic_context_for(t,s,0),
                teacher_diagnostic=p.diagnostic_json(out.diagnostic[0].tolist()))
            assert p.verify_tripod_sample(record,t.cfg)==[]
            assert 'tripod_captured_load_n' not in t._rows[0]
            assert 'tripod_combined_reserve' not in t._rows[0]
            # A new obstacle must capture its own force scale, not reuse240N.
            s=feedback(s,t,out)
            s.course_ids[:]=1; s.recovered.zero_()
            s.centers_top[:,0,0]=s.wheel_pos_w[:,0,0]+.05+.11915+.06
            s.wheel_force_w[:,:,2]=80.
            for _ in range(80):
                nxt=t.step(s)
                if t._rows[0].get('prepared'):
                    assert t._rows[0]['tripod_capture_identity'][2]==1
                    assert t._rows[0]['tripod_captured_load_n'].item()==320.
                    break
                s=feedback(s,t,nxt)
            else: raise AssertionError('new target not captured')
            break
        s=feedback(s,t,out)
    else: raise AssertionError('fixture did not finish restoration')
