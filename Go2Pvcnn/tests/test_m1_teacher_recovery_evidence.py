"""Measured recovery replay, identity binding and acceptance regression tests."""
import copy
from dataclasses import replace

import pytest
import torch

from test_m1_teacher_probe_contract import probe, episode, verify_episode, real_video_files


def recovery_evidence(record):
    """Hand-checked CPU measurements: sixteen qualifying observations, 15 intervals."""
    from ame_baseline.m1_reference_teacher import LEG_COLUMNS
    count=len(record['samples']); crossing=record['stage']==3
    ids=list(range(8)) if crossing else []
    required=[[w in ((0,2) if i%2==0 else (1,3)) for w in range(4)] for i in ids]
    record['recovery_contract']='crossing-recovery-0p3-v1'
    record['initial_root_quat_w']=[1.,0.,0.,0.]
    record['recovery_nominal_root_z_w']=.62
    record['recovery_scope']=dict(dtype='float32',env_id=[record['env_id']],
        episode_id=[record['episode_id']],scope_id=[record['episode_id']],course_ids=[ids],
        required=[required],centers_w=[[[-2.+i*.1,0.,.1] for i in ids]],
        half_extents=[[[.05,.09] for i in ids]],forward_w=[[1.,0.,0.]])
    for sample in record['samples']:
        f=sample['frame']; ready=crossing and f>=count-15
        sample['receipt']=copy.deepcopy(record['required']) if ready else []
        sample['far_side_recovery']=copy.deepcopy(sample['receipt'])
        sample['course_ids']=ids.copy()
        sample['course_centers_top']=[[-2.+i*.1,0.,.1] for i in ids]
        sample['course_half_extents']=[[.05,.09] for i in ids]
        sample['course_valid']=[True for i in ids]
        sample['control_dt_s']=.02
        sample['natural_done']=bool(not crossing and f==count)
        sample['timeout']=sample['natural_done']
        sample['wheel_quaternion']=[[1.,0.,0.,0.]]*4
        sample['wheel_position']=[[sample['root'][0]+x,y,.096] for x,y in ((.3,.2),(.3,-.2),(-.3,.2),(-.3,-.2))]
        sample['force']=[[0.,0.,50.]]*4
        sample['joints']=sample['action_default_joint_pos'].copy()
        sample['default_leg_pos']=[sample['action_default_joint_pos'][i] for i in LEG_COLUMNS]
        sample['nominal_root_z_w']=.62
        sample['measurement_valid']=True; sample['base_contact']=False
        sample['recovery_input']=dict(env_id=[record['env_id']],episode_id=[record['episode_id']],
            scope_id=[record['episode_id']],frame=[f],sim_time_s=[sample['sim_time']],dt_s=[.02],
            root_state_w=[sample['root'].copy()],leg_pos=[[sample['joints'][i] for i in LEG_COLUMNS]],
            default_leg_pos=[sample['default_leg_pos']],wheel_pos_w=[sample['wheel_position']],
            wheel_quat_w=[sample['wheel_quaternion']],wheel_force_w=[sample['force']],
            nominal_root_z_w=[.62],course_ids=[ids.copy()],
            recovered=[copy.deepcopy(required) if ready else [[False]*4 for _ in ids]],
            valid=[True],collision=[False],penetration=[False],base_contact=[False],
            physical_failure=[False],reset=[False],ended=[bool(sample.get('timeout',False))])
        n=f-(count-15)
        stable=ready
        sample['recovery_result']=dict(eligible=[ready],stable=[stable],success=[ready and n>=15],
            vetoed=[False],interval_count=[max(0,n) if ready else 0],
            start_frame=[count-15 if ready else -1],last_frame=[f if ready else -1],
            elapsed_s=[n*.02 if ready else 0.],start_time_s=[(count-15)*.02 if ready else float('nan')],
            net_forward_m=[n*.006 if ready else float('nan')],
            reason=['ended' if sample['timeout'] else 'success' if ready and n>=15 else 'pending_window' if ready else 'incomplete_scope'])
    record['terminal']=copy.deepcopy(record['samples'][-1])
    return record


