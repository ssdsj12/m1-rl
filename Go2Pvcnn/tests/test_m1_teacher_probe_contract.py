"""CPU tests for the native probe's fail-closed evidence verifier."""
import copy
import importlib.util
import itertools
import json
from functools import lru_cache
from pathlib import Path

import pytest

VIDEOS = {}
TRACE_IDS = itertools.count()


@pytest.fixture(scope='module', autouse=True)
def real_video_files(tmp_path_factory):
    import imageio.v2 as imageio
    import numpy as np
    root=tmp_path_factory.mktemp('teacher_video')
    for count in (10,1000):
        path=root/f'{count}.mp4'
        with imageio.get_writer(str(path),fps=10) as writer:
            for i in range(count//5+1):
                rgb=np.zeros((32,32,3),dtype=np.uint8); rgb[:16,:,0]=100+i%100
                writer.append_data(rgb)
        VIDEOS[count]=path


@lru_cache(maxsize=1)
def probe():
    path = Path(__file__).parents[1] / 'scripts/probe_m1_teacher.py'
    assert path.exists(), 'native teacher evidence verifier is not implemented'
    spec = importlib.util.spec_from_file_location('teacher_probe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_trace(record,rows=None):
    """A real fixture artifact, rebound after intentional non-artifact mutations."""
    if 'trace' not in record:
        path=VIDEOS[10].parent/f'trace_{next(TRACE_IDS)}.jsonl'
    else: path=Path(record['trace']['path'])
    with path.open('w',encoding='utf-8') as stream:
        for sample in record['samples'] if rows is None else rows:
            stream.write(json.dumps(sample,separators=(',',':'))+'\n')
    record['trace']=dict(path=str(path),bytes=path.stat().st_size,sha256=probe().file_digest(path))


def verify_episode(record):
    # These tests exercise other contracts with matching real trace evidence.
    # Trace-tampering tests below call the verifier directly without rebinding.
    write_trace(record)
    return probe().verify_episode(record)


def episode(stage=3, seed=101, episode_id=0):
    required = [[i, w] for i in range(8) for w in ((0, 2) if i % 2 == 0 else (1, 3))]
    frames = []
    count = 1000 if stage == 0 else 10
    for f in range(1, count+1):
        from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
        from ame_baseline.m1_reference_teacher import TEACHER_DIAGNOSTIC_FIELDS
        frames.append(dict(env_id=0, episode_id=episode_id, attempt_id=1, frame=f,
            schema_version=3,teacher_scope='course',failure_locked=False,
            student_demonstration_usable=True,applied_target_valid=True,
            applied_targets=[0.]*16,applied_target_joint_names=list(M1_ASSET_JOINT_NAMES),
            applied_substeps=[dict(index=i,targets=[0.]*16,sim_time=(f-1)*.02+i*.005,
                write_seen=True,physics_seen=True) for i in range(4)],
            action_process_count=1,physics_decimation=4,action_matches_request=True,
            requested_processed_targets=[0.]*16,action_default_joint_pos=[0.]*16,
            action_target_dtype='float32',
            teacher_diagnostic={**{n:None for n in TEACHER_DIAGNOSTIC_FIELDS},
                'reference_valid':1,'diagnostic_only':0},last_applied_leg_target=[0.]*12,
            teacher_input_frame=f-1,teacher_input_episode_id=episode_id,teacher_input_sim_time=(f-1)*.02,
            teacher_action=[0.]*16,executed_action=[0.]*16,processed_targets=[0.]*16,
            action_joint_names=list(M1_ASSET_JOINT_NAMES),processed_target_joint_names=list(M1_ASSET_JOINT_NAMES),
            raw_joint_names=list(M1_ASSET_JOINT_NAMES),joints=[0.]*16,
            active_target=0,teacher_ages_after_decision=dict(age=0,body_age=-1,lift_age=-1),
            sim_time=f*.02, active_wheel=0, Fz=[50.]*4, wheel_bottom=[0.]*4,
            obstacle_top=[.10]*8, collision=False, support_lost=False,
            penetration=False, failure=False, teacher_valid=True,
            root=[f*.006,0.,.62,1.,0.,0.,0.,.3,0.,0.,0.,0.,0.],
            far_side_recovery=required if f == count and stage else [],
            receipt=required if f == count and stage else []))
    record=dict(schema_version=3,teacher_scope='course',stage=stage, seed=seed, env_id=0, episode_id=episode_id,
        raw_joint_names=list(M1_ASSET_JOINT_NAMES),
        required=required if stage else [], samples=frames, end='task_complete' if stage else 'flat_horizon',
        timeout=stage == 0, natural_done=stage == 0,
        initial_root=[0.,0.,.62], command_distance=count*.006,
        terminal=copy.deepcopy(frames[-1]),
        video=dict(path=str(VIDEOS[count]), sha256=probe().file_digest(VIDEOS[count]), bytes=VIDEOS[count].stat().st_size,
            isolated_robot=True, nonblack=True, frame_indices=list(range(0,count+1,5)),
            sim_times=[f*.02 for f in range(0,count+1,5)], first_frame=0, last_frame=count))
    write_trace(record)
    return record


def test_accepts_only_full_receipt_episode():
    assert verify_episode(episode())['success']


@pytest.mark.parametrize('mutation', [
    lambda e: e.update(end='phase_complete'),
    lambda e: e.update(terminal=None),
    lambda e: e.update(video=None),
    lambda e: e.update(timeout=True),
    lambda e: e.update(natural_done=True),
    lambda e: e['samples'][-1].update(receipt=[[0,0]]),
    lambda e: e['samples'][-1].update(far_side_recovery=[]),
    lambda e: e['samples'][2].update(collision=True),
    lambda e: e['samples'][2].update(support_lost=True),
    lambda e: e['samples'][2].update(penetration=True),
    lambda e: e['samples'][2].update(failure=True),
    lambda e: e['samples'][2].update(teacher_valid=False),
    lambda e: e['samples'][2].pop('attempt_id'),
    lambda e: e['samples'][2].update(frame=2),
    lambda e: e['samples'][2].update(sim_time=.061),
    lambda e: e['samples'][2].update(episode_id=999),
    lambda e: e['samples'][2].update(Fz=[]),
    lambda e: e['samples'][2].update(root=[]),
    lambda e: e['samples'][2].update(Fz=[float('nan')]*4),
    lambda e: e['video'].update(last_frame=5),
    lambda e: e['video'].update(isolated_robot=False),
    lambda e: e['video'].update(nonblack=False),
    lambda e: e.update(required=[]),
])
def test_rejects_false_success(mutation):
    e = episode(); mutation(e)
    assert not verify_episode(e)['success']


def test_flat_needs_actual_full_horizon_not_empty_required_vacuity():
    e = episode(0)
    assert verify_episode(e)['success']
    e['samples'] = e['samples'][:10]
    assert not verify_episode(e)['success']


def test_flat_stationary_full_horizon_is_not_locomotion_success():
    e=episode(0)
    for sample in e['samples']: sample['root'][0]=0.
    e['terminal']=copy.deepcopy(e['samples'][-1])
    assert not verify_episode(e)['success']


def test_missing_or_tampered_video_file_is_rejected():
    e=episode(); e['video']['path'] += '.missing'
    assert not verify_episode(e)['complete']
    e=episode(); e['video']['sha256']='f'*64
    assert not verify_episode(e)['complete']


def test_stage3_cannot_change_the_16_required_obligations():
    e = episode(); e['required'] = e['required'][:1]
    assert not verify_episode(e)['success']


def test_flat_uses_same_post_step_origin_as_curriculum_gate():
    e=episode(0)
    e['samples'][-1]['root'][0]=4.201
    e['terminal']=copy.deepcopy(e['samples'][-1])
    # Gate captures start_x on first actual sample (.006), not the reset pose.
    assert not verify_episode(e)['success']


def test_suite_requires_unique_20_per_seed_and_both_stages():
    module = probe()
    records = [episode(stage,seed,n) for stage in (0,3) for seed in range(101,106) for n in range(20)]
    assert module.verify_suite(records)['milestone_a'] == 'PASS'
    assert module.verify_suite(records[:-1])['milestone_a'] != 'PASS'
    assert module.verify_suite(records+[records[-1]])['milestone_a'] != 'PASS'
    for e in records[100:106]:
        e['samples'][2]['collision'] = True
        write_trace(e)
    assert module.verify_suite(records)['milestone_a'] != 'PASS'


def test_early_stop_never_uses_small_denominator():
    result = probe().verify_suite([episode()], diagnostic=True)
    assert result['milestone_a'] == 'FAILED_DIAGNOSTIC'


def test_candidate_and_python_are_explicit_and_bound(tmp_path):
    module = probe()
    with pytest.raises(ValueError): module.validate_paths(tmp_path, '/not/the/running/python', tmp_path/'out')


def test_collision_verifier_checks_final_wrapper_and_reset_locality():
    module = probe()
    rows = [dict(cost=[2.,2. if i%2==0 else 0.,0.,0.], total=[2.*(i+1),2.*(i//2+1),0.,0.],
        done=[i==9,False,False,False], failure=[0.]*4,
        raw=[-1.]*4, positive=[1.]*4, final=[-2.,-2. if i%2==0 else -1.,-1.,-1.],
        reset_total=[0. if i==9 else 2.*(i+1),2.*(i//2+1),0.,0.]) for i in range(10)]
    assert module.verify_collision_rows(rows)['passed']
    rows[-1]['failure'][0] = -20.
    assert not module.verify_collision_rows(rows)['passed']
    rows[-1]['failure'][0] = 0.; rows[-1]['final'][0] = -1.
    assert not module.verify_collision_rows(rows)['passed']


def test_native_step_rejects_hidden_extra_physics_advance():
    from types import SimpleNamespace
    import torch
    run=object.__new__(probe().NativeProbe)
    run.torch=torch; run.env=SimpleNamespace(sim=SimpleNamespace(current_time=0.),common_step_counter=0)
    run.tracker_calls=0; run.frames=torch.zeros(4,dtype=torch.long)
    run.inner_failed=torch.zeros(4,dtype=torch.bool)
    def extra_step(action):
        run.env.common_step_counter+=1; run.tracker_calls+=1
        run.env.sim.current_time+=.025
        return torch.zeros(4,1621),torch.zeros(4),torch.zeros(4),{}
    run.w=SimpleNamespace(step=extra_step)
    with pytest.raises(AssertionError): run.step(torch.zeros(4,16))


@pytest.mark.parametrize('center,quat,expected', [
    ((-.13,0.,.19),(1.,0.,0.,0.),False),  # round leading edge is separated
    ((0.,0.,.15),(1.,0.,0.,0.),True),
    ((0.,0.,.1959),(1.,0.,0.,0.),False),  # top tangency
    ((.1459,0.,.05),(1.,0.,0.,0.),False),  # side tangency
    ((.145,0.,.05),(1.,0.,0.,0.),True),
    ((0.,0.,.11),(.70710678,.70710678,0.,0.),True),
    ((-.13,0.,.19),(.70710678,.70710678,0.,0.),False),
])
def test_penetration_requires_one_actual_cylinder_point_inside_box(center,quat,expected):
    import torch
    module=probe()
    assert hasattr(module,'cylinder_penetration_witness'), 'positive same-point witness missing'
    pos=torch.tensor([[center]]); rotation=torch.tensor([[quat]])
    top=torch.tensor([[0.,0.,.1]]); half=torch.tensor([[.05,.09]])
    assert bool(module.cylinder_penetration_witness(pos,rotation,top,half)[0,0]) is expected


def test_round_edge_regression_and_unknown_are_not_penetration_certificates():
    import torch
    from ame_baseline.m1_reference_geometry import cylinder_bottom,cylinder_box_xy_witness,cylinder_clears_box
    rotation=torch.tensor([[[1.,0.,0.,0.]]])
    top=torch.tensor([[0.,0.,.1]]); half=torch.tensor([[.05,.09]])
    separated=torch.tensor([[[-.13,0.,.19]]])
    assert bool(cylinder_box_xy_witness(separated,rotation,top,half)[0,0])
    assert bool(cylinder_bottom(separated,rotation)[0,0]<.1)
    assert bool(cylinder_clears_box(separated,rotation,top,half)[0,0])
    assert not bool(probe().cylinder_penetration_witness(separated,rotation,top,half)[0,0])
    # A sub-sampling sliver has neither a separation certificate nor a sampled
    # penetration witness. The production strict/collision gates still apply.
    unknown=torch.tensor([[[.14585,0.,.1]]])
    assert not bool(cylinder_clears_box(unknown,rotation,top,half)[0,0])
    assert not bool(probe().cylinder_penetration_witness(unknown,rotation,top,half)[0,0])


@pytest.mark.parametrize('domain',['ame_baseline','extension','rsl_rl','tracking','go2_pvcnn'])
def test_candidate_binding_rejects_preloaded_foreign_domain(domain,tmp_path,monkeypatch):
    import sys
    from types import ModuleType
    module=probe()
    assert hasattr(module,'bind_candidate_imports'), 'candidate import binding missing'
    foreign=ModuleType(domain+'.foreign_probe')
    foreign.__file__=str(tmp_path/domain/'foreign_probe.py')
    monkeypatch.setitem(sys.modules,foreign.__name__,foreign)
    with pytest.raises(ValueError,match='outside candidate'):
        module.bind_candidate_imports(Path(__file__).parents[1])


def test_candidate_binding_precedes_hostile_pythonpath_and_records_loaded_file(tmp_path):
    import subprocess
    import sys
    import os
    module=probe()
    assert hasattr(module,'bind_candidate_imports'), 'candidate import binding missing'
    candidate=Path(__file__).parents[1]
    foreign=tmp_path/'ame_baseline'; foreign.mkdir()
    (foreign/'__init__.py').write_text("raise RuntimeError('foreign package executed')",encoding='utf-8')
    # A child starts without pytest's already-imported candidate modules.
    code='''import importlib.util,json,sys
from pathlib import Path
candidate=Path(sys.argv[1]); foreign=sys.argv[2]
sys.path.insert(0,foreign)
spec=importlib.util.spec_from_file_location('probe',candidate/'scripts/probe_m1_teacher.py')
probe=importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
probe.bind_candidate_imports(candidate)
import ame_baseline.m1_collision_budget
manifest=probe.loaded_candidate_modules(candidate)
item=manifest['ame_baseline.m1_collision_budget']
assert Path(item['path']) == (candidate/'ame_baseline/m1_collision_budget.py').resolve()
assert item['sha256'] == probe.file_digest(candidate/'ame_baseline/m1_collision_budget.py')
assert sys.path[:2] == [str(candidate.resolve()),str((candidate/'rsl_rl').resolve())]
'''
    result=subprocess.run([sys.executable,'-c',code,str(candidate),str(tmp_path)],
        env={**os.environ,'PYTHONPATH':str(tmp_path),'CUDA_VISIBLE_DEVICES':''},capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


def test_candidate_namespace_package_has_only_candidate_search_locations(tmp_path,monkeypatch):
    import sys
    from types import ModuleType
    candidate=Path(__file__).parents[1].resolve()
    namespace=ModuleType('go2_pvcnn.sensor')
    namespace.__path__=[str(candidate/'go2_pvcnn/sensor')]
    monkeypatch.setitem(sys.modules,namespace.__name__,namespace)
    record=probe().loaded_candidate_modules(candidate)[namespace.__name__]
    assert record['kind']=='namespace' and record['locations']==namespace.__path__
    namespace.__path__.append(str(tmp_path/'go2_pvcnn/sensor'))
    with pytest.raises(ValueError,match='outside candidate'):
        probe().loaded_candidate_modules(candidate)


def test_course_coordinates_use_authored_tile_not_two_meter_spawn_offset():
    import torch
    from types import SimpleNamespace
    module=probe()
    assert hasattr(module,'course_tile_coordinates'), 'authored tile-frame extraction missing'
    origins=torch.zeros(4,2,3); origins[3,1]=torch.tensor([48.,8.,0.])
    terrain=SimpleNamespace(terrain_origins=origins,
        terrain_levels=torch.tensor([3]),terrain_types=torch.tensor([1]),
        env_origins=torch.tensor([[46.,8.,0.]]))
    local=torch.tensor([[[-1.2+1.1*i,.215 if i%2==0 else -.215,.1] for i in range(8)]])
    world=local+origins[3,1]
    actual=module.course_tile_coordinates(terrain,{'centers_top':world})
    torch.testing.assert_close(actual,local,atol=3e-6,rtol=0)
    assert not torch.allclose(world-terrain.env_origins[:,None],local)
    torch.testing.assert_close(world,local+origins[3,1])  # geometry was not mutated


def test_probe_render_configuration_disables_temporal_reconstruction_only():
    from types import SimpleNamespace
    module=probe()
    assert hasattr(module,'configure_probe_rendering'), 'probe temporal rendering guard missing'
    cfg=SimpleNamespace(sim=SimpleNamespace(dt=.005,render_interval=4,
        physx=SimpleNamespace(solver_position_iteration_count=4,solver_velocity_iteration_count=2),
        render=SimpleNamespace(antialiasing_mode='DLSS',enable_dlssg=True,enable_shadows=True)),decimation=4)
    before=copy.deepcopy(cfg)
    result=module.configure_probe_rendering(cfg)
    assert result==dict(antialiasing_mode='Off',enable_dlssg=False,settle_render_frames=3)
    assert cfg.sim.render.antialiasing_mode=='Off' and cfg.sim.render.enable_dlssg is False
    assert cfg.sim.dt==before.sim.dt and cfg.decimation==before.decimation
    assert cfg.sim.render_interval==before.sim.render_interval
    assert vars(cfg.sim.physx)==vars(before.sim.physx)
    assert cfg.sim.render.enable_shadows==before.sim.render.enable_shadows


@pytest.mark.parametrize('change',[
    lambda s:s.pop('executed_action'),
    lambda s:s.update(processed_targets=[]),
    lambda s:s.update(executed_action=[float('nan')]*16),
    lambda s:s.update(teacher_input_frame=999),
    lambda s:s.update(teacher_input_episode_id=999),
    lambda s:s.update(teacher_input_sim_time=s['sim_time']),
    lambda s:s.update(action_joint_names=list(reversed(s['action_joint_names']))),
    lambda s:s.update(processed_target_joint_names=[]),
    lambda s:s.pop('active_target'),
])
def test_action_evidence_is_required_and_tied_to_precontrol_identity(change):
    e=episode(); change(e['samples'][2])
    assert not verify_episode(e)['success']


def test_action_evidence_freezes_real_processed_values_before_row_reset():
    import torch
    from types import SimpleNamespace
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    module=probe()
    assert hasattr(module,'ActionEvidence'), 'pre-reset executed action observer missing'
    term,asset,clock,evidence,calls=applied_fixture()
    state=SimpleNamespace(control_step=torch.tensor([37,91]),episode_id=torch.tensor([0,4]))
    output=SimpleNamespace(action=torch.full((2,16),.3),active_target=torch.tensor([9900,9901]))
    teacher=SimpleNamespace(_rows=[dict(age=2,body_age=3,lift_age=2),dict(age=9)])
    evidence.begin(state,output,teacher,10.)
    with pytest.raises(AssertionError,match='processed'):
        evidence.row(0,10.02)
    executed=output.action.clamp(-.2,.2)
    term.process_actions(executed)
    for i in range(4):
        term.apply_actions(); evidence.observe_write(); evidence.observe_physics(); clock.current_time+=.005
    terminal=evidence.row(0,10.02)
    # Natural reset can clear/reuse all live buffers; snapshots stay old-episode.
    term.processed_actions.zero_(); executed.zero_(); output.action.zero_()
    state.control_step.zero_(); state.episode_id.zero_(); teacher._rows[0]['lift_age']=99
    assert calls.count('process')==1
    assert terminal==evidence.row(0,10.02)
    assert terminal['teacher_input_frame']==37 and terminal['teacher_input_episode_id']==0
    assert terminal['executed_action']==pytest.approx([.2]*16)
    assert terminal['teacher_action']==pytest.approx([.3]*16)
    assert terminal['processed_targets']==pytest.approx([7.2]*16)
    assert terminal['action_joint_names']==list(M1_ASSET_JOINT_NAMES)
    assert terminal['processed_target_joint_names']==list(M1_ASSET_JOINT_NAMES)
    assert terminal['active_target']==9900
    assert terminal['teacher_ages_after_decision']==dict(age=2,body_age=3,lift_age=2)
    assert evidence.row(1,10.02)['teacher_input_episode_id']==4
    with pytest.raises(AssertionError,match='20ms'):
        evidence.row(0,10.04)
    with pytest.raises(AssertionError,match='once'):
        term.process_actions(executed)


@pytest.mark.parametrize('change',[
    lambda e:e['samples'][2].pop('raw_joint_names'),
    lambda e:e['samples'][2].update(raw_joint_names=list(reversed(e['raw_joint_names']))),
    lambda e:e['samples'][2].update(joints=[]),
    lambda e:e['samples'][2].update(joints=[float('nan')]*16),
    lambda e:e.pop('raw_joint_names'),
    lambda e:e.update(raw_joint_names=[e['raw_joint_names'][0]]*16),
])
def test_raw_joint_measurements_must_bind_unique_names_to_contract(change):
    e=episode(); change(e)
    assert not verify_episode(e)['success']


def test_raw_joint_snapshot_preserves_actual_order_and_old_buffers():
    import torch
    from types import SimpleNamespace
    module=probe()
    assert hasattr(module,'raw_joint_snapshot'), 'actual raw joint names snapshot missing'
    # Deliberately unlike action order; observer must not sort or guess it.
    names=['rear_knee','front_abad','wheel']
    robot=SimpleNamespace(joint_names=names,data=SimpleNamespace(joint_pos=torch.tensor([[1.,2.,3.]])))
    result=module.raw_joint_snapshot(robot,0)
    robot.joint_names.reverse(); robot.data.joint_pos.zero_()
    assert result==dict(raw_joint_names=['rear_knee','front_abad','wheel'],joints=[1.,2.,3.])


def applied_fixture(decimation=4):
    import torch
    from types import SimpleNamespace
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    names=list(reversed(M1_ASSET_JOINT_NAMES))
    asset=SimpleNamespace(joint_names=names,data=SimpleNamespace(
        joint_pos_target=torch.full((2,16),-3.),joint_vel_target=torch.full((2,16),-4.)))
    term=SimpleNamespace(_joint_names=M1_ASSET_JOINT_NAMES,_asset=asset,
        processed_actions=torch.zeros(2,16),raw_actions=torch.zeros(2,16))
    events=[]
    def process(action):
        events.append('process'); term.raw_actions.copy_(action); term.processed_actions.copy_(action+7.)
    def apply():
        events.append('apply')
        for col,name in enumerate(term._joint_names):
            buf=asset.data.joint_vel_target if 'FOOT' in name else asset.data.joint_pos_target
            buf[:,names.index(name)]=term.processed_actions[:,col]
    term.process_actions=process; term.apply_actions=apply
    clock=SimpleNamespace(current_time=10.)
    evidence=probe().ActionEvidence(term,decimation=decimation,sim_time=lambda:clock.current_time)
    return term,asset,clock,evidence,events


def test_apply_evidence_precedes_physics_and_survives_reset():
    import torch
    from types import SimpleNamespace
    term,asset,clock,evidence,events=applied_fixture()
    state=SimpleNamespace(control_step=torch.tensor([37,91]),episode_id=torch.tensor([0,4]),
        last_applied_leg_target=torch.full((2,12),-3.),applied_target_valid=torch.ones(2,dtype=torch.bool))
    output=SimpleNamespace(action=torch.full((2,16),.3),active_target=torch.tensor([9,10]))
    evidence.begin(state,output,SimpleNamespace(_rows=[{},{}]),10.)
    term.process_actions(output.action)
    for i in range(4):
        term.apply_actions(); evidence.observe_write(); evidence.observe_physics()
        clock.current_time+=.005
    old=evidence.row(0,10.02)
    asset.data.joint_pos_target.zero_(); term.processed_actions.zero_()
    state.episode_id.fill_(100)
    assert old==evidence.row(0,10.02)
    assert events==['process']+['apply']*4
    assert old['applied_targets']==pytest.approx([7.3]*16)
    assert old['teacher_input_episode_id']==0
    assert all(x['write_seen'] and x['physics_seen'] for x in old['applied_substeps'])


def test_wrapper_changed_target_rejects_label():
    e=episode(); e['samples'][2]['action_matches_request']=False
    assert not verify_episode(e)['success']
    assert not verify_episode(e)['student_demonstration_usable']


def test_locked_failure_counts_in_suite_denominator():
    e=episode(); e['end']='teacher_failure_locked'; e['samples'][-1]['failure_locked']=True
    e['terminal']=copy.deepcopy(e['samples'][-1])
    assert verify_episode(e)['complete']
    result=probe().verify_suite([e])
    assert result['counted_episodes']==1 and result['locked_failures']==1
    bound=probe().FailureDiagnosticBound()
    assert [bound.update(0,True) for _ in range(7)]==[False]*5+[True,True]


@pytest.mark.parametrize('scope',['flat-preparation','single-wheel','first-obstacle','transitions'])
def test_local_scope_cannot_claim_course_success(scope):
    e=episode(); e['teacher_scope']=scope
    assert not verify_episode(e)['success']
    with pytest.raises(ValueError,match='course'):
        probe().validate_scope(scope,acceptance=True,active_wheel=None)


def test_reset_bootstrap_reads_real_buffers_without_step_or_nonreset_mutation():
    import torch
    term,asset,clock,evidence,events=applied_fixture()
    term.process_actions(torch.full((2,16),.2)); term.apply_actions()
    before=asset.data.joint_pos_target[1].clone(); processed=term.processed_actions[1].clone()
    record=evidence.bootstrap_reset(torch.tensor([True,False]))
    assert clock.current_time==10. and events==['process','apply','process','apply']
    assert torch.equal(before,asset.data.joint_pos_target[1])
    assert torch.equal(processed,term.processed_actions[1])
    assert record['rows']==[0] and record['physics_steps']==0
    assert record['applied_targets'][0]==pytest.approx([7.]*16)
    target,valid=evidence.prior_leg_targets()
    assert target[0].tolist()==pytest.approx([7.]*12) and valid.tolist()==[True,True]


def test_missing_video_or_hash_fails_acceptance():
    e=episode(); e['video'].pop('sha256')
    assert not verify_episode(e)['success']


def test_old_schema_readable_without_new_field_fabrication():
    e=episode(); e.pop('schema_version')
    result=verify_episode(e)
    assert not result['success'] and 'legacy schema lacks actual apply evidence' in result['errors']


def test_failed_early_attempt_stays_in_fixed_200_episode_denominator():
    records=[episode(stage,seed,n) for stage in (0,3) for seed in range(101,106) for n in range(20)]
    failed=records[-1]; failed['end']='teacher_failure_locked'
    failed['samples'][-1]['failure_locked']=True
    failed['samples'][2]['last_applied_leg_target']=[10.]*12
    failed['terminal']=copy.deepcopy(failed['samples'][-1])
    write_trace(failed)
    result=probe().verify_suite(records)
    assert result['complete_full_denominator'] is True
    assert result['counted_episodes']==200 and result['locked_failures']==1
    assert result['stage3_success']==99
    assert result['milestone_a']=='FAIL'  # corrupted evidence never passes acceptance


@pytest.mark.parametrize('mutation',[
    lambda s:s.pop('applied_substeps'),
    lambda s:s['applied_substeps'].pop(),
    lambda s:s['applied_substeps'][2].update(physics_seen=False),
    lambda s:s['applied_substeps'][2].update(write_seen=False),
    lambda s:s['applied_substeps'][2].update(targets=[1.]*16),
    lambda s:s['applied_substeps'][2].update(sim_time=s['sim_time']),
    lambda s:s.update(action_process_count=2),
    lambda s:s.update(applied_targets=[1.]*16),
    lambda s:s.update(last_applied_leg_target=[1.]*12),
    lambda s:s.update(teacher_diagnostic={}),
])
def test_actual_apply_contract_rejects_missing_or_inconsistent_substep_evidence(mutation):
    e=episode(); mutation(e['samples'][2])
    assert not verify_episode(e)['success']


def test_bootstrap_preserves_old_terminal_and_resets_multiple_rows():
    import torch
    from types import SimpleNamespace
    term,asset,clock,evidence,events=applied_fixture()
    state=SimpleNamespace(control_step=torch.tensor([2,8]),episode_id=torch.tensor([3,4]))
    output=SimpleNamespace(action=torch.full((2,16),.2),active_target=torch.tensor([1,2]))
    evidence.begin(state,output,SimpleNamespace(_rows=[{},{}]),10.)
    term.process_actions(output.action)
    for i in range(4):
        term.apply_actions(); evidence.observe_write(); evidence.observe_physics(); clock.current_time+=.005
    terminal=evidence.row(0,10.02)
    record=evidence.bootstrap_reset(torch.tensor([True,True]))
    assert record['rows']==[0,1] and record['physics_steps']==0
    assert evidence.row(0,10.02)==terminal
    assert terminal['applied_targets']==pytest.approx([7.2]*16)
    assert evidence.read_targets()[0].tolist()==pytest.approx([7.]*16)
    assert events.count('process')==2 and events.count('apply')==5


def test_bootstrap_aborts_if_actual_buffer_differs_from_processed_request():
    import torch
    term,asset,clock,evidence,events=applied_fixture()
    term.apply_actions=lambda:asset.data.joint_pos_target.zero_()
    with pytest.raises(RuntimeError,match='readback mismatch'):
        evidence.bootstrap_reset(torch.tensor([True,True]))


def test_bootstrap_aborts_if_nonreset_processed_or_actual_buffers_change():
    import torch
    term,asset,clock,evidence,events=applied_fixture()
    term.process_actions(torch.full((2,16),.2)); term.apply_actions()
    term.raw_actions[1]=1.  # actual previous request/processed evidence inconsistent
    with pytest.raises(RuntimeError,match='non-reset processed'):
        evidence.bootstrap_reset(torch.tensor([True,False]))


def test_diagnostic_json_has_named_fields_and_preserves_missing_as_null():
    from ame_baseline.m1_reference_teacher import TEACHER_DIAGNOSTIC_FIELDS,TEACHER_DIAGNOSTIC_INTEGER_FIELDS
    values=[float('nan')]*len(TEACHER_DIAGNOSTIC_FIELDS)
    values[TEACHER_DIAGNOSTIC_FIELDS.index('reference_valid')]=1.
    result=probe().diagnostic_json(values)
    assert result['reference_valid']==1 and type(result['reference_valid']) is int
    assert result['com_x'] is None and set(result)==set(TEACHER_DIAGNOSTIC_FIELDS)


def test_apply_target_change_between_write_and_physics_is_rejected():
    import torch
    from types import SimpleNamespace
    term,asset,clock,evidence,events=applied_fixture()
    state=SimpleNamespace(control_step=torch.tensor([0,0]),episode_id=torch.tensor([0,0]))
    output=SimpleNamespace(action=torch.zeros(2,16),active_target=torch.tensor([0,0]))
    evidence.begin(state,output,SimpleNamespace(_rows=[{},{}]),10.)
    term.process_actions(output.action); term.apply_actions(); evidence.observe_write()
    asset.data.joint_pos_target.fill_(99.)
    with pytest.raises(AssertionError,match='before physics'):
        evidence.observe_physics()


def test_scope_schedule_preserves_original_stage_and_uses_all_preparation_wheels():
    module=probe()
    assert module.teacher_schedule('flat-preparation',None)==[(0,0),(0,1),(0,2),(0,3)]
    assert module.teacher_schedule('single-wheel',2)==[(0,2)]
    assert module.teacher_schedule('first-obstacle',None)==[(3,None)]
    assert module.teacher_schedule('transitions',None)==[(3,None)]
    assert module.teacher_schedule('course',None)==[(0,None),(3,None)]


@pytest.mark.parametrize('mutation',[
    lambda s:s['teacher_diagnostic'].update(reference_valid=0),
    lambda s:s['teacher_diagnostic'].update(diagnostic_only=1),
    lambda s:s.update(teacher_scope='single-wheel'),
])
def test_label_must_agree_with_named_reference_valid_and_scope(mutation):
    e=episode(); mutation(e['samples'][2])
    assert not verify_episode(e)['success']


def test_empty_failed_attempt_counts_without_becoming_complete_evidence():
    e=episode(); e['samples']=[]; e['terminal']=None
    result=probe().verify_suite([e])
    assert result['counted_episodes']==1 and result['complete_episodes']==0
    assert result['milestone_a']=='FAIL'


def test_bootstrap_preserves_bit_pattern_of_nonreset_actual_buffers():
    import torch
    term,asset,clock,evidence,events=applied_fixture()
    term.process_actions(torch.full((2,16),.2)); term.apply_actions()
    # Irrelevant velocity buffer of a leg must also be bit-identical. IEEE
    # signed zeros compare equal numerically but are not an unchanged buffer.
    index=asset.joint_names.index('FBL_ABAD_JOINT')
    asset.data.joint_vel_target[1,index]=-0.
    previous=term.apply_actions
    def changed():
        previous(); asset.data.joint_vel_target[1,index]=0.
    term.apply_actions=changed
    with pytest.raises(RuntimeError,match='non-reset actual target buffers'):
        evidence.bootstrap_reset(torch.tensor([True,False]))


@pytest.mark.parametrize('mutate',[
    lambda e:e.pop('trace'),
    lambda e:e.update(trace=None),
    lambda e:e['trace'].pop('sha256'),
    lambda e:e['trace'].update(sha256='f'*64),
    lambda e:e['trace'].update(bytes=1),
    lambda e:e['trace'].update(path=e['trace']['path']+'.missing'),
])
def test_missing_or_tampered_trace_artifact_rejects_success_and_bc(mutate):
    e=episode(); mutate(e)
    result=probe().verify_episode(e)
    assert not result['success'] and not result['student_demonstration_usable']


def test_trace_content_tamper_is_rejected_without_trusting_metadata():
    e=episode(); path=Path(e['trace']['path'])
    path.write_text(path.read_text(encoding='utf-8').replace('"Fz":[50.0','"Fz":[51.0',1),encoding='utf-8')
    result=probe().verify_episode(e)
    assert not result['success'] and 'trace artifact verification failed' in result['errors']


@pytest.mark.parametrize('mutate',[
    lambda rows:rows[2]['teacher_diagnostic'].update(ik_residual_m_0=.123),
    lambda rows:rows[2]['teacher_action'].__setitem__(0,.01),
    lambda rows:rows.pop(),
    lambda rows:rows.append(copy.deepcopy(rows[-1])),
    lambda rows:rows[2].pop('teacher_diagnostic'),
])
def test_trace_rows_must_match_samples_even_after_valid_hash_refresh(mutate):
    e=episode(); rows=copy.deepcopy(e['samples']); mutate(rows); write_trace(e,rows)
    result=probe().verify_episode(e)
    assert not result['success'] and 'trace records differ from samples' in result['errors']


def test_invalid_json_trace_is_rejected():
    e=episode(); path=Path(e['trace']['path']); path.write_text('{not json}\n',encoding='utf-8')
    e['trace'].update(bytes=path.stat().st_size,sha256=probe().file_digest(path))
    result=probe().verify_episode(e)
    assert not result['success'] and 'trace artifact unreadable' in result['errors']


def test_corresponding_nan_diagnostic_is_preserved_and_compared_without_dummy_values():
    e=episode(); e['samples'][2]['teacher_diagnostic']['ik_residual_m_0']=float('nan')
    write_trace(e)
    assert probe().verify_episode(e)['success']
    rows=copy.deepcopy(e['samples']); rows[2]['teacher_diagnostic']['ik_residual_m_0']=0.
    write_trace(e,rows)
    result=probe().verify_episode(e)
    assert not result['success'] and 'trace records differ from samples' in result['errors']


@pytest.mark.parametrize('mutate',[
    lambda s:s['teacher_action'].__setitem__(1,.01),
    lambda s:s['executed_action'].__setitem__(1,.01),
    lambda s:s['requested_processed_targets'].__setitem__(1,.01),
    lambda s:(s['teacher_action'].__setitem__(1,.01),s['executed_action'].__setitem__(1,.01)),
    lambda s:s.pop('requested_processed_targets'),
    lambda s:s.pop('action_default_joint_pos'),
    lambda s:s.pop('action_target_dtype'),
])
def test_actual_request_execution_and_decoded_target_content_overrule_true_flag(mutate):
    e=episode(); mutate(e['samples'][2]); write_trace(e)
    assert e['samples'][2]['action_matches_request'] is True
    result=probe().verify_episode(e)
    assert not result['success'] and not result['student_demonstration_usable']


@pytest.mark.parametrize('dtype',['float32','float64'])
def test_request_target_roundtrip_uses_recorded_real_dtype_without_tolerance(dtype):
    import torch
    from ame_baseline.m1_ame_contract import m1_action_targets
    e=episode(); sample=e['samples'][2]
    sample['action_target_dtype']=dtype
    sample['teacher_action'][1]=.01; sample['teacher_action'][3]=.3
    action=torch.tensor([sample['teacher_action']],dtype=getattr(torch,dtype))
    defaults=torch.tensor([sample['action_default_joint_pos']],dtype=getattr(torch,dtype))
    sample['teacher_action']=action[0].tolist(); sample['executed_action']=action[0].tolist()
    targets=m1_action_targets(action,defaults)[0].tolist()
    sample['requested_processed_targets']=targets.copy(); sample['processed_targets']=targets.copy()
    sample['applied_targets']=targets.copy()
    for sub in sample['applied_substeps']: sub['targets']=targets.copy()
    write_trace(e)
    assert probe().verify_episode(e)['success']
    # Smaller than physical slew tolerance: still a provenance contradiction.
    sample['requested_processed_targets'][1]+=1e-10; write_trace(e)
    result=probe().verify_episode(e)
    assert not result['success']


def diagnostic_runner(tmp_path,monkeypatch,scenario):
    """Run the real scheduling/trace/video/result path with CPU command buffers.

    Only simulator measurement/step and teacher output are fixtures; this does
    not claim physical geometry. No UI/app, placement or native process exists.
    """
    import torch
    import numpy as np
    from types import SimpleNamespace as NS
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    import ame_baseline.m1_reference_teacher as teacher_module
    module=probe(); run=object.__new__(module.NativeProbe)
    run.torch=torch; run.output=tmp_path; run.teacher_cfg=teacher_module.TeacherConfig()
    run.frames=torch.zeros(4,dtype=torch.long); run.episode=run.frames.clone(); run.attempt=run.frames.clone()
    run.support_acquired=torch.zeros(4,dtype=torch.bool); run.inner_failed=run.support_acquired.clone()
    run.recording={}; run.terminal={}; run.raw_joint_names=tuple(M1_ASSET_JOINT_NAMES)
    run.wheels=list(range(4)); run.video_validated=True; run.started=[]; run.control_calls=0
    run.env=NS(device='cpu',sim=NS(current_time=0.),seed=lambda seed:None,
        command_manager=NS(get_command=lambda name:torch.zeros(4,3)))
    asset=NS(joint_names=M1_ASSET_JOINT_NAMES,data=NS(root_pos_w=torch.zeros(4,3),
        body_pos_w=torch.zeros(4,4,3),joint_pos_target=torch.zeros(4,16),joint_vel_target=torch.zeros(4,16)))
    run.robot=asset
    term=NS(_joint_names=M1_ASSET_JOINT_NAMES,_asset=asset,raw_actions=torch.zeros(4,16),processed_actions=torch.zeros(4,16))
    def process(action): term.raw_actions.copy_(action); term.processed_actions.copy_(action)
    def apply():
        asset.data.joint_pos_target.copy_(term.processed_actions)
        asset.data.joint_vel_target.copy_(term.processed_actions)
    term.process_actions=process; term.apply_actions=apply
    run.action_evidence=module.ActionEvidence(term,sim_time=lambda:run.env.sim.current_time)
    run.bind_reset_identity=lambda rows:None
    def stage(value): run.stage=value; run.started.append((value,run.diagnostic_wheel))
    run.set_stage=stage
    required=[[i,w] for i in range(8) for w in ((0,2) if i%2==0 else (1,3))]
    def state(reset=None):
        mask=torch.zeros(4,8,4,dtype=torch.bool)
        if run.stage==3:
            for target,wheel in required: mask[:,target,wheel]=True
        return NS(course_ids=torch.arange(8).expand(4,-1),required_wheels=mask,
            control_step=run.frames.clone(),episode_id=run.episode.clone(),
            last_applied_leg_target=torch.zeros(4,12),default_joint_pos=torch.zeros(4,16))
    run.state=state
    class FixtureTeacher:
        def __init__(self,cfg): self._rows=[{} for _ in range(4)]
        def decide(self,state,wheel):
            prepared=(scenario in ('prepared','bad-evidence') or (wheel is not None and wheel>0)
                or scenario=='transient' and int(state.control_step[0])>=1)
            self._rows=[dict(prepared=prepared,stable=0) for _ in range(4)]
            data=torch.full((4,len(teacher_module.TEACHER_DIAGNOSTIC_FIELDS)),float('nan'))
            for field,value in (('reference_valid',0 if scenario=='transient' and not prepared else 1),
                    ('diagnostic_only',int(wheel is not None))):
                data[:,teacher_module.TEACHER_DIAGNOSTIC_FIELDS.index(field)]=value
            locked=torch.zeros(4,dtype=torch.bool)
            if scenario in ('locked','acceptance-failure') and (wheel==0 or wheel is None): locked[0]=True
            if scenario=='locked-last' and wheel==0: locked[3]=True
            return NS(action=torch.zeros(4,16),active_target=torch.full((4,),-1,dtype=torch.long),
                active_wheel=torch.full((4,),wheel or 0,dtype=torch.long),diagnostic=data,
                failure_locked=locked,valid=torch.zeros(4,dtype=torch.bool))
        def diagnostic_step(self,state,*,active_wheel,lift): return self.decide(state,active_wheel)
        def step(self,state): return self.decide(state,None)
    monkeypatch.setattr(teacher_module,'ReferenceTeacher',FixtureTeacher)
    image=np.zeros((32,32,3),dtype=np.uint8); image[:16,:,0]=128
    run.render_row=lambda row:image
    def step(action):
        run.control_calls+=1; run.frames+=1; term.process_actions(action)
        for _ in range(4):
            term.apply_actions(); run.action_evidence.observe_write(); run.action_evidence.observe_physics()
            run.env.sim.current_time+=.005
        run.action_evidence.observing=False
        done=torch.full((4,),scenario=='acceptance-failure',dtype=torch.bool)
        run.terminal={row:sample(row) for row in range(4)} if bool(done.any()) else {}
        return None,None,done,None
    run.step=step
    def sample(row):
        action=run.action_evidence.row(row,run.env.sim.current_time)
        if scenario=='bad-evidence' and row==3: action['action_target_dtype']='unsupported'
        return dict(schema_version=3,teacher_scope=run.scope,env_id=row,episode_id=int(run.episode[row]),
            attempt_id=0,frame=int(run.frames[row]),sim_time=run.env.sim.current_time,
            active_wheel=run.diagnostic_wheel or 0,phase=1,teacher_reason=5 if row==0 else 0,
            teacher_valid=False,student_demonstration_usable=False,
            failure_locked=bool(run.last_output.failure_locked[row]),Fz=[50.]*4,
            wheel_position=[[0.,0.,0.]]*4,wheel_bottom=[0.]*4,obstacle_top=[.1]*8,
            collision=False,support_lost=False,penetration=False,failure=False,timeout=False,
            receipt=[],far_side_recovery=[],root=[0.,0.,.62,1.,0.,0.,0.]+[0.]*6,
            raw_joint_names=list(M1_ASSET_JOINT_NAMES),joints=[0.]*16,**action)
    run.sample=sample
    run.reset_row=lambda row:None
    return run


def test_flat_preparation_critical_failure_drains_batch_and_never_starts_next_wheel(tmp_path,monkeypatch):
    run=diagnostic_runner(tmp_path,monkeypatch,'locked')
    run.teacher(acceptance=False,diagnostic_steps=20,scope='flat-preparation')
    assert run.started==[(0,0)]
    assert run.control_calls==6  # locking frame plus at most5 more control steps
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['counted_episodes']==4 and result['diagnostic_stopped'] is True
    assert result['diagnostic_stop']['env_id']==0
    assert [x['wheel'] for x in result['not_run']]==[1,2,3]
    records=[json.loads(path.read_text()) for path in tmp_path.glob('stage*.json')]
    assert len(records)==4
    assert [r['end'] for r in records if r['env_id']==0]==['teacher_failure_locked']
    for record in records:
        assert Path(record['video']['path']).is_file() and Path(record['trace']['path']).is_file()
        assert len(record['samples'])==6 and not record['student_demonstration_usable']
        if record['env_id']!=0:
            assert record['end']=='diagnostic_interrupted'
            assert not any(s['failure_locked'] or s['failure'] for s in record['samples'])
            assert record['terminal']['diagnostic_interruption']['env_id']==0


def test_flat_preparation_unmet_bound_stops_without_claiming_physical_failure(tmp_path,monkeypatch):
    run=diagnostic_runner(tmp_path,monkeypatch,'unmet')
    run.teacher(acceptance=False,diagnostic_steps=2,scope='flat-preparation')
    assert run.started==[(0,0)] and run.control_calls==2
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['diagnostic_stop']['reason']=='diagnostic_goal_unmet'
    assert result['counted_episodes']==4 and len(result['not_run'])==3
    for path in tmp_path.glob('stage*.json'):
        record=json.loads(path.read_text())
        assert not any(s['failure'] or s['failure_locked'] for s in record['samples'])


def test_acceptance_gate_does_not_discard_fixed_200_failed_attempts(tmp_path,monkeypatch):
    run=diagnostic_runner(tmp_path,monkeypatch,'acceptance-failure')
    run.teacher(acceptance=True,diagnostic_steps=1,scope='course')
    result=json.loads((tmp_path/'result.json').read_text())
    assert run.started==[(0,None)]*5+[(3,None)]*5
    assert result['counted_episodes']==200 and result['complete_full_denominator'] is True
    assert result['milestone_a']=='FAIL'
    assert result.get('diagnostic_stopped',False) is False


def test_diagnostic_valid_false_successful_preparation_does_not_stop_next_wheel(tmp_path,monkeypatch):
    run=diagnostic_runner(tmp_path,monkeypatch,'prepared')
    run.teacher(acceptance=False,diagnostic_steps=3,scope='flat-preparation')
    assert run.started==[(0,0),(0,1),(0,2),(0,3)]
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['counted_episodes']==16 and not result.get('diagnostic_stopped',False)


def test_unlocked_finite_ik_refusal_does_not_trigger_batch_stop(tmp_path,monkeypatch):
    run=diagnostic_runner(tmp_path,monkeypatch,'transient')
    run.teacher(acceptance=False,diagnostic_steps=3,scope='flat-preparation')
    assert run.started==[(0,0),(0,1),(0,2),(0,3)] and run.control_calls==5
    result=json.loads((tmp_path/'result.json').read_text())
    assert not result['diagnostic_stopped'] and result['counted_episodes']==16


def test_last_env_failure_is_latched_before_peer_finishes(tmp_path,monkeypatch):
    run=diagnostic_runner(tmp_path,monkeypatch,'locked-last')
    run.teacher(acceptance=False,diagnostic_steps=20,scope='flat-preparation')
    assert run.started==[(0,0)] and run.control_calls==6
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['diagnostic_stop']['env_id']==3 and result['counted_episodes']==4
    for path in tmp_path.glob('stage*.json'):
        record=json.loads(path.read_text())
        if record['env_id']!=3:
            assert record['end']=='diagnostic_interrupted' and record['diagnostic_interruption']['env_id']==3


def test_late_evidence_failure_relabels_ended_peers_without_rewriting_trace(tmp_path,monkeypatch):
    run=diagnostic_runner(tmp_path,monkeypatch,'bad-evidence')
    run.teacher(acceptance=False,diagnostic_steps=3,scope='flat-preparation')
    assert run.started==[(0,0)] and run.control_calls==1
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['diagnostic_stop']['reason']=='evidence_invalid' and result['diagnostic_stop']['env_id']==3
    for path in tmp_path.glob('stage*.json'):
        record=json.loads(path.read_text())
        assert probe().file_digest(record['trace']['path'])==record['trace']['sha256']
        assert not record['student_demonstration_usable']
        if record['env_id']==3:
            assert record['end']=='diagnostic_evidence_failure'
        else:
            assert record['end']=='diagnostic_interrupted' and not record['verification']['errors']


@pytest.mark.parametrize('flags,reason,physical',[
    ({'failure_locked':True},'failure_locked',False),
    ({'collision':True},'collision',True),
    ({'failure_locked':True,'collision':True},'failure_locked',True),
    ({'action_matches_request':False},'action_evidence_invalid',False),
    ({'teacher_valid':False,'teacher_diagnostic':{'reference_valid':0}},None,False),
])
def test_diagnostic_gate_failure_classification_preserves_observed_physics(flags,reason,physical):
    gate=probe().DiagnosticBatchGate(False)
    gate.observe_sample(dict(env_id=2,episode_id=0,frame=7,**flags),7)
    if reason is None: assert gate.failure is None
    else: assert gate.failure['reason']==reason and gate.failure['physical_failure'] is physical
