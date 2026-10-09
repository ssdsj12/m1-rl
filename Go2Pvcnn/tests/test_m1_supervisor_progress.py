"""CPU-only watchdog tests: real shell helpers, virtual wall-clock times."""
import ast
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[1]
SUPERVISOR = ROOT / 'scripts/supervise_m1_ame_long_train.sh'


def shell(tmp_path, body):
    log = tmp_path / 'attempt.log'
    log.touch()
    script = '''
set -eu
source "$SUPERVISOR"
ATTEMPT_LOG="$TEST_LOG"
started_at=0
last_progress_at=0
last_checkpoint_at=0
last_logged_iteration=0
current_iteration=0
''' + body
    env = dict(os.environ, SUPERVISOR_SOURCE_ONLY='1', SUPERVISOR=str(SUPERVISOR),
               TEST_LOG=str(log), SAVE_INTERVAL='100', STALL_TIMEOUT_SECONDS='300',
               STARTUP_GRACE_SECONDS='180', CHECKPOINT_TIMEOUT_SECONDS='900')
    result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_healthy_hundred_iteration_checkpoint_period_exceeds_stall_timeout(tmp_path):
    output = shell(tmp_path, '''
for i in {1..100}; do
    printf '\033[1m Learning iteration %s/1000 \033[0m\n' "$i" >> "$ATTEMPT_LOG"
    now=$((i * 7))
    watchdog_observe_progress "$now"
    if reason=$(watchdog_failure_reason "$now"); then echo "$reason"; exit 1; fi
done
echo "$SAVE_INTERVAL $last_logged_iteration $last_progress_at"
''')
    assert output == '100 100 700'


def test_repeated_and_regressed_iterations_do_not_refresh_liveness(tmp_path):
    output = shell(tmp_path, '''
printf 'Learning iteration 12/1000\n' >> "$ATTEMPT_LOG"
watchdog_observe_progress 200
printf 'Learning iteration 12/1000\nLearning iteration 3/1000\nnoise\n' >> "$ATTEMPT_LOG"
watchdog_observe_progress 499
echo "$last_logged_iteration $last_progress_at"
watchdog_failure_reason 500
''')
    assert output == '12 200\niteration'


def test_absent_iteration_progress_times_out_after_startup_grace(tmp_path):
    output = shell(tmp_path, '''
watchdog_observe_progress 299
if watchdog_failure_reason 299; then exit 1; fi
watchdog_failure_reason 300
''')
    assert output == 'iteration'


def test_checkpoint_has_independent_deadline_despite_live_iterations(tmp_path):
    output = shell(tmp_path, '''
printf 'Learning iteration 128/1000\n' >> "$ATTEMPT_LOG"
watchdog_observe_progress 899
if watchdog_failure_reason 899; then exit 1; fi
watchdog_failure_reason 900
last_checkpoint_at=900
if watchdog_failure_reason 901; then exit 1; fi
''')
    assert output == 'checkpoint'


def test_resume_ignores_logged_iterations_not_beyond_checkpoint(tmp_path):
    output = shell(tmp_path, '''
last_logged_iteration=600
current_iteration=600
printf 'Learning iteration 599/1000\nLearning iteration 600/1000\n' >> "$ATTEMPT_LOG"
watchdog_observe_progress 200
echo "$last_logged_iteration $last_progress_at"
printf 'Learning iteration 601/1000\n' >> "$ATTEMPT_LOG"
watchdog_observe_progress 250
echo "$last_logged_iteration $last_progress_at"
''')
    assert output == '600 0\n601 250'


def test_main_uses_separate_progress_and_checkpoint_clocks():
    source = SUPERVISOR.read_text()
    main = source.split('main() {', 1)[1]
    assert 'watchdog_observe_progress "${now}"' in main
    assert 'watchdog_failure_reason "${now}"' in main
    assert 'last_checkpoint_at="${now}"' in main


def test_reward_probe_accepts_current_m1_observation_dimensions():
    tree = ast.parse((ROOT / 'scripts/probe_m1_rewards.py').read_text())
    shape_asserts = [node.test.comparators[0] for node in ast.walk(tree)
                    if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare)
                    and ast.unparse(node.test.left).endswith('.shape')]
    dimensions = [node.elts[-1].value for node in shape_asserts
                  if isinstance(node, ast.Tuple) and isinstance(node.elts[-1], ast.Constant)]
    assert 1589 in dimensions and 1592 in dimensions, dimensions
