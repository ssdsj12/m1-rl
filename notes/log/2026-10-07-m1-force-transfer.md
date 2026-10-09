# Optional force-aware transfer: negative physical result

Stage: diagnostic support transfer; parent
[T306.force-versus-margin-handoff](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:`a71cf2c`; Candidate Ref:commit containing this log.
Key files:`m1_load_transfer.py`, `test_m1_load_transfer.py`, `probe_m1_contact_prepare.py`.

## Scoped candidate

Optional wheel_force input allocates a30N minimum target among three nonselected
supports by moving load from legs above30N, preserving total measured support
load. The force-weighted center displacement proposes root correction; project
it onto hard20mm geometric constraints. Keep original8cm entry/speed/IK/slew
bounds. No geometric fallback may silently erase the requested load correction.
Missing force fails closed; support<=10N or total<90N is reason6, not recovery.
PREPARE omits force input, retaining geometric behavior. Probe opt-in flag
--lift_force_feedback requires --lift_support_transfer; defaults remain off.

Three RED tests failed on missing force feedback. GREEN checks nonzero shift
toward weak support despite valid geometry, row-local missing/lost-contact
rejection, and target-load conservation/floor. Full focused suite92 passed
in5.43s, exit0; same eleven-file command as previous logs. Syntax check passed.
Target force is a proposal, not evidence of achieved contact force.

## Actual8-env result

GPU7/amp,flat8 seed2,standing32/PREPARE100/LIFT200maximum,dt.02,
speed.04,bound.08. Command adds --lift_support_transfer --lift_force_feedback.
Log:/tmp/m1_contact_lift_force_feedback_20261007.log,nativeexit0.
Stops atliftstep43, env3 reason106 (transfer load/contact reason6): nonselected
leg0 force7.882N. Its measured geometric margin20.85mm is nevertheless positive
and above the20mm gate, independently illustrating insufficiency of geometry.
Proposed support forces[30,211.55,139.57]N are NOT actual achieved forces.
Final target19.999..36.800mm; actualrise -3.09..1.09mm, no useful clearance.
No claim that force feedback solved support allocation or that crossing works.

## Architecture review / next step

Pose-only, planar COM-only and force-weighted planar position proposals have
not established support during lift. Do not continue tuning planar gains or
thresholds in isolation. Review load-bearing joint/whole-body posture dynamics
and bounded effort compensation, with independent model checks before enabling.
Installed local IsaacLab has set_joint_effort_target (buffer only; write_data_to_sim
applies it); installed PhysX tensors api.py exposes get_jacobians,
get_generalized_gravity_forces and get_gravity_compensation_forces. These are
source-interface findings only: tensor conventions, floating-base mapping and
runtime availability must be verified before any effort is applied.
New child:whole-body-load-model. Existing candidate stays optional/off; full
recovery, obstacle trajectory/landing/collision/video/bypass/PPO remain open.

## Resources

Exact own placeholder733255 stopped/restored762874, verified alive; other user
ldc3227360 alive. No GPU reset/display changes, unrelated job stop, training or push.
