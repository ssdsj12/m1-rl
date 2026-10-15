import copy
import pytest
from test_m1_teacher_load_feedback_evidence import sample

def test_height_transaction_independent_roundtrip():
    p,t,s=sample()
    assert s['teacher_diagnostic']['height_enabled']==1
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]

@pytest.mark.parametrize('name',['height_previous_3','height_proposed_3','height_selected_3',
                                'height_committed_3','height_geometry_3','height_captured'])
def test_independent_height_audit_rejects_forgery(name):
    p,t,s=sample();s=copy.deepcopy(s)
    s['teacher_diagnostic'][name]+=1
    with pytest.raises(ValueError):p.verify_support_height(s,t.cfg)

@pytest.mark.parametrize('phase',['LIFT','RESTORE'])
def test_retained_height_history_roundtrip_and_binding(monkeypatch,phase):
    import test_m1_teacher_load_feedback_evidence as factory
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_reference_teacher import advance
    teacher,state=load_teacher()
    assert teacher.step(state).valid.item()
    teacher._rows[0]['phase']=getattr(__import__('ame_baseline.m1_reference_teacher',fromlist=['Phase']).Phase,phase)
    state=advance(state);state.root_pos_w[:,2]-=.001
    monkeypatch.setattr(factory,'load_teacher',lambda:(teacher,state))
    p,t,s=factory.sample()
    assert s['teacher_diagnostic']['height_captured']==0
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]
    forged=copy.deepcopy(s)
    forged['feedback_context']['support_height_previous'][3]+=.001
    with pytest.raises(ValueError,match='history'):p.verify_support_height(forged,t.cfg)
