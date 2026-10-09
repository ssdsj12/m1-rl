from pathlib import Path


ROOT = Path('/home/hexinkun/m1_rl/Go2Pvcnn')


def test_m1_serial_phase_defaults_are_long_enough_and_consistent():
    wrapper = (ROOT / 'ame_baseline/ame_env_wrapper.py').read_text()
    teacher = (ROOT / 'ame_baseline/m1_mpc_teacher.py').read_text()
    # At 0.10--0.12 m/s a 10 cm block plus approach/touchdown needs at least
    # 64 control frames.  All phase consumers must share the same default;
    # otherwise selection and Cartesian arc drift out of sync.
    assert wrapper.count('M1_TEACHER_PHASE_BLOCK", "32"') >= 3
    assert teacher.count('M1_TEACHER_PHASE_BLOCK", "32"') >= 1


def test_m1_wrapper_keeps_support_joints_measured_by_default():
    script = (ROOT / 'scripts/run_m1_train_with_placeholder.sh').read_text()
    assert 'M1_TEACHER_PHASE_BLOCK:-32' in script
    assert 'M1_TEACHER_REPROJECT_STANCE:-0' in script
