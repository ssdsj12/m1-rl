# Physical lift after load-feasible preparation

Parent:[T306 whole-body-load-model](../todo/T306-m1-ame-long-train-stability.md).
Baseline/Candidate Ref:f3adc98; no control code change in this experiment.
Key files:probe_m1_contact_prepare.py,m1_load_transfer.py,m1_single_lift.py.

## Procedure and results

Flat8 seed2, GPU7,32 warmup +100 PREPARE +budget200 LIFT steps. Command adds
--prepare_load_floor --lift_steps 200 to prior load-feasible PREPARE probe;
speed.04m/s,bound.08m, --dynamics_audit --headless --device cuda:0.
Raw:/tmp/m1_load_feasible_lift_20261007.log. Native0 indicates clean diagnostic
exit, NOT a passed physical gate. Stopped=lift_guard_rejected atliftstep38.
Row3 nonselected wheel0 force8.4878N triggers reason2. Commanded lift3.12..4cm;
actual wheel rise -2.38..2.14mm. No lift or clearance success.
PREPARE load feasibility was verified, but cannot ensure load during motion.

## Tracking evidence and next action

At rejection, measured root is12.0..16.5mm below commanded root. Actual leg
joint positions differ from already applied position targets by maxima roughly
.07..08rad per row (not comparing against the newly proposed next command).
Root tilt magnitude by axis remains<.042rad, yet support distribution degrades.
This strengthens the need for whole-body load/actuator tracking rather than
another increase of PREPARE margin or reward. It does not alone identify which
tracking component causes the entire lost wheel rise.

Next child remains bounded-effort-lifecycle under whole-body-load-model:
test explicit named-joint ownership, rate-limited feedforward and clearing on
invalid/reset/exit, with total PD+feedforward bound before application. Then
bounded standing trial first, measuring actual drift and loads; only then lift.
Do not silently activate in training, relax support guard, or call clean exit
success. Full obstacle traversal/landing/collision/bypass/PPO remain unverified.

## Resources

Only exact own placeholder890689 stopped, restored906048 and verified alive.
Other user ldc3227360 alive. No new training, display changes, driver reset or
upload. Raw trace retained locally and remotely; tests unchanged fromf3adc98.
