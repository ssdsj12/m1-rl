# 2026-10-08 live-state contact-step rejection and root-cause isolation

Parent [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:0bce18a. Candidate/Verified Ref:this live-step diagnostic commit.
Key files:[step constraints](../../Go2Pvcnn/ame_baseline/m1_wbc_contact_step.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-contact-step.md).

## Model and test scope

Explicit local semiimplicit predictor v_next=v+dt*(J*qdd+b), predicted gap
g_next=g+dt*vn_next. Attached tangent target0, normal targetmax(0,-g/dt).
Released normal lower bound-g/dt, contact force0. Measured state not reset.
Full native h=gravity+C, articulated material-point acceleration bias included,
all10 native contact slots retained. This does NOT certify impacts, finite-step
geometry changes or contact-mode validity. No actuator output consumer yet.

Four new tests RED before implementation; full suite113passed in2.28s.
Checks predicted gap/velocity, releasedforce0, explicitdt, invalid motion,
native full-bias wiring. Existing read-only/unchanged-control checks retained.

## Native evidence

Raw:/tmp/m1_wbc_contact_step_native_20261008.log;
local artifacts/wbc_contact_step_native.log. Bounded read-only probe exited0
with final marker. dt.005; point acceleration bias is nonzero (up to.05272m/s²),
native C up to.03444 in generalized force units. All3 live candidates rejected:
allattached inconsistent equalities; rearrelease/oppositerelease inequalities
infeasible. OSQP and active-set independently rejected. No command applied.
Unchanged diagnostic acceleration box: rootlinear±.05, rootangular±.2,
joints±1; original measured friction, effort and35N/group support preserved.

## CPU causal isolation (not a controller proposal)

Exact M1_WBC_LIVE_REPLAY kwargs processed by /tmp/diagnose_live_step_20261008.py
using least squares and scipy HiGHS LP. Only contact equalities, separation
inequalities and acceleration box used to isolate kinematic infeasibility
before full dynamics/friction/effort. No GPU usage in this analysis.

- Allattached equality rank14; minimum least-squares max error.000245775,
  above1e-5 original constraint check. Removing box entirely still infeasible.
  Forcing simultaneous sticking at both distinct FAR material locations is
  incompatible with this moving-state local bias/target; not a torque shortage.
- Rearrelease equality rank12, error1.71e-15; equality plus unilateral separation
  feasible without diagnostic box but not inside it. Minimum uniform box-factor
  LP1.0543155 (attribution only, NOT adopted). Thus changing solver alone cannot
  make this one-step arrest satisfy original diagnostic limits.
- Oppositerelease rank12/error1.47e-15; minimum boxfactor10.56674, not adopted.
- Unbounded LP witnesses can contain enormous joint accelerations due to
  redundant/near-null directions; never usable as actuator commands or success.

## Next dependency / no silent limit expansion

Audit diagnostic acceleration boxes versus authored state/torque constraints
and reference-motion limits; they are not interchangeable. Need a physically
validated finite-step transition/velocity convergence strategy and sole-owner
handoff, not resetting measured motion or arbitrarily increasing box bounds.
No crossing/stance success inferred from tests or relaxed diagnostic LP.

GPU7 placeholder889301 verified/stopped, restored913319 verified exactsleep.py,
solecompute10624MiB. No display/driver/otherGPU/process change. No training.
