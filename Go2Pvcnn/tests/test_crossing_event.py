import importlib.util
from pathlib import Path


def verifier():
    path = Path(__file__).with_name('crossing_event.py')
    if not path.exists():
        path = Path(__file__).resolve().parents[1] / 'scripts/m1_crossing_event.py'
    assert path.exists(), 'event verifier missing'
    spec = importlib.util.spec_from_file_location('crossing_event', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.verify_event


def sample(x, bottom, contact=False, **kw):
    return dict(episode=0, x=x, y=0.35, bottom=bottom,
                contact=contact, collision=False, tilt=0.0, **kw)


BOX = (0.525, 0.575, 0.325, 0.375, 0.085)


def good():
    return [sample(.38, 0, True), sample(.39, .04), sample(.50, .14),
            sample(.70, .14), sample(.72, 0, True),
            sample(.73, 0, True), sample(.74, 0, True)]


def test_verified_crossing_requires_stable_far_side_touchdown():
    assert verifier()(good(), BOX, .12)['success']


def test_premature_descent_is_rejected():
    rows = good(); rows[3] = sample(.562, .042)
    assert verifier()(rows, BOX, .12)['reason'] == 'insufficient_overlap_clearance'


def test_side_skirt_is_not_crossing():
    rows = good()
    for row in rows: row['y'] = .20
    assert not verifier()(rows, BOX, .12)['success']


def test_reset_cannot_complete_old_crossing():
    rows = good(); rows[-1]['episode'] = 1
    assert not verifier()(rows, BOX, .12)['success']


def test_missing_collision_evidence_fails_closed():
    rows = good(); rows[2]['collision'] = None
    assert not verifier()(rows, BOX, .12)['success']


def test_one_touchdown_sample_is_insufficient():
    assert not verifier()(good()[:-2], BOX, .12)['success']
