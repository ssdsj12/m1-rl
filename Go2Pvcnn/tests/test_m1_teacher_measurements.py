"""CPU evidence contracts: measured COM and actual applied leg targets."""
from types import SimpleNamespace

import pytest
import torch


def test_actuation_snapshot_names_and_missing_api():
    from ame_baseline import m1_teacher_adapter as adapter
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES,M1_PLANNER_JOINT_NAMES
    wrapper,_,_,_=fixture(batch=2); robot=wrapper.unwrapped.scene['robot']
    robot.data.joint_vel=torch.arange(32,dtype=torch.float32).reshape(2,16)
    robot.data.computed_torque=robot.data.joint_vel+100
    robot.data.applied_torque=robot.data.joint_vel+200
    result=adapter.read_actuation_evidence(robot)
    assert result['joint_names']==M1_ASSET_JOINT_NAMES
    assert result['leg_joint_names']==M1_PLANNER_JOINT_NAMES
    assert torch.equal(result['joint_vel'],robot.data.joint_vel.flip(-1))
    ids=[robot.joint_names.index(name) for name in M1_PLANNER_JOINT_NAMES]
    assert torch.equal(result['leg_computed_effort'],robot.data.computed_torque[:,ids])
    assert torch.equal(result['leg_applied_effort'],robot.data.applied_torque[:,ids])
    assert result['sources']['leg_applied_effort']['api']=='robot.data.applied_torque'
    assert result['sources']['leg_applied_effort']['kind']=='explicit_actuator_command'
    assert result['sources']['leg_applied_effort']['unit']=='N m'
    assert result['sources']['leg_applied_effort']['estimated'] is False
    robot.data.joint_vel.zero_(); robot.data.computed_torque.zero_(); robot.data.applied_torque.zero_()
    assert result['leg_applied_effort'].min()>100 and result['joint_vel'].max()>0
    for name in ('joint_vel','computed_torque','applied_torque'):
        old=getattr(robot.data,name); delattr(robot.data,name)
        with pytest.raises(ValueError): adapter.read_actuation_evidence(robot)
        setattr(robot.data,name,old)
    robot.joint_names=robot.joint_names[:-1]+(robot.joint_names[0],)
    with pytest.raises(ValueError): adapter.read_actuation_evidence(robot)


@pytest.mark.parametrize('field',['joint_vel','computed_torque','applied_torque'])
def test_actuation_nonfinite_leg_is_row_local_and_shape_rejected(field):
    from ame_baseline.m1_teacher_adapter import read_actuation_evidence
    from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES
    wrapper,_,_,_=fixture(batch=2); robot=wrapper.unwrapped.scene['robot']
    for name in ('joint_vel','computed_torque','applied_torque'): setattr(robot.data,name,torch.ones(2,16))
    getattr(robot.data,field)[0,robot.joint_names.index(M1_PLANNER_JOINT_NAMES[0])]=float('nan')
    assert read_actuation_evidence(robot)['valid'].tolist()==[False,True]
    setattr(robot.data,field,torch.ones(2,15))
    with pytest.raises(ValueError): read_actuation_evidence(robot)


def test_terminal_evidence_is_pre_reset():
    from ame_baseline.m1_teacher_adapter import read_actuation_evidence
    wrapper,s,_,_=fixture(); robot=wrapper.unwrapped.scene['robot']
    for name in ('joint_vel','computed_torque','applied_torque'): setattr(robot.data,name,torch.ones(1,16))
    terminal=dict(episode_id=int(s.episode_id[0]),actuation=read_actuation_evidence(robot))
    s.episode_id.add_(1)
    for name in ('joint_vel','computed_torque','applied_torque'): getattr(robot.data,name).fill_(99)
    assert terminal['episode_id']!=int(s.episode_id[0])
    assert terminal['actuation']['joint_vel'].eq(1).all()
    assert terminal['actuation']['leg_applied_effort'].eq(1).all()


def test_mass_weighted_com_is_not_root_proxy():
    from ame_baseline.m1_teacher_measurements import mass_weighted_com
    com, valid = mass_weighted_com(torch.tensor([[[0., 0., 0.], [4., 0., 0.]]]),
                                   torch.tensor([[3., 1.]]))
    assert valid.tolist() == [True]
    assert torch.equal(com, torch.tensor([[1., 0., 0.]]))


