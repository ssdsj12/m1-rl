# Explicit wheel effort delivery comparison

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), loaded-drive child.
Baseline Ref:16c9916. Candidate Ref:containing commit.
Key files:m1_rolling_speed.py,probe_m1_contact_prepare.py,test_m1_roll_torque.py.

## Method and bounds

Default-off roll_explicit_torque=3Nm replaces supportwheel velocity drive with
explicit feedforward during bounded20stepROLL only. Targetvelocity0 retains
originaldamping5. Torque ramps<=20Nm/s, starts/ends0, selectedwheel0. Existing
leg gravity FF remains separately guarded; fresh wheel damping+FF estimate must
fit actual effortlimits and befinite. Same contact/pose/IK guards; no limits
increased. Nondefault rejects lifted-only or altered-damping combinations.
Native actuationforce telemetry verifies delivered explicit effort, distinct
from the earlier implicit PD estimate. This is not a trainingcontroller.

## Verification

RED5missinghelper; GREEN54focused tests1.70s (torque,boundary,unload gate,
selection,geometry,freewheel,timestep,substeps,drivegain,speed/reference,reserve).
Same original5ms fixed-physics shoulder8envseed2, rearreserve40/front35,
90lift/20roll/90land/100settle, with substepaudit; add explicit3Nm mode.
Raw:/tmp/m1_explicit_wheel_20261007.log. Session18283 terminalexit0.

Native step100env3 actuation=[3,3,3,0]Nm; step109 all0 matching requested.
stopped=null,landing_complete=true,finalstep244. All8settle complete.
Final rolling root displacement-.001532..+.000121m, no useful traversal.
Env3 full rolling qdelta[FBL,FAR,RBL,RAR]=
[.03739128,-.00014533,.00093475,.00024547]rad. The lightlyloaded FBL rotates
more while main loaded FAR/RBL remain effectively stationary. Actual explicit
effort delivery is demonstrated, not net motor torque after damping/contact.

## Decision / next

Do not increase torque again or train from this result. The source collision
mesh previously collapsed into a low-vertex convex hull; diagnostic cylinder
and shoulder also retain coarse faces. Investigate a source-mesh-faithful
collision route and installed support (e.g. dynamic mesh/SDF if supported),
including resource cost and original envelope preservation, before another
physical candidate. This is a hypothesis, not confirmation of a geometry defect.
Original-wheel, realobstacle5cmclearance/far-side landing, bypass/video/policy
acceptance still open. GPU7placeholder2857178->2915023 restored and verified;
no display/driver/unrelated process or dirtyoriginal checkout changes.
