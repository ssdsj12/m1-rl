import importlib.util
from pathlib import Path
import torch


def gate():
    path = Path(__file__).parents[1] / 'ame_baseline/m1_unload_gate.py'
    assert path.exists(), 'measured unload gate missing'
    spec = importlib.util.spec_from_file_location('unload_gate', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.unload_ready


def inputs():
    force = torch.full((4, 4), 100.)
    force[torch.arange(4), torch.arange(4)] = 2.
    return dict(force=force, selected=torch.arange(4), tilt=torch.zeros(4, 2),
                rate=torch.zeros(4, 2), effort_error=torch.zeros(4),
                allocation_valid=torch.ones(4, dtype=torch.bool))


def test_all_four_single_leg_choices():
    assert gate()(**inputs()).all()


def test_loaded_selected_or_weak_other_support_cannot_pass():
    args = inputs()
    args['force'][0, 0] = 10.
    args['force'][1, 0] = 29.
    assert gate()(**args).tolist() == [False, False, True, True]


def test_pose_unsettled_effort_and_missing_allocation_reject():
    args = inputs()
    args['tilt'][0, 0] = .16
    args['rate'][1, 0] = .21
    args['effort_error'][2] = 1.1
    args['allocation_valid'][3] = False
    assert not gate()(**args).any()


def test_nonfinite_evidence_never_ready():
    args = inputs()
    args['force'][0, 0] = float('nan')
    args['effort_error'][1] = float('nan')
    args['rate'][2, 0] = float('nan')
    args['tilt'][3, 0] = float('nan')
    assert not gate()(**args).any()
