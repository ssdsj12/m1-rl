"""Candidate-only native teacher evidence. No training or production writes.

The pure verifier imports no simulator. Native entry imports AppLauncher before
Isaac/pxr/omni. A diagnostic run can never report milestone A PASS.
"""
import argparse
import copy
from collections import Counter
from dataclasses import asdict
import hashlib
import importlib.machinery
import json
import math
from pathlib import Path
import sys
from functools import lru_cache


SAMPLE_KEYS = {'env_id','episode_id','attempt_id','frame','sim_time','active_wheel',
    'Fz','wheel_bottom','obstacle_top','collision','support_lost','penetration',
    'failure','teacher_valid','far_side_recovery','receipt','root',
    'teacher_input_frame','teacher_input_episode_id','teacher_input_sim_time',
    'teacher_action','executed_action','processed_targets','action_joint_names',
    'processed_target_joint_names','active_target','teacher_ages_after_decision','raw_joint_names','joints'}
SCHEMA_VERSION = 4
TEACHER_SCOPES = ('flat-preparation','single-wheel','first-obstacle','transitions','course')
APPLY_KEYS = {'schema_version','teacher_scope','failure_locked','student_demonstration_usable',
    'applied_targets','applied_target_joint_names','applied_substeps','action_process_count',
    'physics_decimation','action_matches_request','applied_target_valid','teacher_diagnostic',
    'last_applied_leg_target','requested_processed_targets','action_default_joint_pos','action_target_dtype'}


def validate_scope(scope, *, acceptance, active_wheel):
    if scope not in TEACHER_SCOPES: raise ValueError('unknown teacher scope')
    if acceptance and scope != 'course': raise ValueError('acceptance requires course scope')
    if scope == 'single-wheel':
        if type(active_wheel) is not int or active_wheel not in range(4):
            raise ValueError('single-wheel requires active wheel 0..3')
    elif active_wheel is not None: raise ValueError('active wheel is only for single-wheel')


def teacher_schedule(scope,active_wheel):
    validate_scope(scope,acceptance=False,active_wheel=active_wheel)
    if scope=='flat-preparation': return [(0,wheel) for wheel in range(4)]
    if scope=='single-wheel': return [(0,active_wheel)]
    if scope in ('first-obstacle','transitions'): return [(3,None)]
    return [(0,None),(3,None)]


class FailureDiagnosticBound:
    """The locking frame plus at most five further observed control steps."""
    def __init__(self): self.counts={}
    def update(self,row,locked):
        if not locked: return False
        self.counts[row]=self.counts.get(row,-1)+1
        return self.counts[row]>=5
    def reset(self,row): self.counts.pop(row,None)


class DiagnosticBatchGate:
    """Diagnostic-only stop latch; a peer interruption is not physical failure."""
    def __init__(self,acceptance): self.acceptance=acceptance; self.failure=None

    @staticmethod
    def sample_reason(sample):
        for reason in ('failure_locked','collision','support_lost','penetration','failure'):
            if sample.get(reason,False): return reason
        if sample.get('action_matches_request') is False or sample.get('applied_target_valid') is False:
            return 'action_evidence_invalid'
        return None

    def latch(self,sample,step,reason,errors=None):
        if not self.acceptance and self.failure is None:
            self.failure=dict(env_id=sample['env_id'],episode_id=sample['episode_id'],
                frame=sample['frame'],control_step=step,reason=reason,
                physical_failure=any(sample.get(key,False) for key in ('collision','support_lost','penetration','failure')),
                errors=list(errors or ()))

    def observe_sample(self,sample,step):
        reason=self.sample_reason(sample)
        if reason: self.latch(sample,step,reason)

    def observe_end(self,sample,end,step):
        if ((end=='diagnostic_bound' or end=='natural_done' and sample.get('timeout',False))
                and not sample.get('scope_observation_complete',False)):
            self.latch(sample,step,'diagnostic_goal_unmet')

    def observe_record(self,record,step):
        errors=record['verification']['errors']
        if errors: self.latch(record['terminal'],step,'evidence_invalid',errors)
        elif (record.get('stage')==0 and record.get('end')=='flat_horizon'
                and not record['verification']['success']):
            self.latch(record['terminal'],step,'diagnostic_goal_unmet')

    def deadline(self,step):
        return self.failure is not None and step-self.failure['control_step']>=5

    def is_source(self,sample):
        return self.failure is not None and (sample['env_id'],sample['episode_id'])==(
            self.failure['env_id'],self.failure['episode_id'])


def diagnostic_json(value):
    from ame_baseline.m1_reference_teacher import TEACHER_DIAGNOSTIC_FIELDS,TEACHER_DIAGNOSTIC_INTEGER_FIELDS
    if len(value)!=len(TEACHER_DIAGNOSTIC_FIELDS): raise ValueError('teacher diagnostic width mismatch')
    integers=set(TEACHER_DIAGNOSTIC_INTEGER_FIELDS)
    return {name:(int(v) if name in integers else float(v)) if math.isfinite(float(v)) else None
            for name,v in zip(TEACHER_DIAGNOSTIC_FIELDS,value)}


def readiness_measurement(state,row,sim_time):
    """Owned real measurements only; absent input stays explicitly incomplete."""
    names=('root_pos_w','root_quat_w','root_lin_vel_w','root_ang_vel_w',
           'com_pos_w','wheel_pos_w','wheel_force_w','measurement_valid')
    if not all(hasattr(state,name) for name in names): return None
    root=[]
    for name in names[:4]: root.extend(getattr(state,name)[row].detach().clone().tolist())
    return dict(env_id=row,episode_id=int(state.episode_id[row]),frame=int(state.control_step[row]),
        sim_time=float(sim_time),root=root,com=state.com_pos_w[row].detach().clone().tolist(),
        wheels=state.wheel_pos_w[row].detach().clone().tolist(),
        forces=state.wheel_force_w[row].detach().clone().tolist(),
        measurement_valid=bool(state.measurement_valid[row]))


