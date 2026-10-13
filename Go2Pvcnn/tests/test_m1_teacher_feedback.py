"""Pure CPU position-feedback contract; no simulator or IK dependencies."""
from dataclasses import FrozenInstanceError, fields
import importlib
import importlib.util
import math

import pytest
import torch


@pytest.fixture
def feedback():
    assert importlib.util.find_spec('ame_baseline.m1_teacher_feedback') is not None, 'pure feedback API is absent'
    return importlib.import_module('ame_baseline.m1_teacher_feedback')


def inputs(feedback, error=(0., 0., 0.), batch=1, dtype=torch.float64):
    ref = torch.tensor([error], dtype=dtype).repeat(batch, 1)
    return dict(root_ref_w=ref, root_meas_w=torch.zeros_like(ref),
                captured_yaw=ref.new_zeros(batch),
                previous=feedback.FeedbackState(torch.zeros_like(ref), torch.zeros_like(ref)),
                dt=ref.new_full((batch,), .02), cfg=feedback.FeedbackConfig(),
                active=torch.ones(batch, dtype=torch.bool))


def selected(feedback, previous, proposal, safe=True, transaction_valid=True, backtracked=False):
    batch = previous.integral.shape[0]
    mask = lambda v: torch.full((batch,), v, dtype=torch.bool)
    return feedback.select_integral(previous, proposal, safe=mask(safe),
        transaction_valid=mask(transaction_valid), backtracked=mask(backtracked))


def test_heading_and_axis_assignment(feedback):
    args = inputs(feedback, (0., .03, 0.))
    args['captured_yaw'].fill_(math.pi/2)
    p = feedback.propose_feedback(**args)
    torch.testing.assert_close(p.error_h, torch.tensor([[.03, 0., 0.]], dtype=torch.float64))
    torch.testing.assert_close(p.integral_candidate, p.error_h * p.error_h.new_tensor([.2, .5, .5]) * .02)
    torch.testing.assert_close(p.raw_output, torch.tensor([[.03012, 0., 0.]], dtype=torch.float64))
    for axis in (1, 2):
        args = inputs(feedback)
        args['root_ref_w'][0, axis] = .03
        p = feedback.propose_feedback(**args)
        torch.testing.assert_close(p.raw_output[0, 0], torch.tensor(0., dtype=torch.float64))
        torch.testing.assert_close(p.raw_output[0, axis], torch.tensor(.0153, dtype=torch.float64))
    args = inputs(feedback, (-.01, 0., 0.))
    assert feedback.propose_feedback(**args).output[0, 0] < 0


@pytest.mark.parametrize('dtype', [torch.float32, torch.float64])
def test_limits_and_units(feedback, dtype):
    args = inputs(feedback, (1., 1., 1.), dtype=dtype)
    p = feedback.propose_feedback(**args)
    torch.testing.assert_close(p.output, args['root_ref_w'].new_tensor([[.002, .0004, .0004]]))
    assert p.limited.all()
    max_output = p.output.new_tensor([.04, .02, .02])
    max_integral = p.output.new_tensor([.02, .01, .01])
    for _ in range(150):
        p = feedback.propose_feedback(**args)
        assert (p.output.abs() <= max_output + 1e-8).all()
        assert (p.integral_candidate.abs() <= max_integral + 1e-8).all()
        args['previous'] = feedback.FeedbackState(selected(feedback, args['previous'], p), p.output)
    torch.testing.assert_close(p.output, max_output[None])
    torch.testing.assert_close(args['previous'].integral, torch.zeros_like(p.output))


def test_unlimited_integral_uses_exact_gains(feedback):
    args = inputs(feedback, (.001, .0001, -.0001))
    p = feedback.propose_feedback(**args)
    assert not p.limited.any()
    torch.testing.assert_close(p.integral_candidate, p.output.new_tensor([[.000004, .000001, -.000001]]))
    torch.testing.assert_close(p.raw_output, p.output.new_tensor([[.001004, .000051, -.000051]]))
    torch.testing.assert_close(selected(feedback, args['previous'], p), p.integral_candidate)


@pytest.mark.parametrize('safe,valid,backtracked', [(False, True, False), (True, False, False), (True, True, True)])
def test_antiwindup_and_unwind(feedback, safe, valid, backtracked):
    args = inputs(feedback, (.001, .0001, .0001))
    p = feedback.propose_feedback(**args)
    torch.testing.assert_close(selected(feedback, args['previous'], p, safe, valid, backtracked), args['previous'].integral)


def test_saturation_unwind_is_per_axis_and_requires_safe_valid(feedback):
    args = inputs(feedback, (-.005, .03, -.03))
    old_i = args['root_ref_w'].new_tensor([[.01, .005, -.005]])
    args['previous'] = feedback.FeedbackState(old_i, torch.zeros_like(old_i))
    p = feedback.propose_feedback(**args)
    assert p.limited.all()
    expected = old_i.clone()
    expected[:, 0] -= .00002
    torch.testing.assert_close(selected(feedback, args['previous'], p), expected)
    torch.testing.assert_close(selected(feedback, args['previous'], p, backtracked=True), expected)
    torch.testing.assert_close(selected(feedback, args['previous'], p, safe=False), old_i)
    torch.testing.assert_close(selected(feedback, args['previous'], p, transaction_valid=False), old_i)


