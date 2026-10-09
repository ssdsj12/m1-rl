from pathlib import Path


def test_default_leg_sequence_matches_alternating_obstacle_tracks():
    teacher = Path("ame_baseline/m1_mpc_teacher.py").read_text()
    wrapper = Path("scripts/run_m1_train_with_placeholder.sh").read_text()
    probe = Path("scripts/probe_m1_teacher_physx.py").read_text()
    assert '"M1_TEACHER_LEG_SEQUENCE", "0,3,2,1"' in teacher
    assert 'M1_TEACHER_LEG_SEQUENCE="${M1_TEACHER_LEG_SEQUENCE:-0,3,2,1}"' in wrapper
    assert '"M1_TEACHER_LEG_SEQUENCE": "0,3,2,1"' in probe
