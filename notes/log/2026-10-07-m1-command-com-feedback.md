# Command-to-COM tracking correction

Stage: bounded contact transfer; parent
[T306.command-to-COM-tracking](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:`d4539df`; Candidate Ref:commit containing this log.
Key files:`m1_load_transfer.py`, `test_m1_load_transfer.py`, `probe_m1_contact_prepare.py`.

## Evidence and RED/GREEN

Added same-frame previous/next root command and desired transfer root to LIFT
telemetry. Unchanged physical repeat `/tmp/m1_contact_lift_command_trace_20261007.log`
exits0 and repeats200-step plateau. Final command-minus-measured horizontal
offset components reach ~30mm; measured margins remain11.97..19.13mm.
This confirms measured pose is not interchangeable with the last command.

CPU regression constructs a20mm command tracking offset with measured15mm
margin. Old formula returned a desired command increment of -5mm along the
required correction direction despite needing at least+5mm. RED failed on this
numerical assertion (not an import/error). Correction applies measured COM
error to previous commanded root, including the hard-margin fallback coordinate
origin. Entry/Z/RPY bounds, speed and IK/slew remain unchanged; this is bounded
horizontal feedback, not integrating measured sag or increasing limits.
Eleven-file focused suite:89 passed in5.31s, exit0. Same command as preceding logs.

## Physical candidate

Native exit0: same flat8 seed2, standing32/PREPARE100/LIFT200 maximum,
dt.02,speed.04,bound.08,--lift_support_transfer. Log:
`/tmp/m1_contact_lift_command_feedback_20261007.log`.
PREPARE ends8/8ready, no regression of that single-seed gate. LIFT stops atstep45
withreason2 inenv7: nonselected leg0 force0N. Final commandedrise20.8..36.8mm,
actualrise -3.13..1.35mm. No meaningful clearance, no successful lift/crossing.

The telemetry exposes another concrete control mismatch: env3 margin20.75mm
but nonselected leg0 force20.55N (<30N preventive advance threshold). Probe
requests support hold, yet transfer_target's geometric>=20mm stopping predicate
returns the unchanged root. This is not a measured load-redistribution controller.
The command-space correction is necessary for its reproduced regression but
insufficient to maintain three-support force during unloading.

Next child:force-versus-margin-handoff. Analyze physically feasible support-load
targets and bounded body position/attitude jointly. Do not just lower force
threshold, increase limits, or continue escalating translation gains. If adequate
three-support loading is infeasible in the current stance, report that explicitly
and use the approved bounded posture preparation/recovery rather than treating
geometric readiness as a stability guarantee. Full recovery, clearance/traverse/
landing/event metrics/video/bypass and learned-policy gates remain open.

## Resource lifecycle

Trace run stopped exact own placeholder695745 and restored719146, verified.
Candidate run stopped719146 and restored733255, verified alive. Other user ldc3227360
remains alive. No display/driver edits, unrelated termination, training or push.
