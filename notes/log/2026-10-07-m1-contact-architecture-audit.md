# Contact/control architecture audit after scalar comparisons

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), traction child.
Baseline Ref:ea14185; Candidate Ref:same runtime, containing evidence commit.
Key files:m1_support_effort.py,m1_ame_actions.py,probe_m1_contact_prepare.py.

## Design alignment

Re-read approved contact-crossing design: full event geometry, actual forward
traversal, contact support, recovery/bypass and policy integration remain required.
The diagnostic static vertical allocation explicitly lacks tangential forces,
accelerations and contact moments. It must not be described as whole-body
dynamic control or a proof of feasibility. A full controller rewrite is not
justified merely by that limitation; first isolate the demonstrated stall.

Read actual ManagerBasedRLEnv.step and M1MixedJointAction.apply_actions:
ordinary path applies targets, advances physics, updates buffers; M1 writes
leg position and wheel velocity targets, not wheel position resets. This
inspection does not rule out all event/solver mechanisms. Prior native substep
audit separately ruled out stale cache for the sampled window.

## New matched contact evidence

Read existing rear-preload-drive.log and roll-drive-gain.log, env3step100.
All three audited wheels have two geometric contact records with~30.024mm
separation. Positive normal loads differ:

| Wheel | gain5 point forces N | gain20 point forces N |
| --- | --- | --- |
| FBL |36.995,0|37.573,0|
| FAR |90.337,98.441|91.076,97.595|
| RBL |85.752,84.667|88.366,81.617|

FBL (the lighter support) is able to unload one point and rotates more; the
two main supports retain both positive contacts and tiny net angles despite
larger implicit drive estimates. For a rigid wheel, two fixed separated ground
points geometrically prevent unconstrained axle rotation; actual solver contacts
are unilateral and can slip/unload, so this does NOT prove both points are fixed
or that this alone causes the stall. Drive estimates are not measured impulses.
The correlation makes contact isolation more informative than another gain tweak.

## Next bounded test / decision

Keep original5ms/gain5 geometry/preload baseline. In an opt-in diagnostic only,
command the already lifted wheel while grounded wheels receive zero speed;
measure its actual angle versus targets and substep velocities, keeping all
existing lift/support/landing guards. Do not count in-air rotation as crossing.
If free wheel responds normally, ground contact/loaded dynamics become the
primary isolation target; if not, investigate drive/articulation integration.
Only then select a justified contact representation or coordinated-controller
change, preserving the original physical envelope for eventual acceptance.

No test run or runtime change this turn; this is a read-only evidence audit.
No GPU use/training; own placeholder2723800 was verified live on entry. No
display/driver/other-job or dirty-checkout changes. No success/PT capability claim.
