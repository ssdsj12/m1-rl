# Opt-in WBC base priority: braking improved, contact transition still open

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), children
execution-physical/braking-allocation and contact-transition-consistency.
Baseline223a0ec; candidate uncommitted codex/m1-contact-crossing.

## Change and regression

Approved WBC design separates physical support tasks from nominal joint motion.
Diagnostic `--base_priority` opts into sixbase tracking first,16joint damping
second. Default22equal objective remains available and unchanged. Hard effort,
20Nm/s slew, contact/friction/load and acceleration bounds unchanged.
No PPO/teacher activation or reference-height change.

Files: `Go2Pvcnn/ame_baseline/m1_wbc_execution_adapter.py`,
`Go2Pvcnn/scripts/probe_m1_wbc_pd_handoff.py`,
`Go2Pvcnn/tests/test_m1_wbc_support_priority.py`.
TDD:3tests failed on missing option before implementation. Real SPD coupled
inverse-dynamics test reproduces xdd=-.8 under equal weighting vs0base target
under hierarchy; no mocked solver.78focused tests passed, then
`OPENBLAS_NUM_THREADS=1 PYTHONPATH=. python -m pytest -q tests/test_m1_wbc*.py`
197passed in2.99s. `git diff --check` clean.

## Actual physical comparison

GPU0,1env,seed7,dt.001,settle2000/stable100,hold500, `--base_priority`.
Log `/tmp/m1_wbc_base_priority_20261009_5Qvtuy.log`, SHA256
`061a2b81a09181a4bbc3dd27738e2d0297e3365af03eb96904d57c6c98a2da0e`.
Same native294ms handoff as baseline. Maxspeed.00623546m/s,last.00326917;
minload83.2994N,maxangular.0150482rad/s,maxtilt.00362215rad.
Atfeedback237 targetxdd-.00226478,solved-.00226456,measured-.00488898.
This materially improves baseline persistent opposite-sign acceleration.

Still FAILED, not support/crossing acceptance: feedback471 next solve returns
`maximum iterations reached; inconsistent_equalities`. Last sample sees one
wheel load jump to170.058N and base acceleration model error grows to.471m/s2.
Process0 does not override error marker. Need actual rejected contact equations,
not threshold relaxation, silent point deletion, or another long training run.
Default/training untouched, GPU7 placeholder1768831 untouched.

## Next diagnostic

Transparent input capture repeat logs full rejected solve inputs to separate
contact row inconsistency from numerical solver failure. Maintain complete
force/moment geometry and unilateral conditions; don't drop contact points to
manufacture feasibility. Physical lift, rolling over10cm,3--5cm wheel-bottom
clearance, collision-free touchdown, recovery and policy-only avoidance remain open.

## Completed failure-frame diagnosis

Transparent repeat `/tmp/m1_wbc_base_priority_capture_20261009_JeoNbg.log`, SHA256
`9889a9404771a088b6d8abca84aa94c132269694cb380e23efd1c10594aab019`,
terminated feedback469/native764. Failure frame has5contactpoints, group counts
[1,2,1,1]. The doubled wheel's world-Z contact RHS is-4.16645 and+3.54123m/s2.
`/tmp/m1_audit_wbc_failure_equalities_20261009.py LOG` verifies:

- full15x22 contact matrix rank14, unconstrained least-squares residual1.80e-8;
  do NOT call that small residual alone the physical root cause;
- contact equations plus original acceleration box are infeasible via independent
  HiGHS LP, even before dynamics/torque/friction constraints;
- normal-only and tangent-only rows each feasible with that same box, jointly not;
- deleting either doubled-wheel point removes the algebraic residual, but this is
  diagnostic only, NOT a valid repair (force/moment/nonpenetration must remain).

Source `contact_mode_for_state` sets every currently loaded point attached and
applies circular-wheel geometry migration independently to all of them. New
patch arrival is treated as permanent simultaneous no-slip support. Next child:
reconstruct point gap/velocity/normal-force history and build a verified transition
mode, retaining unilateral contact and full wrench. Do not increase acceleration,
friction or slew bounds, silently drop a point, or erase the failure as numerical noise.
Both native candidate runs ended; no live diagnostic or training remains.
