"""Candidate-only native teacher evidence. No training or production writes.

The pure verifier imports no simulator. Native entry imports AppLauncher before
Isaac/pxr/omni. A diagnostic run can never report milestone A PASS.
"""
import argparse
import copy
from collections import Counter
from dataclasses import asdict, fields
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
SCHEMA_VERSION = 7
TEACHER_SCOPES = ('flat-preparation','single-wheel','first-obstacle','transitions','course')
APPLY_KEYS = {'schema_version','teacher_scope','failure_locked','student_demonstration_usable',
    'applied_targets','applied_target_joint_names','applied_substeps','action_process_count',
    'physics_decimation','action_matches_request','applied_target_valid','teacher_diagnostic',
    'last_applied_leg_target','requested_processed_targets','action_default_joint_pos','action_target_dtype','teacher_executable',
    'actuation_evidence','feedback_context','selection_context'}


def recovery_json(value):
    return {field.name: (getattr(value,field.name).detach().cpu().tolist()
        if hasattr(getattr(value,field.name),'detach') else list(getattr(value,field.name)))
        for field in fields(value)}


def recovery_raw_types(value, scalar_types):
    """Reject coercion of untrusted JSON identity/boolean measurements."""
    if isinstance(value,list): return all(recovery_raw_types(item,scalar_types) for item in value)
    return type(value) in scalar_types


def recovery_pairs(required, scope):
    """Freeze diagnostic obligations once; retain the full old course contract."""
    ids=list(dict.fromkeys(target for target,_ in required))
    if scope in ('flat-preparation','single-wheel'): return []
    if scope=='first-obstacle': ids=ids[:1]
    elif scope=='transitions': ids=ids[:2]
    return [pair for pair in required if pair[0] in ids]


def capture_recovery_scope(state: 'TeacherState', rows: 'Tensor', required_pairs: list,
        *, scope_ids: 'Tensor') -> 'RecoveryScope':
    from ame_baseline.m1_crossing_recovery import RecoveryScope, CrossingRecoveryTracker
    import torch
    if rows.dtype==torch.bool: rows=rows.nonzero().flatten()
    if (rows.dtype!=torch.long or rows.ndim!=1 or rows.unique().numel()!=rows.numel()
            or len(required_pairs)!=rows.numel() or scope_ids.shape!=rows.shape):
        raise ValueError('recovery scope rows/identity mismatch')
    selected=[]; masks=[]
    for row,pairs in zip(rows.tolist(),required_pairs):
        ids=list(dict.fromkeys(target for target,_ in pairs))
        actual={}
        for index in state.course_valid[row].nonzero().flatten().tolist():
            target=int(state.course_ids[row,index])
            if target<0 or target in actual: raise ValueError('ambiguous course identity')
            actual[target]=index
        indices=[]; mask=torch.zeros(len(ids),4,dtype=torch.bool,device=rows.device)
        for col,target in enumerate(ids):
            if target not in actual: raise ValueError('missing course identity')
            index=actual[target]
            indices.append(index)
            for pair_target,wheel in pairs:
                if pair_target==target:
                    if wheel not in range(4) or not bool(state.required_wheels[row,index,wheel]):
                        raise ValueError('scope obligation differs from actual course')
                    mask[col,wheel]=True
        selected.append(torch.tensor(indices,dtype=torch.long,device=rows.device)); masks.append(mask)
    if len({len(indices) for indices in selected})>1: raise ValueError('scope subbatch needs equal course counts')
    # The simulator clock is double precision. Promote measured float32 values
    # exactly for the outcome path so long-running global clocks keep real dt.
    quat=state.root_quat_w[rows].double()
    quat=quat/quat.norm(dim=-1,keepdim=True)
    w,x,y,z=quat.unbind(-1)
    yaw=torch.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
    forward=torch.stack((torch.cos(yaw),torch.sin(yaw),torch.zeros_like(yaw)),-1)
    scope=RecoveryScope(env_id=rows.clone(),episode_id=state.episode_id[rows].clone(),scope_id=scope_ids.clone(),
        course_ids=torch.stack([state.course_ids[row,indices] for row,indices in zip(rows.tolist(),selected)]),
        required=torch.stack(masks),centers_w=torch.stack([state.centers_top[row,indices] for row,indices in zip(rows.tolist(),selected)]).double(),
        half_extents=torch.stack([state.half_extents[row,indices] for row,indices in zip(rows.tolist(),selected)]).double(),forward_w=forward)
    # Validate the complete captured interface, and clone away from live buffers.
    CrossingRecoveryTracker(scope)
    return scope


def recovery_scope_from_json(raw):
    import torch
    from ame_baseline.m1_crossing_recovery import RecoveryScope
    if set(raw)!={f.name for f in fields(RecoveryScope)}|{'dtype'} or raw['dtype'] not in ('float32','float64'):
        raise ValueError('missing recovery scope fields/dtype')
    for field in fields(RecoveryScope):
        types=(int,) if field.name in ('env_id','episode_id','scope_id','course_ids') else (
            (bool,) if field.name=='required' else (float,int))
        if not recovery_raw_types(raw[field.name],types): raise ValueError('invalid raw recovery scope type')
    dtype=getattr(torch,raw['dtype']); n=len(raw['env_id']); c=len(raw['course_ids'][0])
    values={f.name:torch.tensor(raw[f.name],dtype=torch.long if f.name in
        ('env_id','episode_id','scope_id','course_ids') else torch.bool if f.name=='required' else dtype)
        for f in fields(RecoveryScope)}
    for name,shape in (('course_ids',(n,c)),('required',(n,c,4)),('centers_w',(n,c,3)),('half_extents',(n,c,2))):
        values[name]=values[name].reshape(shape)
    return RecoveryScope(**values)


def capture_recovery_frame(snapshot: dict, scope: 'RecoveryScope') -> 'RecoveryFrame':
    """Explicitly map actual course IDs to the frozen scope before consumption."""
    import torch
    from ame_baseline.m1_crossing_recovery import RecoveryFrame
    names={f.name for f in fields(RecoveryFrame)}
    if set(snapshot)!=names|{'course_ids'}: raise ValueError('missing raw recovery frame fields')
    dtype=scope.centers_w.dtype; device=scope.centers_w.device; n=len(scope.env_id)
    values={}
    booleans={'valid','collision','penetration','base_contact','physical_failure','reset','ended','recovered'}
    integers={'env_id','episode_id','scope_id','frame'}
    for name in names|{'course_ids'}:
        types=(int,) if name in integers|{'course_ids'} else (bool,) if name in booleans else (float,int)
        if not recovery_raw_types(snapshot[name],types): raise ValueError('invalid raw recovery frame type')
    for name in names-{'recovered'}:
        values[name]=torch.tensor(snapshot[name],dtype=torch.long if name in integers else
            torch.bool if name in booleans else dtype,device=device)
    mapped=torch.zeros_like(scope.required)
    if len(snapshot['course_ids'])!=n or len(snapshot['recovered'])!=n: raise ValueError('course identity batch mismatch')
    for row in range(n):
        actual=snapshot['course_ids'][row]; recovered=snapshot['recovered'][row]
        if (len(set(actual))!=len(actual) or len(recovered)!=len(actual)
                or any(len(mask)!=4 or any(type(flag) is not bool for flag in mask) for mask in recovered)):
            raise ValueError('ambiguous actual receipt identity')
        for col,target in enumerate(scope.course_ids[row].tolist()):
            if target not in actual: raise ValueError('missing actual course identity')
            mapped[row,col]=torch.tensor(recovered[actual.index(target)],dtype=torch.bool,device=device)
    values['recovered']=mapped
    return RecoveryFrame(**values)


def recovery_input_from_sample(sample, scope):
    from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES, M1_ASSET_JOINT_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    columns=resolve_named_indices(sample['raw_joint_names'],M1_PLANNER_JOINT_NAMES)
    defaults=resolve_named_indices(M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES)
    flags=('measurement_valid','teacher_executable','action_matches_request','applied_target_valid',
        'failure_locked','collision','penetration','base_contact','failure','support_lost','timeout')
    if (any(type(sample[key]) is not bool for key in flags)
            or type(sample['actuation_evidence']['valid']) is not bool
            or type(sample.get('natural_done',False)) is not bool):
        raise ValueError('invalid raw recovery boolean measurement')
    if sample['default_leg_pos']!=[sample['action_default_joint_pos'][i] for i in defaults]:
        raise ValueError('recovery defaults differ from actual default joint pose')
    if len(sample['course_ids'])!=len(sample['course_valid']): raise ValueError('course validity/identity mismatch')
    ids=[target for target,valid in zip(sample['course_ids'],sample['course_valid']) if valid]
    for key in ('receipt','far_side_recovery'):
        pairs=sample[key]
        if (not isinstance(pairs,list) or any(not isinstance(pair,list) or len(pair)!=2
                or any(type(value) is not int for value in pair) for pair in pairs)):
            raise ValueError('invalid raw receipt identity')
    receipts={tuple(pair) for pair in sample['receipt']}
    far={tuple(pair) for pair in sample['far_side_recovery']}
    if (any(type(target) is not int or target<0 for target in ids) or len(set(ids))!=len(ids)
            or any(type(target) is not int or type(wheel) is not int or target not in ids or wheel not in range(4)
                for target,wheel in receipts|far)):
        raise ValueError('receipt identity does not match measured course')
    if not far<=receipts: raise ValueError('far-side recovery lacks same-frame receipt')
    return dict(env_id=[sample['env_id']],episode_id=[sample['episode_id']],scope_id=scope.scope_id.tolist(),
        frame=[sample['frame']],sim_time_s=[sample['sim_time']],dt_s=[sample['control_dt_s']],
        root_state_w=[sample['root']],leg_pos=[[sample['joints'][i] for i in columns]],
        default_leg_pos=[sample['default_leg_pos']],wheel_pos_w=[sample['wheel_position']],
        wheel_quat_w=[sample['wheel_quaternion']],wheel_force_w=[sample['force']],
        nominal_root_z_w=[sample['nominal_root_z_w']],course_ids=[ids],
        recovered=[[[ (target,wheel) in far for wheel in range(4)] for target in ids]],
        valid=[bool(sample['measurement_valid'] and sample['teacher_executable'] and
            sample['action_matches_request'] and sample['applied_target_valid'] and
            sample['actuation_evidence']['valid'] and not sample['failure_locked'])],
        collision=[sample['collision']],penetration=[sample['penetration']],base_contact=[sample['base_contact']],
        physical_failure=[sample['failure'] or sample['support_lost']],reset=[False],
        ended=[bool(sample.get('natural_done',False) or sample['timeout'])])


def recovery_result_matches(actual, recorded):
    if set(actual)!=set(recorded): return False
    for key,want in actual.items():
        got=recorded[key]
        if not isinstance(got,list) or len(got)!=len(want): return False
        for a,b in zip(want,got):
            if isinstance(a,float):
                if not isinstance(b,(float,int)) or isinstance(b,bool): return False
                if math.isnan(a) and math.isnan(b): continue
                if not math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-7): return False
            elif type(a)!=type(b) or a!=b: return False
    return True


def verify_recovery_record(record: dict) -> list[str]:
    """Replay every raw observation; cached success never grants completion."""
    from ame_baseline.m1_crossing_recovery import CrossingRecoveryTracker, RECOVERY_CONTRACT
    import torch
    errors=[]
    try:
        if record['recovery_contract']!=RECOVERY_CONTRACT or record['schema_version']!=SCHEMA_VERSION:
            raise ValueError('incompatible recovery contract')
        scope=recovery_scope_from_json(record['recovery_scope']); tracker=CrossingRecoveryTracker(scope)
        if scope.env_id.tolist()!=[record['env_id']] or scope.episode_id.tolist()!=[record['episode_id']]:
            raise ValueError('recovery scope episode identity mismatch')
        required={(int(target),wheel) for target,mask in zip(scope.course_ids[0].tolist(),scope.required[0].tolist())
            for wheel,needed in enumerate(mask) if needed}
        if required!={tuple(pair) for pair in recovery_pairs(record['required'],record['teacher_scope'])}:
            raise ValueError('recovery scope obligations changed')
        quat=record['initial_root_quat_w']; norm=math.sqrt(sum(value*value for value in quat))
        if not math.isfinite(norm) or norm==0: raise ValueError('invalid fixed recovery direction')
        w,x,y,z=[value/norm for value in quat]
        yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
        if any(not math.isclose(a,b,abs_tol=1e-6) for a,b in zip(scope.forward_w[0].tolist(),[math.cos(yaw),math.sin(yaw),0.])):
            raise ValueError('fixed recovery direction changed')
        for sample in record['samples']:
            raw=sample['recovery_input']
            expected=recovery_input_from_sample(sample,scope)
            if sample['nominal_root_z_w']!=record['recovery_nominal_root_z_w']:
                raise ValueError('nominal recovery height changed during the episode')
            if not same_json_evidence(raw,expected): raise ValueError('raw recovery input differs from actual sample')
            for col,target in enumerate(scope.course_ids[0].tolist()):
                index=sample['course_ids'].index(target)
                if (not sample['course_valid'][index] or
                        not torch.equal(torch.tensor(sample['course_centers_top'][index],dtype=scope.centers_w.dtype),scope.centers_w[0,col]) or
                        not torch.equal(torch.tensor(sample['course_half_extents'][index],dtype=scope.centers_w.dtype),scope.half_extents[0,col])):
                    raise ValueError('frozen recovery geometry changed')
            result=recovery_json(tracker.update(capture_recovery_frame(raw,scope)))
            if not recovery_result_matches(result,sample['recovery_result']):
                raise ValueError('cached recovery result differs from replay')
        final=result['success']==[True]
        if record['teacher_scope'] in ('flat-preparation','single-wheel') and final:
            raise ValueError('local diagnostic cannot claim whole-body recovery')
        if record['end'] in ('task_complete','scope_observed') and record['stage']==3 and not final:
            raise ValueError('completion lacks measured recovery window')
    except (KeyError,ValueError,TypeError,IndexError,RuntimeError,UnboundLocalError):
        errors.append('missing or inconsistent measured recovery evidence')
    return errors


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


class PreparationHoldCounter:
    """Probe-only first ready sample plus five consecutive additional frames."""
    def __init__(self): self.rows={}
    def update(self,row,*,input_ready,output_ready,frame,episode_id):
        old=self.rows.get(row)
        if old and old[0]==episode_id and old[1]==frame: return old[2]>=6
        ready=bool(input_ready and output_ready)
        count=(old[2]+1 if old and old[0]==episode_id and old[1]+1==frame else 1) if ready else 0
        self.rows[row]=(episode_id,frame,count)
        return count>=6
    def reset(self,row): self.rows.pop(row,None)


def pose_context(reference):
    if reference is None: return None
    return dict(root=reference.body.pos_w[0].detach().clone().tolist()+
        reference.body.quat_w[0].detach().clone().tolist(),wheels=reference.wheels_w[0].detach().clone().tolist())


def prepare_feedback_context(teacher,state):
    """Expire only rows whose episode/frame changed; preserve duplicate decisions.

    A quota reset evaluates the whole real Teacher batch and may compute/cache
    a live peer's next decision. That peer's context belongs to its cached
    output and must survive the following same-frame normal decide call.
    """
    contexts=teacher._probe_feedback_context
    identities=teacher._probe_feedback_context_identity
    resets=getattr(state,'reset_mask',None)
    for row in range(len(state.episode_id)):
        identity=(int(state.episode_id[row]),int(state.control_step[row]))
        if identities.get(row)!=identity or resets is not None and bool(resets[row]):
            contexts.pop(row,None)
            identities[row]=identity