def preparation_observed(sample,cfg):
    """Independently recompute the original measured gate on both action sides.

    Input tracks the prior accepted reference and same-decision goal. Output
    tracks the newly accepted reference and that goal, never adjacent reset loads.
    No predicted COM or private capture flag participates.
    """
    import torch
    from ame_baseline.m1_teacher_pose import support_margin
    from ame_baseline.m1_reference_teacher import quaternion_rpy
    axes=('x','y','z','qw','qx','qy','qz')
    try:
        diagnostic=sample['teacher_diagnostic']; wheel=sample['active_wheel']
        if (diagnostic['reference_valid']!=1 or diagnostic['preparation_ready']!=1
                or isinstance(wheel,bool) or wheel not in range(4)
                or sample.get('failure_locked',False)
                or any(sample.get(k,True) for k in ('collision','support_lost','penetration','failure'))): return False
        pose=lambda prefix:torch.tensor([diagnostic[prefix+axis] for axis in axes],dtype=torch.float64)
        prior=pose('preparation_prior_root_'); goal=pose('preparation_goal_root_'); accepted=pose('accepted_root_')
        for side,refs,frame,time in (
                ('input',(prior,goal),sample['teacher_input_frame'],sample['teacher_input_sim_time']),
                ('output',(accepted,goal),sample['frame'],sample['sim_time'])):
            measured=sample['preparation_'+side]
            if (measured['env_id']!=sample['env_id'] or measured['episode_id']!=sample['episode_id']
                    or measured['frame']!=frame or not math.isclose(measured['sim_time'],time,abs_tol=1e-6)
                    or measured['measurement_valid'] is not True): return False
            root=torch.tensor(measured['root'],dtype=torch.float64)
            com=torch.tensor(measured['com'],dtype=torch.float64)
            wheels=torch.tensor(measured['wheels'],dtype=torch.float64)
            forces=torch.tensor(measured['forces'],dtype=torch.float64)
            if (root.shape!=(13,) or com.shape!=(3,) or wheels.shape!=(4,3) or forces.shape!=(4,3)
                    or not all(bool(torch.isfinite(x).all()) for x in (root,com,wheels,forces,*refs))
                    or abs(float(root[3:7].norm())-1)>1e-3): return False
            rpy=quaternion_rpy(root[None,3:7])[0]
            if (root[7:10].norm()>cfg.balance_speed_limit_m_s
                    or rpy[:2].abs().max()>cfg.recovery_tilt_rad
                    or root[10:12].abs().max()>cfg.recovery_rate_rad_s): return False
            for ref in refs:
                if abs(float(ref[3:7].norm())-1)>1e-3: return False
                delta=rpy-quaternion_rpy(ref[None,3:7])[0]
                delta=torch.atan2(torch.sin(delta),torch.cos(delta))
                if (torch.linalg.vector_norm(root[:3]-ref[:3])>cfg.balance_position_tolerance_m
                        or delta.abs().max()>cfg.recovery_pose_rad): return False
            margin,valid=support_margin(com[None],wheels[None],torch.tensor([wheel]))
            support=[i for i in range(4) if i!=wheel]
            bearing=(forces[:,2]>cfg.support_min_force_n)&(forces[:,:2].norm(dim=-1)<=cfg.support_max_tangential_ratio*forces[:,2])
            if not bool(valid[0] and margin[0]>=cfg.com_margin_m and bearing[support].all()): return False
            if side=='output' and (measured['root']!=sample['root'] or measured['wheels']!=sample['wheel_position']
                    or [f[2] for f in measured['forces']]!=sample['Fz']
                    or measured['forces']!=sample.get('force')): return False
        return True
    except (KeyError,TypeError,ValueError,RuntimeError,IndexError): return False


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same_json_evidence(actual,expected):
    """Exact corresponding values, with NaN equal only to NaN at the same key.

    Missing measurement markers remain untouched. No field, array entry or
    finite contradiction is omitted, filled or approximately compared.
    """
    if type(actual) is not type(expected): return False
    if isinstance(actual,dict):
        return actual.keys()==expected.keys() and all(same_json_evidence(actual[k],expected[k]) for k in actual)
    if isinstance(actual,list):
        return len(actual)==len(expected) and all(same_json_evidence(a,b) for a,b in zip(actual,expected))
    if isinstance(actual,float) and math.isnan(actual): return math.isnan(expected)
    return actual==expected


def verify_trace(trace,samples):
    """Read and hash current bytes; metadata alone never certifies trajectory."""
    errors=[]
    try:
        path=Path(trace['path']); stat=path.stat(); raw=path.read_bytes()
        if (not isinstance(trace.get('bytes'),int) or trace['bytes']<=0
                or stat.st_size!=trace['bytes'] or len(raw)!=trace['bytes']
                or hashlib.sha256(raw).hexdigest()!=trace['sha256']):
            errors.append('trace artifact verification failed')
        lines=raw.decode('utf-8-sig').splitlines()
        matches=len(lines)==len(samples)
        for index,line in enumerate(lines):
            actual=json.loads(line)
            if index>=len(samples) or not same_json_evidence(actual,samples[index]): matches=False
        if not matches: errors.append('trace records differ from samples')
    except (KeyError,OSError,ValueError,TypeError):
        errors.append('trace artifact unreadable')
    return errors


