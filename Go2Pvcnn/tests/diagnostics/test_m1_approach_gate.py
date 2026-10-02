import json
import subprocess
import sys
from pathlib import Path


def test_m1_approach_gate_holds_leg_action_until_short_trigger():
    repo = Path('/home/hexinkun/m1_rl/Go2Pvcnn')
    script = repo / 'tests/diagnostics/audit_m1_approach_gate.py'
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert not payload['premature_swing_reproduced'], payload