def test_bad_mass_is_row_local():
    from ame_baseline.m1_teacher_measurements import mass_weighted_com
    pos = torch.tensor([[[0., 0., 0.], [4., 0., 0.]]]).repeat(4, 1, 1)
    masses = torch.tensor([[3., 1.], [float('nan'), 1.], [-1., 2.], [0., 0.]])
    com, valid = mass_weighted_com(pos, masses)
    assert valid.tolist() == [True, False, False, False]
    assert com[0, 0] == 1.
    assert torch.isnan(com[1:]).all()


def fixture(batch=1):
    from test_m1_reference_teacher import state
    from extension.parallelism.m1_kinematics import M1_ASSET_JOINT_NAMES
    from ame_baseline.m1_teacher_adapter import WHEEL_BODY_NAMES
    s = state(batch=batch)
    names = tuple(reversed(M1_ASSET_JOINT_NAMES))
    bodies = tuple(reversed(WHEEL_BODY_NAMES))
    robot = SimpleNamespace(joint_names=names, body_names=bodies,
        root_physx_view=SimpleNamespace(get_masses=lambda: torch.tensor([[3., 1., 0., 0.]]).repeat(batch,1)),
        data=SimpleNamespace(root_pos_w=s.root_pos_w, root_quat_w=s.root_quat_w,
            root_lin_vel_w=s.root_lin_vel_w, root_ang_vel_w=s.root_ang_vel_w,
            joint_pos=s.default_joint_pos.flip(-1), default_joint_pos=s.default_joint_pos.flip(-1),
            body_pos_w=s.wheel_pos_w.flip(1), body_quat_w=s.wheel_quat_w.flip(1),
            body_com_pos_w=torch.tensor([[[0., 0., 0.], [4., 0., 0.], [8., 0., 0.], [9., 0., 0.]]]).repeat(batch,1,1),
            default_root_state=torch.tensor([[0., 0., .62]+[0.]*10]).repeat(batch,1)))
    sensor = SimpleNamespace(body_names=bodies, data=SimpleNamespace(net_forces_w=s.wheel_force_w.flip(1)))
    class Scene(dict):
        env_origins = torch.zeros(batch, 3)
    calls = dict(step=0, reset=0)
    def forbidden(name):
        def call(*args, **kwargs):
            calls[name] += 1
            raise AssertionError(name)
        return call
    env = SimpleNamespace(scene=Scene(robot=robot, contact_forces=sensor), step_dt=.02,
                          step=forbidden('step'), reset=forbidden('reset'))
    course = dict(centers_top=s.centers_top, half_extents=s.half_extents,
                  ground_z=s.ground_z, valid=s.course_valid, ids=s.course_ids)
    wrapper = SimpleNamespace(unwrapped=env, _m1_current_course=lambda: course,
        _m1_strict_crossing=SimpleNamespace(recovered_for_course=lambda _: s.recovered))
    kwargs = dict(control_step=s.control_step, episode_id=s.episode_id,
                  reset_mask=s.reset_mask, collision=s.collision)
    return wrapper, s, kwargs, calls


def test_adapter_normalizes_mass_tensor_at_pure_boundary(monkeypatch):
    from ame_baseline import m1_teacher_adapter as adapter
    wrapper, s, kwargs, _ = fixture()
    raw = torch.tensor([[3., 1., 0., 0.]], dtype=torch.float64)
    wrapper.unwrapped.scene['robot'].root_physx_view.get_masses = lambda: raw
    pure = adapter.mass_weighted_com
    seen = []
    def checked(pos, masses):
        assert masses.device == pos.device
        assert masses.dtype == pos.dtype
        seen.append(masses)
        return pure(pos, masses)
    monkeypatch.setattr(adapter, 'mass_weighted_com', checked)
    result = adapter.ReferenceTeacherAdapter(wrapper).snapshot(**kwargs,
        last_applied_leg_target=s.last_applied_leg_target, applied_target_valid=s.applied_target_valid)
    assert len(seen) == 1 and result.com_pos_w.dtype == torch.float32
    assert torch.equal(result.com_pos_w, torch.tensor([[1., 0., 0.]]))
    assert raw.dtype == torch.float64