def feedback_context_for(teacher,state,row):
    identity=(int(state.episode_id[row]),int(state.control_step[row]))
    resets=getattr(state,'reset_mask',None)
    if resets is not None and bool(resets[row]): return None
    if getattr(teacher,'_probe_feedback_context_identity',{}).get(row)!=identity: return None
    return copy.deepcopy(getattr(teacher,'_probe_feedback_context',{}).get(row))


def observe_feedback_transactions(teacher):
    """Read-only probe observer of the real bounded transaction's minimal inputs.

    No alternate controller: the original bound method runs once unchanged.
    Context is an owned JSON snapshot (not a reference to the mutable row).
    """
    teacher._probe_feedback_context={}
    teacher._probe_feedback_context_identity={}
    original=getattr(teacher,'_feedback_transaction',None)
    if original is None: return  # CPU lifecycle fixture without a controller.
    def observed(s,i,work,accepted,requested,q,branch,nominal,evidence):
        teacher._probe_feedback_context_identity[i]=(int(s.episode_id[i]),int(s.control_step[i]))
        take=lambda value:value.detach().clone().reshape(-1).tolist()
        teacher._probe_feedback_context[i]=dict(accepted_before=pose_context(accepted),
            retained_physical=pose_context(work.get('accepted')),
            retained_command=pose_context(work.get('accepted_command')),
            requested=pose_context(requested),q_seed=take(q),branch_q=take(branch),
            measured_root=take(s.root_pos_w[i]),captured_yaw=take(work.get('yaw',q.new_zeros(1)))[0],
            measured_quat=take(s.root_quat_w[i]),execution_enabled=bool(evidence.get('execution_enabled',False)),
            integral_before=take(work['feedback'].integral),output_before=take(work['feedback'].output),
            active=bool(work['prepared'] and int(work['phase'])!=0),dt=float(s.dt[i]),
            nominal_speed=take(nominal),last_applied_q=take(s.last_applied_leg_target[i]),
            default_joint_pos=take(s.default_joint_pos[i]),
            retained_q=take(teacher._rows[i]['last_q']) if teacher._rows[i].get('last_q') is not None else None,
            retained_branch_q=take(teacher._rows[i]['branch_q']) if teacher._rows[i].get('branch_q') is not None else None,
            control_phase=int(work['phase']),active_wheel=int(work.get('wheel',-1)),
            wheel_anchor=work['wheel_anchor'].detach().clone().tolist()[0] if work.get('wheel_anchor') is not None else None,
            measured_wheels=s.wheel_pos_w[i].detach().clone().tolist())
        if teacher.cfg.load_feedback and 'support_load_proposal' in work:
            teacher._probe_feedback_context[i]['load_feedback']=dict(
                previous=take(work.get('support_load_offset',q.new_zeros(1,4))),
                proposed=take(work['support_load_proposal']),
                fractions=take(work.get('support_load_fractions',q.new_zeros(1,3))),
                geometry_valid=bool(work['support_load_geometry_valid'][0]) if 'support_load_geometry_valid' in work else False,
                raw=take(s.wheel_force_w[i,:,2]),restore=int(work['phase'])==4)
            if 'attitude_error' in evidence:
                teacher._probe_feedback_context[i]['load_feedback']['attitude']=dict(
                    command=pose_context(evidence['attitude_command']),error=take(evidence['attitude_error']),
                    error0=take(evidence['attitude_error0']),delta=take(evidence['attitude_delta']),
                    previous=take(work['support_attitude_error0']) if 'support_attitude_error0' in work else None)
            teacher._probe_feedback_context[i]['support_height_previous']=(
                take(work['support_execution_z']) if 'support_execution_z' in work else None)
            for key in ('support_heave','support_heave_error0','support_capture_root_z'):
                teacher._probe_feedback_context[i][key+'_previous']=take(work[key]) if key in work else None
        return original(s,i,work,accepted,requested,q,branch,nominal,evidence)
    teacher._feedback_transaction=observed


def _dynamic_pack(value):
    """JSON-only owned snapshot; no pickle or executable class names."""
    import torch
    from dataclasses import is_dataclass
    if isinstance(value, torch.Tensor):
        return dict(tensor=value.detach().cpu().tolist(), dtype=str(value.dtype).removeprefix('torch.'))
    if is_dataclass(value):
        return dict(kind=type(value).__name__, values={f.name:_dynamic_pack(getattr(value,f.name)) for f in fields(value)})
    if isinstance(value, dict):
        return {k:_dynamic_pack(v) for k,v in value.items() if k!='output'}
    return int(value) if hasattr(value,'name') and isinstance(value,int) else value


def _dynamic_unpack(value, device):
    import torch
    from ame_baseline.m1_teacher_pose import BodyPose, PoseReference
    from ame_baseline.m1_teacher_feedback import FeedbackState
    if not isinstance(value,dict): return value
    if set(value)=={'tensor','dtype'}:
        dtypes=dict(float32=torch.float32,float64=torch.float64,int64=torch.int64,bool=torch.bool)
        return torch.tensor(value['tensor'],dtype=dtypes[value['dtype']],device=device)
    if set(value)=={'kind','values'}:
        classes=dict(BodyPose=BodyPose,PoseReference=PoseReference,FeedbackState=FeedbackState)
        return classes[value['kind']](**{k:_dynamic_unpack(v,device) for k,v in value['values'].items()})
    return {k:_dynamic_unpack(v,device) for k,v in value.items()}


def observe_dynamic_support(teacher):
    if getattr(teacher,'_probe_dynamic_observed',False): return
    if not hasattr(teacher,'_step_row'): return  # Lifecycle-only CPU fixture.
    teacher._probe_dynamic_observed=True
    teacher._probe_dynamic_context={}
    original=teacher._step_row
    def observed(s,i,diagnostic):
        identity=[int(s.episode_id[i]),int(s.control_step[i]),bool(s.reset_mask[i])]
        cached=teacher._probe_dynamic_context.get(i)
        if cached is not None and cached['identity']==identity:
            return original(s,i,diagnostic)
        if not teacher.cfg.slow_rolling or diagnostic is not None:
            teacher._probe_dynamic_context.pop(i,None)
            return original(s,i,diagnostic)
        context=dict(identity=identity,fingerprint=teacher.cfg.fingerprint,
            dynamic_candidate_limit=teacher.cfg.dynamic_candidate_limit,
            input={f.name:_dynamic_pack(getattr(s,f.name)[i:i+1]) for f in fields(s)},
            pre=_dynamic_pack(teacher._rows[i]))
        out=original(s,i,diagnostic)
        context.update(post=_dynamic_pack(teacher._rows[i]), action=out.action[0].tolist(),
            diagnostic=diagnostic_json(out.diagnostic[0].tolist()),valid=bool(out.valid[0]))
        teacher._probe_dynamic_context[i]=context
        return out
    teacher._step_row=observed


def dynamic_context_for(teacher,state,row):
    context=getattr(teacher,'_probe_dynamic_context',{}).get(row)
    if context is None: return None
    identity=[int(state.episode_id[row]),int(state.control_step[row]),bool(state.reset_mask[row])]
    return copy.deepcopy(context) if context is not None and context['identity']==identity else None


def _dynamic_equal(left,right):
    if isinstance(left,dict) and isinstance(right,dict):
        return left.keys()==right.keys() and all(_dynamic_equal(left[k],right[k]) for k in left)
    if isinstance(left,list) and isinstance(right,list):
        return len(left)==len(right) and all(_dynamic_equal(a,b) for a,b in zip(left,right))
    if type(left) is float or type(right) is float:
        return (math.isnan(left) and math.isnan(right)) or math.isclose(left,right,abs_tol=2e-6,rel_tol=2e-6)
    return left==right


def verify_tripod_sample(sample,cfg):
    """Independent scalar equilibrium check, never production tripod helper."""
    if not cfg.slow_rolling:
        return []
    try:
        c=sample['dynamic_support']; d=sample['teacher_diagnostic']
        if c is None: return ['missing tripod outer context']
        inp=c['input']; pre=c['pre'] or {}; post=c['post'] or {}
        take=lambda name:inp[name]['tensor'][0]
        episode,step,reset=c['identity']
        if reset:
            if 'tripod_captured_load_n' in post: return ['tripod capture survived reset']
            return []
        # No prediction before preparation or after an early safety refusal.
        if not d.get('tripod_current_total_n',0):
            return []
        current=sum(max(0.,f[2]) for f in take('wheel_force_w'))
        finished=c['valid'] and pre.get('prepared') and not post.get('prepared')
        row=post if c['valid'] and not finished else pre
        captured=row.get('tripod_captured_load_n',{}).get('tensor',[current])[0]
        forces=row.get('tripod_capture_forces_w',{}).get('tensor',[take('wheel_force_w')])[0]
        identity=row.get('tripod_capture_identity',[episode,step,post.get('target_id'),post.get('wheel')])
        active=int(row.get('wheel',-1))
        if (identity[0]!=episode or identity[1]>step or identity[2]!=row.get('target_id')
                or identity[3]!=active):
            raise ValueError('capture identity mismatch')
        def close(a,b,name,atol=3e-4):
            if a is None or not math.isfinite(a) or not math.isclose(a,b,rel_tol=3e-5,abs_tol=atol):
                raise ValueError(name)
        close(captured,sum(max(0.,f[2]) for f in forces),'captured load differs from raw forces')
        if identity[1]==step:
            if forces!=take('wheel_force_w'): raise ValueError('capture differs from same input')
            if c['valid'] and not post.get('prepared'): raise ValueError('capture without preparation')
        elif pre.get('tripod_capture_identity')!=post.get('tripod_capture_identity') and c['valid'] and post.get('prepared'):
            raise ValueError('capture replaced outside capture transaction')
        total=min(current,captured)
        close(d['tripod_current_total_n'],current,'current total')
        close(d['tripod_captured_total_n'],captured,'captured total')
        close(d['tripod_effective_total_n'],total,'effective total')
        indices=[j for j in range(4) if j!=active]
        def equilibrium(com,wheels):
            x=[wheels[j][0]-com[0] for j in indices]
            y=[wheels[j][1]-com[1] for j in indices]
            det=(x[1]-x[0])*(y[2]-y[0])-(x[2]-x[0])*(y[1]-y[0])
            if abs(det)<=1e-10 or total<=0: raise ValueError('invalid tripod')
            a=(x[1]*y[2]-x[2]*y[1])/det
            b=(x[2]*y[0]-x[0]*y[2])/det
            fractions=[a,b,1-a-b]
            return fractions,[f*total for f in fractions]
        fractions,loads=equilibrium(take('com_pos_w'),take('wheel_pos_w'))
        close(d['tripod_valid'],1.,'valid')
        for j in range(3):
            close(d[f'tripod_support_index_{j}'],indices[j],'support index')
            close(d[f'tripod_fraction_{j}'],fractions[j],'fraction')
            close(d[f'tripod_load_n_{j}'],loads[j],'load')
        minimum=min(loads); reserve=max(0.,min(1.,(minimum-30.)/15.))
        close(d['tripod_min_load_n'],minimum,'minimum')
        close(d['tripod_reserve'],reserve,'reserve')
        if c['valid'] and pre.get('phase')==1 and post.get('phase')==2 and minimum<=30.:
            raise ValueError('lift entered without reserve')
        combined=reserve
        selected=post.get('tripod_selected_reference') if c['valid'] else None
        if selected is not None and (d.get('dynamic_enabled') or d.get('candidate_index',-1)>=0):
            ref=selected['values']; body=ref['body']['values']
            pos=body['pos_w']['tensor'][0]; quat=body['quat_w']['tensor'][0]
            def rotate(q,v):
                w,x,y,z=q; a,b,c_=v
                return [(1-2*y*y-2*z*z)*a+2*(x*y-z*w)*b+2*(x*z+y*w)*c_,
                    2*(x*y+z*w)*a+(1-2*x*x-2*z*z)*b+2*(y*z-x*w)*c_,
                    2*(x*z-y*w)*a+2*(y*z+x*w)*b+(1-2*x*x-2*y*y)*c_]
            mq=take('root_quat_w'); mq=[mq[0],-mq[1],-mq[2],-mq[3]]
            offset=rotate(mq,[a-b for a,b in zip(take('com_pos_w'),take('root_pos_w'))])
            predicted=[a+b for a,b in zip(pos,rotate(quat,offset))]
            if inp['root_pos_w']['dtype']=='float32':
                # Match the recorded world-coordinate representation before
                # independent scalar equilibrium. At |Y|~152m a float32 ULP
                # is15um; comparing an unrounded double COM invents precision.
                import struct
                predicted=[struct.unpack('f',struct.pack('f',v))[0] for v in predicted]
            for name,wheels in (('anchor',ref['wheels_w']['tensor'][0]),('measured',take('wheel_pos_w'))):
                candidate_fractions,candidate_loads=equilibrium(predicted,wheels)
                if name=='measured' and d.get('load_enabled') and not d.get('load_restore'):
                    recorded=sample['feedback_context']['load_feedback']
                    if recorded['geometry_valid'] is not True: raise ValueError('selected load geometry invalid')
                    for a,b in zip(recorded['fractions'],candidate_fractions): close(a,b,'load fraction binding',2e-6)
                close(d[f'tripod_selected_{name}_min_n'],min(candidate_loads),'selected minimum')
                if min(candidate_loads)<30.-3e-4: raise ValueError('selected tripod below30N')
                combined=min(combined,max(0.,min(1.,(min(candidate_loads)-30.)/15.)))
            close(d['tripod_combined_reserve'],combined,'combined tripod reserve',3e-5)
        if d.get('dynamic_enabled') and c['valid']:
            if selected is None: raise ValueError('missing selected tripod geometry')
            expected=min(combined,max(0.,min(1.,(d['dynamic_conservative_fz']-cfg.support_min_force_n)/cfg.measured_lift_force_band_n)),
                max(0.,min(1.,(d['dynamic_conservative_margin']-cfg.com_margin_m)/cfg.measured_lift_margin_band_m)))
            close(d['dynamic_reserve'],expected,'merged reserve',3e-5)
            accepted=pre['accepted']['values']['wheels_w']['tensor'][0][active][2]
            measured=take('wheel_pos_w')[active][2]
            target=int(pre['target'])
            ceiling=take('ground_z')[target]+.0959+(cfg.front_max_lift_m if active<2 else cfg.rear_max_lift_m)
            reached=accepted>=ceiling or measured>=ceiling
            base=max(accepted,measured) if expected>0 and not reached else accepted
            increment=min(cfg.measured_lift_rate_m_s*take('dt')*expected,
                max(0.,measured+cfg.measured_lift_lead_m-base),0. if reached else max(0.,ceiling-base))
            if not d['wheel_progress_ready']: base=accepted; increment=0.
            close(d['dynamic_accepted_z'],accepted,'accepted height',2e-7)
            close(d['dynamic_measured_z'],measured,'measured height',2e-7)
            close(d['dynamic_increment_m'],increment,'height increment',2e-7)
            close(d['dynamic_requested_z'],base+increment,'next height',2e-7)
            start=row['lift_start_z']['tensor']
            if isinstance(start,list): start=start[0]
            close(d['dynamic_actual_lift_m'],measured-start,'actual lift',2e-7)
            fb=sample.get('feedback_context')
            if fb is not None:
                close(fb['requested']['wheels'][active][2],base+increment,'requested wheel height',2e-7)
        return []
    except (KeyError,ValueError,TypeError,IndexError,ZeroDivisionError) as exc:
        return [f'tripod independent evidence mismatch: {exc}']


