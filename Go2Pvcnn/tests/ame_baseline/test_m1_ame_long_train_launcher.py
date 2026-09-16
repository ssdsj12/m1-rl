import os
import signal
import subprocess
import sys
import time
from pathlib import Path
import os
import subprocess

import pytest
import torch


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts/train_m1_cross_large_complex_ame_headless.sh"
SUPERVISOR = ROOT / "scripts/supervise_m1_ame_long_train.sh"


def test_headless_launcher_builds_physical_cuda4_compute_only_argv(tmp_path):
    capture = tmp_path / "argv.txt"
    probe_capture = tmp_path / "probe.txt"
    probe = tmp_path / "probe_isaac_vulkan.py"
    fake_python = tmp_path / "python"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"${1:-}\" == \"${VULKAN_PROBE_PATH}\" ]]; then\n"
        "  printf 'VK_DRIVER_FILES=%s\\n' \"${VK_DRIVER_FILES-unset}\" > \"${PROBE_CAPTURE_FILE}\"\n"
        "  printf 'VK_ICD_FILENAMES=%s\\n' \"${VK_ICD_FILENAMES-unset}\" >> \"${PROBE_CAPTURE_FILE}\"\n"
        "  printf '%s\\n' \"$@\" >> \"${PROBE_CAPTURE_FILE}\"\n"
        "  exit 0\n"
        "fi\n"
        "printf 'PYTHON=%s\\n' \"$0\" > \"${CAPTURE_FILE}\"\n"
        "printf 'VK_DRIVER_FILES=%s\\n' \"${VK_DRIVER_FILES-unset}\" >> \"${CAPTURE_FILE}\"\n"
        "printf 'VK_ICD_FILENAMES=%s\\n' \"${VK_ICD_FILENAMES-unset}\" >> \"${CAPTURE_FILE}\"\n"
        "printf 'CUDA_VISIBLE_DEVICES=%s\\n' \"${CUDA_VISIBLE_DEVICES-unset}\" >> \"${CAPTURE_FILE}\"\n"
        "printf '%s\\n' \"$@\" >> \"${CAPTURE_FILE}\"\n"
    )
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env.update(
        {
            "CUDA_VISIBLE_DEVICES": "7",
            "REPO_ROOT": str(ROOT.parent),
            "ISAAC_ENV": str(tmp_path),
            "PYTHON_BIN": str(fake_python),
            "CAPTURE_FILE": str(capture),
            "PROBE_CAPTURE_FILE": str(probe_capture),
            "VULKAN_PROBE": str(probe),
            "VULKAN_PROBE_PATH": str(probe),
        }
    )

    subprocess.run(["bash", str(LAUNCHER)], env=env, check=True)

    argv = capture.read_text().splitlines()
    expected_icd = ROOT / "config/vulkan/nvidia_egl_icd.json"
    assert argv[0] == f"PYTHON={fake_python}"
    assert argv[1] == f"VK_DRIVER_FILES={expected_icd}"
    assert argv[2] == f"VK_ICD_FILENAMES={expected_icd}"
    assert argv[3] == "CUDA_VISIBLE_DEVICES=unset"
    assert argv[argv.index("--device") + 1] == "cuda:4"
    kit_args = argv[argv.index("--kit_args") + 1]
    assert "--/renderer/multiGpu/enabled=false" in kit_args
    assert "--/renderer/multiGpu/autoEnable=false" in kit_args
    assert "--/app/vulkan=false" not in kit_args

    probe_argv = probe_capture.read_text().splitlines()
    assert probe_argv[:2] == [
        f"VK_DRIVER_FILES={expected_icd}",
        f"VK_ICD_FILENAMES={expected_icd}",
    ]
    assert probe_argv[2:] == [
        str(probe),
        "--prefix",
        str(tmp_path),
        "--expect-device-count",
        "8",
    ]


