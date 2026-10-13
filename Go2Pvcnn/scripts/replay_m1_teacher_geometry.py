"""Replay only recorded geometry; never synthesize missing state or physical success."""
import argparse
from dataclasses import fields
import hashlib
import json
import math
from pathlib import Path
import sys


def _finite(value,shape):
    import torch
    tensor=torch.tensor(value,dtype=torch.float64)
    if tuple(tensor.shape)!=shape or not bool(torch.isfinite(tensor).all()):
        raise ValueError('nonfinite or wrong-shaped recorded geometry')
    return tensor


def _ik_json(result):
    from ame_baseline.m1_teacher_ik import IKReason
    out={f.name:getattr(result,f.name)[0].tolist() for f in fields(result)}
    out['reason_names']=[IKReason(i).name for i in out['reason']]
    return out


def replay_trace(path,frames):
    import torch
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES
    from extension.parallelism.rl_adapter import resolve_named_indices
    from ame_baseline.m1_teacher_pose import BodyPose,PoseReference,world_to_goal_body
    from ame_baseline.m1_teacher_ik import body_feet,solve_constrained_ik
    path=Path(path); raw=path.read_bytes()
    rows=[json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    result=dict(schema_version=1,trace=str(path.resolve()),trace_sha256=hashlib.sha256(raw).hexdigest(),
        requested_input_frames=list(frames),physical_success=False,full_teacher_replay=False,
        student_demonstration_usable=False,frames=[])
    for frame in frames:
        item=dict(input_frame=frame,output_frame=None,status='rejected_missing_input',
            physical_success=False,full_teacher_replay=False)
        result['frames'].append(item)
        outputs=[r for r in rows if r.get('teacher_input_frame')==frame]
        if len(outputs)!=1:
            item['missing_fields']=['unique execution row tied to requested input frame']; continue
        output=outputs[0]; item['output_frame']=output.get('frame')
        item['execution_row_sha256']=hashlib.sha256(json.dumps(output,sort_keys=True).encode()).hexdigest()
        inputs=[r for r in rows if r.get('frame')==frame and
                r.get('env_id')==output.get('env_id') and
                r.get('episode_id')==output.get('teacher_input_episode_id')]
        if len(inputs)!=1:
            item['missing_fields']=['recorded input frame']; continue
        source=inputs[0]
        item['input_row_sha256']=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()
        need=('raw_joint_names','joints','root','wheel_position')
        missing=[k for k in need if k not in source]
        missing.extend(k for k in ('processed_targets','processed_target_joint_names') if k not in output)
        if missing: item['missing_fields']=missing; continue
        names=source['raw_joint_names']; target_names=output['processed_target_joint_names']
        if (len(names)!=16 or len(set(names))!=16 or set(names)!=set(M1_ASSET_JOINT_NAMES)
                or len(target_names)!=16 or len(set(target_names))!=16 or set(target_names)!=set(M1_ASSET_JOINT_NAMES)):
            item['missing_fields']=['unique actual joint-name contract']; continue
        try:
            joint=_finite(source['joints'],(16,)); root=_finite(source['root'],(13,))
            wheel=_finite(source['wheel_position'],(4,3))
            old_targets=_finite(output['processed_targets'],(16,))
            if abs(float(root[3:7].norm())-1)>1e-3: raise ValueError('invalid recorded root quaternion')
            q=joint[list(resolve_named_indices(names,M1_PLANNER_JOINT_NAMES))][None]
            old_q=old_targets[list(resolve_named_indices(target_names,M1_PLANNER_JOINT_NAMES))][None]
            reference=PoseReference(BodyPose(root[None,:3],root[None,3:7]),wheel[None])
            # This measured-anchor question is the maximal common recorded subset.
            # Old rejected reference goals, captured anchors, actual COM and prior
            # execution targets were not recorded, so no full new-teacher replay.
            new_body=world_to_goal_body(reference)
            new_ik=solve_constrained_ik(q,new_body,q)
            old_body=body_feet(old_q)
            old_ik=solve_constrained_ik(q,old_body,q)
        except (ValueError,TypeError,RuntimeError) as exc:
            item.update(status='rejected_invalid_input',rejection=str(exc)); continue
        unavailable=[k for k in ('com_pos_w','last_applied_leg_target','applied_target_valid',
            'captured_world_anchors','rejected_old_wheel_goal') if k not in source]
        item.update(status='geometric_subset',raw_joint_names=list(names),
            actual_input_frame=source['frame'],old_target_kind='recorded_processed_action_fk',
            new_target_kind='measured_wheel_anchor_in_measured_root',
            old_target_body=old_body[0].tolist(),new_target_body=new_body[0].tolist(),
            old_processed_leg_target=old_q[0].tolist(),measured_leg_pos=q[0].tolist(),
            old_ik=_ik_json(old_ik),new_ik=_ik_json(new_ik),
            unavailable_full_teacher_inputs=unavailable,
            limitation='Recorded processed target may be a fallback; rejected old request is unavailable. '
                'Measured-anchor IK is geometry only, without COM, slew, state machine or physics evidence.')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace',required=True,type=Path)
    parser.add_argument('--frames',required=True)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    frames=[int(x) for x in args.frames.split(',')]
    if not frames or len(set(frames))!=len(frames) or min(frames)<0: raise ValueError('unique nonnegative input frames required')
    if args.output.exists(): raise ValueError('output already exists; never overwrite evidence')
    result=replay_trace(args.trace,frames)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(dict(trace_sha256=result['trace_sha256'],frames=[dict(input_frame=f['input_frame'],
        output_frame=f['output_frame'],status=f['status']) for f in result['frames']],
        physical_success=False,full_teacher_replay=False)))


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    main()