def verify_active_horizontal_anchor(sample,cfg):
    """Audit anchor history with scalar geometry, without producer replay.

    Common support rolling is the only ordinary anchor translation. The first
    committed BALANCE-to-LIFT step additionally captures active XY, never Z.
    Failed transactions must retain the old anchors exactly.
    """
    if not cfg.slow_rolling: return []
    try:
        context=sample['dynamic_support']
        pre,post=context['pre'],context['post']
        if not pre.get('prepared') or not post.get('prepared'): return []
        def wheels(value):
            result=value['tensor'][0]
            if len(result)!=4 or any(len(row)!=3 for row in result):
                raise ValueError('anchor shape')
            if any(not math.isfinite(float(x)) for row in result for x in row):
                raise ValueError('nonfinite anchor')
            return result
        old=wheels(pre['wheel_anchor'])
        actual=wheels(post['wheel_anchor'])
        expected=copy.deepcopy(old)
        if context['valid']:
            wheel=int(pre['wheel'])
            if wheel not in range(4): raise ValueError('active wheel')
            measured=wheels(context['input']['wheel_pos_w'])
            previous=wheels(pre['support_previous'])
            yaw=float(pre['yaw']['tensor'][0])
            if not math.isfinite(yaw): raise ValueError('nonfinite yaw')
            forward=(math.cos(yaw),math.sin(yaw))
            support=[i for i in range(4) if i!=wheel]
            advance=sum(sum((measured[i][j]-previous[i][j])*forward[j]
                            for j in range(2)) for i in support)/3.
            for row in expected:
                for j in range(2): row[j]+=advance*forward[j]
            if int(pre['phase'])==1 and int(post['phase'])==2:
                expected[wheel][:2]=measured[wheel][:2]
        # Float32 world coordinates can have ~15um ULP in displaced envs.
        tolerance=5e-5 if context['valid'] else 0.
        if any(abs(actual[i][j]-expected[i][j])>tolerance
               for i in range(4) for j in range(3)):
            return ['active horizontal anchor history mismatch']
        if context['valid'] and int(post['phase']) in (2,3):
            requested=sample['feedback_context']['requested']['wheels']
            if context['diagnostic']['wheel_progress_ready']:
                request_xy=expected
            else:
                request_xy=copy.deepcopy(wheels(pre['accepted']['values']['wheels_w']))
                for row in request_xy:
                    for j in range(2): row[j]+=advance*forward[j]
            if len(requested)!=4 or any(len(row)!=3 for row in requested):
                raise ValueError('requested wheel shape')
            if any(not math.isfinite(float(requested[i][j])) or
                   abs(requested[i][j]-request_xy[i][j])>tolerance
                   for i in range(4) for j in range(2)):
                return ['active horizontal requested XY mismatch']
        return []
    except (KeyError,ValueError,TypeError,IndexError,OverflowError) as exc:
        return [f'invalid active horizontal anchor history: {exc}']


