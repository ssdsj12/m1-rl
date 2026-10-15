import copy
import pytest
from test_m1_teacher_dynamic_support_evidence import sample


def bound_sample():
    p,t,s=sample()
    s['applied_targets']=list(p.decoded_request_targets(tuple(s['teacher_action']),
        tuple(s['action_default_joint_pos']),s['action_target_dtype']))
    return p,t,s


def test_measured_transaction_replays_final_execution():
    p,t,s=bound_sample()
    assert s['teacher_diagnostic']['execution_mode']==1
    assert p.verify_feedback_transaction(s,t.cfg)==[]


@pytest.mark.parametrize('key',['measured_quat','active_wheel','execution_enabled','missing'])
def test_measured_context_cannot_be_substituted(key):
    p,t,s=bound_sample(); s=copy.deepcopy(s); c=s['feedback_context']
    if key=='measured_quat': c[key]=[1.,0.,.01,0.]
    elif key=='active_wheel': c[key]=1
    elif key=='missing': c.pop('measured_quat',None)
    else: c[key]=False
    assert p.verify_feedback_transaction(s,t.cfg)


@pytest.mark.parametrize('key',['execution_mode','execution_fraction','execution_body_goal_0_z','execution_body_step_0_z'])
def test_execution_diagnostic_cannot_be_forged(key):
    p,t,s=bound_sample(); s['teacher_diagnostic'][key]+=.1
    assert p.verify_feedback_transaction(s,t.cfg)


def test_shared_producer_target_bug_is_rejected_independently(monkeypatch):
    from dataclasses import replace
    import ame_baseline.m1_teacher_execution_targets as target
    real=target.execution_targets
    def wrong(*args):
        result=real(*args)
        # A support-leg corruption survives active-intent recomputation.
        # Corrupting only leg 0 can be corrected by that real downstream path.
        goal=result.body_goal.clone(); goal[:,1,2]+=.004
        step=result.body_step.clone(); step[:,1,2]+=.004*result.fraction
        return replace(result,body_goal=goal,body_step=step)
    monkeypatch.setattr(target,'execution_targets',wrong)
    p,t,s=bound_sample()
    p.replay_feedback_transaction.cache_clear()
    assert p.verify_feedback_transaction(s,t.cfg), 'replay shares producer bug; independent geometry must reject'
