# M1 execution gates contract

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
