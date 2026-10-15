import copy
import pytest
from test_m1_teacher_load_feedback_transaction import load_teacher
from test_m1_teacher_probe_contract import probe
from ame_baseline.m1_ame_contract import m1_action_targets

def sample():
    p=probe();teacher,s=load_teacher()
    p.observe_feedback_transactions(teacher);p.observe_dynamic_support(teacher)
    out=teacher.step(s)
    sample=dict(dynamic_support=p.dynamic_context_for(teacher,s,0),
        feedback_context=p.feedback_context_for(teacher,s,0),
        teacher_diagnostic=p.diagnostic_json(out.diagnostic[0].tolist()),
        teacher_action=out.action[0].tolist(),applied_targets=m1_action_targets(out.action,s.default_joint_pos)[0].tolist(),
        preparation_input=p.readiness_measurement(s,0,0.),
        action_target_dtype='float32',phase=int(out.phase[0]),
        teacher_input_frame=int(s.control_step[0]),teacher_input_episode_id=int(s.episode_id[0]),
        teacher_input_leg_pos=s.leg_pos[0].tolist(),last_applied_leg_target=s.last_applied_leg_target[0].tolist(),
        action_default_joint_pos=s.default_joint_pos[0].tolist())
    return p,teacher,sample

def test_load_feedback_roundtrip_and_geometry():
    p,t,s=sample()
    assert s['teacher_diagnostic']['load_enabled']==1
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]
    assert p.verify_tripod_sample(s,t.cfg)==[]

@pytest.mark.parametrize('name',['load_raw_3','load_target_3','load_previous_3','load_proposed_3',
                                 'load_selected_3','load_committed_3','load_attempted_3',
                                 'load_unprojected_3','load_affine_2','load_moment_x','load_moment_y','load_active_fz'])
def test_independent_load_audit_rejects_forged_values(name):
    p,t,s=sample();s=copy.deepcopy(s)
    s['teacher_diagnostic'][name]+=1.
    with pytest.raises(ValueError):p.verify_load_feedback(s,t.cfg)
    assert p.verify_feedback_transaction(s,t.cfg)

def test_independent_audit_binds_raw_wheel_geometry():
    p,t,s=sample();s=copy.deepcopy(s)
    s['feedback_context']['measured_wheels'][0][0]+=.01
    with pytest.raises(ValueError,match='geometry binding'):
        p.verify_load_feedback(s,t.cfg)

def test_near_collinear_float32_producer_to_independent_audit():
    import torch
    from ame_baseline.m1_teacher_load_feedback import propose_load_feedback
    p,t,s=sample();c=s['feedback_context'];d=s['teacher_diagnostic'];load=c['load_feedback']
    wheels=torch.tensor([[[.3,.2,.1],[0.,0.,.1],[1.,1.,.1],[1.,1.+1e-7,.1]]])
    raw=torch.tensor([[60.,100.,100.,100.]]);fractions=torch.tensor([[.4,.4,.2]])
    old=torch.zeros_like(raw)
    out=propose_load_feedback(raw,fractions,torch.tensor([0]),old,raw.new_tensor([c['dt']]),
        torch.tensor([True]),wheels_w=wheels)
    c['active_wheel']=0;c['control_phase']=2;c['measured_wheels']=wheels[0].tolist()
    s['preparation_input']['wheels']=wheels[0].tolist()
    s['preparation_input']['forces']=[[0.,0.,float(f)] for f in raw[0]]
    s.pop('dynamic_support',None)
    load.update(previous=old[0].tolist(),raw=raw[0].tolist(),fractions=fractions[0].tolist(),
        proposed=out.offset[0].tolist(),geometry_valid=True,restore=False)
    d.update(load_enabled=1,load_proposal_valid=1,load_restore=0,reference_valid=1,backtrack_index=0,load_active_fz=60.)
    for name,values in (('raw',raw),('target',out.target_fz),('unprojected',out.unprojected_fz),
        ('previous',old),('proposed',out.offset),('attempted',out.offset),('selected',out.offset),('committed',out.offset)):
        for j in range(4):d[f'load_{name}_{j}']=float(values.float()[0,j])
    for j in range(3):d[f'load_affine_{j}']=float(out.active_affine.float()[0,j])
    for j,axis in enumerate('xy'):d[f'load_moment_{axis}']=float(out.moment_residual_xy.float()[0,j])
    p.verify_load_feedback(s,t.cfg)

def test_probe_load_switch_is_explicit():
    p=probe()
    assert p.probe_teacher_config(slow_rolling=True,load_feedback=True).load_feedback
    assert not p.probe_teacher_config(slow_rolling=True).load_feedback
    with pytest.raises(ValueError):p.probe_teacher_config(load_feedback=True)

def test_fraction_source_cannot_be_forged():
    p,t,s=sample();s=copy.deepcopy(s)
    s['feedback_context']['load_feedback']['fractions']=[.333,.333,.334]
    assert p.verify_tripod_sample(s,t.cfg)
