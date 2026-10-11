# M1 fill-obstacle role conflict before implementation planning

## Purpose / authorization / scope

The user approved the [written lift-and-roll spec](../../docs/superpowers/specs/2026-10-11-m1-alternating-lift-roll-design.md).
The behavior and written spec are approved; do not ask for those again.
Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/density-exposure/lift-roll-layout/fill-role-contract`.
This read-only CPU check resolves the spec's explicit warning that fill geometry
may be interpreted as unrelated mandatory crossing obligations. No production
code or training process was changed.

## Procedure / evidence

Current host a21472797434572800304964, worktree contact-recovery.
Executed the following against deployed source with `CUDA_VISIBLE_DEVICES=`,
`OMP_NUM_THREADS=1`, `PYTHONPATH=Go2Pvcnn`, environment Python `env_issacsim`:

```python
import torch
from types import SimpleNamespace
from ame_baseline.m1_course_registry import CourseRegistry
from ame_baseline.m1_required_crossing import progressive_required_wheels

def obj(slot, y):
    return SimpleNamespace(row=1, col=0, slot_index=slot, semantic_class='small',
        shape_kind='cuboid', shape_params={'size': (.10, .18, .03)},
        world_center=(0., y, .015))

for name, objects in [('track_only', [obj(0, .215)]),
                     ('track_plus_background', [obj(0, .215), obj(1, 1.)])]:
    course = CourseRegistry(objects, rows=4, cols=1, device='cpu').for_envs(
        torch.tensor([1]), torch.tensor([0]))
    print(name, int(course['valid'].sum()), int(course['landing_valid'].sum()))
    try:
        print(progressive_required_wheels(course, torch.zeros(1)).tolist())
    except ValueError as exc:
        print(type(exc).__name__, str(exc))
print('cuda_initialized', torch.cuda.is_initialized())
```

Observed: track-only targets1/landing_geometry1, required wheels
`[[[True, False, True, False]]]`. Adding y=1m fill produces targets2/
landing_geometry2, then `ValueError: progressive obstacle has no authored M1 wheel track`.
`cuda_initialized False`; command exited0 because the diagnostic captured the
expected exception. This is a reproduced interface incompatibility, not a passing
terrain implementation test and not a fault in the currently deployed sparse layout.

Source trace: CourseAnchor/GroundedCourseObstacle contain semantic class but no
target/fill role; CourseRegistry puts every semantic-small object into `valid`;
progressive_required_wheels requires every such object to intersect a nominal
authored wheel lane. All-geometry landing_registry correctly includes both.
Therefore simply adding small background blocks is not a safe implementation.

## Approved minimal contract / implementation evidence

Use explicit `required_crossing` metadata for stage1--3 geometry: alternating
track targets true; off-track fill false. Preserve semantic small classification,
USD collision, scanner visibility and all-geometry landing checks for both.
Only the mandatory target list/receipts/route obligations use this distinction.
Do not relabel fill as semantic-large merely to bypass the check, delete the
assertion wholesale, or omit fill from the registry's safety geometry.
Stage0/mixed4+ keep existing behavior; old metadata-free layouts retain their
legacy interpretation, so checkpoint/controller/std do not change.

The user has confirmed this role addition and selected inline execution in the
dedicated local mirror. Do not ask for these approvals again. Implementation is
isolated from production under `/tmp/m1-lift-roll-candidate-20261011`.
Task1 RED: new tests failed9/passed1 against old source. GREEN: role fields in
both dataclasses and both grounding paths, strict bool/None validation, and
encounter-only fill filtering passed47 tests in2.03s (fill roles, registry,
persistent route, dynamic crossing, semantic curriculum layout). Landing still
rejects a wheel over fill; legacy None/missing roles retain targets. No production
change, GPU probe, signal, restart or GitHub publication occurred.

## Follow-up / refs

Continue the approved implementation plan with geometry packing, bounded bypass
search, CPU regression, checkpoint-safe native validation and same-lineage resume.
Baseline Ref:e8260f7 (design); Last Feature/Verified Feature:5a366ff unchanged.
Key Files:extension/semantic_course.py,ame_baseline/m1_course_registry.py,
ame_baseline/m1_required_crossing.py and the written spec.