@lru_cache(maxsize=256)
def decoded_request_targets(action,defaults,dtype):
    """Cache pure decoding for identical inputs only; never cache validity."""
    import torch
    from ame_baseline.m1_ame_contract import m1_action_targets
    if dtype not in ('float32','float64'): raise ValueError('unsupported recorded action target dtype')
    target=m1_action_targets(torch.tensor([action],dtype=getattr(torch,dtype)),
        torch.tensor([defaults],dtype=getattr(torch,dtype)))
    return tuple(target[0].tolist())


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
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    raw_names=record.get('raw_joint_names',[])
    redesigned=record.get('schema_version')==SCHEMA_VERSION
    if not redesigned: errors.append('legacy schema lacks actual apply evidence')
    if len(raw_names)!=16 or len(set(raw_names))!=16 or set(raw_names)!=set(M1_ASSET_JOINT_NAMES):
        errors.append('missing unique raw joint contract')
    samples = record.get('samples', [])
    from ame_baseline.m1_reference_teacher import TeacherConfig
    readiness_cfg=None
    if record.get('teacher_scope')=='flat-preparation':
        try:
            if set(record['teacher_config'])!=set(asdict(TeacherConfig())):
                raise ValueError('incomplete readiness config')
            readiness_cfg=TeacherConfig(**record['teacher_config'])
            if readiness_cfg.fingerprint!=record['teacher_hash']: raise ValueError('config hash mismatch')
        except (KeyError,TypeError,ValueError): errors.append('missing readiness configuration evidence')
    stage = record.get('stage')
    if not samples or stage not in (0,3):
        return dict(complete=False, success=False, errors=['missing trajectory or stage'])
    start_time = samples[0].get('sim_time', 0.)-.02
    for index, sample in enumerate(samples, 1):
        if not SAMPLE_KEYS <= sample.keys():
            errors.append('missing sample fields'); continue
        if redesigned:
            if not APPLY_KEYS <= sample.keys(): errors.append('missing actual apply evidence')
            else:
                substeps=sample['applied_substeps']; targets=sample['applied_targets']
                if (sample['schema_version']!=SCHEMA_VERSION or sample['physics_decimation']!=4
                        or sample['action_process_count']!=1 or len(substeps)!=4
                        or sample['applied_target_joint_names']!=list(M1_ASSET_JOINT_NAMES)
                        or len(targets)!=16 or not all(math.isfinite(x) for x in targets)
                        or not sample['applied_target_valid']
                        or len(sample['last_applied_leg_target'])!=12
                        or not all(math.isfinite(x) for x in sample['last_applied_leg_target'])):
                    errors.append('invalid actual apply evidence')
                for i,sub in enumerate(substeps):
                    if (sub.get('index')!=i or sub.get('targets')!=targets
                            or not sub.get('write_seen') or not sub.get('physics_seen')
                            or not math.isclose(sub.get('sim_time',float('nan')),
                                sample['teacher_input_sim_time']+i*.005,abs_tol=1e-6)):
                        errors.append('apply not bound to each physics substep')
                if targets!=sample['processed_targets']: errors.append('applied targets differ from processed request')
                from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES
                from extension.parallelism.rl_adapter import resolve_named_indices
                if len(targets)==16 and len(sample['last_applied_leg_target'])==12:
                    legs=[targets[i] for i in resolve_named_indices(M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES)]
                    if any(abs(q-p)>.05+1e-7 for q,p in zip(legs,sample['last_applied_leg_target'])):
                        errors.append('actual applied leg target exceeds 20ms slew')
                from ame_baseline.m1_reference_teacher import TEACHER_DIAGNOSTIC_FIELDS
                if set(sample['teacher_diagnostic'])!=set(TEACHER_DIAGNOSTIC_FIELDS):
                    errors.append('missing named teacher diagnostic schema')
                diagnostic=sample['teacher_diagnostic']
                if sample['teacher_valid'] and diagnostic.get('reference_valid')!=1:
                    errors.append('label disagrees with reference validity')
                local=record.get('teacher_scope') in ('flat-preparation','single-wheel')
                if diagnostic.get('diagnostic_only')!=int(local) or sample['teacher_scope']!=record.get('teacher_scope'):
                    errors.append('label disagrees with diagnostic scope')
        if (sample['env_id'],sample['episode_id']) != (record['env_id'],record['episode_id']):
            errors.append('episode identity changed')
        if sample['frame'] != index or not math.isclose(sample['sim_time']-start_time, index*.02, abs_tol=1e-6):
            errors.append('not a contiguous 50Hz trajectory')
        if (sample['teacher_input_frame']!=sample['frame']-1
                or sample['teacher_input_episode_id']!=sample['episode_id']
                or not math.isclose(sample['sim_time']-sample['teacher_input_sim_time'],.02,abs_tol=1e-6)):
            errors.append('action not tied to precontrol identity/time')
        if any(sample[key]!=list(M1_ASSET_JOINT_NAMES) for key in
                ('action_joint_names','processed_target_joint_names')):
            errors.append('action target joint order mismatch')
        if any(len(sample[key])!=16 or not all(math.isfinite(x) for x in sample[key])
                for key in ('teacher_action','executed_action','processed_targets')):
            errors.append('missing or nonfinite action measurement')
        if sample['teacher_action']!=sample['executed_action']:
            errors.append('requested action differs from executed action')
        if redesigned and {'requested_processed_targets','action_default_joint_pos','action_target_dtype'}<=sample.keys():
            requested=sample['requested_processed_targets']; defaults=sample['action_default_joint_pos']
            finite=lambda value:isinstance(value,list) and len(value)==16 and all(
                isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x) for x in value)
            if not finite(requested) or not finite(defaults):
                errors.append('missing or nonfinite requested target decoding evidence')
            else:
                try:
                    decoded=decoded_request_targets(tuple(sample['teacher_action']),tuple(defaults),sample['action_target_dtype'])
                    if list(decoded)!=requested or requested!=sample['processed_targets'] or requested!=sample.get('applied_targets'):
                        errors.append('requested target decoding disagrees with processed or applied targets')
                except (ValueError,TypeError,RuntimeError):
                    errors.append('invalid requested target decoding evidence')
        if (sample['raw_joint_names']!=raw_names or len(sample['joints'])!=len(raw_names)
                or not all(math.isfinite(x) for x in sample['joints'])):
            errors.append('raw joint measurement/name contract mismatch')
        if len(sample['Fz'])!=4 or len(sample['wheel_bottom'])!=4 or len(sample['root'])!=13:
            errors.append('missing physical measurement dimensions')
        if not all(math.isfinite(x) for key in ('Fz','wheel_bottom','obstacle_top','root') for x in sample[key]):
            errors.append('nonfinite physical measurement')
    terminal = record.get('terminal')
    if record.get('teacher_scope')=='flat-preparation':
        for sample in samples:
            if sample.get('scope_observation_complete') and (readiness_cfg is None or not preparation_observed(sample,readiness_cfg)):
                errors.append('preparation endpoint lacks same-decision input and post-action measured readiness')
        if record.get('end')=='scope_observed' and not samples[-1].get('scope_observation_complete'):
            errors.append('preparation endpoint not observed')
    if not same_json_evidence(terminal,samples[-1]): errors.append('missing or mismatched pre-reset terminal snapshot')
    errors.extend(verify_trace(record.get('trace') or {},samples))
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
    complete = not errors and record.get('end') in ('task_complete','flat_horizon','natural_done','teacher_failure_locked')
    unsafe = any(s.get(k,True) for s in samples for k in ('collision','support_lost','penetration','failure'))
    locked=any(s.get('failure_locked',False) for s in samples)
    invalid = any(not s.get('teacher_valid',False) or not s.get('action_matches_request',False)
                  or not s.get('student_demonstration_usable',False) for s in samples) or locked
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
    success=success and record.get('teacher_scope')=='course'
    return dict(complete=complete, success=bool(success), errors=sorted(set(errors)),
                unsafe=unsafe, invalid_teacher=invalid,failure_locked=locked,
                student_demonstration_usable=bool(success))


def verify_suite(records, *, diagnostic=False):
    identities = [(r['stage'],r['seed'],r['env_id'],r['episode_id']) for r in records]
    verified = [verify_episode(r) for r in records]
    counts = Counter((r['stage'],r['seed']) for r in records)
    successes = Counter(r['stage'] for r,v in zip(records,verified) if v['success'])
    full = (len(identities) == len(set(identities)) == 200 and
        counts == Counter({(stage,seed):20 for stage in (0,3) for seed in range(101,106)}))
    passed = full and all(v['complete'] for v in verified) and successes[0] >= 95 and successes[3] >= 95 and not diagnostic
    return dict(milestone_a='PASS' if passed else ('FAILED_DIAGNOSTIC' if diagnostic else 'FAIL'),
        complete_full_denominator=full, flat_success=successes[0], stage3_success=successes[3],
        recorded_episodes=len(records), complete_episodes=sum(v['complete'] for v in verified),
        counted_episodes=len(records),locked_failures=sum(v.get('failure_locked',False) for v in verified),
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


CANDIDATE_DOMAINS = frozenset(('ame_baseline','extension','rsl_rl','tracking','go2_pvcnn'))


def candidate_module_record(candidate, name, origin, locations=None):
    """Validate the executed file, not just the script or configured PYTHONPATH."""
    root=name.split('.')[0]
    base=candidate/'rsl_rl' if root=='rsl_rl' else candidate
    stem=base.joinpath(*name.split('.'))
    allowed=(stem.with_suffix('.py'),stem/'__init__.py')
    if not origin:
        # Real repository namespaces (for example go2_pvcnn.sensor) have no
        # __file__. They must have exactly their candidate-only package path.
        paths=[Path(p).resolve() for p in locations or ()]
        if (paths==[stem.resolve()] and stem.is_dir() and candidate in stem.resolve().parents):
            return dict(kind='namespace',path=None,sha256=None,locations=[str(p) for p in paths])
        raise ValueError(f'{name} has no verifiable source file; outside candidate contract')
    actual=Path(origin).resolve()
    if (candidate not in actual.parents or actual not in [p.resolve() for p in allowed]
            or not actual.is_file()):
        raise ValueError(f'{name} loaded outside candidate: {actual}')
    return dict(kind='source',path=str(actual),sha256=file_digest(actual))


def loaded_candidate_modules(candidate):
    candidate=Path(candidate).resolve()
    return {name:candidate_module_record(candidate,name,getattr(module,'__file__',None),getattr(module,'__path__',None))
        for name,module in sorted(list(sys.modules.items()))
        if name.split('.')[0] in CANDIDATE_DOMAINS and module is not None}


class CandidateSourceFinder:
    """Resolve candidate domains before any foreign module body can execute."""
    def __init__(self,candidate): self.candidate=candidate

    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] not in CANDIDATE_DOMAINS: return None
        spec=importlib.machinery.PathFinder.find_spec(fullname,path,target)
        if spec is None: raise ModuleNotFoundError(f'candidate module unavailable: {fullname}')
        candidate_module_record(self.candidate,fullname,spec.origin,spec.submodule_search_locations)
        return spec


