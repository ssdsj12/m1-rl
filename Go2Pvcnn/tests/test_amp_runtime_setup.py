from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "setup_amp_runtime.sh"
)


def test_amp_runtime_setup_declares_reproducible_amp_stack():
    script = SCRIPT.read_text(encoding="utf-8")

    required_fragments = (
        "set -euo pipefail",
        "AMP_PREFIX=${AMP_PREFIX:-/home/hexinkun/miniconda3/envs/amp}",
        "python=3.10",
        "gcc_linux-64",
        "gxx_linux-64",
        "libegl=1.7.0",
        "libglvnd=1.7.0",
        "libopengl=1.7.0",
        "libglu=9.0.3",
        "torch==2.7.0",
        "torchvision==0.22.0",
        "isaacsim[all,extscache]==4.5.0.0",
        "numpy==1.26.4",
        "gymnasium==1.2.0",
        "warp-lang==1.17.0",
        "pillow==11.2.1",
        "/home/hexinkun/IsaacLab45",
        "${REPO_ROOT}/Go2Pvcnn/rsl_rl",
        "${REPO_ROOT}/Go2Pvcnn",
        'STAMP="$(date +%Y%m%d_%H%M%S)"',
        "pip freeze --all",
        "amp-before-conda-explicit-${STAMP}.txt",
        "amp-before-pip-freeze-${STAMP}.txt",
        "amp-after-conda-explicit-${STAMP}.txt",
        "amp-after-pip-freeze-${STAMP}.txt",
        "amp-after-pip-check-${STAMP}.txt",
        "env -u PYTHONPATH -u CUDA_VISIBLE_DEVICES",
    )

    for fragment in required_fragments:
        assert fragment in script

    assert "/home/hexinkun/miniconda3/envs/m1" not in script
    assert "isaaclab_rl[rsl_rl]" not in script

    ordered_stages = (
        '"${CONDA_BIN}" install',
        "'pip<27' 'setuptools<81' wheel",
        "torch==2.7.0 torchvision==0.22.0",
        "'isaacsim[all,extscache]==4.5.0.0'",
        "numpy==1.26.4 gymnasium==1.2.0 warp-lang==1.17.0 pillow==11.2.1",
        '"${ISAACLAB_ROOT}/source/isaaclab"',
        '"${ISAACLAB_ROOT}/source/isaaclab_assets"',
        '"${ISAACLAB_ROOT}/source/isaaclab_tasks"',
        '"${ISAACLAB_ROOT}/source/isaaclab_rl"',
        '"${ISAACLAB_ROOT}/source/isaaclab_mimic"',
        '"${REPO_ROOT}/Go2Pvcnn/rsl_rl"',
        '"${REPO_ROOT}/Go2Pvcnn"',
    )
    positions = [script.index(stage) for stage in ordered_stages]
    assert positions == sorted(positions)