def test_recovery_record_tampering_and_suite_gates():
    module=probe()
    assert hasattr(module,'verify_recovery_record'), 'raw recovery verifier missing'
    record=episode()
    assert module.verify_recovery_record(record)==[]
    assert verify_episode(record)['success']
    for mutate in (
        lambda r:r['samples'][-1]['recovery_input'].pop('wheel_quat_w'),
        lambda r:r['samples'][-1]['recovery_input'].pop('sim_time_s'),
        lambda r:r['samples'][-1]['recovery_input'].pop('episode_id'),
        lambda r:r['samples'][-1]['recovery_result']['net_forward_m'].__setitem__(0,1.),
        lambda r:r['samples'][-1]['recovery_result']['elapsed_s'].__setitem__(0,1.),
        lambda r:r['samples'][0]['recovery_result']['success'].__setitem__(0,True),
        lambda r:r['recovery_scope']['required'][0][0].__setitem__(0,False),
        lambda r:r['recovery_scope']['forward_w'].__setitem__(0,[0.,1.,0.]),
        lambda r:r['recovery_scope']['course_ids'][0].__setitem__(0,.5),
        lambda r:r['samples'][-1]['course_ids'].__setitem__(0,99),
        lambda r:r.pop('recovery_contract'),
    ):
        damaged=copy.deepcopy(record); mutate(damaged)
        assert module.verify_recovery_record(damaged)
        assert not verify_episode(damaged)['success']
    old=copy.deepcopy(record)
    for sample in old['samples']: sample.pop('recovery_input'); sample.pop('recovery_result')
    assert module.verify_recovery_record(old)
    assert verify_episode(episode(stage=0))['success']
    assert module.verify_suite([record],diagnostic=True)['milestone_a']=='FAILED_DIAGNOSTIC'


def test_capture_scope_selection_order_and_explicit_receipt_identity():
    from test_m1_reference_teacher import state
    module=probe()
    assert hasattr(module,'capture_recovery_scope'), 'scope capture missing'
    s=state(batch=3); s=replace(s,course_ids=torch.tensor([[9],[5],[7]]))
    scope=module.capture_recovery_scope(s,torch.tensor([2,0]),[[[7,0],[7,2]],[[9,0],[9,2]]],scope_ids=torch.tensor([8,6]))
    assert scope.env_id.tolist()==[2,0] and scope.course_ids.tolist()==[[7],[9]]
    frozen=scope.centers_w.clone(); s.centers_top.zero_()
    assert torch.equal(scope.centers_w,frozen)
    rec=episode(); raw=copy.deepcopy(rec['samples'][-1]['recovery_input'])
    scope=module.recovery_scope_from_json(rec['recovery_scope'])
    # Same actual IDs in reversed order still map to the frozen IDs.
    raw['course_ids'][0].reverse(); raw['recovered'][0].reverse()
    frame=module.capture_recovery_frame(raw,scope)
    assert torch.equal(frame.recovered,scope.required)
    raw['course_ids'][0][0]=99
    with pytest.raises(ValueError,match='identity'): module.capture_recovery_frame(raw,scope)


def test_native_course_padding_is_not_receipt_identity():
    from test_m1_reference_teacher import state
    s=state()
    s=replace(s,course_ids=torch.tensor([[0,-1,-1]]),course_valid=torch.tensor([[True,False,False]]),
        centers_top=s.centers_top.repeat(1,3,1),half_extents=s.half_extents.repeat(1,3,1),
        required_wheels=s.required_wheels.repeat(1,3,1))
    scope=probe().capture_recovery_scope(s,torch.tensor([0]),[[[0,0],[0,2]]],scope_ids=torch.tensor([0]))
    assert scope.course_ids.tolist()==[[0]]
    flat=replace(s,course_valid=torch.zeros(1,3,dtype=torch.bool))
    scope=probe().capture_recovery_scope(flat,torch.tensor([0]),[[]],scope_ids=torch.tensor([0]))
    assert scope.required.shape==(1,0,4)
    for bad in (replace(s,course_valid=torch.ones(1,3,dtype=torch.bool)),
            replace(s,course_ids=torch.tensor([[0,0,-1]]),course_valid=torch.tensor([[True,True,False]]))):
        with pytest.raises(ValueError,match='identity'):
            probe().capture_recovery_scope(bad,torch.tensor([0]),[[[0,0],[0,2]]],scope_ids=torch.tensor([0]))