def bind_candidate_imports(candidate):
    candidate=Path(candidate).resolve()
    loaded_candidate_modules(candidate)  # Reject cached foreign modules first.
    roots=[str(candidate),str(candidate/'rsl_rl')]
    sys.path[:]=roots+[p for p in sys.path if str(Path(p or '.').resolve()) not in roots]
    if not any(isinstance(f,CandidateSourceFinder) and f.candidate==candidate for f in sys.meta_path):
        sys.meta_path.insert(0,CandidateSourceFinder(candidate))


def cylinder_penetration_witness(pos,quat,centers_top,half_extents,radius=.0959,thickness=.0465):
    """Positive witness: the SAME actual cylinder point is inside XY and below top.

    Finite sampling is not a separation certificate. False means no witness,
    never a claim of clearance. It cannot turn a conservative clears=False
    result or an unrelated global bottom/XY point into penetration evidence.
    One micrometre only excludes floating-point tangency from this diagnostic;
    production collision, zero-clearance and strict receipts are untouched.
    """
    import torch
    if (pos.ndim!=3 or pos.shape[-1]!=3 or quat.shape!=pos.shape[:-1]+(4,)
            or centers_top.shape!=(pos.shape[0],3) or half_extents.shape!=(pos.shape[0],2)
            or any(not bool(torch.isfinite(v).all()) for v in (pos,quat,centers_top,half_extents))
            or bool((half_extents<=0).any()) or bool((quat.norm(dim=-1)<1e-8).any())):
        raise ValueError('finite aligned cylinder and positive box geometry required')
    angle=torch.arange(32,device=pos.device,dtype=pos.dtype)*(2*torch.pi/32)
    rings=[torch.stack((radius*angle.cos(),torch.full_like(angle,y),radius*angle.sin()),-1)
        for y in (-thickness/2,0.,thickness/2)]
    points=torch.cat((*rings,pos.new_tensor([[0,0,0],[0,-thickness/2,0],[0,thickness/2,0]])))
    q=quat/quat.norm(dim=-1,keepdim=True)
    local=points[None,None].expand(pos.shape[0],pos.shape[1],-1,-1)
    xyz=q[...,1:][:,:,None].expand_as(local)
    uv=torch.cross(xyz,local,dim=-1)
    world=local+2*(q[...,0,None,None]*uv+torch.cross(xyz,uv,dim=-1))+pos[:,:,None]
    inside_xy=((world[...,:2]-centers_top[:,None,None,:2]).abs()<half_extents[:,None,None]-1e-6).all(-1)
    below_top=world[...,2]<centers_top[:,None,None,2]-1e-6
    return (inside_xy & below_top).any(-1)


def course_tile_coordinates(terrain,course):
    """Authoring uses tile origins; reset spawn env_origins may be offset -2m."""
    origins=terrain.terrain_origins[terrain.terrain_levels,terrain.terrain_types]
    return course['centers_top']-origins[:,None,:]


def configure_probe_rendering(cfg):
    """Independent-row recordings cannot share DLSS temporal reconstruction."""
    cfg.sim.render.antialiasing_mode='Off'
    cfg.sim.render.enable_dlssg=False
    return dict(antialiasing_mode=cfg.sim.render.antialiasing_mode,
        enable_dlssg=cfg.sim.render.enable_dlssg,settle_render_frames=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--python', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mode', choices=('smoke','contract','teacher','acceptance'), default='smoke')
    parser.add_argument('--diagnostic-steps', type=int, default=200)
    parser.add_argument('--teacher-scope',choices=TEACHER_SCOPES,default='course')
    parser.add_argument('--active-wheel',type=int,choices=range(4),default=None)
    preliminary,_=parser.parse_known_args()
    candidate,output=validate_paths(preliminary.candidate,preliminary.python,preliminary.output)
    bind_candidate_imports(candidate)
    from isaaclab.app import AppLauncher
    AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()
    candidate, output = validate_paths(args.candidate,args.python,args.output)
    if not 1 <= args.diagnostic_steps <= 1000: raise ValueError('diagnostic steps must be 1..1000')
    validate_scope(args.teacher_scope,acceptance=args.mode=='acceptance',active_wheel=args.active_wheel)
    output.mkdir(parents=True)
    launcher = AppLauncher(args)
    env = None
    try:
        loaded_candidate_modules(candidate)
        import torch
        from isaaclab.envs import ManagerBasedRLEnv
        from ame_baseline.m1_teacher_profile import build_teacher_student_env_cfg
        from ame_baseline.ame_env_wrapper import AmeRslRlEnvWrapper
        cfg = build_teacher_student_env_cfg()
        render_configuration=configure_probe_rendering(cfg)
        (output/'render_configuration.json').write_text(json.dumps(render_configuration,indent=2),encoding='utf-8')
        cfg.scene.num_envs=4; cfg.sim.device=args.device; cfg.seed=101
        cfg.commands.base_velocity.debug_vis=False
        env = ManagerBasedRLEnv(cfg=cfg, render_mode='rgb_array')
        wrapper = AmeRslRlEnvWrapper(env)
        loaded_candidate_modules(candidate)
        with torch.inference_mode():
            run = NativeProbe(env,wrapper,output,candidate)
            run.contract()
            run.warmup_video()
            run.flat_contract()
            if args.mode != 'smoke': run.collision_contract()
            if args.mode in ('teacher','acceptance'):
                run.teacher(acceptance=args.mode=='acceptance', diagnostic_steps=args.diagnostic_steps,
                    scope=args.teacher_scope,active_wheel=args.active_wheel)
            else:
                run.write('result.json',dict(mode=args.mode, native_contract=True, milestone_a='NOT_RUN'))
            run.write('imported_modules.json',loaded_candidate_modules(candidate))
    except BaseException as exc:
        (output/'failure.json').write_text(json.dumps(dict(type=type(exc).__name__,message=str(exc))),encoding='utf-8')
        raise
    finally:
        if env is not None: env.close()
        launcher.app.close()


def raw_joint_snapshot(robot,row):
    """Actual PhysX joint order, distinct from the action term's named order."""
    return dict(raw_joint_names=list(robot.joint_names),
        joints=robot.data.joint_pos[row].detach().clone().tolist())


