# Stable preload / higher drive comparison

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), traction child.
Baseline Ref:7efc037; Candidate Ref:same runtime code; containing evidence commit.
Key files:probe_m1_contact_prepare.py,m1_rolling_speed.py,m1_rolling_reference.py.

## Hypothesis and method

Once leg-aware preload removes rolling support failure, a higher drive command
might restore forward rotation. Repeat rear-preload flat8env seed2 fixed-physics
shoulder probe with only --roll_speed changed from .02 to .1; same20step ramp,
90lift/90land/100settle,35front/40rear reserve, GPU7 only. No guard changes.
Raw:/tmp/m1_rear_preload_drive_20261007.log; local rear-preload-drive.log.

The acceleration profile bounds actual peak to .036m/s, NOT .1. Integrated
requested speed over20actions at.02s is7.2mm; this is commanded, not measured,
distance. All samples are pre-action; angle interval endpoints exclude the
final zero-command rolling action, so do not present it as exact total travel.

## Verification

Amp Python under Go2Pvcnn:
`-m pytest -q tests/test_m1_rolling_speed.py tests/test_m1_rolling_reference.py`
14passed1.55s. Physical shell session84153 terminal exit0; process2610226 absent.

stopped=null, landing_complete=true, finalstep244, all8 landingstreak5.
Minimum rolling nonselected support34.2782898N. Last rolling progress inmm:
[-.925388,-.552856,-1.108464,-.931409,-.915730,-.548308,-1.109404,-.934242].
Loaded-wheel net rotation across sampled interval .001154.. .010415rad;
most are .001.. .004rad. Source reserve.02case had .001286.. .003382rad.
This is not useful rolling or an obstacle crossing, despite stable landing.

## Conclusion / next

Higher command within the same bounded start/brake window does not restore
traction. No more speed-only tweaks: compare drive torque adequacy and contact
resistance on this now-stable preload baseline, including actual wheel angles
and contact motion rather than instantaneous qdot. Existing diagnostic tire
is still not source-geometry acceptance. Real obstacle,5cmclearance,+4cmlanding,
safe bypass/video and policy acceptance remain open. No long training.

Exact own placeholder2567503 stopped for test and2623404 verified restored.
No unrelated GPU/process, display settings, drivers or original checkout edits.
