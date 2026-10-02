import pytest

from rsl_rl.runners.on_policy_runner import m1_teacher_ratio


def test_default_schedule_warms_at_one_then_decays_to_zero():
    assert m1_teacher_ratio(0, 100) == pytest.approx(1.0)
    assert m1_teacher_ratio(50, 100) == pytest.approx(0.5)
    assert m1_teacher_ratio(100, 100) == pytest.approx(0.0)


def test_resume_schedule_can_start_at_half_and_end_at_zero():
    assert m1_teacher_ratio(0, 100, start=0.5, end=0.0) == pytest.approx(0.5)
    assert m1_teacher_ratio(100, 100, start=0.5, end=0.0) == pytest.approx(0.0)