def test_headless_launcher_defaults_to_amp_and_requires_vulkan_preflight():
    source = LAUNCHER.read_text()

    assert 'ISAAC_ENV="${ISAAC_ENV:-/home/hexinkun/miniconda3/envs/amp}"' in source
    assert (
        'VULKAN_ICD_MANIFEST="${VULKAN_ICD_MANIFEST:-${REPO_ROOT}/Go2Pvcnn/config/vulkan/nvidia_egl_icd.json}"'
        in source
    )
    assert 'export VK_DRIVER_FILES="${VULKAN_ICD_MANIFEST}"' in source
    assert 'export VK_ICD_FILENAMES="${VULKAN_ICD_MANIFEST}"' in source
    assert "probe_isaac_vulkan.py" in source
    assert "/envs/m1" not in source


def test_resume_preserves_policy_noise_std_by_default():
    source = LAUNCHER.read_text()

    assert 'if [[ "${KEEP_STD:-1}" == "1" ]]; then' in source
    assert "args+=(--keep_std)" in source


def test_long_train_supervisor_has_progress_watchdog_and_safe_resume_contract():
    source = SUPERVISOR.read_text()

    assert 'DEVICE="${DEVICE:-cuda:4}"' in source
    assert 'KEEP_STD="${KEEP_STD:-1}"' in source
    assert 'STALL_TIMEOUT_SECONDS="${STALL_TIMEOUT_SECONDS:-300}"' in source
    assert "goal_iteration" in source
    assert "remaining_iterations" in source
    assert "STALL_DETECTED" in source
    assert "EARLY_TERMINATION" in source
    assert "TRAINING_COMPLETE" in source
    assert "terminate_training" in source


