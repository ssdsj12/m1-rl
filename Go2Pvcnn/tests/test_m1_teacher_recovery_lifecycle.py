"""Run the real probe lifecycle using the established CPU simulator boundary."""
import copy
import ast
import inspect
import textwrap
from types import SimpleNamespace as NS

import pytest
import torch

from test_m1_teacher_probe_contract import diagnostic_runner, probe


def crossing_runner(tmp_path,monkeypatch,*,terminal_at=None,collision_at=None):
    run=diagnostic_runner(tmp_path,monkeypatch,'crossing')
    original_state=run.state; original_sample=run.sample; original_step=run.step
    reset_observations=[]
    def state(reset=None):
        s=original_state(reset)
        s.root_pos_w[:,0]=run.frames*.006
        s.root_lin_vel_w[:,0]=.3
        s.centers_top=torch.tensor([[-2.+i*.1,0.,.1] for i in range(8)]).expand(4,-1,-1).clone()
        s.half_extents=torch.tensor([.05,.09]).expand(4,8,-1).clone()
        s.course_valid=torch.ones(4,8,dtype=torch.bool)
        return s
    run.state=state
    def sample(row):
        raw=original_sample(row)
        raw['teacher_valid']=True; raw['student_demonstration_usable']=True
        raw['root'][0]=float(run.frames[row])*.006; raw['root'][7]=.3
        raw['wheel_position']=[[raw['root'][0]+x,y,.096] for x,y in ((.3,.2),(.3,-.2),(-.3,.2),(-.3,-.2))]
        raw['receipt']=run.pairs(state().course_ids[row],state().required_wheels[row])
        raw['far_side_recovery']=copy.deepcopy(raw['receipt'])
        raw['collision']=collision_at is not None and int(run.frames[row])==collision_at
        raw['timeout']=terminal_at is not None and int(run.frames[row])==terminal_at
        return raw
    run.sample=sample
    def step(action):
        _,_,done,_=original_step(action)
        if terminal_at is not None and int(run.frames[0])==terminal_at:
            run.terminal={row:sample(row) for row in range(4)}
            done.fill_(True)
            # Emulate Isaac reset buffers immediately after terminal capture.
            run.robot.data.root_pos_w.fill_(99.)
        return None,None,done,None
    run.step=step
    run.reset_row=lambda row:reset_observations.append({r:len(rec['samples']) for r,rec in run.recording.items()})
    return run,reset_observations


@pytest.mark.parametrize('scope,obligations',[('first-obstacle',2),('transitions',4),('course',16)])
def test_receipt_completion_does_not_end_before_recovery(tmp_path,monkeypatch,scope,obligations):
    run,_=crossing_runner(tmp_path,monkeypatch)
    if scope=='course':
        monkeypatch.setattr(probe(),'teacher_schedule',lambda scope,wheel:[(3,None)])
    run.teacher(acceptance=False,diagnostic_steps=20,scope=scope)
    import json
    records=[json.loads(p.read_text()) for p in tmp_path.glob('stage*.json')]
    assert run.control_calls==16, 'local receipts ended the episode before 15 recovery intervals'
    assert all(len(r['samples'])==16 for r in records)
    assert all(sum(sum(row) for row in r['recovery_scope']['required'][0])==obligations for r in records)
    assert all(r['terminal']['recovery_result']['success']==[True] for r in records)
    assert all(r['verification']['errors']==[] for r in records)
    assert all(r['terminal']['teacher_action']==r['samples'][0]['teacher_action'] for r in records)
    assert all(all(sample['teacher_action'][column]>0 for column in (3,7,11,15))
        for r in records for sample in r['samples'])


@pytest.mark.parametrize('terminal_at,collision_at,expected_reason',[(16,None,'ended'),(None,2,'veto:collision')])
def test_terminal_recovery_snapshot_and_peer_reset(tmp_path,monkeypatch,terminal_at,collision_at,expected_reason):
    run,resets=crossing_runner(tmp_path,monkeypatch,terminal_at=terminal_at,collision_at=collision_at)
    run.teacher(acceptance=False,diagnostic_steps=18,scope='first-obstacle')
    import json
    records=[json.loads(p.read_text()) for p in tmp_path.glob('stage*.json')]
    assert records
    assert all(r['terminal']['recovery_result']['success']==[False] for r in records)
    assert all(r['terminal']['recovery_result']['reason']==[expected_reason] for r in records)
    assert all(r['terminal']['recovery_input']['root_state_w'][0][0]<1. for r in records)
    assert not resets
    # Execute the actual native reset hook without importing a simulator. The
    # external reset reuses every row's buffers, so freezing only done rows fails.
    module=probe(); native=object.__new__(module.NativeProbe)
    native.recording={i:{} for i in range(4)}; native.terminal={}; native.reset_reason='natural'
    roots=torch.arange(12,dtype=torch.float32).reshape(4,3)
    native.state=lambda:NS(root_pos_w=roots.clone())
    native.sample=lambda row:dict(env_id=row,root=native._sample_state.root_pos_w[row].tolist())
    native.video_frame=lambda row,terminal:None
    native.bootstrap_reset=lambda mask:None
    tree=ast.parse(textwrap.dedent(inspect.getsource(module.NativeProbe.__init__)))
    hook=next(node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name=='reset_hook')
    namespace=dict(self=native,torch=torch,env=NS(device='cpu'),original_reset=lambda ids:roots.fill_(99.))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[hook],type_ignores=[])),'native-reset-hook','exec'),namespace)
    namespace['reset_hook'](torch.tensor([0,2]))
    assert native.pre_reset_samples[1]['root']==[3.,4.,5.]
    assert native.pre_reset_samples[3]['root']==[9.,10.,11.]
    assert native.terminal[0]['root']==[0.,1.,2.]
    assert native.terminal[2]['root']==[6.,7.,8.]
