# Anticipatory transfer deadline audit

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), causalentryforecast.
Baseline Ref:c6ecce5. Candidate Ref:this evidence/diagnostic commit.
Key file:[entry forecast](../../Go2Pvcnn/scripts/forecast_m1_entry.py), new
`--audit-transfer` read-only option. No live timeout/controller change.

## Conflict found

Approved PREPARE maximum2s versus selectedstatic targets20/40/70/75mm.
Existing root_step acceleration cap.05m/s2, velocity cap.04m/s. A rest-to-rest
2s bounded-acceleration/velocity reference can travel at most48mm
(accelerate.8s,cruise.4s,decelerate.8s). Thus70/75mmcannot settle within2s
even with ideal bang-coast-bang timing. This is referencefeasibility, not a
hardware impossibility. Do not silently extend timeout or increaseacceleration.

## Actual primitive replay

dt.02, initialreferencevelocity0, actualroot_step unmodified. For targets
75/70/40/20mm, at2s errors10.665/6.367/3.014/.009mm and speeds
38.005/31.754/5.744/.041mm/s. First error<=1mm AND speed<=1mm/s at
3.56/3.44/2.68/1.30s. These are diagnostic convergence thresholds, not a new
physicalready gate replacing force/contact/pose checks.

## Eight-row candidate path replay

`forecast_m1_entry.py /tmp/m1_entry_snapshot_20261007.log --audit-transfer`
uses causal entry snapshot; offline4s diagnostic budget only.
All8 paths remain within referencebound and every sampled IKreachable.
Maximumjointcommandvelocity.122943rad/s < existing.5rad/s.
Largest finalreferenceerror.030302mm, largestfinalspeed.140528mm/s.
No physical contactforce, effort or dynamics claim. No GPU run/training.

## Decision required

Asked user whether PREPARE alone may become4s while keeping original force,
displacement, clearance, collision and single-leg limits; alternative keep2s
and redesign fastertransfer control. No answer yet. Existing2s contract remains
in force. Await that specific choice before physical candidate integration;
do not mark goalcomplete or pause it. Broader crossing/bypass/policy gates open.
