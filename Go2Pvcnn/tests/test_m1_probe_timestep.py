from types import SimpleNamespace
import pytest


def test_refinement_preserves_control_and_render_periods_and_sensor_period():
    from ame_baseline.m1_rolling_speed import refine_timestep
    cfg=SimpleNamespace(sim=SimpleNamespace(dt=.005,render_interval=4),decimation=4,
                        sensor_period=.005)
    refine_timestep(cfg,2)
    assert cfg.sim.dt==.0025
    assert cfg.decimation==8 and cfg.sim.render_interval==8
    assert cfg.sim.dt*cfg.decimation==.02
    assert cfg.sensor_period==.005


@pytest.mark.parametrize('factor',[0,3,-1,True,2.0])
def test_invalid_refinement_rejected_without_mutating(factor):
    from ame_baseline.m1_rolling_speed import refine_timestep
    cfg=SimpleNamespace(sim=SimpleNamespace(dt=.005,render_interval=4),decimation=4)
    with pytest.raises(ValueError):refine_timestep(cfg,factor)
    assert cfg.sim.dt==.005 and cfg.decimation==4
