# 2026-10-08 entry planner executor-capability fix

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), baselinebb5b6ff.

## Evidence leading to fix

Read-only original FBL mesh support-envelope scan,1441 angular directions:
zero-camber support depth95.80123..95.96301mm, peak adjacent.25deg change.02339mm;
camber normal component.033 range.16169mm, component.138 range.08078mm.
Coordinates transformed into rigid-body frame, no mesh changes. This does not
establish a unique contact failure cause or authorize simplified geometry.

Existing physics_refinement2 preserves20mscontrol period but uses2.5msphysics.
First physical run `/tmp/m1_roll_dt25_20261008.log` stopped before PREPARE:
entry search chose tilted poses for rows1/5 while executor only handles translation.
This is a candidate-set/executor mismatch, not proof no executable candidate exists.

## Change relative to baseline

Add optional translation_only capability to entry_plan, filter attitude grid
before forecasting/selection. Runtime explicitly requests translation-only.
Keep broad offline search default, all35N/.02m/80mm/IK constraints and final
attitude assertion. No fallback that discards requested tilt after selection.
RED2tests (missing API/runtime capability), GREEN20 planner/reference/timestep tests.
Replaying actual2.5msentry yields8/8valid fixed-attitude candidates, shifts
[75,70,40,20,75,70,40,20]mm. Baseline5ms recorded plan roots remain exactly equal.

## Physical smoke / limitation

`/tmp/m1_roll_dt25_capability_20261008.log`: runtime now passes entry selection,
but PREPARE62 rejects row7RBL0N under unchanged support guard, before UNLOAD.
Thus timestep refinement is NOT a contact fix and is not promoted. Default5ms
remains. Both runs exit0 diagnostic completion only, no crossing or training.
First verified placeholder4171104→4191828; second4191828→13723. Final13723 is
verified own sleep.py and soleGPU7compute. No GPU/display/driver changes.

## Next

Neither spatial nor temporal refinement establishes robust contact support.
Investigate source collision solid interpretation and contact/stance controller
robustness, not further scalar resolution/gain sweeps. Keep endpoint guards;
do not average away real normal-force/COM/angular impulses. Actual obstacle,
landing, bypass, video and policy-only acceptance still open.
