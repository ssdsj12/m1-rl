# Four-support rolling without support feedforward

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), effective-rolling-progress.
Baseline Ref / Candidate Ref: 5acecde (no runtime code changes).
Key Files: Go2Pvcnn/scripts/probe_m1_contact_prepare.py; ame_baseline/m1_rolling_speed.py.

## Purpose and procedure

Test whether support feedforward is necessary for the observed near-zero rolling.
Same flat eight-environment probe, GPU7, default wheel damping 5, unchanged
geometry and guards. Command:

`python scripts/probe_m1_contact_prepare.py --device cuda:0 --headless --num_steps 1 --standing_effort_steps 100 --standing_roll --standing_effort_gain 0`

Only the support feedforward gain differs from the previous gain-1 comparison.
Raw evidence: `/tmp/m1_four_support_noff_20261007.log`.

## Result

Process exit 0. M1_STANDING_EFFORT: 100 samples, stopped=null, cleared=true,
gain=0. World X displacement between pre-action samples 60 and 80 (mm):
[-0.65977, -0.69006, -0.63397, -0.65889, -0.67255, -0.67841, -0.62473, -0.66058].
No effective forward traversal. This rules out support feedforward as a
necessary cause under this short diagnostic, not all possible control coupling.

## Follow-up and limitations

The 20-frame triangular profile peaks at 0.036 m/s and integrates to only 7.2 mm.
This is a transient probe, not a steady rolling test. Inspect actual contact
geometry and wheel angular response; a bounded longer four-support drive
comparison would distinguish startup resistance from persistent blockage.
Do not increase gains blindly or call this obstacle-crossing acceptance.
No training started, no display/driver changes. Exact placeholder 2011308 was
stopped and placeholder 2043200 restored and verified after the probe.
