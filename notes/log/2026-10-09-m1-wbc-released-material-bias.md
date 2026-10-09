# Correct released-point acceleration semantics

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), child
execution-physical/contact-transition-consistency/released-material-bias.
Baseline c90bb1d; candidate codex/m1-contact-crossing after that commit.
Stage: pure contact-constraint builder; not a new mode selector or training.

## Defect and change

`rolling_contact_step_constraints` used geometrically transported acceleration
bias for both attached and released points. Attached constraints differentiate
the velocity field at a moving geometric support location; a released-point
nonpenetration prediction must track that rigid material point itself.

For wheel radius.1m and omega=(0,2,0), material bias at its bottom is
omega cross (omega cross arm)=(0,0,.4)m/s2; rolling geometric total bias is0.
The old released bound incorrectly used0 instead of-.4 for J*qdd normal.
Now choose transported bias only for attached rows, material bias for released
rows. Every released force capacity remains0, every original geometry slot
and unilateral nonpenetration condition retained. Expose `constraint_bias`
separately from the existing physical/material/transport diagnostic fields.

## Verification

New `Go2Pvcnn/tests/test_m1_wbc_released_material_point.py`:3RED assertion
failures before code change, including actual predicted-gap discrepancy40um.
After correction all200 `tests/test_m1_wbc*.py` pass in2.90s. Tests cover
all-released and mixed attached/released, unchanged attached equation and
semiimplicit next-gap equality at the nonpenetration bound. `git diff --check`
clean. This fixes a model contract; it does not select a physically valid mode.
Existing live support probe has attached=True everywhere and is unchanged by
this correction. No native claim for a newly released mode is made.

Key files: `Go2Pvcnn/ame_baseline/m1_wbc_contact_step.py`, new test above.
[Native patch diagnosis](2026-10-09-m1-wbc-patch-transition-history.md) still
rejects immediate release under original torque slew. Need anticipatory/impact
transition validation, then actual lift/roll/landing; no long train.
