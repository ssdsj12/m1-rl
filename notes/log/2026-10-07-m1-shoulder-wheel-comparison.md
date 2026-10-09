# Shoulder-preserving wheel collision comparison

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md),effective-rolling-progress.
Baseline Ref:9a3a0c2. Candidate Ref:containing commit.
Key files:m1_wheel_collision_probe.py,probe_m1_contact_prepare.py,test_m1_wheel_collision_probe.py.

## Geometry evidence and change

Source axial radial profile peaks.095963m at center y.0073 and tapers toward
the side boundaries-.0159494/.0305494m. Diagnostic cylinder enlarges shoulders.
Added opt-in shoulder profile:three regular20-point rings (60vertices,42faces),
center radius.095963 and outer rings.084966. Original USD remains untouched.
CPU scan of all source points:maximum radial excess over linear shoulder
surface3.503597mm; angular polygon sag upper bound1.181464mm. Combined radial
under-approximation bound4.685061mm (not a full signed-distance/Hausdorff proof).
Future crossing geometry oracle must use original conservative wheel envelope,
not accept a collision miss caused by this shrinkage. Not yet production.

## Tests and physical comparison

TDD RED:1failure TypeError(profile unsupported),1pass. GREEN24tests pass1.49s.
Read PhysX masses,inertias,material properties after identical seed/reset for
source and shoulder versions:serialized arrays match exactly.
Raw baseline:/tmp/m1_invariants_baseline_20261007.log.
Shoulder:/tmp/m1_shoulder_roll_20261007.log.
M1_OBSTACLE_STAGE=none; same180-step standing roll,gain0,damping5,solver0,
add `--diagnostic_wheel_prism --diagnostic_wheel_profile shoulder`.
Exit0,180samples,stopped=null; cooked60vertices/42polygons.
Rolling-window actual progress(mm):
[60.5670,49.8112,59.0469,60.4312,62.7304,62.0924,59.3408,60.7726].
Source-hull baseline<0.4mm; shoulder version restores8/8forward movement.
This is stronger evidence for collision representation as a cause, independent
of altered masses/inertias/material parameters.

## Next

Verify conservative-envelope clearance and full single-leg lift/land stability
with candidate collision model before adoption/training. Assess whether residual
rolling resistance requires a more accurate regular compound representation,
not arbitrary gain changes or weaker crossing gates. No obstacle success claimed.
Placeholder2193711 stopped exactly;2221235 restored and verified. No unrelated
processes,display or driver changes.
