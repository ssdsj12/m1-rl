from pathlib import Path


def test_runner_preserves_teacher_phase_wheel_slowdown():
    source = (Path(__file__).resolve().parents[1] / 'rsl_rl/rsl_rl/runners/on_policy_runner.py').read_text()
    # Phase calculation has one owner (the wrapper). Recomputing it here
    # used an already advanced age and overwrote the slow wheel action.
    assert 'wheel_command = teacher_action[:, ~leg_mask].clone()' in source
    assert 'wheel_command = wheel_command * wheel_scale' not in source


def test_physx_probe_does_not_replace_teacher_wheel_action_with_full_speed():
    source = (Path(__file__).resolve().parents[1] / 'scripts/probe_m1_teacher_physx.py').read_text()
    assert 'action[:, 3::4] = torch.where' not in source
    assert 'teacher wheel action' in source


def test_teacher_handoff_checks_selected_wheel_not_all_four():
    source = (Path(__file__).resolve().parents[1] / "ame_baseline/ame_env_wrapper.py").read_text()
    assert "gather(1, selected_leg[:, None])" in source
    assert ".all(dim=-1)" not in source[source.index("handoff_ready"):source.index("handoff_ready") + 700]