def test_cross_axis_saturation_freezes_unsaturated_axis_growth(feedback):
    args = inputs(feedback, (.03, .0001, -.0001))
    p = feedback.propose_feedback(**args)
    assert p.limited[0, 0] and not p.limited[0, 1:].any()
    torch.testing.assert_close(selected(feedback, args['previous'], p), args['previous'].integral)


def test_integral_clipping_is_limited_without_output_clipping(feedback):
    args = inputs(feedback, (.0001, .0001, .0001))
    old_i = args['root_ref_w'].new_tensor([[.02, .01, .01]])
    args['previous'] = feedback.FeedbackState(old_i, old_i + args['root_ref_w'] * args['root_ref_w'].new_tensor([1., .5, .5]))
    p = feedback.propose_feedback(**args)
    assert p.limited.all()
    torch.testing.assert_close(p.integral_candidate, old_i)
    torch.testing.assert_close(p.raw_output, p.output)
    torch.testing.assert_close(selected(feedback, args['previous'], p), old_i)


def test_amplitude_clipping_is_limited_without_slew(feedback):
    args = inputs(feedback, (.06, .06, -.06))
    old_o = args['root_ref_w'].new_tensor([[.04, .02, -.02]])
    args['previous'] = feedback.FeedbackState(torch.zeros_like(old_o), old_o)
    p = feedback.propose_feedback(**args)
    assert p.limited.all()
    torch.testing.assert_close(p.output, old_o)
    torch.testing.assert_close(selected(feedback, args['previous'], p), torch.zeros_like(old_o))


def test_exit_slew_with_residual_integral(feedback):
    args = inputs(feedback)
    integral = args['root_ref_w'].new_tensor([[.01, .005, -.005]])
    args['previous'] = feedback.FeedbackState(integral, integral.clone())
    p = feedback.propose_feedback(**args)
    torch.testing.assert_close(p.integral_candidate, integral)
    torch.testing.assert_close(p.output, integral)
    args['active'].fill_(False)
    args['root_ref_w'].fill_(99.)  # Exit never introduces new PI from measured error.
    p = feedback.propose_feedback(**args)
    torch.testing.assert_close(p.integral_candidate, torch.zeros_like(integral))
    torch.testing.assert_close(p.raw_output, torch.zeros_like(integral))
    torch.testing.assert_close(p.output, integral.new_tensor([[.008, .0046, -.0046]]))
    for _ in range(20):
        args['previous'] = feedback.FeedbackState(p.integral_candidate, p.output)
        p = feedback.propose_feedback(**args)
    torch.testing.assert_close(p.output, torch.zeros_like(integral), atol=1e-12, rtol=0.)


def test_batch_active_and_dt_are_per_row(feedback):
    args = inputs(feedback, (1., 1., 1.), batch=2)
    args['dt'][1] = .01
    args['active'][1] = False
    old_o = args['root_ref_w'].new_tensor([[0., 0., 0.], [-.01, .005, -.005]])
    old_i = args['root_ref_w'].new_tensor([[0., 0., 0.], [.01, .005, -.005]])
    args['previous'] = feedback.FeedbackState(old_i, old_o)
    p = feedback.propose_feedback(**args)
    torch.testing.assert_close(p.output, old_o.new_tensor([[.002, .0004, .0004], [-.009, .0048, -.0048]]))
    torch.testing.assert_close(p.integral_candidate[1], torch.zeros(3, dtype=torch.float64))


def test_fixed_integral_recompute_never_integrates_twice(feedback):
    args = inputs(feedback, (.01, .01, .01))
    p = feedback.propose_feedback(**args)
    fixed = selected(feedback, args['previous'], p)
    r = feedback.recompute_feedback(p.error_h, args['previous'], args['dt'], args['cfg'],
                                   active=args['active'], integral=fixed)
    torch.testing.assert_close(r.integral_candidate, fixed)
    torch.testing.assert_close(r.raw_output, p.error_h * p.error_h.new_tensor([1., .5, .5]))
    torch.testing.assert_close(r.output, p.output)
    fixed.fill_(.001)
    torch.testing.assert_close(r.integral_candidate, torch.zeros_like(fixed))


@pytest.mark.parametrize('field', ['root_ref_w', 'root_meas_w', 'captured_yaw', 'dt', 'active'])
def test_bad_shape_nan_dt_and_owned_output(feedback, field):
    args = inputs(feedback)
    args[field] = args[field].unsqueeze(0)
    with pytest.raises(ValueError):
        feedback.propose_feedback(**args)


@pytest.mark.parametrize('field', ['root_ref_w', 'root_meas_w', 'captured_yaw', 'dt'])
@pytest.mark.parametrize('bad', [float('nan'), float('inf')])
def test_nonfinite_inputs_rejected(feedback, field, bad):
    args = inputs(feedback)
    args[field].fill_(bad)
    with pytest.raises(ValueError):
        feedback.propose_feedback(**args)


