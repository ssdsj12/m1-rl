"""Independent orientation evidence, including shared producer/replay defects."""
import copy
import pytest
from test_m1_teacher_bounded_attitude_transaction import frozen_teacher


def record(monkeypatch):
    import test_m1_teacher_load_feedback_evidence as factory
    t,s=frozen_teacher()
    monkeypatch.setattr(factory,'load_teacher',lambda:(t,s))
    return factory.sample()


def test_orientation_roundtrip_and_sign_equivalence(monkeypatch):
    p,t,s=record(monkeypatch)
    assert s['dynamic_support']['valid']
    assert p.verify_bounded_attitude(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]
    request=s['feedback_context']['requested']['root']
    request[3:]=[-v for v in request[3:]]
    assert p.verify_bounded_attitude(s,t.cfg)==[]


@pytest.mark.parametrize('mutation',['request','yaw','tilt','budget','count','com','missing'])
def test_bad_orientation_evidence_fails_closed(monkeypatch,mutation):
    p,t,s=record(monkeypatch);c=s['dynamic_support']
    if mutation=='request':s['feedback_context']['requested']['root'][3:]=[1.,0.,0.,0.]
    if mutation=='yaw':c['pre']['yaw']['tensor'][0]+=.2
    if mutation=='tilt':
        c['post']['tripod_selected_reference']['values']['body']['values']['quat_w']['tensor'][0]=[.98,.2,0.,0.]
    if mutation=='budget':c['dynamic_candidate_limit']=126
    if mutation=='count':c['diagnostic']['dynamic_candidate_count']=126
    if mutation=='com':c['diagnostic']['dynamic_com_target_x']+=.01
    if mutation=='missing':del c['post']['tripod_selected_reference']
    assert p.verify_bounded_attitude(s,t.cfg)


def test_shared_wrong_request_is_not_certified_by_replay(monkeypatch):
    from ame_baseline.m1_reference_teacher import ReferenceTeacher
    from ame_baseline.m1_teacher_pose import PoseReference,BodyPose
    real=ReferenceTeacher._feedback_transaction
    def wrong(self,s,i,work,accepted,requested,q,branch,nominal,evidence):
        # Both producer and replay now send a wrong request despite correct selection.
        bad=PoseReference(BodyPose(requested.body.pos_w,accepted.body.quat_w),requested.wheels_w)
        evidence['requested']=bad
        self._probe_feedback_context[i]['requested']['root'][3:]=accepted.body.quat_w[0].tolist()
        return real(self,s,i,work,accepted,bad,q,branch,nominal,evidence)
    monkeypatch.setattr(ReferenceTeacher,'_feedback_transaction',wrong)
    p,t,s=record(monkeypatch)
    assert s['dynamic_support']['valid']
    assert p.verify_dynamic_support_sample(s,t.cfg)


def test_restore_audit_rejects_retained_crossing_tilt(monkeypatch):
    from dataclasses import replace
    import test_m1_teacher_load_feedback_evidence as factory
    from test_m1_teacher_load_feedback_transaction import load_teacher
    t,state=load_teacher('RESTORE');t.cfg=replace(t.cfg,bounded_crossing_attitude=True)
    monkeypatch.setattr(factory,'load_teacher',lambda:(t,state))
    p,t,s=factory.sample()
    assert s['dynamic_support']['valid']
    assert p.verify_bounded_attitude(s,t.cfg)==[]
    s['dynamic_support']['post']['goal']['values']['body']['values']['quat_w']['tensor'][0]=[.9987502604,.0499791693,0.,0.]
    assert p.verify_bounded_attitude(s,t.cfg)