def _write_executable(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    path.chmod(0o755)


def _supervisor_fixture(tmp_path: Path, launcher_source: str, *, iteration: int = 0):
    repo = tmp_path / "repo"
    checkpoint_root = tmp_path / "checkpoints"
    log_dir = tmp_path / "logs"
    state_dir = tmp_path / "state"
    launcher = repo / "Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh"
    validator = tmp_path / "validate_checkpoint.sh"
    initial = checkpoint_root / "seed" / f"model_{iteration}.pt"

    _write_executable(launcher, launcher_source)
    _write_executable(
        validator,
        """#!/usr/bin/env bash
set -eu
value="$(cat "$1")"
if [[ -n "${VALIDATOR_CALLS_FILE:-}" ]]; then
  printf '%s\n' "$1" >> "${VALIDATOR_CALLS_FILE}"
fi
case "${value}" in
  valid:[0-9]*)
    iteration="${value#valid:}"
    printf '%s %s\n' "${iteration}" "$((iteration + 1))"
    ;;
  *) exit 1 ;;
esac
""",
    )
    initial.parent.mkdir(parents=True)
    initial.write_text(f"valid:{iteration}\n")

    env = os.environ.copy()
    env.update(
        {
            "REPO_ROOT": str(repo),
            "CHECKPOINT_ROOT": str(checkpoint_root),
            "LOG_DIR": str(log_dir),
            "STATE_DIR": str(state_dir),
            "MASTER_LOG": str(log_dir / "supervisor.log"),
            "LOCK_FILE": str(log_dir / "supervisor.lock"),
            "INITIAL_CHECKPOINT": str(initial),
            "CHECKPOINT_VALIDATOR": str(validator),
            "TRAIN_LAUNCHER": str(launcher),
            "WATCH_INTERVAL_SECONDS": "0.05",
            "STARTUP_GRACE_SECONDS": "0",
            "STALL_TIMEOUT_SECONDS": "5",
            "RESTART_DELAY_SECONDS": "0.05",
            "TERM_GRACE_SECONDS": "1",
        }
    )
    return env, checkpoint_root, log_dir, state_dir


def _wait_for(path: Path, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.02)
    pytest.fail(f"timed out waiting for {path}")


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        if Path(f"/proc/{pid}/stat").read_text().split()[2] == "Z":
            return False
    except FileNotFoundError:
        return False
    return True


def _run_supervisor(env, timeout: float = 8.0) -> subprocess.CompletedProcess:
    proc = subprocess.Popen(
        ["bash", str(SUPERVISOR)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        pytest.fail(f"supervisor timed out\nstdout:\n{stdout}\nstderr:\n{stderr}")
    return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)


def test_supervisor_sigterm_stops_the_process_group_without_restarting(tmp_path):
    started = tmp_path / "started"
    grandchild_pid_file = tmp_path / "grandchild.pid"
    launch_count = tmp_path / "launch-count"
    launcher_source = f"""#!/usr/bin/env bash
set -u
printf 'x\n' >> {launch_count!s}
(trap '' TERM; while true; do sleep 0.1; done) &
printf '%s\n' "$!" > {grandchild_pid_file!s}
touch {started!s}
while true; do sleep 0.1; done
"""
    env, _, _, _ = _supervisor_fixture(tmp_path, launcher_source)
    env["TARGET_ITERATIONS"] = "20"

    proc = subprocess.Popen(["bash", str(SUPERVISOR)], env=env, start_new_session=True)
    try:
        _wait_for(started)
        _wait_for(grandchild_pid_file)
        proc.send_signal(signal.SIGTERM)
        assert proc.wait(timeout=6) == 143

        grandchild_pid = int(grandchild_pid_file.read_text().strip())
        deadline = time.monotonic() + 2
        while _pid_is_alive(grandchild_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not _pid_is_alive(grandchild_pid)
        assert launch_count.read_text().splitlines() == ["x"]
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def test_supervisor_flock_rejects_a_second_instance(tmp_path):
    started = tmp_path / "started"
    launch_count = tmp_path / "launch-count"
    launcher_source = f"""#!/usr/bin/env bash
printf 'x\n' >> {launch_count!s}
touch {started!s}
while true; do sleep 0.1; done
"""
    env, _, _, _ = _supervisor_fixture(tmp_path, launcher_source)
    env["TARGET_ITERATIONS"] = "20"

    first = subprocess.Popen(["bash", str(SUPERVISOR)], env=env, start_new_session=True)
    try:
        _wait_for(started)
        second = subprocess.run(
            ["bash", str(SUPERVISOR)],
            env=env,
            capture_output=True,
            text=True,
            timeout=3,
        )
        assert second.returncode == 73
        assert "SUPERVISOR_ALREADY_RUNNING" in second.stdout
        assert launch_count.read_text().splitlines() == ["x"]
    finally:
        if first.poll() is None:
            first.send_signal(signal.SIGTERM)
        try:
            first.wait(timeout=6)
        except subprocess.TimeoutExpired:
            os.killpg(first.pid, signal.SIGKILL)
            first.wait()


def test_supervisor_accepts_only_valid_checkpoints_from_the_attempt_lineage(tmp_path):
    launcher_source = """#!/usr/bin/env bash
set -eu
run_dir="${CHECKPOINT_ROOT}/attempt-owned"
other_dir="${CHECKPOINT_ROOT}/unrelated"
mkdir -p "${run_dir}" "${other_dir}"
echo "[AME] log_dir=${run_dir}"
printf 'valid:999\n' > "${other_dir}/model_999.pt"
printf 'truncated\n' > "${run_dir}/model_7.pt"
sleep 0.1
printf 'valid:7\n' > "${run_dir}/model_7.pt"
echo 'Training Complete - m1_cross_large_complex_ame'
"""
    env, _, log_dir, state_dir = _supervisor_fixture(tmp_path, launcher_source, iteration=5)
    env["TARGET_ITERATIONS"] = "8"

    result = _run_supervisor(env)

    assert result.returncode == 0, result.stdout + result.stderr
    master_log = (log_dir / "supervisor.log").read_text()
    assert "TRAINING_COMPLETE" in master_log
    assert "model_7.pt" in master_log
    assert "model_999.pt" not in master_log
    assert (state_dir / "current_checkpoint").read_text().strip().endswith("attempt-owned/model_7.pt")


def test_resume_math_starts_after_the_last_completed_iteration(tmp_path):
    remaining_file = tmp_path / "remaining"
    launcher_source = f"""#!/usr/bin/env bash
set -eu
printf '%s\n' "${{MAX_ITERATIONS}}" > {remaining_file!s}
run_dir="${{CHECKPOINT_ROOT}}/attempt-owned"
mkdir -p "${{run_dir}}"
echo "[AME] log_dir=${{run_dir}}"
printf 'valid:9999\n' > "${{run_dir}}/model_9999.pt"
echo 'Training Complete - m1_cross_large_complex_ame'
"""
    env, _, _, _ = _supervisor_fixture(tmp_path, launcher_source, iteration=1037)
    env["TARGET_ITERATIONS"] = "10000"

    result = _run_supervisor(env)

    assert result.returncode == 0, result.stdout + result.stderr
    # model_1037 is the 1,038th completed update, so only 8,962 remain.
    assert remaining_file.read_text().strip() == "8962"


def test_initial_selection_uses_highest_valid_iteration_without_loading_history(tmp_path):
    started = tmp_path / "unexpected-launch"
    launcher_source = f"""#!/usr/bin/env bash
touch {started!s}
exit 99
"""
    env, checkpoint_root, _, state_dir = _supervisor_fixture(tmp_path, launcher_source)
    env.pop("INITIAL_CHECKPOINT")
    calls = tmp_path / "validator-calls"
    env["VALIDATOR_CALLS_FILE"] = str(calls)
    env["TARGET_ITERATIONS"] = "1041"
    history = checkpoint_root / "history"
    history.mkdir(parents=True)
    for iteration in range(50):
        (history / f"model_{iteration}.pt").write_text(f"valid:{iteration}\n")
    highest = history / "model_1040.pt"
    highest.write_text("valid:1040\n")
    # A newer mtime on a lower iteration must not cause a rollback.
    os.utime(history / "model_0.pt", None)

    result = _run_supervisor(env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not started.exists()
    assert (state_dir / "current_checkpoint").read_text().strip() == str(highest)
    assert calls.read_text().splitlines() == [str(highest)]


def test_default_checkpoint_validator_rejects_incompatible_ame_metadata(tmp_path):
    valid = tmp_path / "model_12.pt"
    invalid = tmp_path / "model_13.pt"
    base_payload = {
        "model_state_dict": {},
        "optimizer_state_dict": {},
        "iter": 12,
        "ame_architecture_signature": "ame_xyz_semantic_v1_c6_s16_mha64_h16",
        "ame_num_actor_obs": 1585,
        "ame_num_critic_obs": 1588,
        "ame_num_actions": 16,
    }
    torch.save(base_payload, valid)
    torch.save(
        {
            **base_payload,
            "iter": 13,
            "ame_architecture_signature": "wrong-architecture",
        },
        invalid,
    )
    env = {
        **os.environ,
        "SUPERVISOR_SOURCE_ONLY": "1",
        "CHECKPOINT_PYTHON": sys.executable,
    }

    accepted = subprocess.run(
        ["bash", "-c", f'source "{SUPERVISOR}"; checkpoint_metadata "{valid}"'],
        env=env,
        capture_output=True,
        text=True,
    )
    rejected = subprocess.run(
        ["bash", "-c", f'source "{SUPERVISOR}"; checkpoint_metadata "{invalid}"'],
        env=env,
        capture_output=True,
        text=True,
    )

    assert accepted.returncode == 0
    assert accepted.stdout.strip() == "12 13"
    assert rejected.returncode != 0


def test_supervisor_v2_avoids_process_substitution_and_kills_process_groups():
    source = SUPERVISOR.read_text()

    assert "flock -n" in source
    assert "setsid" in source
    assert '> >(' not in source
    assert 'kill -TERM -- "-${TRAIN_PGID}"' in source
    assert 'kill -KILL -- "-${TRAIN_PGID}"' in source
    assert "request_shutdown" in source
    assert "LINEAGE_FILE" in source


def test_supervisor_accepts_only_a_verified_setsid_process_group():
    source = SUPERVISOR.read_text()

    assert '[[ "${observed_pgid}" == "${TRAIN_PID}"' in source
    assert '"${observed_sid}" == "${TRAIN_PID}" ]]' in source
    assert 'TRAIN_PGID="${TRAIN_PID}"' not in source
    assert "TRAIN_GROUP_UNVERIFIED" in source