@pytest.mark.parametrize('bad', ['root_quaternion', 'wheel_quaternion', 'target'])
def test_snapshot_invalidity_is_row_local(bad):
    from ame_baseline.m1_teacher_adapter import ReferenceTeacherAdapter
    wrapper, s, kwargs, _ = fixture(batch=2)
    robot = wrapper.unwrapped.scene['robot']
    if bad == 'root_quaternion':
        robot.data.root_quat_w[0].zero_()
    elif bad == 'wheel_quaternion':
        robot.data.body_quat_w[0,0].zero_()
    else:
        s.last_applied_leg_target[0,0] = float('nan')
    result = ReferenceTeacherAdapter(wrapper).snapshot(**kwargs,
        last_applied_leg_target=s.last_applied_leg_target, applied_target_valid=s.applied_target_valid)
    assert result.measurement_valid.tolist() == ([True, True] if bad == 'target' else [False, True])
    assert result.applied_target_valid.tolist() == ([False, True] if bad == 'target' else [True, True])
    assert torch.equal(result.com_pos_w[1], torch.tensor([1., 0., 0.]))


def test_snapshot_clones_named_targets_and_never_steps():
    from ame_baseline.m1_teacher_adapter import ReferenceTeacherAdapter
    from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES
    wrapper, s, kwargs, calls = fixture()
    target = s.leg_pos.flip(-1).clone() + .02
    validity = torch.tensor([True])
    result = ReferenceTeacherAdapter(wrapper).snapshot(**kwargs,
        last_applied_leg_target=target, applied_target_valid=validity,
        applied_leg_joint_names=tuple(reversed(M1_PLANNER_JOINT_NAMES)))
    assert torch.equal(result.last_applied_leg_target, s.leg_pos + .02)
    assert torch.equal(result.com_pos_w, torch.tensor([[1., 0., 0.]]))
    target.zero_(); validity.zero_()
    assert result.applied_target_valid.item()
    assert not torch.equal(result.last_applied_leg_target, target)
    assert calls == dict(step=0, reset=0)
    with pytest.raises(TypeError):
        ReferenceTeacherAdapter(wrapper).snapshot(**kwargs)


@pytest.mark.parametrize('bad', ['com', 'mass', 'quaternion', 'target', 'missing_com', 'explicit_invalid'])
def test_snapshot_marks_bad_evidence_invalid(bad):
    from ame_baseline.m1_teacher_adapter import ReferenceTeacherAdapter
    wrapper, s, kwargs, _ = fixture()
    robot = wrapper.unwrapped.scene['robot']
    valid = torch.tensor([True])
    if bad == 'com':
        robot.data.body_com_pos_w[0,0,0] = float('nan')
    elif bad == 'mass':
        robot.root_physx_view.get_masses = lambda: torch.tensor([[-1., 1., 0., 0.]])
    elif bad == 'quaternion':
        robot.data.root_quat_w.zero_()
    elif bad == 'target':
        s.last_applied_leg_target[0,0] = float('nan')
    elif bad == 'missing_com':
        del robot.data.body_com_pos_w
    else:
        valid.zero_()
    result = ReferenceTeacherAdapter(wrapper).snapshot(**kwargs,
        last_applied_leg_target=s.last_applied_leg_target, applied_target_valid=valid)
    flag = result.applied_target_valid if bad in ('target', 'explicit_invalid') else result.measurement_valid
    assert not flag.item()


@pytest.mark.parametrize('bad', ['mass_type', 'mass_dtype', 'mass_shape', 'body_shape', 'target_shape', 'valid_dtype', 'names'])
def test_snapshot_rejects_malformed_contract(bad):
    from ame_baseline.m1_teacher_adapter import ReferenceTeacherAdapter
    wrapper, s, kwargs, _ = fixture()
    robot = wrapper.unwrapped.scene['robot']
    kwargs.update(last_applied_leg_target=s.last_applied_leg_target, applied_target_valid=s.applied_target_valid)
    if bad == 'mass_type':
        robot.root_physx_view.get_masses = lambda: [[3.,1.,0.,0.]]
    elif bad == 'mass_dtype':
        robot.root_physx_view.get_masses = lambda: torch.ones(1,4, dtype=torch.long)
    elif bad == 'mass_shape':
        robot.root_physx_view.get_masses = lambda: torch.ones(1,3)
    elif bad == 'body_shape':
        robot.data.body_com_pos_w = torch.zeros(1,3,3)
    elif bad == 'target_shape':
        kwargs['last_applied_leg_target'] = torch.zeros(1,16)
    elif bad == 'valid_dtype':
        kwargs['applied_target_valid'] = torch.ones(1)
    else:
        kwargs['applied_leg_joint_names'] = ('bad',)*12
    with pytest.raises(ValueError):
        ReferenceTeacherAdapter(wrapper).snapshot(**kwargs)
