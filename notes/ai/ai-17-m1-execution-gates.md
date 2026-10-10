# M1 execution gates contract

Latest [repair](../log/2026-10-10-m1-recovery-prelift-pooling-repair.md): default
recovery binds robot and surfaces errors; per-encounter .3 incremental measured
wheel-bottom reward with world high-water anti-farming; obstacle pooling gathers
highest valid winning-class hit XYZ. Event/success thresholds remain unchanged.

Latest: [required-crossing](../log/2026-10-10-m1-required-crossing.md) removes
positive reward in progressive obstacle slabs; actual single prelift and stable
recovery pulses replace sliding progress. Per-overlap3cm mesh-bottom minimum,
three-wheel support, fresh training required. Speed-error gate remains removed.

Latestflat-first profile:emptyflat starts,newfreshPPO; realpre-reset progress
andcompletedepisode gates selectrows0..3flat,then4..9mixed. Speederror logged only. Stage0..3originsX-2m;
body/tirebounds timeoutpreventsadjacenttileunregisteredobstacles. Stable recovery
counter,notfirsttouchdown,qualifiesobstaclepromotion. SavecurriculumstateinPT;
oldmodelswithoutitcannotresumeprofile. [Evidence](../log/2026-10-10-m1-flat-first-curriculum.md).

User-authorized stance exception:585mm total source mesh height, root .4560008115,
hip -.8826416550, knee1.6824843873. Asset-calibrated angles, not vendor preset
verification. Pure PPO/no teacher unchanged. Physical stability and checkpoint
adaptation are required before deployment. [Evidence](../log/2026-10-10-m1-585mm-stance.md).

Reward-query repair: retain old physical lookahead bounds but add2cm longitudinal
samples so5cm blocks cannot fall between15cm probes. No coefficient, policy,
actuator or strict-success changes. [Evidence](../log/2026-10-10-m1-ppo-narrow-probe-repair.md).

Dense-forward update:2048env launcher; mixed16x16tiles, eight10cm alternating
anchors on y=+/- .215 per tile, fixed spawnxy/yaw and forward-only command limits.
Background excludes landing corridor. This is layout exposure, not a controller
enforcing one-leg lift. [Validation](../log/2026-10-10-m1-dense-forward-2048.md).

2026-10-10 override: pure PPO is the active training contract. No MPC teacher,
imitation or action takeover; WBC diagnostics below are historical, not training gates.
Only reward/terrain tuning is authorized. Strict physical crossing remains the acceptance
criterion, distinct from lift reward and proxy rate. [Evidence](../log/2026-10-10-m1-pure-ppo.md).

Contact model correction: attached acceleration uses moving-geometry total
bias; released unilateral nonpenetration uses material-point bias. Both fields
remain available; `constraint_bias` identifies the one actually used perpoint.
Released force capacity0, geometry/order retained.200WBCtests, no actual
released-mode acceptance. Native history identifies filtered zero-force
approaching points; immediate release still infeasible at original slew.
[Evidence](../log/2026-10-09-m1-wbc-released-material-bias.md).

Support diagnostic update: `pd_handoff_acceleration_contract(base_priority=True)`
splits sixbase tracking before16joint damping, preserving every original hard
bound. Only isolated probe `--base_priority` opts in; default and train unchanged.
197WBCtests. Native500tick comparison suppresses wrong-way acceleration
(maxspeed.006235m/s) but stops at471 on contact equation inconsistency.
Not accepted for UNLOAD/lift/crossing; contact transition remains OPEN.
[Evidence](../log/2026-10-09-m1-wbc-base-priority.md).

Latest physical evidence: PREPARE deadline restored to200steps/4s,8/8ready;
PD-onlyUNLOAD0/8. Existing selected-leg world-height correction aborts atstep19,
0/8complete. Body-pose drift plus joint tracking cancels most commanded rise.
No effort-assisted lift, WBC handoff or obstacle-crossing acceptance inherited.
[Evidence](../log/2026-10-09-m1-pd-unload-diagnosis.md).

Mixed-course update (2026-10-09): train defaults to mixed reference terrain,
flat small density x1.5; M1 and16actions retained. Registry indexes actual
grounded objects by live terrain row/column. Encounter state latches wheel,
obstacle and direction; early lift requires contact loss plus measured rise
from last loaded wheel bottom, not obstacle-ground elevation or unloading.
All small/large objects and all four wheel footprints gate landing. Failed or
abandoned encounters release outside their vicinity without erasing attempts.
Primary strict success is events/attempts in mixed mode; proxy and recovery
remain separate.148passed/1skipped; native scene/scan passed with2376records,
2280small10cm bounds,172semantic-small hits and2neutral steps (strict0).
These are measurement gates, not proven future-foothold planning or crossing.
[Ledger](../log/2026-10-09-m1-mixed-dense-progress.md).

Measured-bottom update: strict wrapper uses authored collision vertices in
wheel body frames plus measured body poses, not fixed radius. Cached env0 mesh
requires identical replicated assets; recreate after geometry edits. Convex hull
preserves extrema.52tests/sourceUSD checked; live PhysX/SDF offsets unverified.
[Evidence](../log/2026-10-09-m1-oriented-wheel-bottom.md).

Latest user contract: use vendor Climb/state8 posture, not maximum-extension
height, Stair, or HighLowStance. Numeric preset still unknown; require vendor
definition or verified named joint/IMU capture. Wheel-bottom target3--5cm
(default4cm), strict wrapper threshold3cm; load reduction is not physical lift.
[Source audit](../log/2026-10-09-m1-climb-sdk-and-bottom-clearance.md).

Human pair: [human-17](../human/human-17-m1-execution-gates.md).
Task: [T306](../todo/T306-m1-ame-long-train-stability.md).
Evidence: [PREPARE](../log/2026-10-09-m1-batched-prepare-controller.md).

Upstream: settled measured robot COM, wheel positions/contact forces, actual
mass, entry pose/joints, per-env episode/obstacle/selected-leg identity.
Method: `M1PrepareController`, four grounded wheel anchors, bounded COM/root
reference (.08m displacement,.04m/s,.05m/s2),12legIK, canonical16PD actions.
Output: proposed position action and eligibility; fresh readiness/failure mask.
`advance_reference=False` consumes final evidence without mutating the last
executed root/joint/velocity. Failures are latched until explicit per-row reset.

Ready: five consecutive measured frames through PrepareGate plus stopped
reference<=.001m/s and forecast supporting-load reserve. `lift_authorized`
is alwaysfalse. `finish` never converts timeout/history-only success to ready.
Probe `--batched_prepare` and legacy mode accept1..200steps (4s).

Downstream: future measured UNLOAD must inherit last executed reference and
fresh contacts, not a future proposal. Effort-owned UNLOAD evidence cannot be
faked for this PD path. Runtime training teacher integration is still OPEN.
Production WBC sole-owner torque, lift/hold/roll/landing,10cm obstacle clearance,
policy-only crossing and large-obstacle avoidance remain separate open gates.