class ActionEvidence:
    """Observe the actual term once, before physics and automatic row resets.

    Teacher action is pre-wrapper; executed_action is the term's real input
    (including any wrapper clipping). Targets are read back, never recomputed.
    Their named order uses leg radians and wheel rad/s, as in the mixed term.
    """
    def __init__(self,term,*,decimation=4,sim_time=None):
        if type(decimation) is not int or decimation<1: raise ValueError('positive decimation required')
        self.term=term; self.decimation=decimation; self.sim_time=sim_time
        self.pending=None; self.observing=False
        self.names=list(term._joint_names)
        original=term.process_actions
        def process_hook(action):
            if self.pending is not None and self.observing:
                assert self.processed is None, 'action term must process exactly once'
            result=original(action)
            if self.pending is not None and self.observing:
                self.executed=action.detach().clone().tolist()
                self.processed=term.processed_actions.detach().clone().tolist()
            return result
        term.process_actions=process_hook
        original_apply=getattr(term,'apply_actions',None)
        if original_apply is not None:
            def apply_hook():
                result=original_apply()
                if self.pending is not None and self.observing:
                    assert self.processed is not None, 'apply must follow process'
                    assert len(self.applied)<self.decimation, 'too many action applies'
                    if self.applied: assert self.applied[-1]['physics_seen'], 'apply before prior physics'
                    target=self.read_targets().detach().clone().tolist()
                    if self.applied: assert target==self.applied[0]['targets'], 'targets changed within decimation'
                    self.applied.append(dict(index=len(self.applied),targets=target,
                        sim_time=float(self.sim_time()) if self.sim_time else None,
                        write_seen=False,physics_seen=False))
                return result
            term.apply_actions=apply_hook

    def read_targets(self):
        import torch
        from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
        from extension.parallelism.rl_adapter import resolve_named_indices
        asset=self.term._asset
        if tuple(self.names)!=M1_ASSET_JOINT_NAMES: raise ValueError('actual target action names mismatch')
        ids=resolve_named_indices(tuple(asset.joint_names),self.names)
        position=asset.data.joint_pos_target; velocity=asset.data.joint_vel_target
        if position.shape!=velocity.shape or position.ndim!=2 or position.shape[1]!=len(asset.joint_names):
            raise ValueError('actual target buffer shape mismatch')
        return torch.stack([velocity[:,i] if 'FOOT' in n else position[:,i]
                            for n,i in zip(self.names,ids)],dim=-1).clone()

    def prior_leg_targets(self):
        import torch
        from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES
        from extension.parallelism.rl_adapter import resolve_named_indices
        targets=self.read_targets()
        legs=targets[:,list(resolve_named_indices(self.names,M1_PLANNER_JOINT_NAMES))].clone()
        return legs,torch.isfinite(legs).all(-1)

    def observe_write(self):
        if self.pending is None or not self.observing: return
        assert self.applied and not self.applied[-1]['write_seen'], 'write must follow one action apply'
        assert self.read_targets().tolist()==self.applied[-1]['targets'], 'target changed before simulation write'
        self.applied[-1]['write_seen']=True

    def observe_physics(self):
        if self.pending is None or not self.observing: return
        assert self.applied and self.applied[-1]['write_seen'], 'physics must follow target write'
        assert not self.applied[-1]['physics_seen'], 'extra physics substep'
        assert self.read_targets().tolist()==self.applied[-1]['targets'], 'target changed before physics'
        self.applied[-1]['physics_seen']=True

    def bootstrap_reset(self,mask):
        """Separate no-physics command event; old pending evidence is owned and retained."""
        import torch
        if mask.dtype!=torch.bool or mask.shape!=(self.term.raw_actions.shape[0],):
            raise ValueError('reset mask must be bool [B]')
        before=self.read_targets(); processed=self.term.processed_actions.clone()
        buffers=[self.term._asset.data.joint_pos_target,self.term._asset.data.joint_vel_target]
        before_buffers=[x.clone() for x in buffers]
        raw=self.term.raw_actions.clone(); action=raw.clone(); action[mask]=0.
        old_observing=self.observing; self.observing=False
        start=float(self.sim_time()) if self.sim_time else None
        try:
            self.term.process_actions(action)
            if not torch.equal(processed[~mask].contiguous().view(torch.uint8),
                               self.term.processed_actions[~mask].contiguous().view(torch.uint8)):
                raise RuntimeError('bootstrap changed non-reset processed targets')
            self.term.apply_actions()
            after=self.read_targets()
            if not torch.equal(before[~mask],after[~mask]):
                raise RuntimeError('bootstrap changed non-reset actual targets')
            if any(not torch.equal(a[~mask].contiguous().view(torch.uint8),
                                   b[~mask].contiguous().view(torch.uint8))
                   for a,b in zip(before_buffers,buffers)):
                raise RuntimeError('bootstrap changed non-reset actual target buffers')
            if not torch.equal(after[mask],self.term.processed_actions[mask]):
                raise RuntimeError('bootstrap actual target readback mismatch')
            if not bool(torch.isfinite(after[mask]).all()): raise RuntimeError('nonfinite bootstrap targets')
            if self.sim_time and float(self.sim_time())!=start: raise RuntimeError('bootstrap advanced physics')
            return dict(kind='reset_command_bootstrap',rows=mask.nonzero().flatten().tolist(),
                action=action[mask].tolist(),processed_targets=self.term.processed_actions[mask].clone().tolist(),
                applied_targets=after[mask].tolist(),joint_names=list(self.names),sim_time=start,
                physics_steps=0,process_count=1,apply_count=1,physics_completed=False,
                nonreset_processed_unchanged=True,nonreset_actual_buffers_unchanged=True,
                student_demonstration_usable=False)
        finally: self.observing=old_observing

    def begin(self,state,output,teacher,sim_time):
        self.pending=[]; self.observing=True; self.processed=None; self.executed=None; self.applied=[]
        for row in range(len(state.episode_id)):
            ages=teacher._rows[row] or {}
            requested=None
            if hasattr(state,'default_joint_pos'):
                from ame_baseline.m1_ame_contract import m1_action_targets
                requested=m1_action_targets(output.action[row:row+1],state.default_joint_pos[row:row+1])[0].tolist()
            self.pending.append(dict(teacher_input_frame=int(state.control_step[row]),
                teacher_input_episode_id=int(state.episode_id[row]),teacher_input_sim_time=float(sim_time),
                teacher_action=output.action[row].detach().clone().tolist(),
                requested_processed_targets=requested,
                action_default_joint_pos=state.default_joint_pos[row].detach().clone().tolist()
                    if hasattr(state,'default_joint_pos') else None,
                action_target_dtype=str(state.default_joint_pos.dtype).removeprefix('torch.')
                    if hasattr(state,'default_joint_pos') else None,
                last_applied_leg_target=state.last_applied_leg_target[row].detach().clone().tolist()
                    if hasattr(state,'last_applied_leg_target') else None,
                teacher_diagnostic=diagnostic_json(output.diagnostic[row].tolist())
                    if hasattr(output,'diagnostic') else {},
                active_target=int(output.active_target[row]),
                preparation_input=readiness_measurement(state,row,sim_time),
                teacher_recovery_stable_count=int(ages.get('stable',0)),
                teacher_ages_after_decision={key:int(ages.get(key,-1)) for key in ('age','body_age','lift_age')}))

    def row(self,row,sim_time):
        if self.pending is None: return {}  # Non-teacher contract fixture.
        assert self.processed is not None, 'actual processed targets have not been observed'
        assert len(self.applied)==self.decimation and all(s['physics_seen'] for s in self.applied), 'missing applied physics substeps'
        result=copy.deepcopy(self.pending[row])
        assert math.isclose(sim_time-result['teacher_input_sim_time'],.02,abs_tol=1e-6), 'sample must follow action by 20ms'
        result.update(executed_action=list(self.executed[row]),processed_targets=list(self.processed[row]),
            applied_targets=list(self.applied[0]['targets'][row]),applied_target_joint_names=list(self.names),
            applied_substeps=[dict(s,targets=list(s['targets'][row])) for s in self.applied],
            action_process_count=1,physics_decimation=self.decimation,
            applied_target_valid=all(math.isfinite(v) for v in self.applied[0]['targets'][row]),
            action_matches_request=self.executed[row]==result['teacher_action'] and
                self.applied[0]['targets'][row]==self.processed[row] and
                (result['requested_processed_targets'] is None or
                 result['requested_processed_targets']==self.processed[row]),
            action_joint_names=list(self.names),processed_target_joint_names=list(self.names))
        return result


