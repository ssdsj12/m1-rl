from pathlib import Path


def test_teacher_physx_probe_reports_setup_and_control_step_progress():
    source = (Path(__file__).parents[1] / "scripts/probe_m1_teacher_physx.py").read_text()

    assert "M1_TEACHER_PHYSX_PROGRESS" in source
    for stage in (
        "app_started",
        "environment_created",
        "trajectory_manager_attached",
        "wrapper_reset_complete",
    ):
        assert f'"{stage}"' in source
    assert "M1_PROBE_PROGRESS_EVERY" in source
    assert '"control_step"' in source


def test_teacher_physx_sample_records_first_strict_failure_state():
    source = (Path(__file__).parents[1] / "scripts/probe_m1_teacher_physx.py").read_text()

    assert '"strict_failed": bool(wrapped._m1_strict_crossing.failed[0].item())' in source
