"""Candidate-only native teacher evidence. No training or production writes.

The pure verifier imports no simulator. Native entry imports AppLauncher before
Isaac/pxr/omni. A diagnostic run can never report milestone A PASS.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
from functools import lru_cache


SAMPLE_KEYS = {'env_id','episode_id','attempt_id','frame','sim_time','active_wheel',
    'Fz','wheel_bottom','obstacle_top','collision','support_lost','penetration',
    'failure','teacher_valid','far_side_recovery','receipt','root'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=256)
def inspect_video(path, size, mtime_ns):
    """Decode the actual artifact once per immutable file identity."""
    import imageio.v2 as imageio
    reader=imageio.get_reader(path)
    try:
        count=reader.count_frames()
        first=reader.get_data(0); last=reader.get_data(count-1)
        return dict(sha256=file_digest(path),frames=count,
            nonblack=bool(first.std()>2 and first.max()>30 and last.std()>2 and last.max()>30))
    finally: reader.close()


def verify_episode(record):
    """Evidence validation and success are distinct; failures still count episodes."""
    errors = []
    samples = record.get('samples', [])
    stage = record.get('stage')
    if not samples or stage not in (0,3):
        return dict(complete=False, success=False, errors=['missing trajectory or stage'])
    start_time = samples[0].get('sim_time', 0.)-.02
    for index, sample in enumerate(samples, 1):
        if not SAMPLE_KEYS <= sample.keys():
            errors.append('missing sample fields'); continue
        if (sample['env_id'],sample['episode_id']) != (record['env_id'],record['episode_id']):
            errors.append('episode identity changed')
        if sample['frame'] != index or not math.isclose(sample['sim_time']-start_time, index*.02, abs_tol=1e-6):
            errors.append('not a contiguous 50Hz trajectory')
        if len(sample['Fz'])!=4 or len(sample['wheel_bottom'])!=4 or len(sample['root'])!=13:
            errors.append('missing physical measurement dimensions')
        if not all(math.isfinite(x) for key in ('Fz','wheel_bottom','obstacle_top','root') for x in sample[key]):
            errors.append('nonfinite physical measurement')
    terminal = record.get('terminal')
    if terminal != samples[-1]: errors.append('missing or mismatched pre-reset terminal snapshot')
    video = record.get('video') or {}
    indices = video.get('frame_indices', [])
    times = video.get('sim_times', [])
    if (not video.get('path') or len(video.get('sha256','')) != 64 or video.get('bytes',0) <= 0
            or not video.get('isolated_robot') or not video.get('nonblack')
            or video.get('first_frame') != 0 or video.get('last_frame') != len(samples)
            or not indices or indices[0] != 0 or indices[-1] != len(samples)
            or len(indices) != len(times)
            or any(b <= a or b-a > 5 for a,b in zip(indices,indices[1:]))
            or any(not math.isclose(t-start_time, f*.02, abs_tol=1e-6) for f,t in zip(indices,times))):
        errors.append('missing complete isolated video and time mapping')
    try:
        path=Path(video['path']); stat=path.stat()
        artifact=inspect_video(str(path),stat.st_size,stat.st_mtime_ns)
        if (stat.st_size != video['bytes'] or artifact['sha256'] != video['sha256']
                or artifact['frames'] != len(indices) or not artifact['nonblack']):
            errors.append('video artifact verification failed')
    except (KeyError,OSError,ValueError,RuntimeError,IndexError):
        errors.append('video artifact unreadable')
    complete = not errors and record.get('end') in ('task_complete','flat_horizon','natural_done')
    unsafe = any(s.get(k,True) for s in samples for k in ('collision','support_lost','penetration','failure'))
    invalid = any(not s.get('teacher_valid',False) for s in samples)
    required = {tuple(x) for x in record.get('required',[])}
    receipt = {tuple(x) for x in samples[-1].get('receipt',[])}
    far = {tuple(x) for x in samples[-1].get('far_side_recovery',[])}
    if stage == 3:
        obligation_valid = len(required) == 16 and len({x[0] for x in required}) == 8
        success = (complete and obligation_valid and required <= receipt and required <= far
            and record.get('end') == 'task_complete' and not record.get('natural_done',True)
            and not record.get('timeout',True) and not unsafe and not invalid)
    else:
        initial=samples[0].get('root',[])
        final=samples[-1].get('root',[])
        progress=final[0]-initial[0] if initial and final else float('nan')
        command_distance=record.get('command_distance',float('nan'))
        success = (complete and not required and len(samples) == 1000
            and record.get('end') == 'flat_horizon' and record.get('timeout')
            and math.isclose(command_distance,6.,abs_tol=1e-4)
            and math.isfinite(progress) and progress>0 and progress>=.7*command_distance
            and not unsafe and not invalid)
    return dict(complete=complete, success=bool(success), errors=sorted(set(errors)),
                unsafe=unsafe, invalid_teacher=invalid)


def verify_suite(records, *, diagnostic=False):
    identities = [(r['stage'],r['seed'],r['env_id'],r['episode_id']) for r in records]
    verified = [verify_episode(r) for r in records]
    counts = Counter((r['stage'],r['seed']) for r,v in zip(records,verified) if v['complete'])
    successes = Counter(r['stage'] for r,v in zip(records,verified) if v['success'])
    full = (len(identities) == len(set(identities)) == 200 and
        counts == Counter({(stage,seed):20 for stage in (0,3) for seed in range(101,106)}))
    passed = full and successes[0] >= 95 and successes[3] >= 95 and not diagnostic
    return dict(milestone_a='PASS' if passed else ('FAILED_DIAGNOSTIC' if diagnostic else 'FAIL'),
        complete_full_denominator=full, flat_success=successes[0], stage3_success=successes[3],
        recorded_episodes=len(records), complete_episodes=sum(v['complete'] for v in verified),
        duplicate_episodes=len(identities)-len(set(identities)))


def verify_collision_rows(rows):
    errors = []
    if len(rows) != 10: errors.append('expected ten consecutive contact steps')
    for i,row in enumerate(rows):
        expected = [2.*(i+1),2.*(i//2+1),0.,0.]
        if row['cost'] != [2.,2. if i%2 == 0 else 0.,0.,0.]: errors.append('per-step cost')
        if row['total'] != expected: errors.append('cumulative or intermittent total')
        if row['done'] != [i==9,False,False,False]: errors.append('row-local budget reset')
        if row['failure'] != [0.]*4: errors.append('extra termination charge')
        reset_expected = [0. if i==9 else expected[0],*expected[1:]]
        if row['reset_total'] != reset_expected: errors.append('reset budget locality')
        for j in range(4):
            if row['cost'][j] and not math.isclose(row['final'][j],row['raw'][j]-row['positive'][j],abs_tol=2e-5):
                errors.append('final wrapper reward composition')
    return dict(passed=not errors, errors=sorted(set(errors)))


def validate_paths(candidate, python, output):
    candidate, python, output = Path(candidate).resolve(), Path(python).resolve(), Path(output).resolve()
    if python != Path(sys.executable).resolve(): raise ValueError('explicit Python must be the running interpreter')
    if Path(__file__).resolve().parent.parent != candidate: raise ValueError('probe must execute from explicit candidate source')
    if candidate == Path('/root/quad/m1-rl/.worktrees/contact-recovery/Go2Pvcnn').resolve():
        raise ValueError('production is not a candidate')
    if output.exists(): raise ValueError('evidence directory already exists; never overwrite')
    if candidate not in output.parents: raise ValueError('evidence must be inside candidate')
    return candidate, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--python', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mode', choices=('smoke','contract','teacher','acceptance'), default='smoke')
    parser.add_argument('--diagnostic-steps', type=int, default=200)
    from isaaclab.app import AppLauncher
    AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()
    candidate, output = validate_paths(args.candidate,args.python,args.output)
    if not 1 <= args.diagnostic_steps <= 1000: raise ValueError('diagnostic steps must be 1..1000')
    output.mkdir(parents=True)
    launcher = AppLauncher(args)
    env = None
    try:
        import torch
        from isaaclab.envs import ManagerBasedRLEnv
        from ame_baseline.m1_teacher_profile import build_teacher_student_env_cfg
        from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
        cfg = build_teacher_student_env_cfg()
        cfg.scene.num_envs=4; cfg.sim.device=args.device; cfg.seed=101
        cfg.commands.base_velocity.debug_vis=False
        env = ManagerBasedRLEnv(cfg=cfg, render_mode='rgb_array')
        wrapper = AmeRslRlEnvWrapper(env)
        with torch.inference_mode():
            run = NativeProbe(env,wrapper,output,candidate)
            run.contract()
            run.warmup_video()
            run.flat_contract()
            if args.mode != 'smoke': run.collision_contract()
            if args.mode in ('teacher','acceptance'):
                run.teacher(acceptance=args.mode=='acceptance', diagnostic_steps=args.diagnostic_steps)
            else:
                run.write('result.json',dict(mode=args.mode, native_contract=True, milestone_a='NOT_RUN'))
    except BaseException as exc:
        (output/'failure.json').write_text(json.dumps(dict(type=type(exc).__name__,message=str(exc))),encoding='utf-8')
        raise
    finally:
        if env is not None: env.close()
        launcher.app.close()


class NativeProbe:
    """Probe-only observers. Exactly one wrapper.step per 20ms sample."""
    def __init__(self, env, wrapper, output, candidate):
        import torch
        from ame_baseline.m1_teacher_adapter import ReferenceTeacherAdapter, WHEEL_BODY_NAMES
        from ame_baseline.m1_reference_teacher import TeacherConfig
        from extension.parallelism.rl_adapter import resolve_named_indices
        self.torch=torch; self.env=env; self.w=wrapper; self.output=output
        self.robot=env.scene['robot']; self.sensor=env.scene['contact_forces']
        self.adapter=ReferenceTeacherAdapter(wrapper); self.teacher_cfg=TeacherConfig()
        self.wheels=list(resolve_named_indices(tuple(self.robot.body_names),WHEEL_BODY_NAMES))
        self.contacts=list(resolve_named_indices(tuple(self.sensor.body_names),WHEEL_BODY_NAMES))
        self.episode=torch.zeros(4,dtype=torch.long,device=env.device)
        self.frames=torch.zeros_like(self.episode); self.attempt=torch.zeros_like(self.episode)
        self.terminal={}; self.recording={}; self.capture={}; self.reset_reason='initial'
        self.support_acquired=torch.zeros(4,dtype=torch.bool,device=env.device)
        self.inner_failed=torch.zeros_like(self.support_acquired)
        self.last_output=None; self.current_stage=0
        self.tracker_calls=0; self.video_validated=False
        files={str(p.relative_to(candidate)):file_digest(p) for folder in ('ame_baseline','extension')
            for p in sorted((candidate/folder).rglob('*.py'))}
        files['scripts/probe_m1_teacher.py']=file_digest(Path(__file__))
        self.write('source.json',dict(candidate=str(candidate),python=sys.executable,files=files,
            code_sha256=digest(files),teacher=asdict(self.teacher_cfg),teacher_hash=self.teacher_cfg.fingerprint,
            effective_cfg_sha256=digest(env.cfg.to_dict()),effective_cfg=env.cfg.to_dict()))
        print('CANDIDATE_SOURCE '+json.dumps(dict(candidate=str(candidate),python=sys.executable,
            code_sha256=digest(files),teacher_hash=self.teacher_cfg.fingerprint)),flush=True)
        original_reset=env._reset_idx
        def reset_hook(ids):
            if self.reset_reason == 'natural':
                for row in ids.tolist():
                    snap=self.sample(row)
                    self.terminal[row]=snap
                    if row in self.recording: self.video_frame(row,terminal=True)
            return original_reset(ids)
        env._reset_idx=reset_hook
        original_reward=env.reward_manager.compute
        def reward_hook(dt):
            value=original_reward(dt)
            self.capture=dict(raw=value.clone(),parts={name:env.reward_manager._step_reward[:,i].clone()*dt
                for i,name in enumerate(env.reward_manager.active_terms)})
            return value
        env.reward_manager.compute=reward_hook
        original_inner=wrapper._m1_strict_crossing.inner.update
        def inner_hook(**kwargs):
            out=original_inner(**kwargs)
            self.inner_failed |= wrapper._m1_strict_crossing.inner.failed
            return out
        wrapper._m1_strict_crossing.inner.update=inner_hook
        original_tracker=wrapper._m1_strict_crossing.update
        def tracker_hook(**kwargs):
            out=original_tracker(**kwargs)
            self.tracker_calls+=1
            self.attempt += out['attempt_started'].long()
            self.inner_failed |= out['failed']
            self.tracker_evidence={k:v.clone() for k,v in out.items() if isinstance(v,torch.Tensor)}
            self.tracker_inputs={k:v.clone() for k,v in kwargs.items() if isinstance(v,torch.Tensor)}
            return out
        wrapper._m1_strict_crossing.update=tracker_hook

    def write(self,name,value):
        (self.output/name).write_text(json.dumps(value,indent=2,default=str),encoding='utf-8')

    def contract(self):
        import omni.usd
        from pxr import UsdGeom
        from isaaclab.actuators import DCMotor, ImplicitActuator
        from ame_baseline.m1_teacher_profile import require_teacher_student_backend
        from ame_baseline.m1_ame_actions import M1MixedJointAction
        from ame_baseline.m1_ame_contract import m1_action_targets
        from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
        env,w,t=self.env,self.w,self.torch
        require_teacher_student_backend(env)
        assert w.num_actions == env.action_manager.total_action_dim == 16
        term=env.action_manager.get_term('JointPositionAction')
        assert isinstance(term,M1MixedJointAction) and tuple(term._joint_names)==M1_ASSET_JOINT_NAMES
        action=t.linspace(-.1,.1,16,device=env.device).expand(4,-1).clone()
        term.process_actions(action)
        t.testing.assert_close(term.processed_actions,m1_action_targets(action,term._default_pos))
        assert not getattr(env,'_trajectory_manager',None)
        assert math.isclose(env.physics_dt,.005) and env.cfg.decimation==4
        assert math.isclose(env.step_dt,.02) and env.max_episode_length==1000
        legs,wheels=self.robot.actuators['legs'],self.robot.actuators['wheels']
        assert isinstance(legs,DCMotor) and isinstance(wheels,ImplicitActuator)
        pd={}
        for name,actuator,values in (('legs',legs,dict(stiffness=120.,damping=5.5,effort_limit=150.,velocity_limit=20.)),
                ('wheels',wheels,dict(stiffness=0.,damping=30.,effort_limit=200.,velocity_limit=20.))):
            pd[name]={}
            for key,expected in values.items():
                actual=getattr(actuator,key)
                assert bool(t.all(actual==expected)),(name,key,actual)
                pd[name][key]=actual.tolist()
        props=env.cfg.scene.robot.spawn.articulation_props
        assert (props.solver_position_iteration_count,props.solver_velocity_iteration_count)==(4,2)
        assert env.cfg.events.add_base_mass is None
        assert bool(t.all(self.robot.data.default_root_state[:,2]==.62))
        materials=self.robot.root_physx_view.get_material_properties()
        t.testing.assert_close(materials[...,:2],t.ones_like(materials[...,:2]))
        assert bool((materials[...,2]==0).all())
        stage=omni.usd.get_context().get_stage()
        for row in range(4):
            for wheel in self.wheels:
                path=f'/World/envs/env_{row}/Robot/{self.robot.body_names[wheel]}'
                assert not stage.GetPrimAtPath(path+'/collisions').IsActive()
                cylinder=UsdGeom.Cylinder(stage.GetPrimAtPath(path+'/wheel_collision'))
                assert cylinder.GetAxisAttr().Get()=='Y'
                assert abs(cylinder.GetRadiusAttr().Get()-.0959)<1e-8
                assert abs(cylinder.GetHeightAttr().Get()-.0465)<1e-8
        self.set_stage(0)
        observations=env.observation_manager.compute()
        dimensions={name:list(value.shape) for name,value in observations.items()}
        for name,size in (('policy_state',85),('critic_state',88),
                ('policy_elevation_semantic_map',1536),('critic_elevation_semantic_map',1536)):
            assert observations[name].reshape(4,-1).shape[1]==size,(name,dimensions[name])
        obs,extra=w._format_observations(observations)
        assert obs.shape==(4,1621)
        critic=extra['observations']['critic']
        assert critic.shape==(4,1624),critic.shape
        result=dict(joint_names=list(term._joint_names),actions=w.num_actions,policy=list(obs.shape),
            critic=list(critic.shape),pd=pd,dt=env.physics_dt,decimation=env.cfg.decimation,
            step_dt=env.step_dt,max_episode_steps=env.max_episode_length,
            collision=env._m1_collision_budget.contract,observation_components=dimensions)
        self.write('contract.json',result)
        print('NATIVE_CONTRACT '+json.dumps(result),flush=True)
        self.set_stage(3); self.set_stage(0)

    def set_stage(self, stage):
        from pxr import Usd, UsdGeom
        import omni.usd
        from ame_baseline.m1_required_crossing import progressive_required_wheels
        self.current_stage=stage; self.env._m1_learning_gate.stage=stage
        self.reset_reason='manual'; self.w.reset(); self.reset_reason='natural'
        self.frames.zero_(); self.attempt.zero_(); self.support_acquired.zero_(); self.inner_failed.zero_()
        terrain=self.env.scene.terrain; t=self.torch
        assert bool((terrain.terrain_levels==stage).all())
        course=self.w._m1_current_course()
        required=progressive_required_wheels(course,self.env.scene.env_origins[:,1])
        assert bool((required.sum((1,2))==(16 if stage==3 else 0)).all())
        records=terrain.grounded_course_obstacles; usd=omni.usd.get_context().get_stage()
        bbox=UsdGeom.BBoxCache(Usd.TimeCode.Default(),[UsdGeom.Tokens.default_])
        actual=[]
        for row,col in set(zip(terrain.terrain_levels.tolist(),terrain.terrain_types.tolist())):
            objects=sorted([r for r in records if (r.row,r.col)==(row,col)],key=lambda r:r.slot_index)
            assert len(objects)==(78 if stage==3 else 0)
            if stage==3:
                assert sum(r.required_crossing for r in objects)==8
                for obj in objects:
                    bounds=bbox.ComputeWorldBound(usd.GetPrimAtPath(obj.prim_path)).ComputeAlignedRange()
                    size=[float(bounds.GetMax()[k]-bounds.GetMin()[k]) for k in range(3)]
                    assert abs(size[2]-.10)<2e-4
                    if obj.required_crossing:
                        assert abs(size[0]-.10)<2e-4 and abs(size[1]-.18)<2e-4
                    actual.append(dict(id=obj.slot_index,center=list(obj.world_center),size=size,required=obj.required_crossing))
        if stage==3:
            for row in range(4):
                valid=course['valid'][row]
                centers=course['centers_top'][row,valid]-self.env.scene.env_origins[row]
                t.testing.assert_close(centers[:,0],t.arange(8,device=self.env.device)*1.1-1.2,atol=2e-4,rtol=0)
                assert bool((centers[:,1].abs()-.215).abs().max()<2e-4)
                assert bool((centers[:,2]-.10).abs().max()<2e-4)
        self.write(f'terrain_stage{stage}.json',dict(levels=terrain.terrain_levels.tolist(),
            types=terrain.terrain_types.tolist(),geometry=actual,course_ids=course['ids'].tolist(),
            required=required.tolist(),sha256=digest(actual)))
        print('TERRAIN_CONTRACT '+json.dumps(dict(stage=stage,levels=terrain.terrain_levels.tolist(),
            types=terrain.terrain_types.tolist(),targets=8 if stage else 0,fill=70 if stage else 0,
            height=.10 if stage else 0,geometry_sha256=digest(actual))),flush=True)

    def render_row(self,row,*,visible=True):
        import numpy as np
        robot=self.robot
        try:
            robot.set_visibility(False,env_ids=list(range(4)))
            if visible: robot.set_visibility(True,env_ids=[row])
            root=robot.data.root_pos_w[row].detach().cpu().numpy()
            self.env.sim.set_camera_view(eye=(root+np.array([2.,2.,1.4])).tolist(),target=root.tolist())
            self.env.sim.render()
            rgb=self.env.render().copy()
            assert rgb.ndim==3 and rgb.shape[2]>=3 and np.isfinite(rgb).all()
            return rgb[:,:,:3]
        finally:
            robot.set_visibility(True,env_ids=list(range(4)))

    def warmup_video(self):
        import numpy as np
        import imageio.v2 as imageio
        # Renderer warmup does not advance physics. Visibility is tested against
        # an all-hidden image so Fabric ignoring the USD change fails closed.
        before=float(self.env.sim.current_time)
        for _ in range(3): self.render_row(0)
        visible=self.render_row(0); hidden=self.render_row(0,visible=False)
        difference=float(np.abs(visible.astype(float)-hidden.astype(float)).mean())
        assert visible.std()>2 and visible.max()>30, 'black or empty camera'
        assert difference>.05, 'robot visibility not reflected by renderer/Fabric'
        assert math.isclose(before,float(self.env.sim.current_time),abs_tol=1e-8)
        imageio.imwrite(self.output/'video_warmup_visible.png',visible)
        imageio.imwrite(self.output/'video_warmup_hidden.png',hidden)
        self.video_validated=True
        self.write('video_warmup.json',dict(nonblack=True,isolated_robot=True,
            visibility_image_difference=difference,physics_time_unchanged=True))

    def step(self, action):
        env=self.env
        old_time=float(env.sim.current_time); old_count=env.common_step_counter
        old_calls=self.tracker_calls
        self.terminal={}; self.inner_failed.zero_(); self.frames+=1
        result=self.w.step(action)
        assert env.common_step_counter==old_count+1
        assert self.tracker_calls==old_calls+1
        assert math.isclose(float(env.sim.current_time)-old_time,.02,abs_tol=1e-6)
        assert self.torch.isfinite(result[0]).all() and self.torch.isfinite(result[1]).all()
        return result

    def flat_contract(self):
        from ame_baseline.m1_collision_budget import current_collision_snapshot
        self.set_stage(0)
        action=self.torch.zeros(4,16,device=self.env.device); action[:,[3,7,11,15]]=.30
        start=self.robot.data.root_pos_w.clone(); simtime=float(self.env.sim.current_time)
        for _ in range(100):
            _,_,done,_=self.step(action)
            assert not bool(done.any())
            assert not bool(current_collision_snapshot(self.env)['cost'].any())
        advance=(self.robot.data.root_pos_w[:,0]-start[:,0]).tolist()
        assert min(advance)>.3
        elapsed=float(self.env.sim.current_time)-simtime
        assert math.isclose(elapsed,2.,abs_tol=1e-6)
        self.write('flat_contract.json',dict(steps=100,elapsed=elapsed,advance=advance,passed=True))

    def collision_contract(self):
        from ame_baseline.m1_collision_budget import current_collision_snapshot
        env,t=self.env,self.torch
        self.set_stage(3)
        action=t.zeros(4,16,device=env.device)
        # Fixture placements only. They never enter teacher datasets or success.
        course=self.w._m1_current_course()
        root=self.robot.data.root_state_w.clone(); pose=self.robot.data.joint_pos.clone()
        root[:,7:]=0.; hit=root.clone()
        for row in (0,1):
            box=course['centers_top'][row,course['valid'][row]][0]
            target=box.clone(); target[2]+=.0959-.025
            hit[row,:3]+=target-self.robot.data.body_pos_w[row,self.wheels[0]]
        rows=[]
        for i in range(10):
            placed=root.clone(); placed[0]=hit[0]
            if i%2==0: placed[1]=hit[1]
            self.robot.write_root_state_to_sim(placed)
            self.robot.write_joint_state_to_sim(pose,t.zeros_like(pose))
            env.scene.write_data_to_sim()
            _,reward,done,_=self.step(action)
            snap=current_collision_snapshot(env)
            previous=snap['total'].clone()
            assert current_collision_snapshot(env) is snap
            assert env._m1_collision_budget.update(snap['signal'],env.common_step_counter) is snap
            t.testing.assert_close(snap['total'],previous)
            parts=self.capture['parts']; raw=self.capture['raw']
            t.testing.assert_close(sum(parts.values()),raw)
            t.testing.assert_close(parts['collision_budget_cost'],-snap['cost'])
            row=dict(cost=snap['cost'].tolist(),total=snap['total'].tolist(),done=done.bool().tolist(),
                failure=parts['failure_termination'].tolist(),raw=raw.tolist(),
                positive=sum(p.clamp_min(0) for p in parts.values()).tolist(),final=reward.tolist(),
                reset_total=env._m1_collision_budget.total.tolist(),
                terminals=self.terminal)
            rows.append(row); self.write('collision_steps.json',rows)
        result=verify_collision_rows(rows); self.write('collision_result.json',result)
        assert result['passed'],result
        self.set_stage(0)
        env.episode_length_buf[0]=env.max_episode_length-1
        _,reward,done,_=self.step(action)
        assert done.bool().tolist()==[True,False,False,False]
        assert float(self.capture['parts']['failure_termination'][0])==0
        assert bool(env.termination_manager.time_outs[0])
        timeout=dict(final=reward.tolist(),parts={k:v.tolist() for k,v in self.capture['parts'].items()})
        self.set_stage(0)
        bad=self.robot.data.root_state_w[:1].clone()
        bad[:,3:7]=bad.new_tensor([.70710678,.70710678,0.,0.])
        self.robot.write_root_state_to_sim(bad,env_ids=t.tensor([0],device=env.device)); env.scene.write_data_to_sim()
        for _ in range(30):
            _,reward,done,_=self.step(action)
            if bool(done[0]): break
        assert bool(done[0]) and not bool(done[1:].any())
        assert abs(float(self.capture['parts']['failure_termination'][0])+20.)<1e-5
        t.testing.assert_close(reward,self.capture['raw'])
        self.write('termination_contract.json',dict(timeout=timeout,
            physical_failure=dict(final=reward.tolist(),parts={k:v.tolist() for k,v in self.capture['parts'].items()})))

    def state(self,reset=None):
        from ame_baseline.m1_collision_budget import current_collision_snapshot
        t=self.torch
        collision=t.zeros(4,dtype=t.bool,device=self.env.device)
        if self.env.common_step_counter and self.env._m1_collision_budget.step==self.env.common_step_counter:
            collision=current_collision_snapshot(self.env)['signal']>0
        collision &= self.frames>0
        return self.adapter.snapshot(control_step=self.frames,episode_id=self.episode,
            reset_mask=t.zeros_like(collision) if reset is None else reset,collision=collision)

    @staticmethod
    def pairs(ids,mask):
        return [[int(ids[slot]),int(wheel)] for slot,wheel in mask.nonzero().tolist()]

    def sample(self,row):
        from ame_baseline.m1_collision_budget import current_collision_snapshot
        from ame_baseline.m1_reference_geometry import cylinder_bottom, cylinder_box_xy_witness
        env,t=self.env,self.torch; course=self.w._m1_current_course()
        force=self.sensor.data.net_forces_w[row,self.contacts]
        position=self.robot.data.body_pos_w[row:row+1,self.wheels]
        quat=self.robot.data.body_quat_w[row:row+1,self.wheels]
        bottom=cylinder_bottom(position,quat)[0]
        bearing=(force[:,2]>self.teacher_cfg.support_min_force_n)&(force[:,:2].norm(dim=-1)<=force[:,2])
        lost=bool(self.support_acquired[row] and bearing.sum()<3)
        self.support_acquired[row] |= bearing.sum()>=3
        receipt=self.w._m1_strict_crossing.recovered_for_course(course)[row]
        ids=course['ids'][row]
        from extension.parallelism.m1_kinematics import M1_WHEEL_HORIZONTAL_ENVELOPE_M
        far=(position[0,:,0][None,:] > course['centers_top'][row,:,0,None]+
             course['half_extents'][row,:,0,None]+M1_WHEEL_HORIZONTAL_ENVELOPE_M+self.teacher_cfg.far_margin_m)
        # Every wheel against every authored obstacle (including fill).
        penetration=False
        landing=course['landing_valid'][row]
        top=course['landing_centers_top'][row,landing]
        half=course['landing_half_extents'][row,landing]
        if top.shape[0]:
            xy=cylinder_box_xy_witness(position.expand(top.shape[0],-1,-1),
                quat.expand(top.shape[0],-1,-1),top,half,radius=.0959,thickness=.0465)
            penetration=bool((xy & (bottom[None,:]<top[:,2,None])).any())
        snap=current_collision_snapshot(env)
        output=self.last_output
        failures={name:bool(env.termination_manager.get_term(name)[row])
            for name in env.termination_manager.active_terms}
        timeout=bool(env.termination_manager.time_outs[row])
        failure=bool(env.termination_manager.terminated[row]) or bool(self.inner_failed[row])
        return dict(env_id=row,episode_id=int(self.episode[row]),attempt_id=int(self.attempt[row]),
            frame=int(self.frames[row]),sim_time=float(env.sim.current_time),
            active_wheel=int(output.active_wheel[row]) if output is not None else -1,
            phase=int(output.phase[row]) if output is not None else -1,
            teacher_reason=int(output.reason[row]) if output is not None else -1,
            teacher_valid=bool(output.valid[row]) if output is not None else True,
            Fz=force[:,2].tolist(),force=force.tolist(),wheel_position=position[0].tolist(),
            wheel_bottom=bottom.tolist(),obstacle_top=course['centers_top'][row,:,2].tolist(),
            collision=bool(snap['signal'][row]>0),support_lost=lost,penetration=penetration,
            failure=failure,timeout=timeout,termination_terms=failures,budget={k:v[row].tolist() for k,v in snap.items()},
            receipt=self.pairs(ids,receipt),far_side_recovery=self.pairs(ids,receipt&far),
            root=self.robot.data.root_state_w[row].tolist(),joints=self.robot.data.joint_pos[row].tolist(),
            course_ids=ids.tolist())

    def begin_video(self,row,seed,stage):
        import imageio.v2 as imageio
        stem=f'stage{stage}_seed{seed}_env{row}_episode{int(self.episode[row])}'
        path=self.output/(stem+'.mp4')
        self.recording[row]=dict(writer=imageio.get_writer(str(path),fps=10,codec='libx264'),
            path=path,indices=[],times=[],samples=[],seed=seed,stage=stage,
            initial_root=self.robot.data.root_pos_w[row].tolist(),command_distance=0.,
            trace=(self.output/(stem+'.jsonl')).open('x',encoding='utf-8'))
        self.video_frame(row)

    def video_frame(self,row,terminal=False):
        rec=self.recording[row]; frame=int(self.frames[row])
        if rec['indices'] and rec['indices'][-1]==frame: return
        rec['writer'].append_data(self.render_row(row))
        rec['indices'].append(frame); rec['times'].append(float(self.env.sim.current_time))

    def finish_episode(self,row,required,end,natural,timeout):
        rec=self.recording[row]
        self.video_frame(row,terminal=True)
        rec['writer'].close(); rec['trace'].close()
        video=dict(path=str(rec['path']),sha256=file_digest(rec['path']),bytes=rec['path'].stat().st_size,
            isolated_robot=self.video_validated,nonblack=self.video_validated,
            frame_indices=rec['indices'],sim_times=rec['times'],first_frame=rec['indices'][0],last_frame=rec['indices'][-1])
        result=dict(stage=rec['stage'],seed=rec['seed'],env_id=row,episode_id=int(self.episode[row]),
            required=required,samples=rec['samples'],terminal=rec['samples'][-1],video=video,
            initial_root=rec['initial_root'],command_distance=rec['command_distance'],
            end=end,natural_done=natural,timeout=timeout)
        result['verification']=verify_episode(result)
        self.write(rec['path'].stem+'.json',result)
        del self.recording[row]
        return result

    def reset_row(self,row):
        t=self.torch; mask=t.zeros(4,dtype=t.bool,device=self.env.device); mask[row]=True
        self.reset_reason='manual'
        obs,_=self.env.reset(env_ids=mask.nonzero().flatten())
        self.w._format_observations(obs)
        self.reset_reason='natural'
        for tracker in (self.w._m1_strict_crossing,self.w._m1_required_gate,self.w._m1_stall_window):
            tracker.reset(mask)
        for name in ('_small_candidate_prev','_small_candidate_seen','_small_candidate_lift_seen',
                '_small_candidate_clearance_seen','_large_candidate_seen','_m1_obstacle_event_seen',
                '_m1_initial_teacher_fallback_used','_m1_short_trigger_seen','_m1_short_trigger_clear_steps',
                '_m1_obstacle_clear_steps','_m1_teacher_active','_m1_teacher_age','_m1_teacher_elapsed',
                '_m1_teacher_no_candidate_steps'):
            getattr(self.w,name)[row]=0

    def teacher(self,*,acceptance,diagnostic_steps):
        from ame_baseline.m1_reference_teacher import ReferenceTeacher
        records=[]; t=self.torch
        try:
            for stage in (0,3):
                for seed in (range(101,106) if acceptance else [101]):
                    self.env.seed(seed); self.set_stage(stage)
                    teacher=ReferenceTeacher(self.teacher_cfg)
                    self.episode.zero_(); self.frames.zero_(); self.attempt.zero_()
                    quotas=[5]*4 if acceptance else [1]*4
                    required=[self.pairs(self.state().course_ids[i],self.state().required_wheels[i]) for i in range(4)]
                    # Initialize identity without executing an invalid RESET label.
                    self.frames.fill_(-1)
                    teacher.step(self.state(reset=t.ones(4,dtype=t.bool,device=self.env.device)))
                    self.frames.zero_()
                    for row in range(4): self.begin_video(row,seed,stage)
                    while self.recording:
                        self.last_output=teacher.step(self.state())
                        command=self.env.command_manager.get_command('base_velocity')[:,0]
                        for row,rec in self.recording.items(): rec['command_distance']+=float(command[row])*.02
                        _,_,done,_=self.step(self.last_output.action)
                        for row in list(self.recording):
                            sample=self.terminal.get(row) if bool(done[row]) else self.sample(row)
                            assert sample is not None, 'natural terminal snapshot lost before reset'
                            rec=self.recording[row]; rec['samples'].append(sample)
                            rec['trace'].write(json.dumps(sample)+'\n'); rec['trace'].flush()
                            if int(self.frames[row])%5==0 and not bool(done[row]): self.video_frame(row)
                            complete=(stage==3 and len(required[row])==16 and
                                {tuple(p) for p in required[row]} <= {tuple(p) for p in sample['receipt']} and
                                {tuple(p) for p in required[row]} <= {tuple(p) for p in sample['far_side_recovery']})
                            horizon=stage==0 and int(self.frames[row])==1000
                            diagnostic_end=not acceptance and int(self.frames[row])>=diagnostic_steps
                            if bool(done[row]) or complete or horizon or diagnostic_end:
                                end='flat_horizon' if horizon else ('natural_done' if bool(done[row]) else
                                    ('task_complete' if complete else 'diagnostic_bound'))
                                record=self.finish_episode(row,required[row],end,bool(done[row]),sample['timeout'])
                                records.append(record); quotas[row]-=1
                                print('TEACHER_EPISODE '+json.dumps({k:v for k,v in record.items() if k not in ('samples','terminal','video')}),flush=True)
                                if quotas[row]>0:
                                    if not bool(done[row]): self.reset_row(row)
                                    self.episode[row]+=1; self.frames[row]=0; self.attempt[row]=0
                                    self.support_acquired[row]=False; self.inner_failed[row]=False
                                    # Teacher sees identity change at synthetic pre-control -1 only.
                                    mask=t.zeros(4,dtype=t.bool,device=self.env.device); mask[row]=True
                                    saved=self.frames.clone(); self.frames[row]=-1
                                    teacher.step(self.state(reset=mask)); self.frames.copy_(saved)
                                    self.begin_video(row,seed,stage)
                    result=verify_suite(records,diagnostic=not acceptance)
                    self.write('result.json',result)
            print('MILESTONE_A '+json.dumps(result),flush=True)
        finally:
            for rec in self.recording.values():
                rec['writer'].close(); rec['trace'].close()


if __name__ == '__main__': main()
