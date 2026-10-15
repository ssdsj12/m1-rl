import json
from pathlib import Path
from ame_baseline.m1_reference_teacher import ReferenceTeacher, TeacherConfig, TeacherState
from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig
from test_m1_teacher_probe_contract import probe


def test_native_partial_reserve_transaction_and_independent_receipt():
    # Frozen real env0 input89: best candidate44.57584N, valid IK.
    record=json.loads((Path(__file__).parent/'fixtures/tripod_partial_native.json').read_text())
    p=probe(); raw=record['teacher_config'].copy()
    raw['feedback']=BodyFeedbackConfig(**raw['feedback'])
    cfg=TeacherConfig(**raw); teacher=ReferenceTeacher(cfg)
    c=record['dynamic_support']
    state=TeacherState(**p._dynamic_unpack(c['input'],'cpu'))
    teacher._rows=[p._dynamic_unpack(c['pre'],'cpu')]
    p.observe_dynamic_support(teacher)
    out=teacher.step(state)
    assert out.valid.item(), 'partial reserve must not lock a feasible transaction'
    sample=dict(dynamic_support=p.dynamic_context_for(teacher,state,0),
        teacher_diagnostic=p.diagnostic_json(out.diagnostic[0].tolist()))
    minimum=sample['teacher_diagnostic']['tripod_selected_measured_min_n']
    assert 44.5 < minimum < 45.
    assert p.verify_tripod_sample(sample,cfg)==[]
