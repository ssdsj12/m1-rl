"""Test the real bridge; fake only the Isaac-owned environment boundary."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]


def bridge_module():
    assert (ROOT / 'sync_bridge.py').is_file(), 'Missing post-cross bridge'
    sys.path.insert(0, str(ROOT))
    try:
        spec = importlib.util.spec_from_file_location('bridge_under_test', ROOT / 'sync_bridge.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def boundary(n=2):
    names = [f'{leg}_FOOT_JOINT' for leg in ('FAR', 'FBL', 'RAR', 'RBL')]
    cfg = NS(sim=NS(dt=.005), decimation=4, wave_wheel_action_signs=(1.,)*4,
             wave_front_wheel_action=1., wave_rear_wheel_action=1.,
             wave_rear_wheel_velocity_feedforward=.4, wave_wheel_equalize_gain=3.,
             wave_disable_obstacle_after_root_x=1.15, wave_sync_actual_wheel_velocity=True,
             wave_forward_only_wheels=True)
    term = type('JointVelocityAction', (), {})()
    term._joint_names, term._joint_ids = names, [12,13,14,15]
    term._scale, term._offset = 1., torch.zeros(n,4)
    term.cfg = NS(scale=1., offset=0., preserve_order=True, use_default_offset=True,
                  clip=None, joint_names=names)
    term.processed_actions = torch.zeros(n,4)
    wheel_drive = type('ImplicitActuator', (), {})()
    wheel_drive.velocity_limit_sim=torch.full((n,4),20.)
    wheel_drive.damping=torch.full((n,4),30.)
    wheel_drive.stiffness=torch.zeros(n,4)
    robot = NS(joint_names=[f'leg{i}' for i in range(12)]+names,
               data=NS(default_joint_vel=torch.zeros(n,16), joint_vel=torch.zeros(n,16),
                       root_pos_w=torch.tensor([[0.,0.,.57]]*n)), actuators={'wheels':wheel_drive})
    class Scene(dict):
        pass
    scene=Scene(robot=robot)
    scene.env_origins=torch.zeros(n,3)
    actions = NS(action=torch.zeros(n,16), get_term=lambda name:term,
                 active_terms=['leg_pos','wheel_vel'], total_action_dim=16)
    env=NS(num_envs=n, cfg=cfg, scene=scene, action_manager=actions,
           episode_length_buf=torch.zeros(n,dtype=torch.long), m1_wave_gate=torch.zeros(n,dtype=torch.bool))
    env.unwrapped=env
    sink=NS(expected_step=0, wheel_joint_ids=[12,13,14,15], sync_observer=None)
    return env,sink,term


@pytest.mark.parametrize('fault',[None,'scale','offset','default_velocity','joint_order','limit','damping','gain','flatbase','actuator_type'])
def test_live_contract_fail_closed(fault):
    mod=bridge_module(); env,sink,term=boundary()
    if fault=='scale':term._scale=2.
    if fault=='offset':term._offset[0,0]=.1
    if fault=='default_velocity':env.scene['robot'].data.default_joint_vel[0,12]=1.
    if fault=='joint_order':term._joint_names=list(reversed(term._joint_names))
    if fault=='limit':env.scene['robot'].actuators['wheels'].velocity_limit_sim[0,0]=19.
    if fault=='damping':env.scene['robot'].actuators['wheels'].damping[0,0]=29.
    if fault=='gain':env.cfg.wave_wheel_equalize_gain=0.
    if fault=='flatbase':env.cfg.wave_front_wheel_action=.5
    if fault=='actuator_type':env.scene['robot'].actuators['wheels']=NS(**vars(env.scene['robot'].actuators['wheels']))
    if fault is None:
        assert mod.validate_live_contract(env,sink)['wheel_scale']==1.
    else:
        with pytest.raises(ValueError,match='sync contract'):
            mod.validate_live_contract(env,sink)


def packet(n=2):
    return {'root_pos':np.tile([0.,0.,.57],(n,1)), 'gravity':np.tile([0.,0.,-1.],(n,1)),
            'wheel_pos':np.tile([0.,-.2,.0959],(n,4,1)), 'wheel_contact_force':np.ones((n,4))*10,
            'wheel_bar_force_peak':np.zeros((n,4)), 'nonwheel_bar_force_peak':np.zeros((n,13)),
            'reference_collision':np.zeros((n,4),bool), 'wave_gate':np.zeros(n,bool),
            'phase':np.full(n,-1), 'prepared_actions':np.zeros((n,12)),
            'terminated':np.zeros(n,bool),'timeout':np.zeros(n,bool),'wheel_velocity':np.zeros((n,4)),
            'applied_actions':np.ones((n,16)), 'step':np.asarray(0)}


def test_wrapper_once_and_sidecar_actual_units_and_reset(tmp_path):
    mod=bridge_module(); env,sink,term=boundary()
    class Original:
        def __init__(self,env,clip_actions=1):
            self.env=env; self.calls=0; self._sequential_drive_allowed=torch.ones(2,dtype=torch.bool)
        def _prepare_actions(self,raw):
            self.calls+=1
            return torch.ones_like(raw)
        def reset(self):
            return 'original-reset'
        def step(self,raw):
            final=self._prepare_actions(raw)
            env.action_manager.action=final.clone()
            term.processed_actions=final[:,12:].clone()
            sample=packet(); sample['applied_actions']=final.numpy().copy()
            self._sync_bridge.sample(0,sample)
            self._sync_bridge.on_reset([0])  # actual recorder callback before wrapper returns
            return None,None,torch.tensor([True,False]),{}
    wrapped=mod.make_sync_wrapper(Original)(env)
    wrapped.bind_post_cross(tmp_path,sink)
    wrapped.step(torch.zeros(2,16))
    assert wrapped.calls==1
    assert wrapped._sync_bridge.core.episode_id.tolist()==[1,0]  # done fallback must not reset twice
    wrapped._sync_bridge.flush()
    with np.load(tmp_path/'sync_0000_0000.npz') as a:
        np.testing.assert_array_equal(a['original_actions'],a['final_actions'])
        np.testing.assert_array_equal(a['actual_actions'],a['final_actions'])
        assert a['episode_id'].tolist()==[[0,0]]
    assert wrapped.reset()=='original-reset'
    assert wrapped._sync_bridge.core.episode_id.tolist()==[2,1]


def test_bridge_rejects_nonzero_raw_and_processed_target_mismatch(tmp_path):
    mod=bridge_module(); env,sink,term=boundary()
    bridge=mod.SyncBridge(env,sink,tmp_path)
    wrapped=NS(_sequential_drive_allowed=torch.ones(2,dtype=torch.bool))
    with pytest.raises(ValueError,match='raw'):
        bridge.prepare(wrapped,torch.ones(2,16),torch.zeros(2,16))
    bridge.prepare(wrapped,torch.zeros(2,16),torch.ones(2,16))
    env.action_manager.action=torch.ones(2,16)
    term.processed_actions=torch.zeros(2,4)
    with pytest.raises(ValueError,match='processed'):
        bridge.sample(0,packet())


def test_recorder_post_reset_forwards_only_when_bound():
    path=ROOT/'runtime.py'
    spec=importlib.util.spec_from_file_location('rt_sync_reset_test',path)
    rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
    calls=[]
    sink=NS(sync_observer=NS(on_reset=lambda ids:calls.append(ids)))
    rec=rt.RecorderBridge(lambda:sink)
    assert hasattr(rec,'post_reset'), 'Missing recorder reset hook'
    assert rec.post_reset([1])==(None,None)
    assert calls==[[1]]
    assert rt.RecorderBridge(lambda:None).post_reset(None)==(None,None)


def test_run_wires_sync_and_preserves_native_finalizer():
    source=(ROOT/'run.py').read_text()
    assert 'make_sync_wrapper' in source, 'Missing candidate wrapper installation'
    assert 'bind_post_cross' in source
    assert source.count('diagnostic_candidate')>=2
    assert 'fast_shutdown=False' in source


def test_metadata_matches_core_and_labels_all_candidate_sources():
    mod=bridge_module()
    from post_cross_sync import PARAMETERS
    assert mod.PARAMETERS==PARAMETERS
    if (ROOT/'sync_verdict.py').exists():
        meta=mod.candidate_metadata()
        assert meta['name']=='post_cross_sync_v1'
        assert set(meta['files'])=={'post_cross_sync.py','sync_bridge.py','sync_verdict.py'}
        assert all(len(value)==64 for value in meta['files'].values())


def test_metadata_gate_reason_bits_match_real_controller():
    mod=bridge_module()
    from post_cross_sync import GATE_REASONS
    assert getattr(mod,'GATE_REASONS',None)==GATE_REASONS


def test_sync_bridge_rejects_reset_between_prepare_and_observe(tmp_path):
    mod=bridge_module(); env,sink,term=boundary()
    bridge=mod.SyncBridge(env,sink,tmp_path)
    wrapped=NS(_sequential_drive_allowed=torch.ones(2,dtype=torch.bool))
    bridge.prepare(wrapped,torch.zeros(2,16),torch.ones(2,16))
    with pytest.raises(ValueError,match='pre-reset'):
        bridge.on_reset([0])


def test_wrapper_reset_callback_is_not_counted_twice(tmp_path):
    mod=bridge_module(); env,sink,term=boundary()
    class Original:
        def __init__(self,env,clip_actions=1):self.env=env
        def reset(self):
            self._sync_bridge.on_reset(None)
            return 'reset-with-recorder'
    wrapped=mod.make_sync_wrapper(Original)(env)
    wrapped.bind_post_cross(tmp_path,sink)
    assert wrapped.reset()=='reset-with-recorder'
    assert wrapped._sync_bridge.core.episode_id.tolist()==[1,1]


def test_wrapper_done_fallback_only_when_recorder_did_not_reset(tmp_path):
    mod=bridge_module(); env,sink,term=boundary()
    class Original:
        def __init__(self,env,clip_actions=1):self.env=env
        def step(self,raw):return None,None,torch.tensor([False,True]),{}
    wrapped=mod.make_sync_wrapper(Original)(env)
    wrapped.bind_post_cross(tmp_path,sink)
    wrapped.step(torch.zeros(2,16))
    assert wrapped._sync_bridge.core.episode_id.tolist()==[0,1]


def test_active_bridge_uses_previous_actual_hold_and_records_postprocess_targets(tmp_path):
    mod=bridge_module(); env,sink,term=boundary()
    env.scene['robot'].data.root_pos_w[:,0]=1.2
    class Original:
        def __init__(self,env,clip_actions=1):
            self.env=env; self.calls=0
            self._sequential_drive_allowed=torch.ones(2,dtype=torch.bool)
        def _prepare_actions(self,raw):
            self.calls+=1
            result=torch.zeros_like(raw)
            result[:,12:]=torch.tensor([2.,2.,2.4,2.4])
            return result
        def step(self,raw):
            final=self._prepare_actions(raw)
            env.action_manager.action=final.clone()
            term.processed_actions=final[:,12:].clone()
            sample=packet()
            step=sink.expected_step
            sample['step']=np.asarray(step)
            sample['root_pos']=env.scene['robot'].data.root_pos_w.numpy().copy()
            sample['phase'][:]=11 if step==3 else -1
            x,z,force={0:(.7,.17,0.),1:(.85,.17,0.),2:(1.,.17,0.)}.get(step,(1.,.0959,10.))
            sample['wheel_pos'][:]=[x,-.2,z]
            sample['wheel_contact_force'][:]=force
            sample['applied_actions']=final.numpy().copy()
            self._sync_bridge.sample(step,sample)
            return None,None,torch.zeros(2,dtype=torch.bool),{}
    wrapped=mod.make_sync_wrapper(Original)(env)
    wrapped.bind_post_cross(tmp_path,sink)
    for step in range(11):
        sink.expected_step=step
        env.episode_length_buf[:]=step
        wrapped.step(torch.zeros(2,16))
    wrapped._sync_bridge.flush()
    assert wrapped.calls==11
    with np.load(tmp_path/'sync_0000_0010.npz') as a:
        assert a['activation_step'][-1].tolist()==[8,8]
        np.testing.assert_array_equal(a['original_actions'][:8],a['final_actions'][:8])
        np.testing.assert_array_equal(a['final_actions'][8],a['actual_actions'][7])
        np.testing.assert_array_equal(a['actual_actions'],a['final_actions'])
        np.testing.assert_array_equal(a['processed_wheel_targets'],a['final_actions'][:,:,12:])
        np.testing.assert_array_equal(a['original_actions'][:,:,:12],a['final_actions'][:,:,:12])
        assert np.all(a['final_actions'][9,:,12:]<a['final_actions'][8,:,12:])