@pytest.mark.parametrize('bad', [0., -.02])
def test_nonpositive_dt_rejected(feedback, bad):
    args = inputs(feedback)
    args['dt'].fill_(bad)
    with pytest.raises(ValueError):
        feedback.propose_feedback(**args)


def test_bad_dtype_device_state_and_masks(feedback):
    for field in ('root_meas_w', 'captured_yaw', 'dt', 'active'):
        args = inputs(feedback)
        args[field] = args[field].to('meta')
        with pytest.raises(ValueError):
            feedback.propose_feedback(**args)
    args = inputs(feedback)
    args['root_meas_w'] = args['root_meas_w'].float()
    with pytest.raises(ValueError):
        feedback.propose_feedback(**args)
    args = inputs(feedback)
    args['active'] = args['active'].float()
    with pytest.raises(ValueError):
        feedback.propose_feedback(**args)
    for integral, output in ((torch.zeros(1, 2), torch.zeros(1, 2)),
                             (torch.zeros(1, 3, dtype=torch.long), torch.zeros(1, 3)),
                             (torch.full((1, 3), float('nan')), torch.zeros(1, 3))):
        with pytest.raises(ValueError):
            feedback.FeedbackState(integral, output)
    args = inputs(feedback)
    args['previous'] = feedback.FeedbackState(torch.zeros(2, 3, dtype=torch.float64), torch.zeros(2, 3, dtype=torch.float64))
    with pytest.raises(ValueError):
        feedback.propose_feedback(**args)
    args = inputs(feedback)
    p = feedback.propose_feedback(**args)
    for field in ('safe', 'transaction_valid', 'backtracked'):
        masks = dict(safe=torch.ones(1, dtype=torch.bool), transaction_valid=torch.ones(1, dtype=torch.bool), backtracked=torch.zeros(1, dtype=torch.bool))
        masks[field] = torch.zeros(1)
        with pytest.raises(ValueError):
            feedback.select_integral(args['previous'], p, **masks)


def test_results_are_owned_and_inputs_unchanged(feedback):
    args = inputs(feedback, (.001, .0001, -.0001))
    originals = [args[k] for k in ('root_ref_w', 'root_meas_w', 'captured_yaw', 'dt', 'active')]
    originals += [args['previous'].integral, args['previous'].output]
    saved = [t.clone() for t in originals]
    p = feedback.propose_feedback(**args)
    committed = selected(feedback, args['previous'], p)
    committed.fill_(.123)
    for t in (p.error_h, p.integral_candidate, p.raw_output, p.output):
        t.fill_(.321)
    p.limited.fill_(True)
    for original, snapshot in zip(originals, saved):
        torch.testing.assert_close(original, snapshot)


def test_config_is_fixed_finite_and_frozen(feedback):
    cfg = feedback.FeedbackConfig()
    expected = dict(kp_x=1., ki_x=.2, integral_limit_x=.02, output_limit_x=.04, slew_rate_x=.10,
                    kp_yz=.5, ki_yz=.5, integral_limit_yz=.01, output_limit_yz=.02, slew_rate_yz=.02)
    assert {f.name: getattr(cfg, f.name) for f in fields(cfg)} == expected
    with pytest.raises(FrozenInstanceError):
        cfg.kp_x = 2.
    for name, value in expected.items():
        for bad in (float('nan'), float('inf'), -value, value*2, value/2):
            with pytest.raises(ValueError):
                feedback.FeedbackConfig(**{name: bad})


def test_inactive_rows_do_not_even_compute_integral_increment(feedback):
    args = inputs(feedback, (1e20, 1e20, 1e20), dtype=torch.float32)
    args['dt'].fill_(1e20)
    args['active'].fill_(False)
    p = feedback.propose_feedback(**args)
    torch.testing.assert_close(p.integral_candidate, torch.zeros_like(p.output))
    torch.testing.assert_close(p.output, torch.zeros_like(p.output))


def test_previous_and_fixed_integral_bounds_rejected(feedback):
    args = inputs(feedback)
    for integral, output in (([.021, 0., 0.], [0., 0., 0.]),
                             ([0., 0., 0.], [0., .021, 0.])):
        args['previous'] = feedback.FeedbackState(args['root_ref_w'].new_tensor([integral]), args['root_ref_w'].new_tensor([output]))
        with pytest.raises(ValueError):
            feedback.propose_feedback(**args)
    args = inputs(feedback)
    with pytest.raises(ValueError):
        feedback.recompute_feedback(args['root_ref_w'], args['previous'], args['dt'], args['cfg'],
            active=args['active'], integral=args['root_ref_w'].new_tensor([[0., 0., .011]]))


def test_integral_selection_is_per_row(feedback):
    args = inputs(feedback, (.001, .0001, -.0001), batch=3)
    p = feedback.propose_feedback(**args)
    result = feedback.select_integral(args['previous'], p, safe=torch.tensor([True, False, True]),
        transaction_valid=torch.tensor([True, True, False]), backtracked=torch.zeros(3, dtype=torch.bool))
    torch.testing.assert_close(result[0], p.integral_candidate[0])
    torch.testing.assert_close(result[1:], torch.zeros_like(result[1:]))
