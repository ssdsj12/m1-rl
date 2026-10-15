"""Independent raw-history checks must catch shared producer/replay defects."""
import copy
import pytest
from test_m1_teacher_active_horizontal_anchor import ready_with_drift
from test_m1_reference_teacher import advance


def record(monkeypatch,teacher=None,state=None):
    import test_m1_teacher_load_feedback_evidence as factory
    if teacher is None:teacher,state=ready_with_drift()
    monkeypatch.setattr(factory,'load_teacher',lambda:(teacher,state))
    return factory.sample()


def test_capture_roundtrip_and_independent_history(monkeypatch):
    p,t,s=record(monkeypatch)
    assert s['dynamic_support']['valid']
    assert p.verify_active_horizontal_anchor(s,t.cfg)==[]
    assert p.verify_dynamic_support_sample(s,t.cfg)==[]


@pytest.mark.parametrize('leg,axis',[(0,0),(0,1),(0,2),(1,0),(2,1),(3,2)])
def test_forged_capture_or_support_anchor_rejected(monkeypatch,leg,axis):
    p,t,s=record(monkeypatch)
    s['dynamic_support']['post']['wheel_anchor']['tensor'][0][leg][axis]+=.002
    assert p.verify_active_horizontal_anchor(s,t.cfg)


def test_later_lift_recapture_is_rejected(monkeypatch):
    t,state=ready_with_drift();assert t.step(state).valid.item()
    state=advance(state);state.wheel_pos_w[:,0,0]+=.005
    p,t,s=record(monkeypatch,t,state)
    assert p.verify_active_horizontal_anchor(s,t.cfg)==[]
    s['dynamic_support']['post']['wheel_anchor']['tensor'][0][0][0]+=.005
    assert p.verify_active_horizontal_anchor(s,t.cfg)


def test_invalid_transaction_anchor_mutation_rejected(monkeypatch):
    t,state=ready_with_drift();state.collision[:]=True
    p,t,s=record(monkeypatch,t,state)
    assert not s['dynamic_support']['valid']
    assert p.verify_active_horizontal_anchor(s,t.cfg)==[]
    s['dynamic_support']['post']['wheel_anchor']['tensor'][0][0][0]+=.002
    assert p.verify_active_horizontal_anchor(s,t.cfg)


def test_shared_producer_and_replay_missing_capture_rejected(monkeypatch):
    from ame_baseline.m1_reference_teacher import ReferenceTeacher
    real=ReferenceTeacher._step_row
    t,state=ready_with_drift()
    def wrong(self,s,i,diagnostic):
        row=self._rows[i];old=copy.deepcopy(row)
        out=real(self,s,i,diagnostic)
        if old and old['phase']==1 and out.valid[i] and self._rows[i]['phase']==2:
            self._rows[i]['wheel_anchor']=old['wheel_anchor'].clone()
        return out
    monkeypatch.setattr(ReferenceTeacher,'_step_row',wrong)
    p,t,s=record(monkeypatch,t,state)
    assert p.verify_dynamic_support_sample(s,t.cfg), 'shared replay must not certify missed capture'


def test_shared_request_defect_with_correct_anchor_rejected(monkeypatch):
    from ame_baseline.m1_reference_teacher import ReferenceTeacher
    from ame_baseline.m1_teacher_pose import PoseReference
    real=ReferenceTeacher._feedback_transaction
    t,state=ready_with_drift()
    stale=t._rows[0]['wheel_anchor'][:,0,:2].clone()
    def wrong(self,s,i,work,accepted,requested,q,branch,nominal,evidence):
        wheels=requested.wheels_w.clone()
        wheels[:,0,:2]=stale
        evidence['requested']=PoseReference(requested.body,wheels)
        self._probe_feedback_context[i]['requested']['wheels'][0][:2]=stale[0].tolist()
        return real(self,s,i,work,accepted,PoseReference(requested.body,wheels),
                    q,branch,nominal,evidence)
    # Corrupt the request and its owned context in both producer/replay.
    # The anchor commit itself remains correct, so auditing only post misses it.
    monkeypatch.setattr(ReferenceTeacher,'_feedback_transaction',wrong)
    p,t,s=record(monkeypatch,t,state)
    assert s['dynamic_support']['valid']
    assert p.verify_dynamic_support_sample(s,t.cfg)


def test_frozen_request_uses_transported_accepted_not_anchor(monkeypatch):
    p,t,s=record(monkeypatch)
    c=s['dynamic_support'];c['diagnostic']['wheel_progress_ready']=False
    old=c['pre']['accepted']['values']['wheels_w']['tensor'][0]
    # This fixture has zero common support motion. Only the active wheel drifted.
    s['feedback_context']['requested']['wheels']=copy.deepcopy(old)
    assert p.verify_active_horizontal_anchor(s,t.cfg)==[]
    s['feedback_context']['requested']['wheels'][0][0]+=.002
    assert p.verify_active_horizontal_anchor(s,t.cfg)


def test_independent_anchor_geometry_rotates_with_nonzero_heading(monkeypatch):
    import math
    p,t,s=record(monkeypatch)
    c=s['dynamic_support'];angle=.7
    # Add common forward motion before rotating; previous support stays fixed.
    for rows in (c['input']['wheel_pos_w']['tensor'][0],
                 c['post']['wheel_anchor']['tensor'][0],
                 s['feedback_context']['requested']['wheels']):
        for row in rows: row[0]+=.003
    def rotate(rows):
        for row in rows:
            x,y=row[:2];row[:2]=[x*math.cos(angle)-y*math.sin(angle),
                                x*math.sin(angle)+y*math.cos(angle)]
    for owner,key in ((c['pre'],'wheel_anchor'),(c['pre'],'support_previous'),
                      (c['post'],'wheel_anchor'),(c['input'],'wheel_pos_w')):
        rotate(owner[key]['tensor'][0])
    rotate(c['pre']['accepted']['values']['wheels_w']['tensor'][0])
    rotate(s['feedback_context']['requested']['wheels'])
    c['pre']['yaw']['tensor'][0]+=angle
    assert p.verify_active_horizontal_anchor(s,t.cfg)==[]
    s['feedback_context']['requested']['wheels'][1][1]+=.002
    assert p.verify_active_horizontal_anchor(s,t.cfg)
