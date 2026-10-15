"""Ranking must preserve load priority while avoiding needless knee extension."""
import pytest
import torch
from ame_baseline import m1_teacher_pose as pose


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
@pytest.mark.parametrize('active',range(4))
def test_equal_load_prefers_nonactive_knee_reserve(dtype,active):
    # Candidate0 has a large active-knee margin only; candidate1 supports better.
    margins=torch.full((1,2,4),.2,dtype=dtype)
    margins[:,0,active]=2.
    margins[:,1]=.4
    margins[:,1,active]=.01
    best=pose._rank_load_candidates(torch.tensor([[0.,1.]],dtype=dtype),
        torch.tensor([[80.,80.]],dtype=dtype),margins,torch.tensor([active]),
        torch.ones((1,2),dtype=torch.bool))
    assert best.tolist()==[1]


@pytest.mark.parametrize('load,reserve,cost,eligible,want',[
    ([80.,81.],[.8,.2],[0.,1.],[True,True],1),
    ([80.,80.],[.4,.4],[1.,0.],[True,True],1),
    ([80.,80.],[.4,.4],[0.,0.],[True,True],0),
    ([90.,80.],[.8,.2],[0.,1.],[False,True],1),
])
def test_load_cost_index_and_eligibility_order(load,reserve,cost,eligible,want):
    margins=torch.tensor(reserve,dtype=torch.float64)[None,:,None].expand(1,2,4)
    best=pose._rank_load_candidates(torch.tensor([cost],dtype=torch.float64),
        torch.tensor([load],dtype=torch.float64),margins,torch.tensor([0]),torch.tensor([eligible]))
    assert best.tolist()==[want]


def test_real_pre_lift_selects_support_reserve_without_relaxing_envelope(monkeypatch):
    import json
    from pathlib import Path
    import ame_baseline.m1_reference_teacher as teacher_module
    from ame_baseline.m1_reference_teacher import ReferenceTeacher,TeacherConfig,TeacherState
    from ame_baseline.m1_teacher_feedback import BodyFeedbackConfig
    from scripts.probe_m1_teacher import _dynamic_unpack
    data=json.loads((Path(__file__).parent/'fixtures/m1_v31_knee_reserve.json').read_text())
    cfg=data['config'];cfg['feedback']=BodyFeedbackConfig(**cfg['feedback'])
    c=data['row']['dynamic_support'];s=TeacherState(**_dynamic_unpack(c['input'],'cpu'))
    teacher=ReferenceTeacher(TeacherConfig(**cfg));teacher._rows=[_dynamic_unpack(c['pre'],'cpu')]
    original=teacher_module.choose_support_pose;choices=[]
    def capture(*args,**kwargs):
        choice=original(*args,**kwargs);choices.append(choice);return choice
    monkeypatch.setattr(teacher_module,'choose_support_pose',capture)
    out=teacher._step_row(s,0,None)
    assert out.valid.item() and len(choices)==1
    choice=choices[0]
    # Same safe load optimum XY, with legal pre-bent support rather than
    # the higher posture whose weak support approaches full extension.
    assert choice.reference.body.pos_w[0,:2].tolist()==pytest.approx([-25.9887104,-152.0599365],abs=2e-5)
    assert .54<=choice.reference.body.pos_w[0,2]<.58
    assert choice.ik.extension_margin_rad[0,1:].amin()>.7
    assert choice.predicted_margin_m.item()>=.01
    assert choice.measured_triangle_margin_m.item()>=.01


def test_one_ulp_load_advantage_is_not_grouped_with_equal_load():
    lo=torch.tensor(80.,dtype=torch.float32)
    hi=torch.nextafter(lo,torch.tensor(float('inf')))
    best=pose._rank_load_candidates(torch.tensor([[0.,1.],[1.,0.]]),
        torch.stack((torch.stack((lo,hi)),torch.stack((hi,lo)))),
        torch.tensor([[[.8]*4,[.2]*4],[[.2]*4,[.8]*4]]),
        torch.tensor([0,3]),torch.ones((2,2),dtype=torch.bool))
    assert best.tolist()==[1,0]
