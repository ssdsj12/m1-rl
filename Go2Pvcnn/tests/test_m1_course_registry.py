from types import SimpleNamespace
import pytest
import torch


def obstacle(row=0,col=0,slot=0,kind='cuboid',center=(1.,2.,.55),category='small'):
    params={'size':(.05,.05,.10)} if kind=='cuboid' else {'radius':.025,'height':.10,'axis':'Z'}
    return SimpleNamespace(row=row,col=col,slot_index=slot,shape_kind=kind,
        semantic_class=category,world_center=center,shape_params=params,
        prim_path=f'/World/{category}/{row}/{col}/{slot}')


def test_registry_uses_actual_grounded_shape_not_configured_height():
    from ame_baseline.m1_course_registry import CourseRegistry
    registry=CourseRegistry([obstacle(),obstacle(slot=1,kind='cylinder',center=(3.,4.,.75)),
                             obstacle(category='large')],rows=2,cols=2,device='cpu')
    out=registry.for_envs(torch.tensor([0,1]),torch.tensor([0,1]))
    assert out['valid'].tolist()==[[True,True],[False,False]]
    torch.testing.assert_close(out['centers_top'][0],torch.tensor([[1.,2.,.60],[3.,4.,.80]]))
    torch.testing.assert_close(out['half_extents'][0],torch.full((2,2),.025))
    torch.testing.assert_close(out['ground_z'][0],torch.tensor([.50,.70]))
    assert out['ids'][0].unique().numel()==2
    assert (out['ids'][1]==-1).all()
    assert out['landing_valid'].sum(1).tolist()==[3,0]
    assert out['landing_centers_top'].shape==(2,3,3)


def test_mapping_refreshes_on_terrain_switch_and_empty_registry_stays_empty():
    from ame_baseline.m1_course_registry import CourseRegistry
    registry=CourseRegistry([obstacle(),obstacle(row=1,center=(9.,8.,1.5))],rows=2,cols=1,device='cpu')
    a=registry.for_envs(torch.tensor([0]),torch.tensor([0]))
    b=registry.for_envs(torch.tensor([1]),torch.tensor([0]))
    assert a['ids'].item()!=b['ids'].item()
    assert b['centers_top'][0,0,0]==9
    empty=CourseRegistry([],rows=1,cols=1,device='cpu').for_envs(torch.tensor([0]),torch.tensor([0]))
    assert not empty['valid'].any()
    assert empty['centers_top'].shape==(1,1,3)


def test_registry_rejects_duplicate_nonfinite_or_invalid_shapes_and_indices():
    from ame_baseline.m1_course_registry import CourseRegistry
    for values in ([obstacle(),obstacle()], [obstacle(center=(float('nan'),2.,.5))],
                   [obstacle(row=5)], [obstacle(kind='bad')]):
        with pytest.raises(ValueError):
            CourseRegistry(values,rows=2,cols=2,device='cpu')
    registry=CourseRegistry([],rows=2,cols=2,device='cpu')
    with pytest.raises(ValueError):
        registry.for_envs(torch.tensor([-1]),torch.tensor([0]))


def test_importer_retains_grounded_records_for_runtime_consumers():
    from pathlib import Path
    text=(Path(__file__).parents[1]/'extension/semantic_course.py').read_text()
    assert 'self.grounded_course_obstacles = tuple(obstacles)' in text
