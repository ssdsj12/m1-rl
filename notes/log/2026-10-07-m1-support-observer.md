# M1 support observer and gate contract

Stage: AME pre-action observation, child of
[T306.contact-transfer](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: `24fd181`. Candidate Ref: commit containing this log on
`codex/m1-contact-crossing`.
Key files: [observer](../../Go2Pvcnn/ame_baseline/m1_support_observer.py),
[tests](../../Go2Pvcnn/tests/test_m1_support_observer.py).

## Evidence and change

Read active wrapper and diagnostic probe. Existing wrapper classifies contact
using the force-vector norm; a horizontal collision force can therefore satisfy
its >10 N support condition. New observer uses signed world-Z force on the
approved flat-ground test scene. Existing production wrapper is unchanged pending
full controller integration. Ground contact on top of an obstacle still requires
independent geometry/collision evidence; world-Z alone cannot distinguish it.

Read actual articulation API fields used by the existing working probe:
`body_com_pos_w`, `root_physx_view.get_masses()`, `body_pos_w`, named sensor
`net_forces_w`, `root_quat_w`; observer additionally consumes `root_ang_vel_b`.
COM is mass-weighted over all articulation links, with current masses reread
each call so randomized mass is not silently ignored. Named wheel and sensor
indices are resolved separately; missing or duplicated names raise an error.
Project COM onto the triangle of the three nonselected wheel centers and compute
signed edge-line distances. This approximation is not dynamic stability proof.
Malformed dimensions fail; nonfinite/negative masses, invalid quaternion or
degenerate geometry produce per-row invalidity and NaN margin, refusing readiness.
Euler roll/pitch derivatives include yaw-rate coupling, not just body omega XY.

## Verification

RED: 8 observation tests failed because observer module was absent.
GREEN: all 8 passed in 1.84s. Added 3 integration/robustness tests for observer
feeding real PrepareGate, Euler-rate coupling and reread randomized masses.
Combined amp Python `-m pytest -q` run under `Go2Pvcnn` with:

```
tests/test_m1_support_observer.py tests/test_m1_prepare_gate.py
tests/test_support_geometry.py tests/test_crossing_event.py
tests/test_probe_evidence_contract.py tests/test_m1_foot_frame.py
tests/test_m1_cache_foot_frame.py tests/test_m1_runner_wheel_parity.py
tests/test_m1_unreachable_teacher.py
```

**54 passed in 1.94s, exit 0.** Runtime-shaped fixtures use eight rows, including
per-row corruptions. They are not eight actual Isaac environments or a smoke run.
Input buffers are read-only; old teacher, controller gains and training remain unchanged.

## Remaining gates

Need complete runtime snapshot identity/freshness ownership, obstacle sensing and
collision oracle integration, bounded support transfer and all phase transitions.
Then perform the approved 8-env smoke with actual buffers and physical trajectory
evidence. No GPU job or long training started; no display or driver modification.
No claim that this observer alone fixes lifting or crossing. No GitHub push.