def verify_bounded_attitude(sample,cfg):
    """Scalar raw-evidence check; does not call teacher search or replay."""
    if not cfg.bounded_crossing_attitude: return []
    try:
        c=sample['dynamic_support'];pre=c['pre'];post=c['post'];d=c['diagnostic']
        if c['fingerprint']!=cfg.fingerprint: raise ValueError('fingerprint')
        if c['dynamic_candidate_limit']!=1126: raise ValueError('dynamic budget')
        if not c['valid']: return []
        restoring=bool(pre and pre.get('prepared') and
            (pre.get('phase')==4 or post.get('phase')==4))
        if not d.get('dynamic_enabled') and not restoring: return []
        def quat(q):
            if len(q)!=4 or not all(math.isfinite(v) for v in q): raise ValueError('quaternion shape/finite')
            n=math.sqrt(sum(v*v for v in q))
            if abs(n-1)>2e-6: raise ValueError('unit quaternion')
            return [v/n for v in q]
        def same(a,b):
            a,b=quat(a),quat(b)
            return min(sum((x-y)**2 for x,y in zip(a,b)),sum((x+y)**2 for x,y in zip(a,b)))<=1e-10
        def rotate(q,v):
            w,x,y,z=quat(q);a,b,h=v
            return [(1-2*y*y-2*z*z)*a+2*(x*y-z*w)*b+2*(x*z+y*w)*h,
                2*(x*y+z*w)*a+(1-2*x*x-2*z*z)*b+2*(y*z-x*w)*h,
                2*(x*z-y*w)*a+2*(y*z+x*w)*b+(1-2*x*x-2*y*y)*h]
        yaw=pre['yaw']['tensor'][0]
        if not math.isfinite(yaw): raise ValueError('captured yaw')
        if restoring:
            goal=post['goal']['values']['body']['values']['quat_w']['tensor'][0]
            if not same(goal,[math.cos(yaw/2),0.,0.,math.sin(yaw/2)]):
                raise ValueError('restore baseline orientation')
            return []
        def bounded(q):
            w,x,y,z=quat(q);actual=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
            delta=math.atan2(math.sin(actual-yaw),math.cos(actual-yaw))
            return abs(delta)<=1e-5 and 1-2*(x*x+y*y)>=math.cos(.15)-1e-6
        body=post['tripod_selected_reference']['values']['body']['values']
        selected=body['quat_w']['tensor'][0]
        if not bounded(selected): raise ValueError('selected yaw/tilt')
        request=sample['feedback_context']['requested']['root'][3:]
        if not same(selected,request): raise ValueError('selected/request orientation')
        goal=post['goal']['values']['body']['values']['quat_w']['tensor'][0]
        if not same(selected,goal): raise ValueError('selected/goal orientation')
        index=d['dynamic_candidate_index']
        if int(index)!=index or not 0<=index<1126: raise ValueError('candidate index')
        accepted=pre['accepted']['values']['body']['values']
        aq=accepted['quat_w']['tensor'][0]
        if index==1125:
            expected=aq
        else:
            pairs=[(0.,0.)]+[(r,p) for r in (-.1,0.,.1) for p in (-.1,0.,.1) if (r,p)!=(0.,0.)]
            r,p=pairs[int(index)//125];cr,sr=math.cos(r/2),math.sin(r/2);cp,sp=math.cos(p/2),math.sin(p/2)
            cy,sy=math.cos(yaw/2),math.sin(yaw/2)
            expected=[cr*cp*cy+sr*sp*sy,sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy]
        if not same(selected,expected): raise ValueError('selected pool membership')
        anchor=pre['anchor_pose']['values']['pos_w']['tensor'][0]
        ap=accepted['pos_w']['tensor'][0];dx,dy=ap[0]-anchor[0],ap[1]-anchor[1]
        offsets=[dx*math.cos(yaw)+dy*math.sin(yaw),-dx*math.sin(yaw)+dy*math.cos(yaw),ap[2]-anchor[2]]
        eps=(2**-23 if c['input']['root_pos_w']['dtype']=='float32' else 2**-52)*8
        floor=c['input']['nominal_root_z_w']['tensor'][0]-anchor[2]-.08
        count=225*sum(z>=floor-eps for z in (0.,-.02,-.04,-.06,-.08))
        count+=int(abs(offsets[0])<=.04+eps and abs(offsets[1])<=.06+eps and
            -.08-eps<=offsets[2]<=eps and offsets[2]>=floor-eps and bounded(aq))
        if d['dynamic_candidate_count']!=count: raise ValueError('candidate count')
        inp=c['input'];mq=inp['root_quat_w']['tensor'][0]
        local=rotate([mq[0],-mq[1],-mq[2],-mq[3]],
            [a-b for a,b in zip(inp['com_pos_w']['tensor'][0],inp['root_pos_w']['tensor'][0])])
        predicted=[a+b for a,b in zip(body['pos_w']['tensor'][0],rotate(selected,local))]
        for j,axis in enumerate('xy'):
            value=d['dynamic_com_target_'+axis]
            if value is None or not math.isfinite(value) or abs(value-predicted[j])>3e-5:
                raise ValueError('selected COM orientation')
        return []
    except (KeyError,TypeError,ValueError,IndexError,OverflowError,ZeroDivisionError) as exc:
        return [f'bounded attitude independent mismatch: {exc}']


def verify_dynamic_support_sample(sample,cfg,*,replay_backend='cpu'):
    """Replay the entire outer transaction, independent of feedback-only audit."""
    from ame_baseline.m1_reference_teacher import ReferenceTeacher,TeacherState
    context=sample.get('dynamic_support')
    if context is None:
        return ['missing dynamic outer context'] if cfg.slow_rolling else []
    try:
        if context['fingerprint']!=cfg.fingerprint: return ['dynamic fingerprint mismatch']
        state=TeacherState(**_dynamic_unpack(context['input'],replay_backend))
        state.validate()
        identity=[int(state.episode_id[0]),int(state.control_step[0]),bool(state.reset_mask[0])]
        if identity!=context['identity']: return ['dynamic identity mismatch']
        real=sample['preparation_input']
        root=[]
        for name in ('root_pos_w','root_quat_w','root_lin_vel_w','root_ang_vel_w'):
            root.extend(getattr(state,name)[0].tolist())
        if (identity[:2]!=[sample['teacher_input_episode_id'],sample['teacher_input_frame']]
                or identity[:2]!=[real['episode_id'],real['frame']]
                or root!=real['root'] or state.com_pos_w[0].tolist()!=real['com']
                or state.wheel_pos_w[0].tolist()!=real['wheels']
                or state.wheel_force_w[0].tolist()!=real['forces']
                or bool(state.measurement_valid[0])!=real['measurement_valid']
                or state.leg_pos[0].tolist()!=sample['teacher_input_leg_pos']
                or state.last_applied_leg_target[0].tolist()!=sample['last_applied_leg_target']
                or state.default_joint_pos[0].tolist()!=sample['action_default_joint_pos']
                or str(state.default_joint_pos.dtype).removeprefix('torch.')!=sample['action_target_dtype']
                or not math.isclose(float(state.dt[0]),.02,abs_tol=1e-7)):
            return ['dynamic context differs from actual input']
        teacher=ReferenceTeacher(cfg)
        teacher._rows=[_dynamic_unpack(context['pre'],replay_backend)]
        observe_feedback_transactions(teacher)
        out=teacher._step_row(state,0,None)
        actual=dict(post=_dynamic_pack(teacher._rows[0]),action=out.action[0].tolist(),
            diagnostic=diagnostic_json(out.diagnostic[0].tolist()),valid=bool(out.valid[0]))
        errors=[f'dynamic {k} mismatch' for k,v in actual.items() if not _dynamic_equal(v,context[k])]
        replay_attitude=(getattr(teacher,'_probe_feedback_context',{}).get(0,{})
            .get('load_feedback',{}).get('attitude'))
        recorded_attitude=(sample.get('feedback_context') or {}).get('load_feedback',{}).get('attitude')
        if not _dynamic_equal(replay_attitude,recorded_attitude):
            errors.append('dynamic attitude source mismatch')
        if not _dynamic_equal(context['action'],sample['teacher_action']): errors.append('dynamic applied action mismatch')
        if 'teacher_diagnostic' in sample and not _dynamic_equal(context['diagnostic'],sample['teacher_diagnostic']):
            errors.append('dynamic published diagnostic mismatch')
        errors.extend(verify_tripod_sample(sample,cfg))
        errors.extend(verify_active_horizontal_anchor(sample,cfg))
        errors.extend(verify_bounded_attitude(sample,cfg))
        return errors
    except (ValueError,TypeError,KeyError,RuntimeError,IndexError,AttributeError) as exc:
        return [f'invalid dynamic context: {exc}']


def selection_input_digest(context):
    """Bind the owned producer result to its complete preselection snapshot."""
    payload={key:value for key,value in context.items() if key!='choice'}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()


def selection_choice_json(choice):
    finite=lambda value:float(value) if math.isfinite(float(value)) else None
    return dict(candidate_index=int(choice.candidate_index[0]),valid=bool(choice.valid[0]),
        candidate_count=int(choice.candidate_count[0]),predicted_margin_m=finite(choice.predicted_margin_m[0]),
        measured_triangle_margin_m=finite(choice.measured_triangle_margin_m[0]),reference=pose_context(choice.reference))


def observe_preparation_selection(teacher,state,contexts):
    """Expire changed rows and wrap the single real BALANCE search once.

    A duplicate input keeps the context belonging to its cached output. Reset
    and preselection failures remove only that row's old owned snapshot.
    """
    teacher._probe_selection_context=contexts
    resets=getattr(state,'reset_mask',None)
    for row in list(contexts):
        identity=dict(env_id=row,episode_id=int(state.episode_id[row]),input_frame=int(state.control_step[row]))
        if contexts[row]['identity']!=identity or resets is not None and bool(resets[row]):
            contexts.pop(row)
    if getattr(teacher,'_probe_selection_observed',False): return
    original=getattr(teacher,'_select_preparation_pose',None)
    if original is None: return  # CPU lifecycle fixture without a selector.
    def observed(s,i,work,accepted,q,branch):
        from ame_baseline.m1_teacher_pose import PoseReference
        take=lambda value:value.detach().clone().tolist()
        measured=teacher._reference(s,i)
        context=dict(identity=dict(env_id=i,episode_id=int(s.episode_id[i]),input_frame=int(s.control_step[i])),
            measured=pose_context(measured),
            anchor=pose_context(PoseReference(work['anchor_pose'],work['wheel_anchor'])),
            accepted=pose_context(accepted),com_w=take(s.com_pos_w[i]),
            wheel_anchors_w=take(work['wheel_anchor'][0]),measured_wheels_w=take(measured.wheels_w[0]),
            active_wheel=int(work['wheel']),nominal_root_z_w=float(s.nominal_root_z_w[i]),
            q_seed=take(q[0]),branch_q=take(branch[0]),cfg=asdict(teacher.cfg),
            dtype=str(q.dtype).removeprefix('torch.'),producer_backend=capture_producer_backend(q.device))
        choice=original(s,i,work,accepted,q,branch)
        if 'tripod_effective_load_n' in work:
            context['tripod_total_load_n']=float(work['tripod_effective_load_n'][0])
        context['choice']={**selection_choice_json(choice),'identity':copy.deepcopy(context['identity']),
            'input_digest':selection_input_digest(context)}
        teacher._probe_selection_context[i]=context
        return choice
    teacher._select_preparation_pose=observed
    teacher._probe_selection_observed=True


def selection_context_for(teacher,state,row):
    context=getattr(teacher,'_probe_selection_context',{}).get(row)
    identity=dict(env_id=row,episode_id=int(state.episode_id[row]),input_frame=int(state.control_step[row]))
    resets=getattr(state,'reset_mask',None)
    if (context is None or context['identity']!=identity
            or resets is not None and bool(resets[row])): return None
    return copy.deepcopy(context)


def verify_preparation_selection(context: dict,choice: dict,*,replay_backend: str,
                                 require_backend_evidence: bool) -> list[str]:
    """Replay the original selector on the explicitly trusted producer backend."""
    try:
        backend=check_producer_backend(context.get('producer_backend'),replay_backend,
            required=require_backend_evidence)
    except (ValueError,RuntimeError,TypeError,AttributeError):
        return ['preparation selection producer/replay backend evidence unavailable or mismatched']
    try:
        import torch
        from ame_baseline.m1_teacher_pose import BodyPose,PoseReference,choose_support_pose
        from ame_baseline.m1_reference_teacher import TeacherConfig,ReferenceTeacher
        from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig as FeedbackConfig
        required={'identity','measured','anchor','accepted','com_w','wheel_anchors_w','measured_wheels_w',
            'active_wheel','nominal_root_z_w','q_seed','branch_q','cfg','producer_backend','dtype','choice'}
        if 'tripod_total_load_n' in context: required.add('tripod_total_load_n')
        if set(context)!=required: raise ValueError('incomplete selection snapshot')
        identity=context['identity']
        if (set(identity)!={'env_id','episode_id','input_frame'}
                or any(type(v) is not int for v in identity.values())
                or identity['env_id']<0 or identity['episode_id']<0 or identity['input_frame']<0
                or choice['identity']!=identity or choice['input_digest']!=selection_input_digest(context)):
            raise ValueError('selection input identity/snapshot mismatch')
        if (context['anchor']['wheels']!=context['wheel_anchors_w']
                or context['measured']['wheels']!=context['measured_wheels_w']
                or context['dtype'] not in ('float32','float64')
                or type(context['active_wheel']) is not int): raise ValueError('selection input mismatch')
        config=copy.deepcopy(context['cfg'])
        if (set(config)!=set(asdict(TeacherConfig()))
                or set(config['feedback'])!=set(asdict(FeedbackConfig()))):
            raise ValueError('incomplete selection configuration')
        config['feedback']=FeedbackConfig(**config['feedback'])
        cfg=TeacherConfig(**config)
        with torch.device(backend['device']):
            tensor=lambda value:torch.tensor([value],dtype=getattr(torch,context['dtype']),device=backend['device'])
            ref=lambda value:PoseReference(BodyPose(tensor(value['root'][:3]),tensor(value['root'][3:])),tensor(value['wheels']))
            result=choose_support_pose(ref(context['measured']).body,ref(context['anchor']).body,
                ref(context['accepted']).body,tensor(context['com_w']),tensor(context['wheel_anchors_w']),
                torch.tensor([context['active_wheel']],device=backend['device']),
                tensor(context['nominal_root_z_w']).reshape(1),tensor(context['q_seed']),tensor(context['branch_q']),
                ReferenceTeacher(cfg).ik_cfg,measured_wheels_w=tensor(context['measured_wheels_w']),
                tripod_total_load_n=tensor(context['tripod_total_load_n']).reshape(1) if 'tripod_total_load_n' in context else None)
        expected=selection_choice_json(result)
        if set(choice)!=set(expected)|{'identity','input_digest'}: raise ValueError('incomplete choice')
        for name,value in expected.items():
            actual=choice[name]
            if name in ('candidate_index','candidate_count','valid'):
                if type(actual) is not type(value) or actual!=value: raise ValueError(name)
            elif name=='reference':
                if (set(actual)!={'root','wheels'} or len(actual['root'])!=7
                        or len(actual['wheels'])!=4 or any(len(wheel)!=3 for wheel in actual['wheels'])):
                    raise ValueError('incomplete selected reference')
                flatten=lambda ref:ref['root']+[v for wheel in ref['wheels'] for v in wheel]
                if any(not math.isclose(a,b,rel_tol=2e-5,abs_tol=2e-6)
                        for a,b in zip(flatten(actual),flatten(value))): raise ValueError(name)
            elif actual is None or value is None:
                if actual is not value: raise ValueError(name)
            elif (isinstance(actual,bool) or not isinstance(actual,(int,float))
                    or not math.isclose(actual,value,rel_tol=2e-5,abs_tol=2e-7)): raise ValueError(name)
        return []
    except (KeyError,TypeError,ValueError,RuntimeError,IndexError,AttributeError):
        return ['preparation selection evidence mismatch']


def verify_selection_sample(sample,cfg,*,replay_backend,require_backend_evidence):
    """Bind selection to the real precontrol row; output measurements cannot substitute."""
    try:
        context=sample['selection_context']; d=sample['teacher_diagnostic']
        if context is None:
            feedback=sample.get('feedback_context')
            if (d['candidate_index']!=-1 or d['candidate_count']!=-1
                    or d['candidate_com_margin_m'] is not None
                    or d['candidate_measured_triangle_margin_m'] is not None
                    or feedback is not None and feedback['active'] and
                        (sample['phase']==1 or d['preparation_ready']==1)):
                raise ValueError('missing selection')
            return []
        choice=context['choice']; input_=sample['preparation_input']
        if (context['identity']!=dict(env_id=sample['env_id'],episode_id=sample['teacher_input_episode_id'],
                    input_frame=sample['teacher_input_frame'])
                or context['identity']!=dict(env_id=input_['env_id'],episode_id=input_['episode_id'],input_frame=input_['frame'])
                or context['measured']['root']!=input_['root'][:7]
                or context['com_w']!=input_['com'] or context['measured_wheels_w']!=input_['wheels']
                or context['q_seed']!=sample['teacher_input_leg_pos']
                or context['active_wheel']!=sample['active_wheel']
                or context['dtype']!=sample['action_target_dtype'] or context['cfg']!=asdict(cfg)
                or context['producer_backend']!=sample['producer_backend']):
            raise ValueError('selection differs from real input')
        for name,key in (('candidate_index','candidate_index'),('candidate_count','candidate_count'),
                         ('candidate_com_margin_m','predicted_margin_m'),
                         ('candidate_measured_triangle_margin_m','measured_triangle_margin_m')):
            if d[name]!=choice[key]: raise ValueError('diagnostic differs from producer choice')
        if choice['valid']:
            if [d['preparation_goal_root_'+axis] for axis in 'xyz']!=choice['reference']['root'][:3]:
                raise ValueError('goal differs from selected candidate')
        feedback=sample.get('feedback_context')
        if feedback is not None and (feedback['accepted_before']!=context['accepted']
                or feedback['branch_q']!=context['branch_q']):
            raise ValueError('selection prior/branch differs from actual transaction')
        return verify_preparation_selection(context,choice,replay_backend=replay_backend,
            require_backend_evidence=require_backend_evidence)
    except (KeyError,TypeError,ValueError,IndexError):
        return ['preparation selection evidence mismatch']


@lru_cache(maxsize=1)
def feedback_producer_class():
    from ame_baseline.m1_reference_teacher import ReferenceTeacher
    return ReferenceTeacher


def capture_producer_backend(device):
    """Read trusted device/runtime provenance; never change ambient math/device."""
    import torch
    device=torch.device(device)
    if device.type=='cpu': device=torch.device('cpu')
    elif (device.type!='cuda' or device.index is None or not torch.cuda.is_available()
            or device.index>=torch.cuda.device_count()):
        raise ValueError('requested replay backend unavailable or not explicitly indexed')
    return dict(device=str(device),origin='producer_tensor_device_and_runtime_math_settings',
        torch_version=str(torch.__version__),cuda_version=torch.version.cuda,
        device_name=torch.cuda.get_device_name(device) if device.type=='cuda' else 'cpu',
        matmul_allow_tf32=bool(torch.backends.cuda.matmul.allow_tf32),
        float32_matmul_precision=torch.get_float32_matmul_precision())


def check_producer_backend(metadata,replay_backend,*,required=False):
    """Caller selects backend; untrusted evidence only agrees or is rejected.

    Legacy metadata-free CPU fixtures remain supported. Native callers require
    provenance, as do all explicitly selected CUDA replays; never fall back.
    """
    expected=capture_producer_backend(replay_backend)
    if metadata is None:
        if required or expected['device']!='cpu': raise ValueError('missing producer backend evidence')
    elif metadata!=expected: raise ValueError('producer backend/runtime differs from trusted replay configuration')
    return expected


def replay_feedback_transaction(context_json,config_json,dtype,phase,*,replay_backend='cpu'):
    import torch
    backend=capture_producer_backend(replay_backend)
    # Pure replay only: existing IK as_tensor calls inherit the ambient device.
    # A trusted, scoped guard restores it before returning to any live control.
    with torch.device(backend['device']):
        return _cached_replay_feedback_transaction(context_json,config_json,dtype,phase,
            backend['device'],json.dumps(backend,sort_keys=True))


@lru_cache(maxsize=1024)
def _cached_replay_feedback_transaction(context_json,config_json,dtype,phase,backend,backend_json):
    """Cache only pure expected math for byte-identical complete inputs.

    No sample validity, receipt, source, identity or artifact check is cached.
    Different physical measurements/branch/reference inputs produce new solves.
    """
    import torch
    from types import SimpleNamespace
    from ame_baseline.m1_reference_teacher import ReferenceTeacher,TeacherConfig,LEG_COLUMNS
    from ame_baseline.m1_teacher_feedback import FeedbackState,BodyFeedbackConfig as FeedbackConfig
    from ame_baseline.m1_teacher_pose import BodyPose,PoseReference
    context=json.loads(context_json); config=json.loads(config_json)
    config['feedback']=FeedbackConfig(**config['feedback']); cfg=TeacherConfig(**config)
    tensor=lambda value:torch.tensor([value],dtype=getattr(torch,dtype),device=backend)
    ref=lambda value:PoseReference(BodyPose(tensor(value['root'][:3]),tensor(value['root'][3:])),tensor(value['wheels']))
    old=FeedbackState(tensor(context['integral_before']),tensor(context['output_before']))
    state=SimpleNamespace(root_pos_w=tensor(context['measured_root']),
        root_quat_w=tensor(context.get('measured_quat',[1.,0.,0.,0.])),dt=tensor([context['dt']]).reshape(1),
        default_joint_pos=tensor(context['default_joint_pos']),last_applied_leg_target=tensor(context['last_applied_q']),
        applied_target_valid=torch.tensor([True],device=backend))
    work=dict(feedback=old,prepared=context['active'],phase=context.get('control_phase',1),
        yaw=tensor([context['captured_yaw']]).reshape(1))
    if context.get('wheel_anchor') is not None:
        work.update(wheel_anchor=tensor(context['wheel_anchor']),wheel=context['active_wheel'])
        state.wheel_pos_w=tensor(context['measured_wheels'])
    teacher=feedback_producer_class()(cfg); evidence={'requested':ref(context['requested']),
        'execution_enabled':context.get('execution_enabled',False)}
    load=context.get('load_feedback')
    if load is not None:
        work.update(support_load_offset=tensor(load['previous']),support_load_proposal=tensor(load['proposed']))
        evidence.update(load_enabled=1.,load_restore=float(load['restore']))
        if context.get('support_height_previous') is not None:
            work['support_execution_z']=tensor(context['support_height_previous'])
        for key in ('support_heave','support_heave_error0','support_capture_root_z'):
            if context.get(key+'_previous') is not None:
                work[key]=tensor(context[key+'_previous']).reshape(1)
    solved,selected=teacher._feedback_transaction(state,0,work,ref(context['accepted_before']),
        ref(context['requested']),tensor(context['q_seed']),tensor(context['branch_q']),
        tensor(context['nominal_speed']),evidence)
    valid=bool(solved.valid[0])
    committed=FeedbackState((torch.zeros_like(selected) if phase==0 else selected) if valid else old.integral,
        solved.output if valid else old.output)
    accepted=solved.physical if valid else (ref(context['retained_physical']) if context['retained_physical'] else None)
    command=solved.command if valid else (ref(context['retained_command']) if context['retained_command'] else None)
    row=dict(feedback=committed,accepted=accepted,accepted_command=command,
        last_q=tensor(context['retained_q']) if context['retained_q'] else None,
        invalid_streak=0,age=0,body_age=0,lift_age=0)
    if load is not None:
        row['support_load_offset']=evidence['load_selected_offset'] if valid else tensor(load['previous'])
        if valid and phase!=0 and 'height_selected' in evidence:
            row['support_execution_z']=evidence['height_selected']
            row['support_capture_root_z']=evidence['height_origin']
        elif not valid and 'support_execution_z' in work:
            row['support_execution_z']=work['support_execution_z']
            row['support_capture_root_z']=work['support_capture_root_z']
        if valid and phase!=0 and 'heave_selected' in evidence:
            row['support_heave']=evidence['heave_selected']
            row['support_heave_error0']=evidence['heave_error0']
        elif not valid:
            for key in ('support_heave','support_heave_error0'):
                if key in work:row[key]=work[key]
    from ame_baseline.m1_reference_teacher import encode_targets
    from ame_baseline.m1_ame_contract import m1_action_targets
    if valid:
        action,executable=encode_targets(solved.command_ik.q,tensor(context['nominal_speed']),state.default_joint_pos)
        row['last_q']=m1_action_targets(action,state.default_joint_pos)[:,LEG_COLUMNS]
    else:
        row['branch_q']=tensor(context['retained_branch_q']) if context['retained_branch_q'] else None
        action,executable=teacher._fallback(state,0,row)
    state.com_pos_w=tensor([0.,0.,0.])
    expected=diagnostic_json(teacher._diagnostics(state,0,row,evidence,valid,0,None)[0].tolist())
    return json.dumps(expected,sort_keys=True),tuple(action[0].tolist()),bool(executable)


replay_feedback_transaction.cache_clear=_cached_replay_feedback_transaction.cache_clear
replay_feedback_transaction.cache_info=_cached_replay_feedback_transaction.cache_info


def verify_attitude_preference(sample):
    """Independent scalar geometry plus pre-transaction capture binding."""
    import struct
    c=sample['feedback_context'];d=sample['teacher_diagnostic'];a=c['load_feedback']['attitude']
    active=c['active_wheel'];support=[j for j in range(4) if j!=active]
    cast=(lambda x:struct.unpack('f',struct.pack('f',x))[0]) if sample['action_target_dtype']=='float32' else float
    def rotate(q,v,inverse=False):
        norm=math.sqrt(sum(x*x for x in q))
        if not math.isfinite(norm) or abs(norm-1)>1e-3:raise ValueError('attitude quaternion')
        w,x,y,z=[x/norm for x in q]
        if inverse:x,y,z=-x,-y,-z
        p,r,s=v
        return [(1-2*y*y-2*z*z)*p+2*(x*y-z*w)*r+2*(x*z+y*w)*s,
                2*(x*y+z*w)*p+(1-2*x*x-2*z*z)*r+2*(y*z-x*w)*s,
                2*(x*z-y*w)*p+2*(y*z+x*w)*r+(1-2*x*x-2*y*y)*s]
    root=a['command']['root'];wheels=a['command']['wheels']
    raw=[]
    for j in support:
        p=[x-y for x,y in zip(wheels[j],root[:3])]
        raw.append(rotate(c['measured_quat'],rotate(root[3:],p,True))[2]-p[2])
    mean=sum(raw)/3;center=[cast(x-mean) for x in raw]
    center[2]=cast(-cast(center[0]+center[1]))
    error=[0.]*4
    for j,v in zip(support,center):error[j]=v
    previous=a['previous'];error0=error if previous is None else previous
    dynamic=sample.get('dynamic_support')
    if dynamic is not None:
        history=dynamic['pre'].get('support_attitude_error0')
        if (history is None)!=(previous is None):raise ValueError('attitude history presence')
        if history is not None and history['tensor'][0]!=previous:raise ValueError('attitude history mismatch')
    if len(error0)!=4 or not all(math.isfinite(v) for v in error0) or error0[active]!=0 or abs(sum(error0))>1e-8:
        raise ValueError('attitude capture structure')
    delta=[cast(x-y) for x,y in zip(error,error0)]
    delta[support[2]]=-cast(delta[support[0]]+delta[support[1]])
    if d['attitude_enabled']!=1 or d['attitude_captured']!=int(previous is None):raise ValueError('attitude enabled/capture')
    for name,values in (('error',error),('error0',error0),('delta',delta)):
        for j,value in enumerate(values):
            for actual in (a[name][j],d[f'attitude_{name}_{j}']):
                if not math.isfinite(actual) or not math.isclose(actual,value,rel_tol=2e-5,abs_tol=2e-7):raise ValueError('attitude '+name)
    return delta


def verify_load_feedback(sample,cfg):
    """Scalar audit of measured load allocation; no controller projector calls."""
    d=sample['teacher_diagnostic']; c=sample['feedback_context']
    load=c.get('load_feedback')
    if cfg.coherent_support_pose and (d.get('attitude_enabled',0)!=0 or (load is not None and load.get('attitude') is not None)):
        raise ValueError('coherent mode cannot add indirect attitude preference')
    if load is None:
        if d.get('load_enabled',0): raise ValueError('missing load inputs')
        return
    if not cfg.load_feedback or d['load_enabled']!=1: raise ValueError('load switch')
    active=c['active_wheel']; support=[j for j in range(4) if j!=active]
    old=load['previous']; raw=load['raw']; dt=c['dt']; fractions=load['fractions']
    def close(a,b,label,tol=2e-7):
        if not math.isfinite(a) or not math.isclose(a,b,rel_tol=2e-5,abs_tol=tol): raise ValueError(label)
    if len(old)!=4 or len(raw)!=4 or len(fractions)!=3 or not math.isfinite(dt) or dt<=0:
        raise ValueError('load dimensions/dt')
    if not all(math.isfinite(x) for x in old) or abs(sum(old))>1e-8 or old[active]!=0 or max(map(abs,old))>.015000001:
        raise ValueError('load previous state')
    measured=[f[2] for f in sample['preparation_input']['forces']]
    for a,b in zip(raw,measured):
        if not (a==b or not math.isfinite(a) and not math.isfinite(b)): raise ValueError('raw load binding')
    wheels=sample['preparation_input']['wheels']
    recorded=c['measured_wheels']
    if len(wheels)!=4 or len(recorded)!=4 or any(len(p)!=3 for p in wheels+recorded):
        raise ValueError('load geometry dimensions')
    for p,q in zip(wheels,recorded):
        for a,b in zip(p,q):
            if not (a==b or not math.isfinite(a) and not math.isfinite(b)):
                raise ValueError('load geometry binding')
    dynamic=sample.get('dynamic_support')
    if dynamic is not None:
        prior=dynamic['pre'].get('support_load_offset',{}).get('tensor',[[0.]*4])[0]
        for a,b in zip(old,prior): close(a,b,'load prior binding')
    def project(values,lower,upper,total):
        lo=min(v-u for v,u in zip(values,upper)); hi=max(v-l for v,l in zip(values,lower))
        for _ in range(100):
            mid=(lo+hi)/2
            if sum(max(l,min(u,v-mid)) for v,l,u in zip(values,lower,upper))>total: lo=mid
            else: hi=mid
        return [max(l,min(u,v-(lo+hi)/2)) for v,l,u in zip(values,lower,upper)]
    target=[0.]*4; proposal=old.copy(); unprojected=[0.]*4
    affine=[0.]*3; residual=[0.,0.]; active_fz=0.
    restore=c['control_phase']==4
    if bool(load['restore'])!=restore: raise ValueError('load restore phase')
    valid=True
    if restore:
        peak=max(map(abs,old)); factor=max(0.,1-.01*dt/peak) if peak else 0.
        proposal=[v*factor for v in old]
    else:
        total=sum(max(raw[j],0.) for j in support)
        p0,p1,p2=[wheels[j] for j in support]
        u=[p1[k]-p0[k] for k in range(2)];v=[p2[k]-p0[k] for k in range(2)]
        t=[wheels[active][k]-p0[k] for k in range(2)]
        det=u[0]*v[1]-u[1]*v[0]
        geometry_ok=all(math.isfinite(x) for p in wheels for x in p) and math.isfinite(det) and abs(det)>1e-10
        valid=bool(load['geometry_valid'] and all(math.isfinite(x) for x in raw+fractions)
                   and min(fractions)>=0 and math.isfinite(sum(fractions)) and sum(fractions)>0
                   and math.isfinite(total+max(raw[active],0.)) and total>=135. and geometry_ok)
        if valid:
            b1=(t[0]*v[1]-t[1]*v[0])/det;b2=(u[0]*t[1]-u[1]*t[0])/det
            affine=[1-b1-b2,b1,b2];active_fz=max(raw[active],0.)
            pre=[f*(total+active_fz)/sum(fractions)-active_fz*b for f,b in zip(fractions,affine)]
            desired=project(pre,[45.]*3,[total]*3,total)
            if sample['action_target_dtype']=='float32':
                import struct
                desired=[struct.unpack('f',struct.pack('f',value))[0] for value in desired]
            for j,f in zip(support,pre):unprojected[j]=f
            residual=[sum((d-f)*(wheels[j][k]-p0[k]) for j,d,f in zip(support,desired,pre)) for k in range(2)]
            lower=[max(-.01,(-.015-old[j])/dt) for j in support]
            upper=[min(.01,(.015-old[j])/dt) for j in support]
            preference=[-.0002*(v-raw[j]) for j,v in zip(support,desired)]
            attitude=load.get('attitude')
            if attitude is not None:
                delta=verify_attitude_preference(sample)
                weak=[raw[j]<45. or t-raw[j]>15. for j,t in zip(support,desired)]
                strong=[raw[j]-t>15. and not w for j,t,w in zip(support,desired,weak)]
                lower=[max(l,0.) if s else l for l,s in zip(lower,strong)]
                upper=[min(u,0.) if w else u for u,w in zip(upper,weak)]
                baseline=project(preference,lower,upper,0.)
                lower=[max(l,b) if s else l for l,b,s in zip(lower,baseline,strong)]
                upper=[min(u,b) if w else u for u,b,w in zip(upper,baseline,weak)]
                preference=[v+.5*delta[j] for v,j in zip(preference,support)]
                for j,w,s in zip(support,weak,strong):
                    close(d[f'attitude_weak_{j}'],float(w),'attitude weak')
                    close(d[f'attitude_strong_{j}'],float(s),'attitude strong')
            elif d.get('attitude_enabled',0):raise ValueError('missing attitude context')
            velocity=project(preference,lower,upper,0.)
            for j,f,v in zip(support,desired,velocity): target[j]=f; proposal[j]=old[j]+dt*v
            pl=[max(-.015,old[j]-.01*dt) for j in support]
            pu=[min(.015,old[j]+.01*dt) for j in support]
            if attitude is not None:
                pl=[max(v,old[j]+dt*l) for v,j,l in zip(pl,support,lower)]
                pu=[min(v,old[j]+dt*u) for v,j,u in zip(pu,support,upper)]
            corrected=project([proposal[j] for j in support],pl,pu,0.)
            for j,v in zip(support,corrected): proposal[j]=v
    close(d['load_proposal_valid'],float(valid),'load valid'); close(d['load_restore'],float(restore),'load restore')
    close(d['load_active_fz'],active_fz,'load active force',3e-4)
    for j in range(3):close(d[f'load_affine_{j}'],affine[j],'load affine',3e-5)
    for k,axis in enumerate('xy'):close(d[f'load_moment_{axis}'],residual[k],'load moment',3e-4)
    accepted=d['reference_valid']==1
    beta=d['execution_fraction'] if accepted else 0.
    for j in range(4):
        close(load['proposed'][j],proposal[j],'load proposal binding')
        selected=old[j]+beta*(proposal[j]-old[j])
        for name,value in (('raw',raw[j]),('target',target[j]),('unprojected',unprojected[j]),('previous',old[j]),('proposed',proposal[j]),
                           ('attempted',proposal[j]),('selected',selected),('committed',selected)):
            if math.isfinite(value): close(d[f'load_{name}_{j}'],value,'load '+name,3e-4 if name in ('target','unprojected') else 2e-7)
            elif d[f'load_{name}_{j}'] is not None: raise ValueError('nonfinite raw diagnostic')


def verify_support_height(sample,cfg):
    """Independent world-frame baseline, history and bounded restore audit."""
    import torch
    from ame_baseline.m1_teacher_ik import body_feet
    from ame_baseline.m1_teacher_pose import _rotation
    d=sample['teacher_diagnostic'];c=sample['feedback_context']
    expected_enabled=bool(cfg.load_feedback and not cfg.coherent_support_pose and c.get('execution_enabled') and c.get('control_phase') in (2,3,4))
    if d.get('height_enabled',0)!=int(expected_enabled):raise ValueError('height enable mismatch')
    if not expected_enabled:return
    t=lambda x:torch.tensor([x],dtype=getattr(torch,sample['action_target_dtype']))
    measured=t(c['measured_root']); rotation=_rotation(t(c['measured_quat']))
    captured=(measured[:,None]+torch.einsum('bij,bkj->bki',rotation,body_feet(t(c['last_applied_q']))))[:,:,2]
    previous=c.get('support_height_previous')
    old=captured if previous is None else t(previous)
    if 'support_capture_root_z_previous' not in c:
        raise ValueError('missing height origin history evidence')
    origin_previous=c['support_capture_root_z_previous']
    if (previous is None)!=(origin_previous is None):raise ValueError('height origin paired history')
    if origin_previous is not None and (not isinstance(origin_previous,list) or len(origin_previous)!=1):
        raise ValueError('height origin history shape')
    origin=float(measured[0,2]) if origin_previous is None else origin_previous[0]
    if not isinstance(origin,(float,int)) or not math.isfinite(origin):raise ValueError('height origin finite')
    if d.get('height_origin') is None or not math.isclose(d['height_origin'],origin,rel_tol=0,abs_tol=2e-7):
        raise ValueError('height origin mismatch')
    if d['height_captured']!=int(previous is None):raise ValueError('height capture mismatch')
    dynamic=sample.get('dynamic_support')
    if dynamic is not None:
        history=dynamic['pre'].get('support_execution_z')
        if (history is None)!=(previous is None):raise ValueError('height history presence')
        if history is not None and not torch.equal(t(history['tensor'][0]),old):raise ValueError('height history mismatch')
        origin_history=dynamic['pre'].get('support_capture_root_z')
        if (origin_history is None)!=(origin_previous is None):raise ValueError('height origin history presence')
        if origin_history is not None and origin_history['tensor']!=origin_previous:
            raise ValueError('height origin history mismatch')
    root=t([d['command_requested_root_'+a] for a in ('x','y','z','qw','qx','qy','qz')])
    wheels=t([[d[f'command_requested_world_wheel_{j}_{a}'] for a in 'xyz'] for j in range(4)])
    body=torch.einsum('bij,bkj->bki',_rotation(root[:,3:]).transpose(-1,-2),wheels-root[:,:3,None].transpose(1,2))
    active=c['active_wheel']
    if type(active)!=int or not 0<=active<4:raise ValueError('height active wheel')
    if c['control_phase']!=4:
        body[:,active]=torch.einsum('bij,bj->bi',rotation.transpose(-1,-2),wheels[:,active]-measured)
    geometry=(measured[:,None]+torch.einsum('bij,bkj->bki',rotation,body))[:,:,2]
    geometry=geometry-(measured[:,2]-origin)[:,None]
    proposed=old+(geometry-old).clamp(-.01*c['dt'],.01*c['dt']) if c['control_phase']==4 else old
    beta=d['execution_fraction'] if d['reference_valid']==1 else 0.
    selected=old+beta*(proposed-old)
    for name,value in (('previous',old),('proposed',proposed),('selected',selected),('geometry',geometry)):
        actual=t([d[f'height_{name}_{j}'] for j in range(4)])
        if not torch.allclose(actual,value,atol=2e-6,rtol=0):raise ValueError('height '+name)
    committed=[d[f'height_committed_{j}'] for j in range(4)]
    absent=(d['reference_valid']!=1 and previous is None) or (d['reference_valid']==1 and sample['phase']==0)
    origin_committed=d.get('height_origin_committed')
    if absent:
        if origin_committed is not None:raise ValueError('height origin unexpected commit')
    elif origin_committed is None or not math.isclose(origin_committed,origin,rel_tol=0,abs_tol=2e-7):
        raise ValueError('height origin commit')
    if absent:
        if any(x is not None for x in committed):raise ValueError('height unexpected commit')
    elif not torch.allclose(t(committed),selected if d['reference_valid']==1 else old,atol=2e-6,rtol=0):
        raise ValueError('height commit')


def verify_support_heave(sample,cfg):
    """Independent scalar height-error, rate, history and commit audit."""
    d=sample['teacher_diagnostic'];c=sample['feedback_context']
    enabled=bool(cfg.load_feedback and not cfg.coherent_support_pose and c.get('execution_enabled') and c.get('control_phase') in (2,3,4))
    if d.get('heave_enabled',0)!=int(enabled):raise ValueError('heave enable mismatch')
    if not enabled:return
    previous=c.get('support_heave_previous')
    error_history=c.get('support_heave_error0_previous')
    if (previous is None)!=(error_history is None):raise ValueError('heave paired history')
    old=0. if previous is None else previous[0]
    error=d['command_requested_root_z']-c['measured_root'][2]
    error0=error if error_history is None else error_history[0]
    if d['heave_captured']!=int(previous is None):raise ValueError('heave capture')
    dynamic=sample.get('dynamic_support')
    if dynamic is not None:
        for key,record in (('support_heave',previous),('support_heave_error0',error_history)):
            history=dynamic['pre'].get(key)
            if (history is None)!=(record is None):raise ValueError('heave history presence')
            if history is not None:
                # Scalar state is [B], unlike the four-wheel height state.
                value=history['tensor'][0]
                if value!=record[0]:raise ValueError('heave history mismatch')
    dt=c['dt']
    if not all(math.isfinite(x) for x in (old,error,error0,dt)) or dt<=0 or abs(old)>.020000001:
        raise ValueError('heave nonfinite or bounds')
    target=0. if c['control_phase']==4 else max(-.02,min(.02,-(error-error0)))
    proposed=old+max(-.02*dt,min(.02*dt,target-old))
    beta=d['execution_fraction'] if d['reference_valid']==1 else 0.
    selected=old+beta*(proposed-old)
    for name,value in (('error0',error0),('previous',old),('proposed',proposed),('selected',selected)):
        actual=d['heave_'+name]
        if actual is None or not math.isclose(actual,value,rel_tol=0,abs_tol=2e-7):raise ValueError('heave '+name)
    absent=(d['reference_valid']!=1 and previous is None) or (d['reference_valid']==1 and sample['phase']==0)
    committed=d['heave_committed']
    if absent:
        if committed is not None:raise ValueError('heave unexpected commit')
    elif committed is None or not math.isclose(committed,selected if d['reference_valid']==1 else old,rel_tol=0,abs_tol=2e-7):
        raise ValueError('heave commit')


def verify_execution_geometry(sample,cfg,*,replay_backend='cpu'):
    """Independent of target builder/transaction: frames, FK start and residual.

    Evaluates recorded encoded targets as well as mathematical attempted q;
    does not certify that the physical robot reached either one.
    """
    import torch
    from ame_baseline.m1_teacher_ik import body_feet
    from ame_baseline.m1_reference_teacher import LEG_COLUMNS
    from ame_baseline.m1_teacher_pose import _rotation as producer_rotation
    def _rotation(quats):
        if not cfg.coherent_support_pose:
            return producer_rotation(quats)
        # Independent scalar reconstruction: a producer transform defect must
        # not silently change both the recorded goal and this audit's answer.
        matrices=[]
        for values in quats.detach().cpu().tolist():
            norm=math.sqrt(sum(v*v for v in values))
            if not math.isfinite(norm) or norm<=0:
                raise ValueError('invalid coherent quaternion')
            w,x,y,z=(v/norm for v in values)
            matrices.append([[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],
                             [2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],
                             [2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]])
        return torch.tensor(matrices,dtype=quats.dtype,device=quats.device)
    d=sample['teacher_diagnostic']; c=sample['feedback_context']
    mode=d.get('execution_mode',0)
    if mode==0: return
    expected_mode=2 if c['control_phase']==4 else 1 if c['control_phase'] in (2,3) else 0
    if mode!=expected_mode or not cfg.slow_rolling or not c.get('execution_enabled'):
        raise ValueError('execution mode/phase mismatch')
    device=torch.device(replay_backend)
    dtype=getattr(torch,sample['action_target_dtype'])
    t=lambda x:torch.tensor([x],dtype=dtype,device=device)
    wheels=t([[d[f'command_attempted_world_wheel_{leg}_{axis}'] for axis in 'xyz'] for leg in range(4)])
    command=t([d['command_attempted_root_'+axis] for axis in ('x','y','z','qw','qx','qy','qz')])
    measured=t(c['measured_root']+c['measured_quat'])
    for root in (command,measured):
        if not bool(torch.isfinite(root).all()) or not bool((root[:,3:].norm(dim=-1)-1).abs().max()<=1e-3):
            raise ValueError('invalid geometry pose')
    transform=lambda root:torch.einsum('bij,bkj->bki',_rotation(root[:,3:]).transpose(-1,-2),wheels-root[:,:3,None].transpose(1,2))
    goal=transform(command)
    active=c['active_wheel']
    if type(active)!=int or not 0<=active<4: raise ValueError('invalid active wheel')
    if mode==1 and cfg.load_feedback and not cfg.coherent_support_pose:
        goal=torch.einsum('bij,bkj->bki',_rotation(measured[:,3:]).transpose(-1,-2),
            wheels-command[:,:3,None].transpose(1,2))
    if mode==1: goal[:,active]=transform(measured)[:,active]
    if cfg.load_feedback:
        if d['load_enabled']!=1: raise ValueError('missing load correction')
        if not cfg.coherent_support_pose:
            if d.get('height_enabled')!=1:raise ValueError('missing support height source')
            world_goal=measured[:,:3,None].transpose(1,2)+torch.einsum('bij,bkj->bki',_rotation(measured[:,3:]),goal)
            adjustment=torch.zeros_like(goal)
            origin=d.get('height_origin')
            if origin is None or not math.isfinite(origin):raise ValueError('missing height origin')
            adjustment[:,:,2]=(t([d[f'height_proposed_{j}'] for j in range(4)])
                +(measured[:,2]-origin)[:,None]-world_goal[:,:,2])
            adjustment[:,active]=0
            goal+=torch.einsum('bij,bkj->bki',_rotation(measured[:,3:]).transpose(-1,-2),adjustment)
            world=torch.zeros_like(goal)
            world[:,:,2]=d['heave_proposed']
            world[:,active]=0
            goal+=torch.einsum('bij,bkj->bki',_rotation(measured[:,3:]).transpose(-1,-2),world)
        world=torch.zeros_like(goal)
        world[:,:,2]=t([d[f'load_attempted_{j}'] for j in range(4)])
        goal+=torch.einsum('bij,bkj->bki',_rotation(measured[:,3:]).transpose(-1,-2),world)
    heading=0.
    if mode==1 and cfg.load_feedback and not cfg.coherent_support_pose:
        # Independent yaw reconstruction: do not invoke the producer heading helper.
        def raw_yaw(quat):
            w,x,y,z=(float(v) for v in quat)
            # Valid quaternions may differ slightly from unit norm. Dividing
            # both atan2 arguments by norm squared gives the normalized yaw.
            return math.atan2(2*(w*z+x*y),w*w+x*x-y*y-z*z)
        error=raw_yaw(measured[0,3:])-raw_yaw(command[0,3:])
        heading=max(-.05,min(.05,math.atan2(math.sin(error),math.cos(error))))
        relative=torch.einsum('bij,bkj->bki',_rotation(measured[:,3:]),goal)
        rotated=relative.clone()
        rotated[:,:,0]=math.cos(heading)*relative[:,:,0]-math.sin(heading)*relative[:,:,1]
        rotated[:,:,1]=math.sin(heading)*relative[:,:,0]+math.cos(heading)*relative[:,:,1]
        corrected=torch.einsum('bij,bkj->bki',_rotation(measured[:,3:]).transpose(-1,-2),rotated)
        for j in range(4):
            if j!=active:goal[:,j]=corrected[:,j]
    reported_heading=d.get('execution_heading_delta')
    # Float32 computes two atan2 values near +/-pi before subtraction and
    # wrapping; double reconstruction must allow their accumulated rounding.
    # This is an audit-only angular allowance, not a control/safety threshold.
    heading_roundoff=max(2e-7,16*torch.finfo(dtype).eps)
    if (isinstance(reported_heading,bool) or not isinstance(reported_heading,(int,float))
            or not math.isclose(reported_heading,heading,rel_tol=0,abs_tol=heading_roundoff)):
        raise ValueError('independent support heading')
    fraction=d['execution_fraction']
    if not isinstance(fraction,(float,int)) or not 0<fraction<=1: raise ValueError('invalid execution fraction')
    intent_fraction=d.get('execution_intent_fraction')
    if (isinstance(intent_fraction,bool) or not isinstance(intent_fraction,(float,int))
            or not fraction<=intent_fraction<=1 or mode!=1 and intent_fraction!=fraction):
        raise ValueError('invalid active intent fraction')
    old_wheels=t(c['accepted_before']['wheels'])
    requested_wheels=t(c['requested']['wheels'])
    if mode==1 and torch.equal(old_wheels[:,active],requested_wheels[:,active]) and intent_fraction!=fraction:
        raise ValueError('intent fraction changed without active request')
    expected_wheels=old_wheels+fraction*(requested_wheels-old_wheels)
    if mode==1:
        expected_wheels[:,active]=old_wheels[:,active]+intent_fraction*(requested_wheels[:,active]-old_wheels[:,active])
    if not torch.allclose(wheels,expected_wheels,rtol=0,atol=2e-6):
        raise ValueError('independent active intent commit')
    for prefix in ('attempted', 'accepted'):
        physical=t([[d[f'{prefix}_world_wheel_{leg}_{axis}'] for axis in 'xyz'] for leg in range(4)])
        expected=expected_wheels if prefix=='attempted' or d['reference_valid']==1 else t(c['retained_physical']['wheels'])
        if not torch.allclose(physical,expected,rtol=0,atol=2e-6):
            raise ValueError('independent physical intent '+prefix)
    active_fraction=d.get('execution_active_fraction')
    if (isinstance(active_fraction,bool) or not isinstance(active_fraction,(float,int))
            or not fraction<=active_fraction<=1
            or mode!=1 and active_fraction!=fraction):
        raise ValueError('invalid active execution fraction')
    start=body_feet(t(c['last_applied_q']))
    step=start+fraction*(goal-start)
    if mode==1:step[:,active]=start[:,active]+active_fraction*(goal[:,active]-start[:,active])
    for kind,expected in (('goal',goal),('step',step)):
        recorded=t([[d[f'execution_body_{kind}_{leg}_{axis}'] for axis in 'xyz'] for leg in range(4)])
        if not torch.allclose(recorded,expected,rtol=0,atol=2e-6): raise ValueError('independent execution '+kind)
    q=t([d[f'attempted_q_{j}'] for j in range(12)])
    residual=(body_feet(q)-step).norm(dim=-1)
    tolerance=t([min(cfg.ik_tolerance_m,.0001) if (mode==1 and j==active) or (cfg.load_feedback and j!=active) else cfg.ik_tolerance_m for j in range(4)])
    recorded_tolerance=t([d[f'execution_tolerance_m_{j}'] for j in range(4)])
    if not torch.allclose(recorded_tolerance,tolerance,rtol=0,atol=1e-9): raise ValueError('execution tolerance mismatch')
    for name,points in (('start',start),('goal',goal),('solved',body_feet(q))):
        world=measured[:,:3]+torch.einsum('bij,bj->bi',_rotation(measured[:,3:]),points[:,active])
        recorded=d[f'execution_active_world_{name}_z']
        if recorded is None or not math.isclose(recorded,float(world[0,2]),rel_tol=0,abs_tol=2e-6): raise ValueError('execution world '+name)
    reported=t([d[f'ik_residual_m_{j}'] for j in range(4)])
    if not torch.allclose(residual,reported,rtol=2e-5,atol=2e-6): raise ValueError('independent IK residual')
    if d['reference_valid']==1:
        applied=t([sample['applied_targets'][j] for j in LEG_COLUMNS])
        encoded_residual=(body_feet(applied)-step).norm(dim=-1)
        if not bool((residual<=tolerance+2e-6).all()): raise ValueError('attempted IK residual')
        if not bool((encoded_residual<=tolerance+2e-6).all()): raise ValueError('encoded IK residual')


def verify_feedback_transaction(sample,cfg,*,replay_backend='cpu',require_backend_evidence=False):
    """Authenticate first/final/committed claims and the actual returned command."""
    from ame_baseline.m1_reference_teacher import TEACHER_DIAGNOSTIC_INTEGER_FIELDS
    try:
        check_producer_backend(sample.get('producer_backend'),replay_backend,required=require_backend_evidence)
    except (ValueError,RuntimeError,TypeError):
        return ['producer/replay backend evidence unavailable or mismatched']
    try:
        d=sample['teacher_diagnostic']; context=sample['feedback_context']
        if context is None:
            # No bounded transaction (reset/braking/safety/candidate refusal).
            if (d['feedback_passes']!=0 or d['feedback_first_transaction_valid']!=0
                    or d['reference_valid']!=0 or sample.get('teacher_valid',False)):
                raise ValueError('missing transaction context')
            if any(d[f'nominal_ik_residual_m_{i}'] is not None for i in range(4)):
                raise ValueError('unbound nominal IK')
            feedback=cfg.feedback
            for kind,limit in (
                    ('integral_committed',(feedback.integral_limit_x,feedback.integral_limit_yz,feedback.integral_limit_yz)),
                    ('output_committed',(feedback.output_limit_x,feedback.output_limit_yz,feedback.output_limit_yz))):
                for axis,bound in zip('xyz',limit):
                    if not math.isfinite(d[f'feedback_{kind}_{axis}']) or abs(d[f'feedback_{kind}_{axis}'])>bound+1e-7:
                        raise ValueError('missing committed hold evidence')
            return []
        if sample['action_target_dtype'] not in ('float32','float64'): raise ValueError('invalid dtype')
        if d.get('execution_mode',0)!=0:
            if not context.get('execution_enabled') or 'measured_quat' not in context:
                raise ValueError('missing measured execution input')
            if context['active_wheel']!=d['execution_active_wheel']:
                raise ValueError('execution active wheel mismatch')
            if 'preparation_input' in sample:
                if context['measured_root']+context['measured_quat']!=sample['preparation_input']['root'][:7]:
                    raise ValueError('execution pose differs from actual decision input')
        expected_json,action,executable=replay_feedback_transaction(json.dumps(context,sort_keys=True),
            json.dumps(asdict(cfg),sort_keys=True),sample['action_target_dtype'],sample['phase'],replay_backend=replay_backend)
        expected=json.loads(expected_json)
        # This replay authenticates the bounded command transaction, not the
        # outer phase controller. Do not capture wheel_progress_ready merely
        # because it shares a prefix with the actual wheel-speed evidence.
        checked=[name for name in expected if name.startswith(('feedback_',
            'wheel_nominal_surface_speed_','wheel_final_surface_speed_','wheel_headroom_limited','command_requested_',
            'command_attempted_','command_accepted_','nominal_ik_','ik_','attempted_','accepted_','requested_','last_applied_q_','execution_'))]
        checked+=['reference_valid','backtrack_index']
        # Accepted joint target is the final encoded target, not the mathematical predecoder q.
        integer=set(TEACHER_DIAGNOSTIC_INTEGER_FIELDS)
        for name in checked:
            a,b=d[name],expected[name]
            if a is None or b is None:
                if a is not b: raise ValueError(name)
            elif name in integer:
                if type(a) is not int or a!=b: raise ValueError(name)
            else:
                # Independent replay on the producer-matching backend.
                # These are audit roundoff allowances, not controller gates.
                tolerance=2e-5 if '_q_' in name or 'ik_residual_m_' in name else 2e-6 if (
                    '_root_' in name or '_wheel_' in name and not name.startswith('wheel_')) else 2e-7
                if not math.isclose(a,b,rel_tol=2e-5,abs_tol=tolerance): raise ValueError(name)
        decoded=decoded_request_targets(tuple(sample['teacher_action']),tuple(context['default_joint_pos']),
            sample['action_target_dtype'],replay_backend=replay_backend)
        if list(decoded)!=sample['applied_targets']: raise ValueError('actual receipt')
        verify_execution_geometry(sample,cfg,replay_backend=replay_backend)
        verify_load_feedback(sample,cfg)
        verify_support_height(sample,cfg)
        verify_support_heave(sample,cfg)
        from ame_baseline.m1_reference_teacher import LEG_COLUMNS
        from ame_baseline.m1_ame_contract import M1_LEG_ACTION_SCALE_RAD,M1_WHEEL_ACTION_SCALE_RAD_S
        from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M
        # Only the independent mathematical replay is approximate. The
        # actual teacher request/process/all four apply receipts remain exact.
        if not executable or any(not math.isclose(a,b,rel_tol=0.,abs_tol=(
            2e-5/M1_LEG_ACTION_SCALE_RAD if i in LEG_COLUMNS else
            2e-7/(M1_WHEEL_RADIUS_M*M1_WHEEL_ACTION_SCALE_RAD_S)))
            for i,(a,b) in enumerate(zip(action,sample['teacher_action']))):
            raise ValueError('final or fallback action')
        return []
    except (KeyError,TypeError,ValueError,RuntimeError,IndexError,AttributeError):
        return ['bounded feedback transaction evidence mismatch']


def actuation_snapshot(robot,row,*,env_id,episode_id,frame,sim_time):
    from ame_baseline.m1_teacher_adapter import read_actuation_evidence
    evidence=read_actuation_evidence(robot)
    return {**{key:(value[row].detach().clone().tolist() if hasattr(value,'detach') else
        list(value) if isinstance(value,tuple) else copy.deepcopy(value)) for key,value in evidence.items()},
        'env_id':env_id,'episode_id':episode_id,'frame':frame,'sim_time':sim_time,
        'effort_substep_index':3,'effort_compute_sim_time':sim_time-.005}


def verify_actuation_evidence(sample):
    from ame_baseline.m1_teacher_adapter import ACTUATION_SOURCES
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES
    try:
        e=sample['actuation_evidence']
        if (e['joint_names']!=list(M1_ASSET_JOINT_NAMES) or e['leg_joint_names']!=list(M1_PLANNER_JOINT_NAMES)
                or e['sources']!=ACTUATION_SOURCES or e['valid'] is not True
                or any(e[k]!=sample[k] for k in ('env_id','episode_id','frame','sim_time'))
                or e['effort_substep_index']!=3
                or not math.isclose(e['effort_compute_sim_time'],sample['teacher_input_sim_time']+.015,abs_tol=1e-6)):
            raise ValueError('actuation identity/source mismatch')
        for key,width in (('joint_vel',16),('leg_computed_effort',12),('leg_applied_effort',12)):
            if len(e[key])!=width or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in e[key]):
                raise ValueError('missing measured actuation')
        return []
    except (KeyError,TypeError,ValueError): return ['missing or invalid measured actuation evidence']


