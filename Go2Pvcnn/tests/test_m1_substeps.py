from types import SimpleNamespace
import pytest


def test_observer_preserves_update_order_result_and_restores_method():
    from ame_baseline.m1_substeps import observe_substeps
    events=[]
    original=lambda dt: events.append(('update',dt))
    scene=SimpleNamespace(update=original)
    def step():
        scene.update(.005)
        scene.update(.005)
        return 17
    result,samples=observe_substeps(scene,step,lambda: len(events))
    assert result==17 and samples==[1,2]
    assert events==[('update',.005),('update',.005)]
    assert scene.update is original


def test_observer_restores_on_failed_step():
    from ame_baseline.m1_substeps import observe_substeps
    scene=SimpleNamespace(update=lambda dt:None)
    original=scene.update
    def fail():
        scene.update(.005)
        raise RuntimeError('failed')
    with pytest.raises(RuntimeError): observe_substeps(scene,fail,lambda:0)
    assert scene.update is original
