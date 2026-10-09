# Hard-margin feasibility fallback and physical hold plateau

Stage: contact-driven transfer/LIFT; parent
[T306.hard-margin-bound-feasibility](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:`0fec737`; Candidate Ref:commit containing this log.
Key files:`m1_load_transfer.py`, `test_m1_load_transfer.py`.

## Defect and scoped correction

RED reproduced a target rejected withreason3 although hard20mm support margin
has a solution inside the entry displacement bound. Soft30mm is optional.
Extracted the existing 2D halfplane projection. If the soft solution is outside
the bound or infeasible, project from the entry origin onto hard20mm halfplanes.
This finds minimum entry displacement under the existing rigid COM-translation
model; it does not guarantee the physical robot follows that model.
No position/Z/RPY, contact, joint limit/slew or readiness threshold relaxed.
No enlarged motion bounds. Existing satisfied-margin command hold retained.

The previous 6cm-versus8cm test used an input where only soft30mm needed>6cm;
its COM offset was changed from70 to85mm so hard20mm genuinely needs>6cm.
Default6cm still rejects that fixture while explicit8cm accepts. New regression
checks accepted fallback stays in bound and independently computes>=20mm margin.
Full eleven-file focused regression:88 passed in5.48s, exit0.
Command same as [previous test log](2026-10-07-m1-lift-support-transfer.md).

## Physical evidence — no crossing acceptance

GPU7/amp, flat8 seed2,32standing/100PREPARE/200LIFT,dt.02, speed.04,bound.08,
--lift_steps200 --lift_support_transfer (space between flag and value in CLI).
Log:/tmp/m1_contact_lift_hard_margin_20261007.log, nativeexit0,200 lift samples,
stopped=null (budget ended; NOT successful lift or recovery).

- No early bound/support guard rejection; nonselected support minimum21.02N.
- Max absroll/pitch.03884rad; logged pre-action non-support contact maximum0N.
- Each row advanced height only25,24,30,34,28,24,30,34 times out of200.
- Final target19.2..32.8mm; measured rise -3.50..2.03mm.
- Final margin11.97..19.13mm; all rows waiting rather than advancing.

Thus the false-infeasibility branch is corrected and the bounded trace maintains
support, but it stalls without achieving clearance within the4s leg window.
For the full controller this must count as timeout, never strict success.
No substep collision oracle or landing/bypass/policy acceptance is implied.

## Resources and next causal check

Own placeholder660878 stopped/restored695745 and verified alive. Other user
ldc3227360 remained alive. No unrelated processes/display/driver edits or training.
No GitHub push.

New child under support-load-distribution:command-to-COM-tracking. Compare fixed
phase reference, previous commanded root, measured root, measured COM and desired
root during the plateau. Current mapping uses live_root+required_COM_shift;
test whether static tracking error leaves a steady residual instead of assuming
kinematic projection equals actual load transfer. Gather commanded-root trace
before choosing feedback changes; do not loosen20mm gate to bypass the stall.
Recovery, full geometry crossing/landing/events/video/bypass/PPO remain open.
