"""Frozen geometry is not a physical counterfactual or a successful label."""
import importlib.util
import json
from pathlib import Path

def replay():
    path=Path(__file__).parents[1]/'scripts/replay_m1_teacher_geometry.py'
    assert path.exists(), 'frozen geometry replay is missing'
    spec=importlib.util.spec_from_file_location('geometry_replay',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_frozen_replay_missing_input_is_not_counterfactual(tmp_path):
    path=tmp_path/'old.jsonl'
    path.write_text(json.dumps(dict(frame=49,env_id=0,episode_id=0,root=[0.]*13,joints=[0.]*16))+'\n'+
        json.dumps(dict(frame=50,env_id=0,episode_id=0,teacher_input_frame=49,teacher_input_episode_id=0))+'\n')
    result=replay().replay_trace(path,[49])
    assert result['physical_success'] is False and result['full_teacher_replay'] is False
    assert result['frames'][0]['status']=='rejected_missing_input'
    assert 'raw_joint_names' in result['frames'][0]['missing_fields']
    assert result['frames'][0]['input_frame']==49 and result['frames'][0]['output_frame']==50


def test_replay_geometric_subset_uses_actual_raw_names_and_does_not_invent_com(tmp_path):
    import torch
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES
    from ame_baseline.m1_teacher_ik import body_feet
    q=torch.tensor([[0.,.3,-.6]*2+[0.,-.3,.6]*2],dtype=torch.float64)
    values={n:float(q[0,i]) for i,n in enumerate(M1_PLANNER_JOINT_NAMES)}
    values.update({n:0. for n in M1_ASSET_JOINT_NAMES if 'FOOT' in n})
    names=list(reversed(M1_ASSET_JOINT_NAMES))
    input_row=dict(frame=57,env_id=0,episode_id=0,root=[0.,0.,.62,1.,0.,0.,0.]+[0.]*6,
        raw_joint_names=names,joints=[values[n] for n in names],
        wheel_position=(body_feet(q)[0]+torch.tensor([0.,0.,.62])).tolist())
    output=dict(frame=58,env_id=0,episode_id=0,teacher_input_frame=57,teacher_input_episode_id=0,
        processed_target_joint_names=list(M1_ASSET_JOINT_NAMES),processed_targets=[values[n] for n in M1_ASSET_JOINT_NAMES])
    path=tmp_path/'old.jsonl'; path.write_text(json.dumps(input_row)+'\n'+json.dumps(output)+'\n')
    result=replay().replay_trace(path,[57]); frame=result['frames'][0]
    assert frame['status']=='geometric_subset'
    assert frame['new_ik']['valid'] is True
    assert 'com_pos_w' in frame['unavailable_full_teacher_inputs']
    assert 'com_pos_w' not in frame and result['physical_success'] is False


def test_replay_missing_input_frame_does_not_use_output_measurement(tmp_path):
    path=tmp_path/'old.jsonl'; path.write_text(json.dumps(dict(frame=58,teacher_input_frame=57))+'\n')
    result=replay().replay_trace(path,[57])
    assert result['frames'][0]['status']=='rejected_missing_input'
    assert 'recorded input frame' in result['frames'][0]['missing_fields']
