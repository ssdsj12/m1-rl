# 2026-10-08 actual WBC effort execution in suspended M1

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:60906c0. Candidate/Verified Ref:this QP execution commit.
Key files:[native probe](../../Go2Pvcnn/scripts/probe_m1_wbc_free.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-execution.md).

## Actual execution contract

New --qp_control opt-in to existing free-body probe. Fresh environment native
K/D zero throughout; explicitly write zero and verify direct native readback
before starting per-row explicit-total history. This is not using zero direct
actuation from an implicit-PD warmup as fake total effort.
Every QP uses current full M/h, named state/speed bounds, physical effort limits,
20Nm/s history interval; solved output is actually written and native readback
checked. History advances only after matching write/readback, no in-loop reset.
No contact forces in this suspended oracle. Soft joint acceleration targets
0,+.1,-.1; free-flight root bounds±20linear/±10angular only for this oracle,
not a change to ground reference limits. dt.001, root starts2m.

## Tests and physical evidence

Opt-in/history wiring test observed RED; full125tests passed in2.52s.
Native command: probe_m1_wbc_free.py --qp_control --kinematic_bias --dt .001
--device cuda:0 --headless, bounded300s wrapper requiring passed/result markers.
Raw:/tmp/m1_wbc_execution_native_20261008.log;
local artifacts/wbc_execution_native.log.

Eight rows x3actual physics ticks all executed, all24QP solutions valid.
Native command readback within1e-7Nm; physical effort limits unchanged.
Maximum full dynamics residual.00570679, below existing.02 threshold.
Kinematic maximum linear error.00074673m/s², angular.00065273rad/s² (<.02).
All contact magnitudes0; minimum rootheight1.999897m. No collision support
was present and no support/stance success can be inferred.

Max QP hard residual5.483e-8. Requested rate maximum20.0000548Nm/s, exceeding
nominal20 only by5.483e-8Nm per1ms tick, within explicit1e-6Nm prewrite numerical
check. Do not report this as exact<=20 without numerical qualification.
Last target reversal reached OSQP iteration cap, independent active-set fallback
solved all8rows without changing physical tolerances. No rejected effort used.
This CPU backend is not real-time certified: some solves take~14ms for1ms physics.

## Remaining scope

Closes WBC-to-native sole-owner free-execution child, not grounded initialization.
Next grounded support initialization/continuity and stance/rolling, then all4
single-leg crossing. Any PD-assisted initialization in a fresh diagnostic would
need separately verified total-drive history; no hot-switch of existing jobs.
No gravity/mass/friction/sourceUSD/display/driver change; no training.

GPU7 exactsole placeholder982669 verified/stopped; restored1018794 verified
exact sleep.py and10624MiB solecompute. OtherGPU/processes untouched.
