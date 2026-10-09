# Bounded UNLOAD reference reaches all-leg lift; rolling still rejects

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), dynamic-support child.
Baseline Ref:1c7e9b6. Candidate Ref:containing commit.
Key files:m1_com_trajectory.py,probe_m1_contact_prepare.py,test_m1_com_trajectory.py.
Scope: approved bounded COM-transfer implementation, default-off diagnostic.

## Root-cause evidence and change relative to baseline

Baseline UNLOAD row1 at50 starts root reference from0 to[-.02149,.03376]m/s
in20ms (~2m/s2); row0 at49..52 likewise restarts correction abruptly.
This coincides with measured lateral friction/moment and low-support loss.
Reuse existing com_step reference acceleration/braking (.05m/s2,.04m/s,80mm),
wrapped in fixed-entry world-root XY with explicit unchanged-Z validation.
Default-off unload_com_ramp operates only after a valid transfer proposal;
initial velocity comes from last executed PREPARE command, not inventedzero.
IK, selected-world correction, joint slew, effort, contact/pose, deadline and
entry-displacement rejection remain in force. No controller mass/asset change.

## Tests / experiment

Two new tests RED missing root_step, then49 COM/load-transfer/unload/telemetry
tests passed2.88s. Tests enforce acceleration, entry-height,80mmbound and
invalid-row retention. Explicit flag requires coordinated unload.
Matched GPU7 fullcycle command from friction-substeps plus unload_com_ramp.
8envseed2, sourceSDF128/rest1mm/contact2mm,100PREPARE,100UNLOAD,90LIFT,
20ROLL,90LAND,100SETTLE budgets; no new training.
Raw:/tmp/m1_unload_ramp_20261007.log; session40699 terminalexit0.
Own3932345placeholder stopped;4054047 restored and verified.

## Physical result

Baseline rejectedUNLOAD53 beforelift. Candidate passes unloading at64 with
all selectedforces0, minimum others33.69965N, fresh readiness streaks
[22,8,22,21,22,5,6,11]. Reference velocity acceleration max.028811m/s2;
finite-difference realized world-command max.028888m/s2 (float precision).
8/8reach final LIFT reference.16m; measuredwheel-center rises at89:
[.159756,.159772,.159647,.159607,.159741,.159736,.159665,.159608]m.
Maximum absolute roll/pitch across90LIFT observations.012996rad (~.745deg),
nonwheel contact force0. HOWEVER minimum sampled remaining support overLIFT
is17.3699N: advance gate can pause lift below30N, this is not uniformly stable
>=30N evidence or full-support acceptance. Do not hide this transient.

Candidate stops rolling_support_rejected atglobal95 (ROLLoffset5), before
that step's action. Row1/FAR lifted, RBL support29.69426N<30N. Other rows
advance true. Final rise~.16m but no meaningful forward travel: rollprogress
negative ~.015.. .255mm. No LAND/SETTLE reached. No obstacle in this test.
Wheel-center rise is NOT proof of original-wheel-envelope5cm obstacleclearance.

## Follow-up / limits

Retain opt-in improvement; no longtrain or obstacle success claim.
Next support continuity through LIFT/ROLL: inspect low-force transients,
finalCOM reference velocity (~2.4mm/s, notzero) and wheel-hold→forward transition.
Do not relax30N to pass29.69N, or call90-step lift a complete crossing.
Only controlled matched comparisons with existingforce/pose/effort bounds.
Full landing, actual forward traversal, sixobstacles,5cmclearance,4cmlanding,
bypass/video/policy-only remain open. Notesaligned,localcommitnotuploaded.
