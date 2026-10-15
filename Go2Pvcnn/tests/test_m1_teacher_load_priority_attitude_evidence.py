import copy
import pytest
import torch
from test_m1_teacher_load_feedback_evidence import sample


def test_attitude_context_is_present_and_audited():
    p,t,s=sample()
    assert 'attitude' in s['feedback_context']['load_feedback'], 'attitude context missing'
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]


@pytest.mark.parametrize('mutation',['active_wheel','root_translation'])
def test_attitude_original_command_forgery_rejected(mutation):
    p,t,s=sample()
    command=s['feedback_context']['load_feedback']['attitude']['command']
    if mutation=='active_wheel':command['wheels'][0][2]+=1
    else:command['root'][0]+=1
    assert p.verify_dynamic_support_sample(s,t.cfg), 'source command must bind to outer replay'


def test_float32_load_priority_boundary_matches_scalar_audit():
    from ame_baseline.m1_teacher_load_feedback import propose_load_feedback
    p,t,s=sample();c=s['feedback_context'];d=s['teacher_diagnostic'];load=c['load_feedback']
    wheels=torch.tensor([[[.3,.2,.1],[.3,-.2,.1],[-.3,.2,.1],[-.3,-.2,.1]]])
    raw=torch.tensor([[0.,135.,150.,165.]])
    fractions=torch.tensor([[1/3,.3333333,1/3]])
    old=torch.zeros_like(raw)
    out=propose_load_feedback(raw,fractions,torch.tensor([0]),old,raw.new_tensor([c['dt']]),
        torch.tensor([True]),wheels_w=wheels,attitude_error_m=old)
    c.update(active_wheel=0,control_phase=2,measured_wheels=wheels[0].tolist())
    s['preparation_input']['wheels']=wheels[0].tolist()
    s['preparation_input']['forces']=[[0.,0.,float(f)] for f in raw[0]]
    s.pop('dynamic_support',None)  # Unit-level allocator audit; outer binding tested separately.
    load.update(previous=old[0].tolist(),raw=raw[0].tolist(),fractions=fractions[0].tolist(),
        proposed=out.offset[0].tolist(),geometry_valid=True,restore=False)
    d.update(load_enabled=1,load_proposal_valid=1,load_restore=0,reference_valid=1,
        backtrack_index=0,load_active_fz=0.)
    for name,values in (('raw',raw),('target',out.target_fz),('unprojected',out.unprojected_fz),
        ('previous',old),('proposed',out.offset),('attempted',out.offset),('selected',out.offset),('committed',out.offset)):
        for j in range(4):d[f'load_{name}_{j}']=float(values.float()[0,j])
    weak=(raw<45)|((out.target_fz-raw)>15)
    strong=((raw-out.target_fz)>15)&~weak
    for j in range(1,4):
        d[f'attitude_weak_{j}']=float(weak[0,j]);d[f'attitude_strong_{j}']=float(strong[0,j])
    for j in range(3):d[f'load_affine_{j}']=float(out.active_affine.float()[0,j])
    for j,axis in enumerate('xy'):d[f'load_moment_{axis}']=float(out.moment_residual_xy.float()[0,j])
    p.verify_load_feedback(s,t.cfg)


@pytest.mark.parametrize('field',['delta','error0','error'])
def test_attitude_context_forgery_rejected(field):
    p,t,s=sample()
    assert 'attitude' in s['feedback_context']['load_feedback'], 'attitude context missing'
    s=copy.deepcopy(s);s['feedback_context']['load_feedback']['attitude'][field][3]+=.001
    with pytest.raises(ValueError):p.verify_load_feedback(s,t.cfg)


def test_nonzero_retained_attitude_roundtrip(monkeypatch):
    import test_m1_teacher_load_feedback_evidence as factory
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_reference_teacher import advance
    teacher,state=load_teacher();assert teacher.step(state).valid.item()
    state=advance(state)
    state.root_quat_w[0]=state.root_pos_w.new_tensor([.9999968750016276,.002499997395834147,0.,0.])
    monkeypatch.setattr(factory,'load_teacher',lambda:(teacher,state))
    p,t,s=factory.sample()
    assert 'attitude' in s['feedback_context']['load_feedback'], 'attitude context missing'
    a=s['feedback_context']['load_feedback']['attitude']
    assert max(map(abs,a['delta']))>1e-5
    assert p.verify_feedback_transaction(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]
    forged=copy.deepcopy(s);forged['feedback_context']['load_feedback']['attitude']['previous'][3]+=.001
    with pytest.raises(ValueError):p.verify_load_feedback(forged,t.cfg)


def test_nonzero_attitude_second_pass_backtracks_once(monkeypatch):
    import json
    from dataclasses import asdict
    import test_m1_teacher_load_feedback_evidence as factory
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_reference_teacher import advance
    teacher,state=load_teacher();assert teacher.step(state).valid.item();state=advance(state)
    state.root_quat_w[0]=state.root_pos_w.new_tensor([.9999968750016276,.002499997395834147,0.,0.])
    monkeypatch.setattr(factory,'load_teacher',lambda:(teacher,state))
    p,t,s=factory.sample();found=False
    for shift in (.02,.04,.06,.08):
        c=copy.deepcopy(s['feedback_context']);c['last_applied_q'][2]-=shift
        c['measured_root'][0]-=.005
        raw,_,_=p.replay_feedback_transaction(json.dumps(c),json.dumps(asdict(t.cfg)),s['action_target_dtype'],s['phase'])
        d=__import__('json').loads(raw)
        if d['reference_valid']!=1 or d['feedback_passes']!=2 or d['execution_fraction']>=1:continue
        found=True
        for j in range(4):
            old=c['load_feedback']['previous'][j];new=c['load_feedback']['proposed'][j]
            assert d[f'load_selected_{j}']==pytest.approx(old+d['execution_fraction']*(new-old),abs=1e-8)
    assert found,'must exercise nonzero attitude and a real second-pass backtracked solve'