class NativeProbe:
    """Probe-only observers. Exactly one wrapper.step per 20ms sample."""
    def __init__(self, env, wrapper, output, candidate):
        import torch
        from ame_baseline.m1_teacher_adapter import ReferenceTeacherAdapter, WHEEL_BODY_NAMES
        from ame_baseline.m1_reference_teacher import TeacherConfig
        from extension.parallelism.rl_adapter import resolve_named_indices
        self.torch=torch; self.env=env; self.w=wrapper; self.output=output
        self.robot=env.scene['robot']; self.sensor=env.scene['contact_forces']
        self.raw_joint_names=tuple(self.robot.joint_names)
        self.adapter=ReferenceTeacherAdapter(wrapper); self.teacher_cfg=TeacherConfig()
        self.wheels=list(resolve_named_indices(tuple(self.robot.body_names),WHEEL_BODY_NAMES))
        self.contacts=list(resolve_named_indices(tuple(self.sensor.body_names),WHEEL_BODY_NAMES))
        self.episode=torch.zeros(4,dtype=torch.long,device=env.device)
        self.frames=torch.zeros_like(self.episode); self.attempt=torch.zeros_like(self.episode)
        self.terminal={}; self.recording={}; self.capture={}; self.reset_reason='initial'
        self.support_acquired=torch.zeros(4,dtype=torch.bool,device=env.device)
        self.inner_failed=torch.zeros_like(self.support_acquired)
        self.last_output=None; self.current_stage=0
        self.action_evidence=ActionEvidence(env.action_manager.get_term('JointPositionAction'),
            decimation=env.cfg.decimation,sim_time=lambda:float(env.sim.current_time))
        self.reset_commands=[]; self.scope='course'; self.diagnostic_wheel=None
        self.failure_bound=FailureDiagnosticBound()
        original_write=env.scene.write_data_to_sim
        def write_hook():
            out=original_write(); self.action_evidence.observe_write(); return out
        env.scene.write_data_to_sim=write_hook
        original_physics=env.sim.step
        def physics_hook(*args,**kwargs):
            self.action_evidence.observe_physics()
            return original_physics(*args,**kwargs)
        env.sim.step=physics_hook
        self.tracker_calls=0; self.video_validated=False
        files={str(p.relative_to(candidate)):file_digest(p) for folder in CANDIDATE_DOMAINS
            for p in sorted((candidate/folder).rglob('*.py'))}
        files['scripts/probe_m1_teacher.py']=file_digest(Path(__file__))
        self.write('source.json',dict(candidate=str(candidate),python=sys.executable,files=files,
            code_sha256=digest(files),teacher=asdict(self.teacher_cfg),teacher_hash=self.teacher_cfg.fingerprint,
            loaded_modules=loaded_candidate_modules(candidate),
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
            out=original_reset(ids)
            mask=torch.zeros(4,dtype=torch.bool,device=env.device); mask[ids]=True
            self.bootstrap_reset(mask)
            return out
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

    def bootstrap_reset(self,mask):
        time=float(self.env.sim.current_time); count=self.env.common_step_counter
        record=self.action_evidence.bootstrap_reset(mask)
        assert float(self.env.sim.current_time)==time and self.env.common_step_counter==count
        record.update(control_step=count,previous_episode_id=self.episode[mask].clone().tolist(),
            new_episode_id=None,event_index=len(self.reset_commands),
            identity='post-reset initialization before next episode observation')
        self.reset_commands.append(record); self.write('reset_commands.json',self.reset_commands)

    def bind_reset_identity(self,rows):
        """Bind command events only when the runner assigns the new observed identity."""
        for row in rows:
            for event in reversed(self.reset_commands):
                if row in event['rows']:
                    if event['new_episode_id'] is None: event['new_episode_id']={}
                    event['new_episode_id'][str(row)]=int(self.episode[row])
                    break
        self.write('reset_commands.json',self.reset_commands)

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
        assert len(self.raw_joint_names)==16 and set(self.raw_joint_names)==set(term._joint_names)
        result=dict(joint_names=list(term._joint_names),action_joint_names=list(term._joint_names),
            raw_joint_names=list(self.raw_joint_names),actions=w.num_actions,policy=list(obs.shape),
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
        self.action_evidence.observing=False
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
                    for k in range(3):
                        center=float((bounds.GetMax()[k]+bounds.GetMin()[k])/2)
                        assert abs(center-obj.world_center[k])<2e-4, 'USD/grounded-record world center mismatch'
                    assert abs(size[2]-.10)<2e-4
                    if obj.required_crossing:
                        assert abs(size[0]-.10)<2e-4 and abs(size[1]-.18)<2e-4
                    actual.append(dict(id=obj.slot_index,center=list(obj.world_center),size=size,required=obj.required_crossing))
        if stage==3:
            tile_centers=course_tile_coordinates(terrain,course)
            for row in range(4):
                valid=course['valid'][row]
                authored=sorted([r for r in records if r.row==stage and
                    r.col==int(terrain.terrain_types[row]) and r.required_crossing],key=lambda r:r.slot_index)
                world_top=t.tensor([[*obj.world_center[:2],obj.world_center[2]+obj.shape_params['size'][2]/2]
                    for obj in authored],device=self.env.device)
                t.testing.assert_close(course['centers_top'][row,valid],world_top,atol=2e-4,rtol=0)
                centers=tile_centers[row,valid]
                t.testing.assert_close(centers[:,0],t.arange(8,device=self.env.device)*1.1-1.2,atol=2e-4,rtol=0)
                assert bool((centers[:,1].abs()-.215).abs().max()<2e-4)
                assert bool((centers[:,2]-.10).abs().max()<2e-4)
        self.write(f'terrain_stage{stage}.json',dict(levels=terrain.terrain_levels.tolist(),
            types=terrain.terrain_types.tolist(),geometry=actual,course_ids=course['ids'].tolist(),
            tile_origins=terrain.terrain_origins[terrain.terrain_levels,terrain.terrain_types].tolist(),
            spawn_origins=self.env.scene.env_origins.tolist(),
            required=required.tolist(),sha256=digest(actual)))
        print('TERRAIN_CONTRACT '+json.dumps(dict(stage=stage,levels=terrain.terrain_levels.tolist(),
            types=terrain.terrain_types.tolist(),targets=8 if stage else 0,fill=70 if stage else 0,
            height=.10 if stage else 0,geometry_sha256=digest(actual))),flush=True)

    def render_row(self,row,*,visible=True):
        import numpy as np
        robot=self.robot
        before=float(self.env.sim.current_time)
        try:
            robot.set_visibility(False,env_ids=list(range(4)))
            if visible: robot.set_visibility(True,env_ids=[row])
            root=robot.data.root_pos_w[row].detach().cpu().numpy()
            self.env.sim.set_camera_view(eye=(root+np.array([2.,2.,1.4])).tolist(),target=root.tolist())
            # Bounded render-only settling after visibility/camera changes.
            # The probe disables temporal AA/frame generation before launch.
            for _ in range(3): self.env.sim.render()
            rgb=self.env.render().copy()
            assert rgb.ndim==3 and rgb.shape[2]>=3 and np.isfinite(rgb).all()
            assert math.isclose(before,float(self.env.sim.current_time),abs_tol=1e-8)
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
        restored=self.render_row(0)
        difference=float(np.abs(visible.astype(float)-hidden.astype(float)).mean())
        restored_difference=float(np.abs(restored.astype(float)-hidden.astype(float)).mean())
        roundtrip_difference=float(np.abs(visible.astype(float)-restored.astype(float)).mean())
        assert visible.std()>2 and visible.max()>30, 'black or empty camera'
        assert difference>.05, 'robot visibility not reflected by renderer/Fabric'
        assert restored_difference>.05, 'robot visibility did not restore after hiding'
        assert roundtrip_difference<1., 'visible-hidden-visible render did not settle'
        assert math.isclose(before,float(self.env.sim.current_time),abs_tol=1e-8)
        imageio.imwrite(self.output/'video_warmup_visible.png',visible)
        imageio.imwrite(self.output/'video_warmup_hidden.png',hidden)
        imageio.imwrite(self.output/'video_warmup_restored.png',restored)
        self.video_validated=True
        self.write('video_warmup.json',dict(nonblack=True,isolated_robot=True,
            visibility_image_difference=difference,restored_image_difference=restored_difference,
            visible_roundtrip_difference=roundtrip_difference,physics_time_unchanged=True,
            antialiasing_mode=self.env.cfg.sim.render.antialiasing_mode,
            enable_dlssg=self.env.cfg.sim.render.enable_dlssg,settle_render_frames=3))

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
        if hasattr(self,'action_evidence') and self.action_evidence.pending is not None:
            assert len(self.action_evidence.applied)==env.cfg.decimation
            assert all(x['physics_seen'] for x in self.action_evidence.applied)
            self.action_evidence.observing=False
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
        targets,valid=self.action_evidence.prior_leg_targets()
        return self.adapter.snapshot(control_step=self.frames,episode_id=self.episode,
            reset_mask=t.zeros_like(collision) if reset is None else reset,collision=collision,
            last_applied_leg_target=targets,applied_target_valid=valid)

    @staticmethod
    def pairs(ids,mask):
        return [[int(ids[slot]),int(wheel)] for slot,wheel in mask.nonzero().tolist()]

    def sample(self,row):
        from ame_baseline.m1_collision_budget import current_collision_snapshot
        from ame_baseline.m1_reference_geometry import cylinder_bottom
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
            witness=cylinder_penetration_witness(position.expand(top.shape[0],-1,-1),
                quat.expand(top.shape[0],-1,-1),top,half,radius=.0959,thickness=.0465)
            penetration=bool(witness.any())
        snap=current_collision_snapshot(env)
        output=self.last_output
        failures={name:bool(env.termination_manager.get_term(name)[row])
            for name in env.termination_manager.active_terms}
        timeout=bool(env.termination_manager.time_outs[row])
        failure=bool(env.termination_manager.terminated[row]) or bool(self.inner_failed[row])
        action=self.action_evidence.row(row,float(env.sim.current_time))
        action['preparation_output']=readiness_measurement(self.state(),row,float(env.sim.current_time))
        locked=bool(output.failure_locked[row]) if output is not None else False
        return dict(schema_version=SCHEMA_VERSION,teacher_scope=self.scope,
            diagnostic_active_wheel=self.diagnostic_wheel,failure_locked=locked,
            student_demonstration_usable=bool(output is not None and output.valid[row]
                and not locked and action.get('action_matches_request',False) and self.scope=='course'),
            env_id=row,episode_id=int(self.episode[row]),attempt_id=int(self.attempt[row]),
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
            root=self.robot.data.root_state_w[row].tolist(),**raw_joint_snapshot(self.robot,row),
            course_ids=ids.tolist(),**action)

    def begin_video(self,row,seed,stage):
        import imageio.v2 as imageio
        stem=f'stage{stage}_seed{seed}_env{row}_episode{int(self.episode[row])}'
        path=self.output/(stem+'.mp4')
        self.recording[row]=dict(writer=imageio.get_writer(str(path),fps=10,codec='libx264'),
            path=path,indices=[],times=[],samples=[],seed=seed,stage=stage,
            initial_root=self.robot.data.root_pos_w[row].tolist(),command_distance=0.,
            initial_wheel_z=float(self.robot.data.body_pos_w[row,self.wheels[self.diagnostic_wheel or 0],2]),
            measured_lift_seen=False,local_recovery_count=0,
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
        result=dict(schema_version=SCHEMA_VERSION,teacher_scope=self.scope,
            diagnostic_active_wheel=self.diagnostic_wheel,
            stage=rec['stage'],seed=rec['seed'],env_id=row,episode_id=int(self.episode[row]),
            raw_joint_names=list(self.raw_joint_names),
            teacher_config=asdict(self.teacher_cfg),teacher_hash=self.teacher_cfg.fingerprint,
            required=required,samples=rec['samples'],terminal=rec['samples'][-1],video=video,
            initial_root=rec['initial_root'],command_distance=rec['command_distance'],
            end=end,natural_done=natural,timeout=timeout)
        trace_path=self.output/(rec['path'].stem+'.jsonl')
        result['trace']=dict(path=str(trace_path),sha256=file_digest(trace_path),bytes=trace_path.stat().st_size)
        result['verification']=verify_episode(result)
        result['student_demonstration_usable']=result['verification']['student_demonstration_usable']
        self.write(rec['path'].stem+'.json',result)
        del self.recording[row]
        return result

    def reset_row(self,row):
        t=self.torch; mask=t.zeros(4,dtype=t.bool,device=self.env.device); mask[row]=True
        self.action_evidence.observing=False
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

    def teacher(self,*,acceptance,diagnostic_steps,scope='course',active_wheel=None):
        from ame_baseline.m1_reference_teacher import ReferenceTeacher,Phase
        validate_scope(scope,acceptance=acceptance,active_wheel=active_wheel)
        self.scope=scope
        records=[]; t=self.torch
        schedule=teacher_schedule(scope,active_wheel)
        gate=DiagnosticBatchGate(acceptance); batch_step=0
        try:
            for schedule_index,(stage,wheel) in enumerate(schedule):
                self.diagnostic_wheel=wheel
                for seed in (range(101,106) if acceptance else [101]):
                    self.env.seed(seed); self.set_stage(stage)
                    teacher=ReferenceTeacher(self.teacher_cfg)
                    self.episode.fill_(wheel or 0); self.frames.zero_(); self.attempt.zero_()
                    self.bind_reset_identity(range(4))
                    self.failure_bound=FailureDiagnosticBound()
                    quotas=[5]*4 if acceptance else [1]*4
                    batch_start=len(records)
                    required=[self.pairs(self.state().course_ids[i],self.state().required_wheels[i]) for i in range(4)]
                    def decide(state):
                        return teacher.step(state) if wheel is None else teacher.diagnostic_step(
                            state,active_wheel=wheel,lift=scope=='single-wheel')
                    # Initialize identity without executing an invalid RESET label.
                    self.frames.fill_(-1)
                    decide(self.state(reset=t.ones(4,dtype=t.bool,device=self.env.device)))
                    self.frames.zero_()
                    for row in range(4): self.begin_video(row,seed,stage)
                    while self.recording:
                        batch_step+=1
                        input_time=float(self.env.sim.current_time)
                        input_state=self.state()
                        self.last_output=decide(input_state)
                        self.action_evidence.begin(input_state,self.last_output,teacher,input_time)
                        command=self.env.command_manager.get_command('base_velocity')[:,0]
                        for row,rec in self.recording.items(): rec['command_distance']+=float(command[row])*.02
                        _,_,done,_=self.step(self.last_output.action)
                        # Freeze and inspect the whole batch before ending/resetting
                        # any row, so env ordering cannot hide a peer failure.
                        batch_samples={row:self.terminal.get(row) if bool(done[row]) else self.sample(row)
                            for row in list(self.recording)}
                        for sample in batch_samples.values():
                            assert sample is not None, 'natural terminal snapshot lost before reset'
                            gate.observe_sample(sample,batch_step)
                        for row,sample in batch_samples.items():
                            rec=self.recording[row]; rec['samples'].append(sample)
                            diagnostic=sample.get('teacher_diagnostic',{})
                            reference_valid=diagnostic.get('reference_valid')==1
                            local_complete=False
                            if scope=='flat-preparation':
                                local_complete=preparation_observed(sample,self.teacher_cfg)
                            elif scope=='single-wheel':
                                # Measured rise/unloading, then five real loaded, quiet
                                # RESTORE observations. These are local evidence only.
                                raised=sample['wheel_position'][wheel][2]>rec['initial_wheel_z']+.01
                                rec['measured_lift_seen'] |= raised and sample['Fz'][wheel]<=self.teacher_cfg.support_min_force_n
                                quiet=(sum(x*x for x in sample['root'][7:10])**.5<=self.teacher_cfg.balance_speed_limit_m_s
                                    and sum(x*x for x in sample['root'][10:12])**.5<=self.teacher_cfg.recovery_rate_rad_s)
                                restored=(reference_valid and sample['phase']==int(Phase.RESTORE)
                                    and all(x>self.teacher_cfg.support_min_force_n for x in sample['Fz'])
                                    and sample['wheel_position'][wheel][2]<=rec['initial_wheel_z']+.002
                                    and quiet and not any(sample[k] for k in ('collision','support_lost','penetration','failure')))
                                rec['local_recovery_count']=rec['local_recovery_count']+1 if restored else 0
                                local_complete=(rec['measured_lift_seen'] and rec['local_recovery_count']>=5
                                    and sample.get('teacher_recovery_stable_count',0)>=self.teacher_cfg.stable_samples)
                            elif scope in ('first-obstacle','transitions'):
                                ids=[]
                                for target,_ in required[row]:
                                    if target not in ids: ids.append(target)
                                needed=set(ids[:1 if scope=='first-obstacle' else 2])
                                subset={tuple(p) for p in required[row] if p[0] in needed}
                                local_complete=bool(subset and subset<={tuple(p) for p in sample['far_side_recovery']})
                            local_complete=bool(local_complete and not sample['failure_locked'] and
                                sample.get('action_matches_request',False) and
                                not any(sample[k] for k in ('collision','support_lost','penetration','failure')))
                            sample['scope_observation_complete']=local_complete
                            sample['measured_local_lift_seen']=bool(rec['measured_lift_seen'])
                            sample['local_recovery_count']=int(rec['local_recovery_count'])
                            complete=(scope=='course' and stage==3 and len(required[row])==16 and
                                {tuple(p) for p in required[row]} <= {tuple(p) for p in sample['receipt']} and
                                {tuple(p) for p in required[row]} <= {tuple(p) for p in sample['far_side_recovery']})
                            horizon=scope=='course' and stage==0 and int(self.frames[row])==1000
                            failure_end=self.failure_bound.update(row,sample['failure_locked'])
                            diagnostic_end=not acceptance and int(self.frames[row])>=diagnostic_steps
                            batch_end=gate.deadline(batch_step)
                            ending=bool(done[row]) or complete or horizon or diagnostic_end or failure_end or local_complete or batch_end
                            end=None
                            if ending:
                                end='flat_horizon' if horizon else ('natural_done' if bool(done[row]) else
                                    ('teacher_failure_locked' if failure_end else 'task_complete' if complete else
                                     'scope_observed' if local_complete else 'diagnostic_bound' if diagnostic_end else
                                     'diagnostic_failure' if gate.is_source(sample) or gate.sample_reason(sample) else 'diagnostic_interrupted'))
                                gate.observe_end(sample,end,batch_step)
                                if gate.failure is not None and not gate.is_source(sample) and not gate.sample_reason(sample):
                                    end='diagnostic_interrupted'
                                    sample['diagnostic_interruption']=copy.deepcopy(gate.failure)
                            rec['trace'].write(json.dumps(sample)+'\n'); rec['trace'].flush()
                            if int(self.frames[row])%5==0 and not bool(done[row]): self.video_frame(row)
                            if ending:
                                record=self.finish_episode(row,required[row],end,bool(done[row]),sample['timeout'])
                                gate.observe_record(record,batch_step)
                                records.append(record); quotas[row]-=1
                                print('TEACHER_EPISODE '+json.dumps({k:v for k,v in record.items() if k not in ('samples','terminal','video')}),flush=True)
                                if quotas[row]>0:
                                    if not bool(done[row]): self.reset_row(row)
                                    self.episode[row]+=1; self.frames[row]=0; self.attempt[row]=0
                                    self.bind_reset_identity([row])
                                    self.support_acquired[row]=False; self.inner_failed[row]=False
                                    self.failure_bound.reset(row)
                                    # Teacher sees identity change at synthetic pre-control -1 only.
                                    mask=t.zeros(4,dtype=t.bool,device=self.env.device); mask[row]=True
                                    saved=self.frames.clone(); self.frames[row]=-1
                                    decide(self.state(reset=mask)); self.frames.copy_(saved)
                                    self.begin_video(row,seed,stage)
                    if gate.failure is not None:
                        # Includes peers already finished before a later artifact
                        # error. Update only the summary; trace/video stay intact.
                        for record in records[batch_start:]:
                            changed=False
                            if gate.is_source(record['terminal']) and gate.failure['reason']=='evidence_invalid':
                                record.update(end='diagnostic_evidence_failure',
                                    diagnostic_failure=copy.deepcopy(gate.failure),student_demonstration_usable=False)
                                changed=True
                            elif (not gate.is_source(record['terminal']) and not record['verification']['errors']
                                    and not any(gate.sample_reason(sample) for sample in record['samples'])):
                                record.update(end='diagnostic_interrupted',
                                    diagnostic_interruption=copy.deepcopy(gate.failure),student_demonstration_usable=False)
                                changed=True
                            if changed:
                                record['verification']=verify_episode(record)
                                self.write(Path(record['video']['path']).stem+'.json',record)
                    result=verify_suite(records,diagnostic=not acceptance)
                    result.update(diagnostic_stopped=gate.failure is not None,
                        diagnostic_stop=copy.deepcopy(gate.failure),
                        not_run=[dict(stage=s,wheel=w,scope=scope,status='not_run',reason='prior_diagnostic_stop')
                            for s,w in schedule[schedule_index+1:]] if gate.failure is not None else [])
                    self.write('result.json',result)
                    if gate.failure is not None:
                        print('MILESTONE_A '+json.dumps(result),flush=True)
                        return result
            print('MILESTONE_A '+json.dumps(result),flush=True)
            return result
        finally:
            for rec in self.recording.values():
                rec['writer'].close(); rec['trace'].close()


if __name__ == '__main__': main()
