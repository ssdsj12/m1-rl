import copy
import pytest
from test_m1_teacher_load_feedback_evidence import sample


def test_origin_capture_diagnostic_and_independent_roundtrip():
    probe, teacher, record = sample()
    d = record['teacher_diagnostic']
    assert d['height_origin'] == record['feedback_context']['measured_root'][2]
    assert d['height_origin_committed'] == d['height_origin']
    assert probe.verify_feedback_transaction(record, teacher.cfg) == []
    assert probe.verify_dynamic_support_sample(record, teacher.cfg) == []


@pytest.mark.parametrize('field', ['height_origin', 'height_origin_committed'])
def test_independent_audit_rejects_forged_origin(field):
    probe, teacher, record = sample()
    record = copy.deepcopy(record)
    record['teacher_diagnostic'][field] = record['feedback_context']['measured_root'][2]+.001
    with pytest.raises(ValueError):
        probe.verify_support_height(record, teacher.cfg)


@pytest.mark.parametrize('phase', ['LIFT', 'RESTORE'])
def test_origin_history_after_root_sink_is_bound_and_reconstructed(monkeypatch, phase):
    import test_m1_teacher_load_feedback_evidence as factory
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_reference_teacher import advance
    from ame_baseline.m1_reference_teacher import Phase
    teacher, state = load_teacher()
    assert teacher.step(state).valid.item()
    teacher._rows[0]['phase'] = getattr(Phase, phase)
    origin = state.root_pos_w[0, 2].item()
    state = advance(state)
    state.root_pos_w[:, 2] -= .001
    monkeypatch.setattr(factory, 'load_teacher', lambda: (teacher, state))
    probe, teacher, record = factory.sample()
    assert record['feedback_context']['support_capture_root_z_previous'] == [origin]
    assert probe.verify_feedback_transaction(record, teacher.cfg) == []
    assert probe.verify_dynamic_support_sample(record, teacher.cfg) == []
    forged = copy.deepcopy(record)
    forged['feedback_context']['support_capture_root_z_previous'][0] += .001
    with pytest.raises(ValueError):
        probe.verify_support_height(forged, teacher.cfg)


def test_shared_producer_dropping_origin_is_rejected_independently(monkeypatch):
    import test_m1_teacher_load_feedback_evidence as factory
    import ame_baseline.m1_teacher_execution_targets as target
    from test_m1_teacher_load_feedback_transaction import load_teacher
    from test_m1_reference_teacher import advance
    teacher, state = load_teacher()
    assert teacher.step(state).valid.item()
    state = advance(state)
    state.root_pos_w[:, 2] -= .001
    real = target.execution_targets
    def wrong(*args, **kwargs):
        kwargs.pop('support_capture_root_z', None)
        return real(*args, **kwargs)
    monkeypatch.setattr(target, 'execution_targets', wrong)
    monkeypatch.setattr(factory, 'load_teacher', lambda: (teacher, state))
    probe, teacher, record = factory.sample()
    probe.replay_feedback_transaction.cache_clear()
    assert probe.verify_feedback_transaction(record, teacher.cfg), 'shared replay cannot certify omitted origin'