@pytest.mark.parametrize('start_time,yaw',[(100.,0.),(10000.,.7)])
def test_native_global_clock_keeps_fifteen_real_intervals_after_100_seconds(start_time,yaw):
    import math
    from test_m1_reference_teacher import state
    from ame_baseline.m1_crossing_recovery import CrossingRecoveryTracker
    s=state(); s.centers_top[:,:,0]=-2.
    s.root_quat_w[0]=torch.tensor([math.cos(yaw/2),0.,0.,math.sin(yaw/2)])
    scope=probe().capture_recovery_scope(s,torch.tensor([0]),[[[0,0],[0,2]]],scope_ids=torch.tensor([0]))
    tracker=CrossingRecoveryTracker(scope)
    raw=copy.deepcopy(episode()['samples'][-1]['recovery_input'])
    for i in range(16):
        raw['frame']=[i]; raw['sim_time_s']=[start_time+i*.02]
        raw['root_state_w'][0][:2]=[(.1+i*.002)*math.cos(yaw),(.1+i*.002)*math.sin(yaw)]
        raw['root_state_w'][0][3:7]=s.root_quat_w[0].tolist()
        raw['root_state_w'][0][7:10]=[.3*math.cos(yaw),.3*math.sin(yaw),0.]
        result=tracker.update(probe().capture_recovery_frame(raw,scope))
        if i==14: assert result.success.tolist()==[False]
    assert result.success.tolist()==[True]
    assert result.interval_count.tolist()==[15]


def native_sample_runner():
    """Float32 simulator buffers, with the real NativeProbe sampling method."""
    from types import SimpleNamespace as NS
    from test_m1_reference_teacher import state
    from ame_baseline.m1_reference_teacher import TeacherConfig
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    module=probe(); s=state(); s.centers_top[:,:,0]=-2.
    s.root_pos_w[:,0]=1.; s.root_lin_vel_w[:,0]=.1
    s.wheel_pos_w[:,:,0]=1.; s.wheel_pos_w[:,:,2]=.0959
    native=object.__new__(module.NativeProbe)
    native.torch=torch; native.teacher_cfg=TeacherConfig()
    native.scope='first-obstacle'; native.diagnostic_wheel=None
    native.frames=torch.zeros(1,dtype=torch.long)
    native.episode=s.episode_id.clone(); native.attempt=native.frames.clone()
    native.support_acquired=torch.zeros(1,dtype=torch.bool)
    native.inner_failed=native.support_acquired.clone(); native.last_output=None
    native.wheels=native.contacts=list(range(4)); native.state=lambda:s
    root=torch.cat((s.root_pos_w,s.root_quat_w,s.root_lin_vel_w,s.root_ang_vel_w),1)
    native.robot=NS(joint_names=M1_ASSET_JOINT_NAMES,data=NS(
        root_state_w=root,body_pos_w=s.wheel_pos_w,body_quat_w=s.wheel_quat_w,
        joint_pos=s.default_joint_pos,joint_vel=torch.zeros(1,16),
        computed_torque=torch.zeros(1,16),applied_torque=torch.zeros(1,16)))
    native.sensor=NS(data=NS(net_forces_w=s.wheel_force_w))
    course=dict(ids=s.course_ids,centers_top=s.centers_top,half_extents=s.half_extents,
        valid=s.course_valid,landing_valid=torch.zeros(1,0,dtype=torch.bool),
        landing_centers_top=torch.empty(1,0,3),landing_half_extents=torch.empty(1,0,2))
    native.w=NS(_m1_current_course=lambda:course,
        _m1_strict_crossing=NS(recovered_for_course=lambda course:s.required_wheels))
    native.env=NS(step_dt=.02,sim=NS(current_time=0.),common_step_counter=0,
        _m1_collision_budget=NS(step=0,snapshot=dict(signal=torch.zeros(1))),
        termination_manager=NS(active_terms=['base_contact'],get_term=lambda name:torch.zeros(1,dtype=torch.bool),
            time_outs=torch.zeros(1,dtype=torch.bool),terminated=torch.zeros(1,dtype=torch.bool)))
    # Action publication is outside this sampling/clock boundary. Measurements,
    # sampling, raw input mapping and the recovery monitor all remain real.
    native.action_evidence=NS(row=lambda row,time:dict(action_matches_request=True,
        teacher_executable=True,applied_target_valid=True,
        action_default_joint_pos=s.default_joint_pos[row].tolist()))
    return module,native,s


@pytest.mark.parametrize('start_time',[0.,100.,10000.])
@pytest.mark.parametrize('steps,success',[(list(range(16)),True),(list(range(15)),False),
    (list(range(14))+[15],False)],ids=['fifteen-intervals','fifteen-observations','missing-frame'])
