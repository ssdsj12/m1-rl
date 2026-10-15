import argparse
import pytest
import torch
from test_m1_teacher_probe_contract import probe

def test_cli_unguarded_requires_isolated_scope():
    p=probe();parser=argparse.ArgumentParser();p.add_teacher_motion_options(parser)
    args=parser.parse_args(['--slow-rolling','--load-feedback','--bounded-crossing-attitude','--coherent-support-pose','--unguarded-diagnostic'])
    with pytest.raises(ValueError): p.probe_teacher_config(**vars(args))
    assert p.probe_teacher_config(scope='first-obstacle',**vars(args)).unguarded_diagnostic

def test_diagnostic_batch_continues_physical_failure_but_not_invalid_action():
    p=probe();g=p.DiagnosticBatchGate(False,unguarded=True)
    sample=dict(env_id=0,episode_id=1,frame=2,collision=True,support_lost=True,
                penetration=True,failure=True,action_matches_request=True,applied_target_valid=True)
    g.observe_sample(sample,2)
    assert g.failure is None and sample['collision']
    sample['action_matches_request']=False
    g.observe_sample(sample,3)
    assert g.failure['reason']=='action_evidence_invalid'

def test_reset_filter_preserves_raw_causes_and_numerical_reset():
    from ame_baseline.m1_teacher_diagnostic import DiagnosticTerminationFilter
    class Manager:
        active_terms=['base_contact','nonfinite_robot_state']
        def __init__(self):
            self.terminated=torch.zeros(3,dtype=torch.bool)
            self.time_outs=torch.zeros(3,dtype=torch.bool)
            self.terms={'base_contact':torch.tensor([True,False,False]),
                        'nonfinite_robot_state':torch.tensor([False,True,False])}
        def get_term(self,name):return self.terms[name]
        def compute(self):
            self.terminated.copy_(self.terms['base_contact']|self.terms['nonfinite_robot_state'])
            self.time_outs.copy_(torch.tensor([False,False,True]))
            return self.terminated|self.time_outs
    m=Manager();f=DiagnosticTerminationFilter(m)
    reset=m.compute()
    assert reset.tolist()==[False,True,True]
    assert m.terminated.tolist()==[False,True,False]
    assert f.raw_terminated.tolist()==[True,True,False]
    assert m.get_term('base_contact').tolist()==[True,False,False]
    m.terms['base_contact'].zero_();m.terms['nonfinite_robot_state'].zero_()
    assert m.compute().tolist()==[False,False,True]
    assert not f.raw_terminated.any()
