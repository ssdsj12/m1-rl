from types import SimpleNamespace as NS
import pytest
import torch
from test_m1_fixed_wheel_runtime import runtime
from ame_baseline.m1_ame_contract import m1_last_action, m1_last_leg_action, m1_training_contract
from ame_baseline.m1_ame_rewards import m1_action_rate_l2
from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES


def test_apply_keeps_abad_zero_on_every_substep(runtime):
    assert hasattr(runtime, 'M1FixedAbadHipKneeAction')
    names=list(reversed(M1_ASSET_JOINT_NAMES))
    robot=NS(joint_names=names,data=NS(default_joint_pos=torch.zeros(2,16)))
    robot.set_joint_position_target=lambda target,joint_ids:setattr(robot,'legs',(target.clone(),joint_ids))
    robot.set_joint_velocity_target=lambda target,joint_ids:setattr(robot,'wheels',(target.clone(),joint_ids))
    term=runtime.M1FixedAbadHipKneeAction(runtime.M1FixedAbadHipKneeActionCfg(asset_name='robot',fixed_wheel_speed_m_s=.3),NS(robot=robot))
    assert term.action_dim==8
    for _ in range(20):
        a=torch.linspace(-.1,.1,8).repeat(2,1)
        term.process_actions(a)
        for _ in range(4):
            term.apply_actions()
            target,ids=robot.legs
            by_name={names[i]:target[:,j] for j,i in enumerate(ids)}
            for p in ('FBL','FAR','RBL','RAR'):
                torch.testing.assert_close(by_name[p+'_ABAD_JOINT'],torch.zeros(2))
            selected=torch.stack([by_name[p+'_'+j+'_JOINT'] for p in ('FBL','FAR','RBL','RAR') for j in ('HIP','KNEE')],1)
            torch.testing.assert_close(selected,a*1.5)
            torch.testing.assert_close(robot.wheels[0],torch.full((2,4),.3/.0959))
            assert [names[i] for i in robot.wheels[1]]==[p+'_FOOT_JOINT' for p in ('FBL','FAR','RBL','RAR')]
    with pytest.raises(ValueError):term.process_actions(torch.zeros(2,12))


def test_single_row_reset_history_and_action_cost():
    a=torch.full((2,8),.2)
    env=NS(cfg=NS(m1_fixed_abad=True,m1_fixed_wheel_speed_m_s=.3),action_manager=NS(action=a,prev_action=torch.zeros_like(a)))
    torch.testing.assert_close(m1_last_leg_action(env),torch.tensor([0,.2,.2]*4).repeat(2,1))
    assert m1_last_action(env).shape==(2,16)
    torch.testing.assert_close(m1_action_rate_l2(env),torch.full((2,),.32))
    env.action_manager.action[0]=0
    torch.testing.assert_close(m1_last_leg_action(env)[0],torch.zeros(12))
    torch.testing.assert_close(m1_last_leg_action(env)[1],torch.tensor([0,.2,.2]*4))


def test_eight_policy_distribution_and_config(runtime):
    assert hasattr(runtime,'configure_fixed_abad_control')
    cfg=NS(actions=NS(),commands=NS(base_velocity=NS(ranges=NS(),limit_ranges=NS())),curriculum=NS())
    runtime.configure_fixed_abad_control(cfg,.3)
    assert cfg.action_dim==8 and cfg.m1_fixed_abad
    c=m1_training_contract(fixed_abad=True)
    assert (c['policy_state_dim'],c['critic_state_dim'])==(85,88)
    assert c['robot_physics']==m1_training_contract()['robot_physics']
    from ame_baseline.actor_critic_ame import ActorCriticAME
    model=ActorCriticAME(1621,1624,8,actor_hidden_dims=(8,),critic_hidden_dims=(8,))
    model.eval(); obs=torch.zeros(2,1621)
    actions=model.act(obs)
    assert actions.shape==(2,8) and model.std.numel()==8
    assert model.get_actions_log_prob(actions).shape==(2,)
    assert model.entropy.shape==(2,)


def test_terrain_accepts_eight_only_with_flag(monkeypatch):
    from test_semantic_course_curriculum_layout import _install_fake_isaaclab
    from types import ModuleType
    import sys
    _install_fake_isaaclab(monkeypatch)
    parent=ModuleType('go2_pvcnn.tasks.teacher_elevation_trajectory_mpc_semantic_env_cfg')
    parent.SEMANTIC_TERRAIN_CFG=NS()
    parent.TeacherElevationTrajectoryMpcSemanticCurriculumCfg=lambda:NS(terrain_levels=None)
    monkeypatch.setitem(sys.modules,parent.__name__,parent)
    from ame_baseline.m1_mixed_course import configure_mixed_terrain
    cfg=NS(robot_name='m1',action_dim=8,m1_fixed_abad=True,m1_fixed_wheel_speed_m_s=.3,scene=NS(terrain=NS()),curriculum=NS(),commands=NS(base_velocity=NS(ranges=NS(),limit_ranges=NS())),events=NS(reset_base=NS(params={})))
    configure_mixed_terrain(cfg)
    cfg.m1_fixed_abad=False
    with pytest.raises(ValueError):configure_mixed_terrain(cfg)
