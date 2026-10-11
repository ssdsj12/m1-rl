# M1 execution gates contract

LATEST approved fixed-wheel .30m/s/true12leg PPO:344CPU/real300 explicit conversion passed; original300 preserved. Old7960 safely SIGINT after currentrun700 SHA4a23caf9/CPU validation; isolated native9259 running, no training concurrent. No production deployment yet. [Live evidence](../log/2026-10-11-m1-fixed-wheel-deploy.md). Do not re-ask prior approvals or restart7960/watchers.

LATEST DESIGN ONLY: user confirms fixed forward wheel targets + true12dim leg PPO; no learned wheel/differential actions. Proposed0.30m/s and explicit16-to12 model300/optimizer/std conversion await written-spec review. FK has no independent wheel-yaw steering joint; leg/contact dynamic avoidance remains unverified, not guaranteed. [Design](../log/2026-10-11-m1-fixed-wheel-leg-only-design.md). No production edits or training stop.

Latest implemented contract c7ed76f: per-row autonomous_lift for flat-first levels1–3/non-done only; independent flight/overlap state replaces2cm success prerequisite. Pre-obstacle safe retry preserves highwater/budget. True support/each-overlap3cm/far loaded touchdown/stable recovery remain. Legacy0/mixed4 and2cm telemetry unchanged.307CPU pass; deployment/newmodel300run/exactPT deletion evidence in [current record](../log/2026-10-11-m1-autonomous-lift-timing-deploy.md). Historical DESIGN ONLY below is superseded; no oldPID auto-restart.

DESIGN ONLY: user clarifies horizontal2cm timing, not vertical2cm rise, and confirms autonomous lift/lower timing. [Specification state](../log/2026-10-11-m1-autonomous-lift-timing-design.md): stage1–3 proposed removal of vertical2cm precondition, independent measured support/overlap clearance/far landing/recovery, safe pre-obstacle retries without budget refresh. Existing2cm counter remains telemetry; `.3/.02m` remains a continuous reward scale. No runtime changes or pause in this turn; old deployed thresholds remain until verified deployment.

User override: “长训先，让它自己来折腿” removes static-fold fixture acceptance as a training gate. [Deployment](../log/2026-10-11-m1-lift-roll-self-learning.md) selects m1_lift_roll equal8+70 physical fills,233CPU pass,model300/301+9699/2048 PID4921 started. PPO learns balance/joint actions without trajectories/action takeover; strict3cm/runtime success unchanged. Static controls remain inconclusive, dynamic learning OPEN; earlier no-deploy instructions are historical.

Latest diagnostic-only override: [loaded paired controls](../log/2026-10-11-m1-placement-diagnostic-repair.md) preserve all-frame collision/clearance and final-five support, reject moving/rotating/nonfinite controls, compare normalized quaternion and displacement vectors.232CPU pass;96native recovery placements/runtime readiness pass.56tick empty-ground static folds lose three-wheel support, so classify inconclusive_fixture, not layout rejection/acceptance. No production controls/rewards/std/stance/success changes. Training paused; user-selected current-lineage model300 next301+9699 supersedes1400-only, conditional on remaining native/capacity gates.

Current override: stages1–3 share8targets+70fills, identical XY/footprints, height only3/6/10cm;214CPU pass. Training safely paused at complete model1400; production unchanged. Recovery placement and empty-spawn control both pass measured geometry/support but fail diagnostic pose validity with nearly identical drift. Not proof of physical impossibility and not a native pass. Do not change controller/std/initial stance/runtime thresholds to satisfy diagnostic. See [current evidence](../log/2026-10-11-m1-lift-roll-native-screen.md); earlier4/6/8 preparation is historical.

2026-10-11 [native-screen preparation](../log/2026-10-11-m1-lift-roll-native-screen.md):20cm candidate explicitly selectable only in isolated probe,70physical fills plus4/6/8targets; production stays progressive.213CPU pass; all-tick collision/pose evidence and upward-force+floor-height+all-geometry support checks replace ambiguous final-force-only native measurements. No controller/std/success changes. Static fixture failure is not dynamic impossibility.

2026-10-11 UNDEPLOYED [target/fill roles and candidate gates](../log/2026-10-11-m1-lift-roll-candidate-gates.md):
required_crossing True=target, False=physical fill, None/missing=legacy.
Both grounding paths preserve role; only encounter/mandatory registry excludes
explicit fill. Semantic class, colliders, perception and all-geometry landing
registry stay intact.47CPU pass. Candidate geometry is not production-selected:
2cm seams form an elevated tire-bridge corridor;20cm seams admit optimistic
ground-disk paths. Neither is whole-robot/native accepted; no deployment.

2026-10-11 [deployed density](../log/2026-10-11-m1-density-resume.md): stage1/2
counts4/6 atX=-.6+1.2i;stage3 eight atX=-1.2+1.1i;Yalternates+/-.215.
Stage0/mixed4+,16m tile,spawn-2,585mm,strict metrics unchanged. Stage1/2
along-track density+50%;stage3 instead opens nominal all-wheel landing room.
Current policy/optimizer/std/curriculum retained on checkpoint-boundary restart;
173CPU/native4env passed,1001 resumed from model1000. Nominal positive margins
and placed-pose native checks do not prove dynamic recovery or learned crossing.

2026-10-11 [persistent route cost](../log/2026-10-11-m1-persistent-route-repair.md):
stages1--3 use started, valid, per-wheel unrecovered obligations. Cost is max
over wheel/block pairs of clamp((abs(world_y-block_y)+projected_wheel_half_width
-block_half_width)/.30,0,1), replacing the existing -1 corridor term without
stacking. Actual wheel quaternion determines width. Scanner disappearance,
far exit and retreat do not clear cost; strict per-wheel receipt, done and
registry identity do. Wrapper pre-step snapshot protects terminal accounting.
Stage0/mixed4 keep legacy reward. No pose, std, action or controller changes.
User approved same-model900 resume after native verification; ability OPEN.

Latest [persistent reward](../log/2026-10-10-m1-persistent-crossing-repair.md)
supersedes the finite slab and .3-per-encounter cap. Stages1--3 latch approached
obligations until identity-matched strict recovered receipts for both authored
same-side wheels (FBL/RBL or FAR/RAR). Bypass/far exit/retreat cannot unlock.
Pre-step mask survives Isaac terminal reset; done/registry change clear state.
Actual safe single-wheel progress retains .3/.02m slope through measured
top+required_clearance, frozen initial-loaded budget, no repeated/unsafe-height
credit. Strict2cm event and>=3cm sampled top clearance/recovery gates unchanged.
PurePPO2048 resumes only the current model600 lineage; learned crossing OPEN.

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
