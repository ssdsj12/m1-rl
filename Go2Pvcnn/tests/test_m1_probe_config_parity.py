from pathlib import Path


def test_physx_probe_defaults_match_training_wrapper():
    probe = Path("scripts/probe_m1_teacher_physx.py").read_text()
    wrapper = Path("scripts/run_m1_train_with_placeholder.sh").read_text()
    expected = {
        "M1_TEACHER_FOOT_TRAJECTORY": "1",
        "M1_TEACHER_SERIAL_FORCE": "1",
        "M1_TEACHER_PHASE_BLOCK": "32",
        "M1_TEACHER_STRICT_SEQUENCE": "1",
        "M1_TEACHER_USE_PLANNER_FOOT_TARGET": "1",
        "M1_TEACHER_USE_PLANNER_TOUCHDOWN": "1",
        "M1_TEACHER_USE_MEASURED_HOLD": "1",
        "M1_TEACHER_FOOT_LIFT_M": "0.20",
        "M1_TEACHER_FOOT_ADVANCE_M": "0.22",
        "M1_TEACHER_FOOT_BACKSTEP_M": "0.12",
        "M1_TEACHER_PRELIFT": "1",
    }
    for name, value in expected.items():
        assert f'"{name}": "{value}"' in probe, name
        assert f'{name}="${{{name}:-{value}}}"' in wrapper, name
