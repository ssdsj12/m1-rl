"""No arbitrary top margin; measured passage and safe recovery still required."""
import ast
from pathlib import Path
import pytest
from test_m1_autonomous_lift_timing import Frames
from ame_baseline import m1_ame_contract as contract


def margin():
    # Baseline runtime requires 3cm. New explicit contract must replace it.
    return getattr(contract, 'M1_REQUIRED_TOP_MARGIN_M', .03)


@pytest.mark.parametrize('gap', [.001, .01, .029])
def test_sub3cm_actual_passage_and_stable_landing_succeeds(gap):
    f = Frames(clearance=margin())
    f.step(-.32, 0.)
    f.step(-.20, .1 + gap)
    f.step(0., .1 + gap)
    assert f.step(.30, 0., touch=True)['event_complete'].item()
    for i in range(5):
        out = f.step(.30, 0., touch=True)
        assert out['recovery_complete'].item() == (i == 4)


@pytest.mark.parametrize('failure', ['collision', 'penetration', 'support', 'no_overlap', 'no_landing'])
def test_no_margin_does_not_invent_success(failure):
    f = Frames(clearance=margin())
    f.step(-.32, 0.)
    f.step(-.20, .11)
    if failure != 'no_overlap':
        f.step(0., .09 if failure == 'penetration' else .11,
               collision=failure == 'collision',
               contacts=[False, False, True, True] if failure == 'support' else None)
    out = f.step(.30, .11 if failure == 'no_landing' else 0., touch=failure != 'no_landing')
    assert not out['event_complete'].item()
    assert not out['recovery_complete'].item()


def test_runtime_both_trackers_use_explicit_zero_margin_without_env_floor():
    assert margin() == 0.
    source = (Path(__file__).parents[1]/'ame_baseline/ame_env_wrapper.py').read_text()
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]
    values = [ast.unparse(k.value) for n in calls for k in n.keywords if k.arg == 'required_clearance']
    assert values == ['M1_REQUIRED_TOP_MARGIN_M'] * 2
    assert 'M1_STRICT_TOP_CLEARANCE_M' not in source


def test_checkpoint_contract_distinguishes_old_clearance_policy():
    expected = contract.m1_training_contract()
    assert expected.get('required_top_margin_m') == 0.
    stale = dict(expected, required_top_margin_m=.03)
    with pytest.raises(ValueError, match='training contract'):
        contract.validate_training_contract({'m1_training_contract': stale}, expected)


def test_perception_proxy_does_not_keep_hidden_5cm_margin():
    from test_m1_obstacle_rewards import _case
    from ame_baseline.m1_obstacle_rewards import wheel_obstacle_reward_terms
    from extension.parallelism.m1_kinematics import M1_WHEEL_RADIUS_M
    case = _case()
    case['wheel_pos_w'][..., 2] = .1 + M1_WHEEL_RADIUS_M + .01
    case['return_clearance'] = True
    case['required_top_margin_m'] = margin()
    assert wheel_obstacle_reward_terms(**case)[2].item()
