import os
import json
import subprocess
from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "run_m1_train_with_placeholder.sh"


def test_repository_vulkan_icd_uses_xorg_compatible_nvidia_loader():
    icd_path = RUNNER.parents[1] / "config" / "vulkan" / "nvidia_egl_icd.json"

    icd = json.loads(icd_path.read_text())

    assert icd["ICD"]["library_path"] == "libGLX_nvidia.so.0"


def test_runner_replaces_inherited_vulkan_icd_for_probe_process(tmp_path):
    icd = tmp_path / "nvidia_icd.json"
    icd.write_text('{"ICD": {"library_path": "libGLX_nvidia.so.0"}}\n')
    env = os.environ.copy()
    env.update({
        "M1_CUDA_VISIBLE_DEVICES": "0",
        "M1_VULKAN_ICD": str(icd),
        "VK_DRIVER_FILES": "/stale/custom_egl_icd.json",
        "VK_ICD_FILENAMES": "/stale/custom_egl_icd.json",
    })

    result = subprocess.run(
        ["bash", str(RUNNER), "env"],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)

    assert values["VK_DRIVER_FILES"] == str(icd)
    assert values["VK_ICD_FILENAMES"] == str(icd)


def test_runner_defaults_to_repository_icd_instead_of_inherited_egl_icd():
    env = os.environ.copy()
    env.update({
        "M1_CUDA_VISIBLE_DEVICES": "0",
        "VK_DRIVER_FILES": "/stale/custom_egl_icd.json",
        "VK_ICD_FILENAMES": "/stale/custom_egl_icd.json",
    })
    env.pop("M1_VULKAN_ICD", None)

    result = subprocess.run(
        ["bash", str(RUNNER), "env"],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    expected = RUNNER.parents[1] / "config" / "vulkan" / "nvidia_egl_icd.json"

    assert Path(values["VK_DRIVER_FILES"]).resolve() == expected.resolve()
    assert Path(values["VK_ICD_FILENAMES"]).resolve() == expected.resolve()
