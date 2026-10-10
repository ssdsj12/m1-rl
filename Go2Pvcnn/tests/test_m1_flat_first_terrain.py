import pytest


def test_progressive_rows_begin_empty_and_increase_height_and_exposure():
    from ame_baseline.m1_mixed_course import progressive_row
    assert [progressive_row(i) for i in range(4)] == [(0, 0., 0), (2,.03,0), (4,.06,0), (8,.10,0)]
    assert progressive_row(4) == (90,.10,1)
    with pytest.raises(ValueError):
        progressive_row(-1)


def test_progressive_anchors_have_true_empty_row_and_correct_mesh_parameters(monkeypatch):
    from test_semantic_course_curriculum_layout import _install_fake_isaaclab
    _install_fake_isaaclab(monkeypatch)
    from extension.semantic_course import SemanticCourseLayoutCfg, build_course_anchors
    from extension.semantic_curriculum import SemanticObstacleCurriculumCfg, SemanticObstacleCount
    cfg = SemanticObstacleCurriculumCfg(plane_counts=tuple(SemanticObstacleCount(n,0) for n in (0,2,4,8)),
        min_spacing_clearance_m=(.45,))
    anchors = build_course_anchors([[[16.*i,0.,0.]] for i in range(4)],tile_size=(16.,16.),
        terrain_names=('flat',),semantic_curriculum_cfg=cfg,
        layout_cfg=SemanticCourseLayoutCfg(placement_strategy='m1_progressive',small_shape_pool=('cuboid','cylinder')),
        scale_profile_overrides={'small':(.05,.10),'large':(.45,.55)})
    assert not any(a.row == 0 for a in anchors)
    for row,n,height in ((1,2,.03),(2,4,.06),(3,8,.10)):
        selected = [a for a in anchors if a.row==row]
        assert len(selected)==n
        assert all(a.target_height==height for a in selected)
        assert [a.local_xy[1] for a in selected] == [.215 if i%2==0 else -.215 for i in range(n)]
        assert all(selected[i+1].local_xy[0]-selected[i].local_xy[0]>=.89 for i in range(n-1))


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
