# M1 WBC handoff: same-state counterfactual and clock repair

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
execution-physical/handoff-transient. Baseline ref0dd7508; candidate uncommitted
codex/m1-contact-crossing. Stage: diagnostic only, NOT applied WBC/crossing.

## Why previous attribution was incomplete

Frozen input `/tmp/m1_wbc_priority_snapshot_20261009_zzkXcm.log`, SHA256
4247f880190edf6dddd6422ed55c02df643f4ca6fec3545ee0cc3bd8331826fd.
Exact native22ms snapshot:4contacts, full M/h/J/frames, measured velocities,
same friction and35N support minima. Offline helper
`Go2Pvcnn/scripts/audit_m1_wbc_snapshot.py` never imports Isaac or writes actuators.
Four solves hold all inputs/task priorities constant except named factors:

| Torque bounds | Contact normal RHS | qdd_x m/s2 | max torque change Nm |
| --- | --- | ---: | ---: |
| original20Nm/s slew | original | +1.32645 | .019992 |
| original20Nm/s slew | zero diagnostic | +1.32700 | .019990 |
| native capacity only | original | -.18999 | 9.91434 |
| native capacity only | zero diagnostic | -.05318 | 9.49081 |

Desiredx=-.04142m/s2. Native capacity removes slew ONLY in counterfactual;
zero normal RHS is deliberately invalid as a controller. Neither is applied.
Max constraint violation<=1.74e-6, dynamics residual<=2e-8. This refutes the
old claim that native torque capacity still necessarily drives forward under
this snapshot. No torque-rate/clearance/safety threshold is relaxed.
Largest torque difference is ABAD, e.g.FBL -.613->-10.527Nm. Native knee rates
are~.20--.23rad/s. Five1ms samples with bounded base speed/load were sufficient
for the old probe to break its settle loop at22ms; this is not settled dynamics.
Next hypothesis: early handoff locks transient PD effort into overly restrictive
first-step slew. Need stronger settled-state comparison, not another gain sweep.

## Native comparison exposed a clock false rejection

Existing `--snapshot_only --settle_steps 2000 --stable_frames 100 --hold_steps 1`,
GPU0,1env, unchanged PD, no WBC command application.
`/tmp/m1_wbc_settled_snapshot_20261009_6RFD8E.log` terminates on clock guard.
Read-only clock instrumentation repeat
`/tmp/m1_wbc_settled_snapshot_20261009_PNxRVe.log` confirms:
step294, requested/native dt.001, native time.2940000139642507 vs.294 expected.
Installed Isaac SimulationContext `_physics_timer_callback_fn` sums step_size;
294*float32(.001) exactly reproduces the observed time. Existing constant10ns
comparison wrongly rejects legitimate callback quantization after enough steps.

TDD regression:4failed/4passed before fix. Adapter now checks exact step counts,
native configured dt, and either float64 or float32-promoted tick accumulation.
It does NOT permit an arbitrary growing timing tolerance. Stale one-step and
arbitrary drift remain rejected; native-dt mismatch also fails atstep0.
Fresh combined CPU suite119passed in15.79s: native-clock/execution-adapter,
PD-unload/selected-world/PREPARE, mixed-course/registry/metrics/dynamic-crossing.
The new clock code has not yet been revalidated in native Isaac. User requested
upload of the current version before further physical work; no new run started.

## Current scope and next step

All bounded processes terminal. GPU7 placeholder1768831 untouched. No training,
checkpoint writes, GPU resets or display changes. See [PD lift failure](2026-10-09-m1-pd-unload-diagnosis.md).
Next: rerun ONLY snapshot collection with corrected clock, compare against the
frozen22ms input. Then repair measured handoff eligibility within approved WBC
design if supported. Physical single-wheel lift/roll/landing, actual10cm obstacle
clearance, collision-free crossing, recovery and policy-only avoidance remain open.
