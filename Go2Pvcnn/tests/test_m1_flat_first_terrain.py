import pytest


def test_progressive_rows_begin_empty_then_only_increase_height():
    from ame_baseline.m1_mixed_course import progressive_row
    assert [progressive_row(i) for i in range(4)] == [(0, 0., 0), (8,.03,0), (8,.06,0), (8,.10,0)]
    assert progressive_row(4) == (90,.10,1)
    with pytest.raises(ValueError):
        progressive_row(-1)


def test_progressive_anchors_have_true_empty_row_and_correct_mesh_parameters(monkeypatch):
    from test_semantic_course_curriculum_layout import _install_fake_isaaclab
    _install_fake_isaaclab(monkeypatch)
    from extension.semantic_course import SemanticCourseLayoutCfg, build_course_anchors
    from extension.semantic_curriculum import SemanticObstacleCurriculumCfg, SemanticObstacleCount
    cfg = SemanticObstacleCurriculumCfg(plane_counts=tuple(SemanticObstacleCount(n,0) for n in (0,8,8,8)),
        min_spacing_clearance_m=(.45,))
    anchors = build_course_anchors([[[16.*i,0.,0.]] for i in range(4)],tile_size=(16.,16.),
        terrain_names=('flat',),semantic_curriculum_cfg=cfg,
        layout_cfg=SemanticCourseLayoutCfg(placement_strategy='m1_progressive',small_shape_pool=('cuboid','cylinder')),
        scale_profile_overrides={'small':(.05,.10),'large':(.45,.55)})
    assert not any(a.row == 0 for a in anchors)
    for row,n,height in ((1,8,.03),(2,8,.06),(3,8,.10)):
        selected = [a for a in anchors if a.row==row]
        assert len(selected)==n
        assert all(a.target_height==height for a in selected)
        assert [a.local_xy[1] for a in selected] == [.215 if i%2==0 else -.215 for i in range(n)]
        assert all(selected[i+1].local_xy[0]-selected[i].local_xy[0]>=.89 for i in range(n-1))


@pytest.mark.parametrize('row,count,start,pitch', [(1,8,-1.2,1.1),(2,8,-1.2,1.1),(3,8,-1.2,1.1)])
def test_progressive_density_leaves_nominal_spawn_landing_and_terminal_room(row,count,start,pitch):
    from ame_baseline.m1_mixed_course import progressive_positions
    import torch
    from ame_baseline.m1_ame_contract import M1_TRAINING_JOINT_POS
    from extension.parallelism.m1_kinematics import M1_WHEEL_HORIZONTAL_ENVELOPE_M, m1_fk
    out = progressive_positions(count,0,row=row,seed=42,tile_size=(16.,16.))
    xs = [x for x,_ in out['small']]
    assert xs == pytest.approx([start+pitch*i for i in range(count)])
    assert out['large'] == ()
    # 585mm nominal +X stance has front/rear centers +/- .3295m.
    # These are bounded nominal budgets, NOT a dynamic crossing certificate.
    joints = torch.tensor(M1_TRAINING_JOINT_POS, dtype=torch.float64).reshape(4,4)[:,:3].reshape(1,12)
    feet = m1_fk(torch.zeros(1,3,dtype=torch.float64),torch.zeros(1,3,dtype=torch.float64),joints).foot_pos_w[0]
    assert feet[:,0].tolist() == pytest.approx([.3295,.3295,-.3295,-.3295])
    half_axle, half_block = float(feet[:,0].max()), .05
    radius = M1_WHEEL_HORIZONTAL_ENVELOPE_M
    far, recovery_travel = .04, 5*.02*.45
    assert xs[0] - half_block - (-2.+half_axle+radius) > .25
    for left,right in zip(xs,xs[1:]):
        # Rear wheel clears the previous block while all wheels stay clear
        # of the next, including the minimum five stable recovery frames.
        assert right-left-(2*half_axle+2*(half_block+radius)+far)-recovery_travel > .01
    root_at_recovery = xs[-1]+half_block+radius+far+half_axle+recovery_travel
    assert 8.-.75-root_at_recovery > .15


def test_density_change_keeps_empty_flat_and_mixed_layout_unchanged():
    from ame_baseline.m1_mixed_course import progressive_positions, dense_forward_positions
    assert progressive_positions(0,0,row=0,seed=42) == {'small':(), 'large':()}
    assert progressive_positions(90,1,row=4,seed=42,tile_size=(16.,16.)) == dense_forward_positions(
        90,1,seed=42,tile_size=(16.,16.))


def test_flat_first_profile_selected_before_environment_creation():
    from pathlib import Path
    src=(Path(__file__).parents[1]/'scripts/train_m1_cross_large_complex_ame.py').read_text()
    assert '"flat-first"' in src
    assert src.index('configure_flat_first_terrain(env_cfg)') < src.index('env = gym.make(')


def test_strict_gate_counters_do_not_count_reset_pose_events():
    import torch
    from types import SimpleNamespace
    from ame_baseline.m1_mixed_course import record_curriculum_strict_events
    env=SimpleNamespace(cfg=SimpleNamespace(m1_flat_first=True),num_envs=2,device='cpu')
    event={'attempt_started':torch.tensor([True,True]),'event_complete':torch.tensor([False,True]),
           'recovery_complete':torch.tensor([False,True])}
    record_curriculum_strict_events(env,event,torch.tensor([False,True]))
    assert env._m1_curriculum_attempts.tolist()==[1,0]
    assert env._m1_curriculum_successes.tolist()==[0,0]
    event['event_complete']=torch.tensor([True,False])
    event['recovery_complete'].zero_()
    event['attempt_started'].zero_()
    record_curriculum_strict_events(env,event,torch.tensor([False,False]))
    assert env._m1_curriculum_successes.tolist()==[0,0]
    event['recovery_complete']=torch.tensor([True,False])
    record_curriculum_strict_events(env,event,torch.tensor([False,False]))
    assert env._m1_curriculum_successes.tolist()==[1,0]


def test_course_boundary_checks_wheel_envelope_not_only_root():
    import torch
    from ame_baseline.m1_mixed_course import outside_course_tile
    centers=torch.zeros(3,2)
    root=torch.tensor([[7.,0.],[7.,0.],[0.,0.]])
    wheels=torch.zeros(3,4,2)
    wheels[0,:,0]=7.4
    wheels[1,:,0]=7.9
    wheels[2,:,1]=-7.9
    assert outside_course_tile(root,wheels,centers,(16.,16.),.1).tolist()==[False,True,True]