def test_native_sample_float32_control_dt_preserves_double_recovery_clock(start_time,steps,success):
    from ame_baseline.m1_crossing_recovery import CrossingRecoveryTracker
    module,native,s=native_sample_runner()
    before_dt=s.dt.clone()
    frozen=module.capture_recovery_scope(s,torch.tensor([0]),[[[0,0],[0,2]]],scope_ids=torch.tensor([0]))
    tracker=CrossingRecoveryTracker(frozen)
    for step in steps:
        native.frames[0]=step; s.control_step[0]=step
        native.env.sim.current_time=start_time+step*.02
        s.root_pos_w[0,0]=1.+step*.002
        native.robot.data.root_state_w[0,0]=s.root_pos_w[0,0]
        sample=native.sample(0)
        raw=module.recovery_input_from_sample(sample,frozen)
        result=tracker.update(module.capture_recovery_frame(raw,frozen))
        if step<15: assert not result.success.item()
    assert result.success.item()==success, result.reason
    if success:
        assert result.interval_count.item()==15
        assert result.elapsed_s.item()==pytest.approx(.3)
        assert result.net_forward_m.item()>=.01
    elif steps[-1]==15:
        assert result.interval_count.item()==0 and not result.stable.item()
    else:
        assert result.interval_count.item()==14
    assert sample['control_dt_s']==native.env.step_dt
    assert raw['dt_s']==[native.env.step_dt]
    assert s.dt.dtype==s.root_pos_w.dtype==s.wheel_force_w.dtype==torch.float32
    assert torch.equal(s.dt,before_dt)
    assert float(s.dt[0])!=native.env.step_dt


@pytest.mark.parametrize('kind,key,bad',[
    ('scope','env_id',[False]),('scope','episode_id',[.5]),('scope','scope_id',[True]),
    ('scope','course_ids',[[.5]+list(range(1,8))]),
    ('scope','required',[[[1,False,True,False]]+[[False]*4 for _ in range(7)]]),
    ('scope','forward_w',[[True,0.,0.]]),
    ('frame','env_id',[False]),('frame','episode_id',[.5]),('frame','scope_id',[True]),
    ('frame','frame',[20.5]),('frame','course_ids',[[.5]+list(range(1,8))]),
    ('frame','recovered',[[[1,False,True,False]]+[[False]*4 for _ in range(7)]]),
    ('frame','valid',['true']),('frame','collision',[0]),('frame','reset',[0]),('frame','ended',[0]),
])
def test_raw_recovery_identity_and_boolean_types_do_not_coerce(kind,key,bad):
    record=episode(); module=probe()
    if kind=='scope':
        raw=copy.deepcopy(record['recovery_scope']); raw[key]=bad
        with pytest.raises(ValueError): module.recovery_scope_from_json(raw)
    else:
        raw=copy.deepcopy(record['samples'][-1]['recovery_input']); raw[key]=bad
        with pytest.raises(ValueError): module.capture_recovery_frame(raw,module.recovery_scope_from_json(record['recovery_scope']))


def test_measurement_valid_string_cannot_become_true_in_replay():
    record=episode(); record['samples'][-1]['measurement_valid']='true'
    assert probe().verify_recovery_record(record)


@pytest.mark.parametrize('change',['whole_window','first_qualifying','one_obligation','wrong_identity'])
def test_window_receipts_cannot_be_removed_while_far_side_and_cached_success_remain(change):
    record=episode()
    assert verify_episode(record)['success']
    if change=='whole_window':
        for sample in record['samples'][4:-1]: sample['receipt']=[]
    elif change=='first_qualifying': record['samples'][4]['receipt']=[]
    elif change=='one_obligation': record['samples'][11]['receipt'].pop()
    else: record['samples'][11]['receipt'].append([999,0])
    # The final old receipts, raw recovery input and cached recovery result are
    # untouched, and verify_episode rebinds a real trace after the mutation.
    assert record['samples'][-1]['receipt']==record['required']
    checked=verify_episode(record)
    assert not checked['success'] and checked['errors']
    assert probe().verify_recovery_record(record)


@pytest.mark.parametrize('key,bad_pair',[
    ('receipt',[False,0]),('receipt',[0.0,0]),
    ('far_side_recovery',[False,0]),('far_side_recovery',[0.0,0]),
])
def test_same_value_noninteger_receipt_pair_cannot_hide_behind_a_valid_pair(key,bad_pair):
    record=episode(); sample=record['samples'][11]
    assert sample[key][0]==[0,0]
    sample[key].append(bad_pair)
    checked=verify_episode(record)
    assert not checked['success'] and checked['errors']
    assert probe().verify_recovery_record(record)
