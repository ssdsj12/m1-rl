import copy
import pytest
from test_m1_teacher_load_feedback_evidence import sample

def test_heave_diagnostics_and_independent_roundtrip():
    p,t,s=sample()
    assert s['teacher_diagnostic']['heave_captured']==1
    assert s['teacher_diagnostic']['heave_committed']==0
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]

@pytest.mark.parametrize('field',['heave_error0','heave_previous','heave_proposed','heave_selected','heave_committed','heave_captured'])
def test_heave_independent_audit_rejects_forgery(field):
    p,t,s=sample();s=copy.deepcopy(s)
    s['teacher_diagnostic'][field]=s['teacher_diagnostic'].get(field,0)+.1
    with pytest.raises(ValueError):p.verify_support_heave(s,t.cfg)

@pytest.mark.parametrize('phase',['LIFT','RESTORE'])
def test_heave_retained_history_roundtrip(monkeypatch,phase):
    import test_m1_teacher_load_feedback_evidence as factory
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_reference_teacher import advance,api
    t,state=load_teacher();assert t.step(state).valid.item()
    state=advance(state);state.root_pos_w[:,2]-=.001
    assert t.step(state).valid.item()
    assert t._rows[0]['support_heave'].item()<0
    t._rows[0]['phase']=getattr(api().Phase,phase)
    state=advance(state)
    monkeypatch.setattr(factory,'load_teacher',lambda:(t,state))
    p,t,s=factory.sample()
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]
    changed=copy.deepcopy(s);changed['feedback_context']['support_heave_previous'][0]+=.001
    with pytest.raises(ValueError):p.verify_support_heave(changed,t.cfg)
