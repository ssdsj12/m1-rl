import importlib
import torch


def choose(**kw):
    return importlib.import_module('ame_baseline.m1_anticipatory_support').choose_pose(**kw)


def case():
    return dict(entry_root=torch.zeros(2,3),entry_rpy=torch.zeros(2,3),
        roots=torch.tensor([[[.04,0.,0.],[.06,0.,0.]]]*2),rpys=torch.zeros(2,2,3),
        min_load=torch.full((2,2,3),36.),min_margin=torch.full((2,2,3),.03),
        reachable=torch.ones(2,2,3,dtype=torch.bool))


def test_rejects_mid_lift_underload_not_just_apex():
    x=case();x['min_load'][0,0,1]=29.
    out=choose(**x)
    assert out['index'].tolist()==[1,0]
    assert out['valid'].tolist()==[True,True]


def test_all_invalid_cannot_return_a_successful_candidate():
    x=case();x['reachable'][0,:,1]=False
    out=choose(**x)
    assert out['valid'].tolist()==[False,True]
    assert out['index'].tolist()==[-1,0]
    assert torch.equal(out['root'][0],x['entry_root'][0])


def test_shift_and_pose_bounds_are_not_relaxed_for_load():
    x=case();x['roots'][0,0,0]=.081;x['rpys'][0,1,0]=.081
    assert choose(**x)['valid'].tolist()==[False,True]


def test_nonfinite_and_low_margin_are_rejected_per_sample():
    x=case();x['min_load'][0,0,0]=float('nan');x['min_margin'][0,1,1]=.019
    assert choose(**x)['valid'].tolist()==[False,True]


def test_height_change_and_yaw_change_are_not_hidden():
    x=case();x['roots'][0,0,2]=.001;x['rpys'][0,1,2]=.001
    assert choose(**x)['valid'].tolist()==[False,True]
