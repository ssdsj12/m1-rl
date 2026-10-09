# Half timestep comparison rejected

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), traction/solver child.
Baseline Ref:ec01b92. Candidate Ref:containing commit.
Key files:m1_rolling_speed.py,probe_m1_contact_prepare.py,test_m1_probe_timestep.py.

## Implementation and tests

Opt-in --physics_refinement2 halves physical dt and doubles decimation/render
interval. Control20ms, total phase duration, sensor update period, actuator
gains and guards unchanged. Default1 retains old behavior. Added finite allowed
factor validation and physical-period tests. RED6missinghelper; GREEN24tests
in1.51s (timestep,substeps,roll-drive,rolling-speed,rolling-reference).

## Physical procedure / evidence

Repeat ec01b92 fixed-physics shoulder,8envseed2,none-stage,rearreserve40/front35,
gain5,.1cap20ramp,90lift/90land/100settle,substepaudit; only add refinement2.
Walltimeout480s compensates added compute, NOT changed simulated action budget.
Actual M1_TIMESTEP dt.0025,decimation8,control_dt.02,render_interval8.
Raw:/tmp/m1_timestep_half_20261007.log. Session99606 exited0, but physical
stopped=settle_contact_lost_or_missing,landing_complete=false. Last recorded
sample199; landingstreak[0,1,0,0,0,1,0,0]. Do not count shell exit as success.

20rolling actions, each8substeps; minimum nonselected support31.101N.
Last rolling root progressmm:
[-1.030366,-.597507,-1.125658,-.862474,-1.030216,-.596008,-1.122806,-.860041].
Env3 full rolling angle delta[FBL,FAR,RBL,RAR]:
[.01572338,.00106364,.00139794,.00017070]rad. No effective forward travel.

## Decision / architecture review

Do not promote half timestep or resume training. Keep original5msdefault.
Speed,phasegain andtimestep interventions have failed to create useful rolling;
another scalar tuning loop is not justified. Revisit whether frozen three-leg
posture/translated references with static gravity allocation can produce the
needed coupled contact/wrench dynamics during three-support rolling. Inspect
actual root/leg/contact constraints and existing approved design before changing
the control architecture. Source-geometry, obstacle clearance, far-side stable
landing, safe bypass and learned-policy/video acceptance remain unverified.

Exact own placeholder2696342 stopped;2723800 verified restored. No training,
display/driver/unrelated process or dirty original checkout changes.
