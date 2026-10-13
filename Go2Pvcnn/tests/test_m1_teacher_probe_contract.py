"""CPU tests for the native probe's fail-closed evidence verifier."""
import copy
import importlib.util
from functools import lru_cache
from pathlib import Path

import pytest

VIDEOS = {}


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


def episode(stage=3, seed=101, episode_id=0):
    required = [[i, w] for i in range(8) for w in ((0, 2) if i % 2 == 0 else (1, 3))]
    frames = []
    count = 1000 if stage == 0 else 10
    for f in range(1, count+1):
        frames.append(dict(env_id=0, episode_id=episode_id, attempt_id=1, frame=f,
            sim_time=f*.02, active_wheel=0, Fz=[50.]*4, wheel_bottom=[0.]*4,
            obstacle_top=[.10]*8, collision=False, support_lost=False,
            penetration=False, failure=False, teacher_valid=True,
            root=[f*.006,0.,.62,1.,0.,0.,0.,.3,0.,0.,0.,0.,0.],
            far_side_recovery=required if f == count and stage else [],
            receipt=required if f == count and stage else []))
    return dict(stage=stage, seed=seed, env_id=0, episode_id=episode_id,
        required=required if stage else [], samples=frames, end='task_complete' if stage else 'flat_horizon',
        timeout=stage == 0, natural_done=stage == 0,
        initial_root=[0.,0.,.62], command_distance=count*.006,
        terminal=copy.deepcopy(frames[-1]),
        video=dict(path=str(VIDEOS[count]), sha256=probe().file_digest(VIDEOS[count]), bytes=VIDEOS[count].stat().st_size,
            isolated_robot=True, nonblack=True, frame_indices=list(range(0,count+1,5)),
            sim_times=[f*.02 for f in range(0,count+1,5)], first_frame=0, last_frame=count))


def test_accepts_only_full_receipt_episode():
    assert probe().verify_episode(episode())['success']


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
    assert not probe().verify_episode(e)['success']


def test_flat_needs_actual_full_horizon_not_empty_required_vacuity():
    e = episode(0)
    assert probe().verify_episode(e)['success']
    e['samples'] = e['samples'][:10]
    assert not probe().verify_episode(e)['success']


def test_flat_stationary_full_horizon_is_not_locomotion_success():
    e=episode(0)
    for sample in e['samples']: sample['root'][0]=0.
    e['terminal']=copy.deepcopy(e['samples'][-1])
    assert not probe().verify_episode(e)['success']


def test_missing_or_tampered_video_file_is_rejected():
    e=episode(); e['video']['path'] += '.missing'
    assert not probe().verify_episode(e)['complete']
    e=episode(); e['video']['sha256']='f'*64
    assert not probe().verify_episode(e)['complete']


def test_stage3_cannot_change_the_16_required_obligations():
    e = episode(); e['required'] = e['required'][:1]
    assert not probe().verify_episode(e)['success']


def test_flat_uses_same_post_step_origin_as_curriculum_gate():
    e=episode(0)
    e['samples'][-1]['root'][0]=4.201
    e['terminal']=copy.deepcopy(e['samples'][-1])
    # Gate captures start_x on first actual sample (.006), not the reset pose.
    assert not probe().verify_episode(e)['success']


def test_suite_requires_unique_20_per_seed_and_both_stages():
    module = probe()
    records = [episode(stage,seed,n) for stage in (0,3) for seed in range(101,106) for n in range(20)]
    assert module.verify_suite(records)['milestone_a'] == 'PASS'
    assert module.verify_suite(records[:-1])['milestone_a'] != 'PASS'
    assert module.verify_suite(records+[records[-1]])['milestone_a'] != 'PASS'
    for e in records[100:106]: e['samples'][2]['collision'] = True
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
