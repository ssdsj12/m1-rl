# Load-feasible PREPARE candidate

Parent:[T306 post-lift-load-readiness](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:b33c284. Candidate Ref:commit containing this log.
Key files:m1_load_transfer.py,test_m1_load_transfer.py,probe_m1_contact_prepare.py.

## Change versus baseline

Optional total_weight adds edge-specific COM constraints. For a support triangle,
distance to edge / opposite altitude is its opposite vertex load fraction. Hard
edge margin=max(20mm,30N/weight*altitude); soft=max(30mm,35N/weight*altitude).
The existing nearest-halfplane solver, entry displacement bound, fixed anchors,
root height, speed, IK and joint slew constraints remain. Readiness holds only
after hard load margins are reached. Weight must be finite and >=90N. This
quasi-static vertical model is separate from measured force redistribution and
does not prove actual contact loads after lift. Default training behavior unchanged.
Opt-in probe --prepare_load_floor uses actual per-env mass*9.81 and includes the
new condition in PREPARE's temporal gate. Post-stage dynamics independently check
the resulting pose rather than trusting the geometric implementation alone.

## Verification

Two RED tests failed because total_weight absent; GREEN28 transfer tests.
Tests show geometric21mm alone no longer stops transfer with insufficient
hypothetical load, and invalid weights reject independently per row.
Full focused13-file regression102 passed in5.47s.

Physical flat8 seed2,32 warmup then100 PREPARE steps; speed.04m/s,bound.08m,
--headless --device cuda:0 --dynamics_audit --prepare_load_floor. No lift/torque.
Raw:/tmp/m1_prepare_load_floor_20261007.log, native0, stopped=null.
Final readiness8/8, post-lift-load-ready8/8, all reason0; margins26.71..32.22mm.
Independent fresh Jacobian/gravity allocation30N valid8/8 (baseline2/8).
Weakest predicted support30.667N. This verifies preparatory load feasibility,
NOT physical lifting, crossing, collision avoidance, landing or learned policy.

## Next

Bounded single-leg physical lift from this prepared state, with live support-loss
checks; effort ramp/clear ownership before any feedforward application. Full
crossing/recovery/bypass/PPO gates remain open. No long training or upload.
Own placeholder867441 restored890689, verified alive; ldc3227360 untouched/alive.
No XLaunch/Xorg/VNC, driver or GPU reset changes.
