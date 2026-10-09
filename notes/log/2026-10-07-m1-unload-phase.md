# Explicit measured unloading phase

Parent:[T306 bounded-unload-handoff](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:940fc46; Candidate Ref:commit containing this log.
Key files:m1_unload_gate.py,test_m1_unload_gate.py,probe_m1_contact_prepare.py.

## Difference / tests

Optional bounded100-step UNLOAD keeps PREPARE position command/zero lift height
while three-support feedforward converges. New predicate requires selected<=5N,
other3>=30N, tilt<=.15rad,rate<=.20rad/s, valid allocation and effort target gap<=1Nm.
Caller counts5 fresh consecutive observations, resets streak on failure and stops
on episode reset/contact/pose/allocation failures or timeout. Selected wheel may
be unloaded; other supports still subject to10N abort. Four RED missing-module
tests then GREEN; focused15-file suite112passed5.68s. Defaults unchanged.

## Physical result

GPU7 flat8seed2;32warmup+100PREPARE+100UNLOAD,budget200LIFT, --prepare_load_floor
--phase_effort --unload_steps100 --lift_steps200, transfer_speed.04,bound.08;
CLI values separated. Raw:/tmp/m1_unload_phase_20261007.log; native0.
Stopped=unload_timeout; all100unloadsteps executed,0liftsteps; cleared=true.
Final allocations8/8valid; effort target gaps.00016..00059Nm (command convergence,
not measured motor torque). Selected wheel forces24.89..46.97N, all readinessfalse.
Other supports remain>30N atfinal; original abort never fired.

## What this changes

The failure is not simply insufficient ramp time. Even converged three-support
feedforward with fixed position targets does not achieve selected-contact unloading.
Next child:total-effort-contact-consistency. Log actual joint targets/positions,
PD estimate and added effort alongside measured contact-force Jacobian projection;
check whether implicit PD opposes unloading or model force/effort conventions
remain mismatched. Do not just wait longer, increase gains, lower5N threshold or
cancel PD blindly. Only move to new load-control policy after this evidence.
Full lift/crossing/landing/collision/bypass/PPO remain open; no training/upload.
Own973880 placeholder restored997933, verified alive; ldc3227360 untouched/alive.
No display/driver/reset changes.
