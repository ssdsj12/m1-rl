from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "setup_amp_runtime.sh"
)


def test_amp_runtime_setup_declares_reproducible_amp_stack():
    script = SCRIPT.read_text(encoding="utf-8")

    required_fragments = (
        "AMP_PREFIX=${AMP_PREFIX:-/home/hexinkun/miniconda3/envs/amp}",
        "python=3.10",
        "gcc_linux-64",
        "gxx_linux-64",
        "libegl=1.7.0",
        "libglvnd=1.7.0",
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
    )

    for fragment in required_fragments:
        assert fragment in script
