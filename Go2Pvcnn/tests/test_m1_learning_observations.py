import importlib.util
from types import SimpleNamespace as NS
import torch


def module():
    assert importlib.util.find_spec('ame_baseline.m1_learning_observations') is not None
    from ame_baseline import m1_learning_observations
    return m1_learning_observations


def sample():
    hits=torch.tensor([[[.20,0.,.03],[.24,0.,.03],[.65,0.,.06],[float('nan'),0.,0.]]])
    return [hits,torch.ones(1,4,dtype=torch.long),torch.ones(1,4,dtype=torch.bool),
        torch.zeros(1,4,3),torch.tensor([[1.,0.,0.,0.]]),
        torch.tensor([[[0.,0.,25.],[0.,0.,20.],[0.,0.,30.],[0.,0.,25.]]]),torch.tensor([100.])]


def test_nearest_observed_cluster_and_loads_not_next_obstacle():
    g=module(); f=g.wheel_learning_features(*sample()).reshape(1,4,8)
    torch.testing.assert_close(f[0,0],torch.tensor([.20,.24,0.,.03,1.,1.,.25,.20]))
    assert f.shape==(1,4,8) and torch.isfinite(f).all()


def test_invalid_scan_and_forces_are_finite_without_hallucinated_obstacles():
    g=module(); a=sample(); a[2][:]=False;a[5][:]=float('nan')
    assert torch.equal(g.wheel_learning_features(*a),torch.zeros(1,32))


def test_yaw_and_translation_invariance():
    g=module(); a=sample(); first=g.wheel_learning_features(*a)
    rot=torch.tensor([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    offset=torch.tensor([3.,7.,2.])
    a[0]=a[0]@rot.T+offset;a[3]=a[3]@rot.T+offset
    a[4]=torch.tensor([[2**-.5,0.,0.,2**-.5]])
    torch.testing.assert_close(g.wheel_learning_features(*a),first)


def test_runtime_named_mapping_actual_mass_and_no_registry():
    g=module();a=sample()
    from ame_baseline.m1_ame_rewards import M1_SUPPORT_BODY_NAMES
    order=[2,0,3,1];names=[M1_SUPPORT_BODY_NAMES[i] for i in order]
    robot=NS(body_names=names,data=NS(body_pos_w=a[3][:,order],root_quat_w=a[4]),
        root_physx_view=NS(get_masses=lambda:torch.tensor([[5.,5.]])))
    sensor=NS(body_names=names,data=NS(net_forces_w=a[5][:,order]))
    scan=NS(data=NS(ray_hits_w=a[0],semantic_map=a[1],valid_mask=a[2]))
    env=NS(scene={'robot':robot,'contact_forces':sensor,'semantic_height_scanner':scan},
        cfg=NS(sim=NS(gravity=(0.,0.,-10.))))
    torch.testing.assert_close(g.m1_wheel_learning_observation(env),g.wheel_learning_features(*a))


def test_new_network_shape_and_observation_wiring():
    g=module()
    from ame_baseline.actor_critic_ame import ActorCriticAME
    from pathlib import Path
    source=(Path(__file__).parents[1]/'ame_baseline/m1_ame_env_cfg.py').read_text()
    assert 'wheel_learning = ObsTerm(func=m1_wheel_learning_observation' in source
    net=ActorCriticAME(1621,1624,12,actor_hidden_dims=(8,),critic_hidden_dims=(8,))
    assert net.actor_state_dim==85 and net.critic_state_dim==88
    assert net.act_inference(torch.zeros(2,1621)).shape==(2,12)
