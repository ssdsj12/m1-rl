# Measured obstacle traverse admission gate

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), obstacle-cycle.
Baseline Ref:bd70438. Candidate Ref:commit containing this log.
Key files:m1_traverse_gate.py,test_m1_traverse_gate.py.

## Timing evidence

Read actual last smoke pre-action samples: first15cm rise atsteps
86,85,84,83,86,85,84,83; first LAND contact>10N at177,180,175,176,
177,181,175,176. Worst remaining budget is19steps/.38s. Adding a fixed
forward interval without replanning is not justified.

## Change and verification

Add independent pure measured wheel/box-corridor admission module. Advance
requires measured envelope bottom>=box top+.05m, fresh safe support and available
landing corridor. LAND requires wheel envelope rear>=far box boundary+.04m,
not merely wheel center past edge. Forward output stops once LAND admitted.
Missing/nonfinite geometry, collision latch, stale evidence or unsafe support
closes both permissions. No counters/success flags.

RED12 missing-module tests; GREEN43 focused tests including lift, crossing-event
andsettle. Batch isolation and below-top lowering after actual far-edge clearance
are included. This is CPU testing, not physics smoke or collision certification.

## Runtime integration still required

Module is deliberately not wired into the flat probe: it has no real obstacle
boundaries. Next add actual box geometry and rolling references together, then
connect this gate to bounded TRAVERSE/LAND and runGPU7 smoke. Caller must supply
conservative wheel collision envelope, event identity/earlylift/collision latch,
deadlines and full-body corridor checks. No fabricated obstacle oracle.
Current action contract scales wheel m/s by1/radius, but probe wheel actions are
zero; verify physical rolling direction and co-moving reference before enabled
forward control. No training or GPU process changes in this audit.
