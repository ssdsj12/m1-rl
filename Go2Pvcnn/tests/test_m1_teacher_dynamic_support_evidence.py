import copy
import pytest
from test_m1_teacher_probe_contract import probe
from test_m1_teacher_lift_decoupling import crossing


def sample():
    p=probe(); teacher,state=crossing()
    state.wheel_force_w[:,3,2]=35.
    p.observe_feedback_transactions(teacher)
    p.observe_dynamic_support(teacher)
    out=teacher.step(state)
    return p,teacher,dict(dynamic_support=p.dynamic_context_for(teacher,state,0),
        teacher_action=out.action[0].tolist(),preparation_input=p.readiness_measurement(state,0,0.),
        teacher_input_frame=int(state.control_step[0]),teacher_input_episode_id=int(state.episode_id[0]),
        teacher_input_leg_pos=state.leg_pos[0].tolist(),last_applied_leg_target=state.last_applied_leg_target[0].tolist(),
        action_default_joint_pos=state.default_joint_pos[0].tolist(),action_target_dtype='float32',
        teacher_diagnostic=p.diagnostic_json(out.diagnostic[0].tolist()),
        selection_context=None,feedback_context=p.feedback_context_for(teacher,state,0),phase=int(out.phase[0]))


def test_real_outer_replay_matches_teacher():
    p,t,s=sample()
    assert s['dynamic_support'] is not None
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]
    d=s['dynamic_support']['diagnostic']
    assert d['dynamic_enabled']==1
    assert 0 <= d['dynamic_increment_m'] <= .0004+1e-7
    assert d['dynamic_filtered_fz_3']==35.


@pytest.mark.parametrize('field',['action','fingerprint','post'])
def test_outer_replay_rejects_tampered_commit(field):
    p,t,s=sample(); s=copy.deepcopy(s)
    if field=='action': s['teacher_action'][0]+=.2
    elif field=='fingerprint': s['dynamic_support']['fingerprint']='old'
    else: s['dynamic_support']['post']['dynamic_active_wheel']=3
    assert p.verify_dynamic_support_sample(s,t.cfg)


@pytest.mark.parametrize('field',['root','com','wheels','forces','frame','episode_id'])
def test_outer_replay_must_bind_actual_input(field):
    p,t,s=sample()
    value=s['preparation_input'][field]
    if field in ('frame','episode_id'): s['preparation_input'][field]+=1
    elif field in ('wheels','forces'): value[0][0]+=.1
    else: value[0]+=.1
    assert p.verify_dynamic_support_sample(s,t.cfg)


@pytest.mark.parametrize('field',['dynamic_com_target_x','dynamic_candidate_index','dynamic_increment_m','dynamic_freeze_code'])
def test_outer_com_candidate_increment_freeze_cannot_be_tampered(field):
    p,t,s=sample()
    s['dynamic_support']['diagnostic'][field]+=1
    assert p.verify_dynamic_support_sample(s,t.cfg)


def test_dynamic_candidate_does_not_masquerade_as_balance_selection():
    p,t,s=sample()
    assert p.verify_selection_sample(s,t.cfg,replay_backend='cpu',require_backend_evidence=False)==[]