class DiagnosticBatchGate:
    """Diagnostic-only stop latch; a peer interruption is not physical failure."""
    def __init__(self,acceptance): self.acceptance=acceptance; self.failure=None

    @staticmethod
    def sample_reason(sample):
        for reason in ('failure_locked','collision','support_lost','penetration','failure'):
            if sample.get(reason,False): return reason
        if sample.get('action_matches_request') is False or sample.get('applied_target_valid') is False:
            return 'action_evidence_invalid'
        if sample.get('actuation_evidence',{}).get('valid') is False: return 'actuation_evidence_invalid'
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
            velocity=root[7:10].clone()
            if cfg.slow_rolling:
                velocity[:2]-=cfg.rolling_speed_m_s*torch.stack((rpy[2].cos(),rpy[2].sin()))
            if (velocity.norm()>cfg.balance_speed_limit_m_s
                    or rpy[:2].abs().max()>cfg.recovery_tilt_rad
                    or root[10:13].norm()>cfg.recovery_rate_rad_s): return False
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


def verify_trace(trace,samples,*,allow_empty=False):
    """Read and hash current bytes; metadata alone never certifies trajectory."""
    errors=[]
    try:
        path=Path(trace['path']); stat=path.stat(); raw=path.read_bytes()
        if (not isinstance(trace.get('bytes'),int) or trace['bytes']<0 or (trace['bytes']==0 and not allow_empty)
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


def decoded_request_targets(action,defaults,dtype,*,replay_backend='cpu'):
    import torch
    backend=capture_producer_backend(replay_backend)
    with torch.device(backend['device']):
        return _cached_decoded_request_targets(action,defaults,dtype,backend['device'],json.dumps(backend,sort_keys=True))


@lru_cache(maxsize=256)
def _cached_decoded_request_targets(action,defaults,dtype,backend,backend_json):
    """Cache pure decoding for identical inputs only; never cache validity."""
    import torch
    from ame_baseline.m1_ame_contract import m1_action_targets
    if dtype not in ('float32','float64'): raise ValueError('unsupported recorded action target dtype')
    target=m1_action_targets(torch.tensor([action],dtype=getattr(torch,dtype),device=backend),
        torch.tensor([defaults],dtype=getattr(torch,dtype),device=backend))
    return tuple(target[0].tolist())


decoded_request_targets.cache_clear=_cached_decoded_request_targets.cache_clear
decoded_request_targets.cache_info=_cached_decoded_request_targets.cache_info


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


def verify_aborted_decision(record):
    """An abort is unexecuted input evidence, never a trajectory sample."""
    try:
        artifact=record['abort_artifact']; decision=record['aborted_decision']
        raw=Path(artifact['path']).read_bytes()
        if (len(raw)!=artifact['bytes'] or not raw or hashlib.sha256(raw).hexdigest()!=artifact['sha256']
                or not same_json_evidence(json.loads(raw),decision)
                or decision['kind']!='unexecuted_teacher_decision'
                or (decision['env_id'],decision['episode_id'])!=(record['env_id'],record['episode_id'])
                or decision['input_state']['episode_id']!=decision['episode_id']
                or decision['input_state']['control_step']!=decision['frame']
                or decision['frame']!=(record['samples'][-1]['frame'] if record['samples'] else 0)
                or decision['physics_completed'] is not False
                or decision['student_demonstration_usable'] is not False
                or len(decision['teacher_action'])!=16
                or (decision['teacher_executable'] and not all(math.isfinite(v) for v in decision['teacher_action']))
                or type(decision['teacher_executable']) is not bool
                or decision['teacher_executable']!=(decision['env_id'] not in decision['execution_abort']['failed_env_ids'])
                or ('execution_abort' in record and not same_json_evidence(record['execution_abort'],decision['execution_abort']))
                or any(key in decision for key in ('executed_action','processed_targets','applied_targets','applied_substeps'))):
            raise ValueError('abort bytes or identity mismatch')
        return []
    except (KeyError,OSError,TypeError,ValueError,IndexError):
        return ['aborted decision artifact verification failed']


def verify_episode(record,*,replay_backend='cpu',require_backend_evidence=False):
    """Evidence validation and success are distinct; failures still count episodes."""
    aborted=(record.get('end')=='teacher_nonexecutable' or 'aborted_decision' in record
        or 'abort_artifact' in record or 'execution_abort' in record)
    errors = verify_aborted_decision(record) if aborted else []
    try:
        check_producer_backend(record.get('producer_backend'),replay_backend,required=require_backend_evidence)
    except (ValueError,RuntimeError,TypeError): errors.append('producer/replay backend evidence unavailable or mismatched')
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    raw_names=record.get('raw_joint_names',[])
    redesigned=record.get('schema_version')==SCHEMA_VERSION
    if not redesigned: errors.append('legacy schema incompatible with dual selection/apply evidence')
    errors.extend(verify_recovery_record(record))
    if len(raw_names)!=16 or len(set(raw_names))!=16 or set(raw_names)!=set(M1_ASSET_JOINT_NAMES):
        errors.append('missing unique raw joint contract')
    samples = record.get('samples', [])
    from ame_baseline.m1_reference_teacher import TeacherConfig
    readiness_cfg=None
    if redesigned:
        try:
            if set(record['teacher_config'])!=set(asdict(TeacherConfig())):
                raise ValueError('incomplete readiness config')
            from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig as FeedbackConfig
            config=copy.deepcopy(record['teacher_config'])
            config['feedback']=FeedbackConfig(**config['feedback'])
            readiness_cfg=TeacherConfig(**config)
            if readiness_cfg.fingerprint!=record['teacher_hash']: raise ValueError('config hash mismatch')
        except (KeyError,TypeError,ValueError): errors.append('missing readiness configuration evidence')
    stage = record.get('stage')
    if not samples or stage not in (0,3):
        if aborted: errors.extend(verify_trace(record.get('trace') or {},samples,allow_empty=True))
        return dict(complete=False, success=False, errors=sorted(set(errors+['missing trajectory or stage'])),
            unsafe=False,invalid_teacher=True,failure_locked=False,student_demonstration_usable=False)
    start_time = samples[0].get('sim_time', 0.)-.02
    for index, sample in enumerate(samples, 1):
        try:
            check_producer_backend(sample.get('producer_backend'),replay_backend,required=require_backend_evidence)
        except (ValueError,RuntimeError,TypeError):
            errors.append('sample producer/replay backend evidence unavailable or mismatched')
        if sample.get('producer_backend')!=record.get('producer_backend'):
            errors.append('sample producer backend differs from record')
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
                        or not sample['applied_target_valid'] or sample['teacher_executable'] is not True
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
                from ame_baseline.m1_reference_teacher import TEACHER_DIAGNOSTIC_FIELDS,TEACHER_DIAGNOSTIC_INTEGER_FIELDS
                if set(sample['teacher_diagnostic'])!=set(TEACHER_DIAGNOSTIC_FIELDS):
                    errors.append('missing named teacher diagnostic schema')
                if any(type(sample['teacher_diagnostic'].get(name)) is not int for name in TEACHER_DIAGNOSTIC_INTEGER_FIELDS):
                    errors.append('invalid discrete teacher diagnostic evidence')
                errors.extend(verify_actuation_evidence(sample))
                if readiness_cfg is not None: errors.extend(verify_feedback_transaction(sample,readiness_cfg,
                    replay_backend=replay_backend,require_backend_evidence=require_backend_evidence))
                if readiness_cfg is not None: errors.extend(verify_selection_sample(sample,readiness_cfg,
                    replay_backend=replay_backend,require_backend_evidence=require_backend_evidence))
                if readiness_cfg is not None and readiness_cfg.slow_rolling:
                    errors.extend(verify_dynamic_support_sample(sample,readiness_cfg,replay_backend=replay_backend))
                    current_dynamic=sample.get('dynamic_support')
                    if index>1 and current_dynamic is not None:
                        previous_dynamic=samples[index-2].get('dynamic_support')
                        if previous_dynamic is not None and current_dynamic['identity'][0]==previous_dynamic['identity'][0]:
                            if not _dynamic_equal(current_dynamic['pre'],previous_dynamic['post']):
                                errors.append('dynamic history chain mismatch')
                context=sample.get('feedback_context')
                if context is not None:
                    try:
                        if (context['measured_root']!=sample['preparation_input']['root'][:3]
                                or (context.get('execution_enabled',False) and context.get('measured_quat')!=sample['preparation_input']['root'][3:7])
                                or context['q_seed']!=sample['teacher_input_leg_pos']
                                or context['default_joint_pos']!=sample['action_default_joint_pos']
                                or context['last_applied_q']!=sample['last_applied_leg_target']
                                or not math.isclose(context['dt'],.02,abs_tol=1e-7)):
                            raise ValueError('context/input mismatch')
                        if index>1:
                            prior=samples[index-2]
                            for kind in ('integral','output'):
                                if any(not math.isclose(context[kind+'_before'][j],
                                    prior['teacher_diagnostic'][f'feedback_{kind}_committed_{axis}'],abs_tol=2e-7)
                                    for j,axis in enumerate('xyz')): raise ValueError('feedback state continuity')
                    except (KeyError,TypeError,ValueError): errors.append('feedback context differs from real decision input')
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
                    decoded=decoded_request_targets(tuple(sample['teacher_action']),tuple(defaults),
                        sample['action_target_dtype'],replay_backend=replay_backend)
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
        hold=PreparationHoldCounter()
        for sample in samples:
            ready=readiness_cfg is not None and preparation_observed(sample,readiness_cfg)
            held=hold.update(sample['env_id'],input_ready=ready,output_ready=ready,
                frame=sample['frame'],episode_id=sample['episode_id'])
            if sample.get('scope_observation_complete') and not ready:
                errors.append('preparation endpoint lacks same-decision input and post-action measured readiness')
            if sample.get('scope_observation_complete') and not held:
                errors.append('preparation endpoint lacks five additional consecutive ready frames')
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
            and samples[-1].get('recovery_result',{}).get('success')==[True]
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


def verify_suite(records, *, diagnostic=False,replay_backend='cpu',require_backend_evidence=False):
    identities = [(r['stage'],r['seed'],r['env_id'],r['episode_id']) for r in records]
    verified = [verify_episode(r,replay_backend=replay_backend,
        require_backend_evidence=require_backend_evidence) for r in records]
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


def probe_teacher_config(*, slow_rolling=False, scope='course', load_feedback=False, bounded_crossing_attitude=False, coherent_support_pose=False):
    from ame_baseline.m1_reference_teacher import TeacherConfig
    if slow_rolling and scope not in ('course','first-obstacle'):
        raise ValueError('slow rolling requires course or first-obstacle scope')
    return TeacherConfig(slow_rolling=slow_rolling,load_feedback=load_feedback,
                         bounded_crossing_attitude=bounded_crossing_attitude,coherent_support_pose=coherent_support_pose)


def add_teacher_motion_options(parser):
    parser.add_argument('--slow-rolling',action='store_true',
                        help='0.05m/s continuous rolling teacher; no normal phase stop')
    parser.add_argument('--load-feedback',action='store_true',help='bounded measured support-load feedback')
    parser.add_argument('--bounded-crossing-attitude',action='store_true',
                        help='bounded orientation search during dynamic LIFT/PASS only')
    parser.add_argument('--coherent-support-pose',action='store_true',
                        help='full support XYZ posture with load-only bounded correction')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--python', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mode', choices=('smoke','contract','teacher','acceptance'), default='smoke')
    parser.add_argument('--diagnostic-steps', type=int, default=200)
    parser.add_argument('--teacher-scope',choices=TEACHER_SCOPES,default='course')
    add_teacher_motion_options(parser)
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
    probe_teacher_config(slow_rolling=args.slow_rolling,scope=args.teacher_scope,load_feedback=args.load_feedback,
                         bounded_crossing_attitude=args.bounded_crossing_attitude,coherent_support_pose=args.coherent_support_pose)
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
            run = NativeProbe(env,wrapper,output,candidate,slow_rolling=args.slow_rolling,load_feedback=args.load_feedback,
                              bounded_crossing_attitude=args.bounded_crossing_attitude,coherent_support_pose=args.coherent_support_pose)
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
        if not bool(output.executable.all()):
            raise RuntimeError('nonexecutable teacher batch cannot begin action evidence')
        producer_backend=capture_producer_backend(output.action.device)
        self.pending=[]; self.observing=True; self.processed=None; self.executed=None; self.applied=[]
        for row in range(len(state.episode_id)):
            ages=teacher._rows[row] or {}
            requested=None
            if hasattr(state,'default_joint_pos'):
                from ame_baseline.m1_ame_contract import m1_action_targets
                requested=m1_action_targets(output.action[row:row+1],state.default_joint_pos[row:row+1])[0].tolist()
            self.pending.append(dict(teacher_input_frame=int(state.control_step[row]),
                producer_backend=copy.deepcopy(producer_backend),
                teacher_input_episode_id=int(state.episode_id[row]),teacher_input_sim_time=float(sim_time),
                teacher_action=output.action[row].detach().clone().tolist(),
                teacher_executable=bool(output.executable[row]),
                requested_processed_targets=requested,
                action_default_joint_pos=state.default_joint_pos[row].detach().clone().tolist()
                    if hasattr(state,'default_joint_pos') else None,
                action_target_dtype=str(state.default_joint_pos.dtype).removeprefix('torch.')
                    if hasattr(state,'default_joint_pos') else None,
                last_applied_leg_target=state.last_applied_leg_target[row].detach().clone().tolist()
                    if hasattr(state,'last_applied_leg_target') else None,
                teacher_diagnostic=diagnostic_json(output.diagnostic[row].tolist())
                    if hasattr(output,'diagnostic') else {},
                feedback_context=feedback_context_for(teacher,state,row),
                selection_context=selection_context_for(teacher,state,row),
                dynamic_support=dynamic_context_for(teacher,state,row),
                teacher_input_leg_pos=state.leg_pos[row].detach().clone().tolist() if hasattr(state,'leg_pos') else None,
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
    def __init__(self, env, wrapper, output, candidate, *, slow_rolling=False,load_feedback=False,bounded_crossing_attitude=False,coherent_support_pose=False):
        import torch
        from ame_baseline.m1_teacher_adapter import ReferenceTeacherAdapter, WHEEL_BODY_NAMES
        from ame_baseline.m1_reference_teacher import TeacherConfig
        from extension.parallelism.rl_adapter import resolve_named_indices
        self.torch=torch; self.env=env; self.w=wrapper; self.output=output
        self.producer_backend=capture_producer_backend(env.device)
        self.replay_backend=self.producer_backend['device']
        self.robot=env.scene['robot']; self.sensor=env.scene['contact_forces']
        self.raw_joint_names=tuple(self.robot.joint_names)
        self.adapter=ReferenceTeacherAdapter(wrapper); self.teacher_cfg=probe_teacher_config(slow_rolling=slow_rolling,load_feedback=load_feedback,
            bounded_crossing_attitude=bounded_crossing_attitude,coherent_support_pose=coherent_support_pose)
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
        from ame_baseline.m1_crossing_recovery import RECOVERY_CONTRACT
        files={str(p.relative_to(candidate)):file_digest(p) for folder in CANDIDATE_DOMAINS
            for p in sorted((candidate/folder).rglob('*.py'))}
        files['scripts/probe_m1_teacher.py']=file_digest(Path(__file__))
        self.write('source.json',dict(candidate=str(candidate),python=sys.executable,files=files,
            producer_backend=copy.deepcopy(self.producer_backend),
            code_sha256=digest(files),teacher=asdict(self.teacher_cfg),teacher_hash=self.teacher_cfg.fingerprint,
            loaded_modules=loaded_candidate_modules(candidate),
            effective_cfg_sha256=digest(env.cfg.to_dict()),effective_cfg=env.cfg.to_dict()))
        print('CANDIDATE_SOURCE '+json.dumps(dict(candidate=str(candidate),python=sys.executable,
            code_sha256=digest(files),teacher_hash=self.teacher_cfg.fingerprint)),flush=True)
        original_reset=env._reset_idx
        def reset_hook(ids):
            if self.reset_reason == 'natural':
                # Freeze peers too: original_reset reuses live state/receipt and
                # command buffers before wrapper.step returns to the runner.
                self.pre_reset_samples=self.capture_batch_samples()
                for row in ids.tolist():
                    self.terminal[row]=self.pre_reset_samples.get(row) or self.sample(row)
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

    def verification_options(self):
        # Backend is trusted probe configuration, never chosen by a sample.
        return dict(replay_backend=self.replay_backend,require_backend_evidence=True)

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
        self.terminal={}; self.pre_reset_samples={}; self.inner_failed.zero_(); self.frames+=1
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
        from ame_baseline.m1_reference_teacher import LEG_COLUMNS
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
        action['actuation_evidence']=actuation_snapshot(self.robot,row,env_id=row,
            episode_id=int(self.episode[row]),frame=int(self.frames[row]),sim_time=float(env.sim.current_time))
        state=getattr(self,'_sample_state',None)
        if state is None: state=self.state()
        action['preparation_output']=readiness_measurement(state,row,float(env.sim.current_time))
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
            wheel_quaternion=quat[0].tolist(),default_leg_pos=state.default_joint_pos[row,list(LEG_COLUMNS)].tolist(),
            # Keep the verified double control period for the double simulator
            # clock; state.dt remains the unchanged float32 Teacher input.
            nominal_root_z_w=float(state.nominal_root_z_w[row]),control_dt_s=float(env.step_dt),
            measurement_valid=bool(state.measurement_valid[row]),base_contact=failures['base_contact'],
            wheel_bottom=bottom.tolist(),obstacle_top=course['centers_top'][row,:,2].tolist(),
            collision=bool(snap['signal'][row]>0),support_lost=lost,penetration=penetration,
            failure=failure,timeout=timeout,termination_terms=failures,budget={k:v[row].tolist() for k,v in snap.items()},
            receipt=self.pairs(ids,receipt),far_side_recovery=self.pairs(ids,receipt&far),
            root=self.robot.data.root_state_w[row].tolist(),**raw_joint_snapshot(self.robot,row),
            course_ids=ids.tolist(),course_centers_top=course['centers_top'][row].tolist(),
            course_half_extents=course['half_extents'][row].tolist(),course_valid=course['valid'][row].tolist(),**action)

    def capture_batch_samples(self):
        """Observe every recording row before any automatic or manual reset."""
        self._sample_state=self.state()
        try: return {row:self.sample(row) for row in list(self.recording)}
        finally: self._sample_state=None

    def begin_video(self,row,seed,stage):
        import imageio.v2 as imageio
        from ame_baseline.m1_crossing_recovery import CrossingRecoveryTracker
        state=self.state(); rows=self.torch.tensor([row],dtype=self.torch.long,device=self.env.device)
        pairs=recovery_pairs(self.pairs(state.course_ids[row],state.required_wheels[row]),self.scope)
        scope=capture_recovery_scope(state,rows,[pairs],scope_ids=self.episode[rows])
        stem=f'stage{stage}_seed{seed}_env{row}_episode{int(self.episode[row])}'
        path=self.output/(stem+'.mp4')
        self.recording[row]=dict(writer=imageio.get_writer(str(path),fps=10,codec='libx264'),
            path=path,indices=[],times=[],samples=[],seed=seed,stage=stage,
            initial_root=self.robot.data.root_pos_w[row].tolist(),command_distance=0.,
            initial_root_quat_w=state.root_quat_w[row].tolist(),recovery_scope_object=scope,
            recovery_nominal_root_z_w=float(state.nominal_root_z_w[row]),
            recovery_tracker=CrossingRecoveryTracker(scope),
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
        from ame_baseline.m1_crossing_recovery import RECOVERY_CONTRACT
        verification_options=self.verification_options()
        rec=self.recording[row]
        self.video_frame(row,terminal=True)
        rec['writer'].close(); rec['trace'].close()
        video=dict(path=str(rec['path']),sha256=file_digest(rec['path']),bytes=rec['path'].stat().st_size,
            isolated_robot=self.video_validated,nonblack=self.video_validated,
            frame_indices=rec['indices'],sim_times=rec['times'],first_frame=rec['indices'][0],last_frame=rec['indices'][-1])
        result=dict(schema_version=SCHEMA_VERSION,teacher_scope=self.scope,
            producer_backend=copy.deepcopy(self.producer_backend),
            diagnostic_active_wheel=self.diagnostic_wheel,
            stage=rec['stage'],seed=rec['seed'],env_id=row,episode_id=int(self.episode[row]),
            raw_joint_names=list(self.raw_joint_names),
            teacher_config=asdict(self.teacher_cfg),teacher_hash=self.teacher_cfg.fingerprint,
            required=required,samples=rec['samples'],terminal=rec['samples'][-1] if rec['samples'] else None,video=video,
            initial_root=rec['initial_root'],command_distance=rec['command_distance'],
            initial_root_quat_w=rec['initial_root_quat_w'],recovery_contract=RECOVERY_CONTRACT,
            recovery_nominal_root_z_w=rec['recovery_nominal_root_z_w'],
            recovery_scope={**recovery_json(rec['recovery_scope_object']),
                'dtype':str(rec['recovery_scope_object'].centers_w.dtype).removeprefix('torch.')},
            end=end,natural_done=natural,timeout=timeout)
        for key in ('aborted_decision','abort_artifact'):
            if key in rec: result[key]=rec[key]
        trace_path=self.output/(rec['path'].stem+'.jsonl')
        result['trace']=dict(path=str(trace_path),sha256=file_digest(trace_path),bytes=trace_path.stat().st_size)
        result['verification']=verify_episode(result,**verification_options)
        result['student_demonstration_usable']=result['verification']['student_demonstration_usable']
        self.write(rec['path'].stem+'.json',result)
        del self.recording[row]
        return result

    def abort_execution(self,state,output,input_time,required,records,schedule,schedule_index,acceptance):
        """Persist unexecuted decisions first, then close attempted episodes.

        No normal sample, decoder, process, apply or physics is invoked. This
        boundary applies to formal acceptance too; planned != attempted.
        """
        self.action_evidence.observing=False
        failed=(~output.executable).nonzero().flatten().tolist()
        source=failed[0]
        abort=dict(env_id=source,episode_id=int(state.episode_id[source]),
            frame=int(state.control_step[source]),reason='teacher_nonexecutable',
            teacher_reason=int(output.reason[source]),failed_env_ids=failed,
            physical_failure=False)
        # Write all raw decisions before video closure/verification can raise.
        for row,rec in self.recording.items():
            decision=dict(kind='unexecuted_teacher_decision',env_id=row,
                episode_id=int(state.episode_id[row]),attempt_id=int(self.attempt[row]),
                frame=int(state.control_step[row]),sim_time=input_time,
                teacher_executable=bool(output.executable[row]),teacher_valid=bool(output.valid[row]),
                teacher_reason=int(output.reason[row]),teacher_action=output.action[row].detach().clone().tolist(),
                teacher_phase=int(output.phase[row]),active_target=int(output.active_target[row]),
                active_wheel=int(output.active_wheel[row]),failure_locked=bool(output.failure_locked[row]),
                teacher_diagnostic=diagnostic_json(output.diagnostic[row].tolist()),
                input_state={key:value[row].detach().clone().tolist() for key,value in vars(state).items()},
                physics_completed=False,student_demonstration_usable=False,
                execution_abort=copy.deepcopy(abort))
            path=self.output/(rec['path'].stem+'.abort.json')
            self.write(path.name,decision)
            rec.update(aborted_decision=decision,abort_artifact=dict(path=str(path),
                bytes=path.stat().st_size,sha256=file_digest(path)))
        for row in list(self.recording):
            record=self.finish_episode(row,required[row],
                'teacher_nonexecutable' if row in failed else 'diagnostic_interrupted',False,False)
            record['execution_abort']=copy.deepcopy(abort)
            record['student_demonstration_usable']=False
            self.write(Path(record['video']['path']).stem+'.json',record)
            records.append(record)
        result=verify_suite(records,diagnostic=not acceptance,**self.verification_options())
        planned=200 if acceptance else 4*len(schedule)
        result.update(execution_aborted=True,execution_abort=abort,planned_episodes=planned,
            attempted_episodes=len(records),failed_attempts=len(failed),
            interrupted_attempts=sum(r['end']=='diagnostic_interrupted' for r in records),
            not_run_episodes=planned-len(records),complete_full_denominator=False,
            milestone_a='EXECUTION_ABORTED',diagnostic_stopped=not acceptance,
            diagnostic_stop=abort if not acceptance else None,
            not_run=[dict(stage=s,wheel=w,scope=self.scope,status='not_run',reason='execution_abort')
                for s,w in schedule[schedule_index+1:]])
        self.write('result.json',result)
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
        probe_teacher_config(slow_rolling=self.teacher_cfg.slow_rolling,scope=scope,load_feedback=self.teacher_cfg.load_feedback,
                             bounded_crossing_attitude=self.teacher_cfg.bounded_crossing_attitude,coherent_support_pose=self.teacher_cfg.coherent_support_pose)
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
                    observe_feedback_transactions(teacher)
                    observe_dynamic_support(teacher)
                    preparation_hold=PreparationHoldCounter()
                    self.episode.fill_(wheel or 0); self.frames.zero_(); self.attempt.zero_()
                    self.bind_reset_identity(range(4))
                    self.failure_bound=FailureDiagnosticBound()
                    quotas=[5]*4 if acceptance else [1]*4
                    batch_start=len(records)
                    required=[self.pairs(self.state().course_ids[i],self.state().required_wheels[i]) for i in range(4)]
                    def decide(state):
                        prepare_feedback_context(teacher,state)
                        observe_preparation_selection(teacher,state,getattr(teacher,'_probe_selection_context',{}))
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
                        if not bool(self.last_output.executable.all()):
                            return self.abort_execution(input_state,self.last_output,input_time,
                                required,records,schedule,schedule_index,acceptance)
                        self.action_evidence.begin(input_state,self.last_output,teacher,input_time)
                        command=self.env.command_manager.get_command('base_velocity')[:,0]
                        for row,rec in self.recording.items(): rec['command_distance']+=float(command[row])*.02
                        _,_,done,_=self.step(self.last_output.action)
                        # Freeze and inspect the whole batch before ending/resetting
                        # any row, so env ordering cannot hide a peer failure.
                        frozen=getattr(self,'pre_reset_samples',{})
                        current=self.capture_batch_samples() if not frozen else frozen
                        batch_samples={row:self.terminal.get(row) if bool(done[row]) else current[row]
                            for row in list(self.recording)}
                        for sample in batch_samples.values():
                            assert sample is not None, 'natural terminal snapshot lost before reset'
                            gate.observe_sample(sample,batch_step)
                        # Complete raw/result capture for every row before any
                        # finish_episode, reset, or Teacher identity bootstrap.
                        endings=[]
                        for row,sample in batch_samples.items():
                            rec=self.recording[row]; frozen_scope=rec['recovery_scope_object']
                            sample['natural_done']=bool(done[row])
                            sample['recovery_input']=recovery_input_from_sample(sample,frozen_scope)
                            sample['recovery_result']=recovery_json(rec['recovery_tracker'].update(
                                capture_recovery_frame(sample['recovery_input'],frozen_scope)))
                        for row,sample in batch_samples.items():
                            rec=self.recording[row]; rec['samples'].append(sample)
                            diagnostic=sample.get('teacher_diagnostic',{})
                            reference_valid=diagnostic.get('reference_valid')==1
                            local_complete=False
                            if scope=='flat-preparation':
                                ready=preparation_observed(sample,self.teacher_cfg)
                                local_complete=preparation_hold.update(row,input_ready=ready,output_ready=ready,
                                    frame=sample['frame'],episode_id=sample['episode_id'])
                            elif scope=='single-wheel':
                                # Measured rise/unloading, then five real loaded, quiet
                                # RESTORE observations. These are local evidence only.
                                raised=sample['wheel_position'][wheel][2]>rec['initial_wheel_z']+.01
                                rec['measured_lift_seen'] |= raised and sample['Fz'][wheel]<=self.teacher_cfg.support_min_force_n
                                quiet=(sum(x*x for x in sample['root'][7:10])**.5<=self.teacher_cfg.balance_speed_limit_m_s
                                    and sum(x*x for x in sample['root'][10:13])**.5<=self.teacher_cfg.recovery_rate_rad_s)
                                restored=(reference_valid and sample['phase']==int(Phase.RESTORE)
                                    and all(x>self.teacher_cfg.support_min_force_n for x in sample['Fz'])
                                    and sample['wheel_position'][wheel][2]<=rec['initial_wheel_z']+.002
                                    and quiet and not any(sample[k] for k in ('collision','support_lost','penetration','failure')))
                                rec['local_recovery_count']=rec['local_recovery_count']+1 if restored else 0
                                local_complete=(rec['measured_lift_seen'] and rec['local_recovery_count']>=5
                                    and sample.get('teacher_recovery_stable_count',0)>=self.teacher_cfg.stable_samples)
                            elif scope in ('first-obstacle','transitions'):
                                local_complete=sample['recovery_result']['success']==[True]
                            local_complete=bool(local_complete and not sample['failure_locked'] and
                                sample.get('action_matches_request',False) and
                                not any(sample[k] for k in ('collision','support_lost','penetration','failure')))
                            sample['scope_observation_complete']=local_complete
                            sample['measured_local_lift_seen']=bool(rec['measured_lift_seen'])
                            sample['local_recovery_count']=int(rec['local_recovery_count'])
                            complete=(scope=='course' and stage==3 and len(required[row])==16
                                and sample['recovery_result']['success']==[True])
                            horizon=scope=='course' and stage==0 and int(self.frames[row])==1000
                            failure_end=self.failure_bound.update(row,sample['failure_locked'])
                            diagnostic_end=not acceptance and int(self.frames[row])>=diagnostic_steps
                            batch_end=gate.deadline(batch_step)
                            ending=bool(done[row]) or complete or horizon or diagnostic_end or failure_end or local_complete or batch_end
                            end=None
                            if ending:
                                end='flat_horizon' if horizon and sample['timeout'] else ('natural_done' if bool(done[row]) else
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
                                endings.append((row,end,sample))
                        # Every peer's raw trace is durable before row reset can
                        # mutate shared command or observation buffers.
                        for row,end,sample in endings:
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
                                record['verification']=verify_episode(record,**self.verification_options())
                                self.write(Path(record['video']['path']).stem+'.json',record)
                    result=verify_suite(records,diagnostic=not acceptance,**self.verification_options())
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
