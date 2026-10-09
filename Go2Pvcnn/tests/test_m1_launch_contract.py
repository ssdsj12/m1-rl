import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[1]


def test_headless_launcher_defaults_to_its_own_worktree():
    env = os.environ.copy()
    env.pop('REPO_ROOT', None)
    env.update(PYTHON_BIN='/bin/echo', SKIP_VULKAN_PREFLIGHT='1')
    result = subprocess.run(['bash', str(ROOT/'scripts/train_m1_cross_large_complex_ame_headless.sh')],
                            env=env, text=True, capture_output=True, check=True)
    assert 'TRAIN_REPO_ROOT=' + str(ROOT.parent.resolve()) in result.stdout


def test_probe_and_train_apply_the_same_shared_defaults_before_app_start():
    for script in ['probe_m1_teacher_physx.py', 'train_m1_cross_large_complex_ame.py']:
        source = (ROOT/'scripts'/script).read_text()
        assert 'from ame_baseline.m1_runtime_defaults import apply_m1_runtime_defaults' in source
        assert 'apply_m1_runtime_defaults()' in source
