# Actual cooked wheel hull and contact moments

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md),effective-rolling-progress.
Baseline Ref:b44ebf3. Candidate Ref:containing commit.
Key file:probe_m1_contact_prepare.py (read-only cooked hull telemetry).

## Contact-moment analysis

Using existing clean-flat contact log, compute (point-wheel_center) cross force.
This is WORLD Y moment, not full generalized joint torque/inverse dynamics.
At samples60/80/100/120/140/160 normal moments Nm:
[+.62986,-1.03173,-1.66920,-1.73082,-1.20216,+.58569].
Friction Y moments Nm:[-.22131,-.09628,-.00367,+.05584,-.07656,-.21006].
Estimated implicit drive:[-.89147,2.95576,4.34873,4.29355,3.32027,-.79486].
Do not equate the implicit estimate with measured actuator torque or claim
these world-frame moments close the full articulated dynamics balance.

## Actual runtime convex geometry

Read get_physx_cooking_interface().get_nb_convex_mesh_data / get_convex_mesh_data
after env.reset; simulation loaded, no forced reload or USD edits.
API reference: https://docs.omniverse.nvidia.com/kit/docs/omni_physics/104.0/source/extensions/omni.physx/docs/index.html
Probe command: M1_OBSTACLE_STAGE=none, --device cuda:0 --headless --num_steps1
(actual CLI: `--num_steps 1`). Exit0. Raw:/tmp/m1_cooked_wheel_20261007.log.
FBL runtime hull:34vertices,62polygons, compared with194634 source points.
Outer-ring samples are uneven: e.g. (x,z)=(.000967,-.095958),
(-.051922,-.080703),(.043930,-.085317). Hull therefore has large planar
approximations around the tread, not the smooth visual circumference.
This strengthens the faceted-contact hypothesis but does not alone prove
causality. No collision geometry, friction, mass, inertia or gain changed.

## Next

Controlled wheel-collision approximation comparison preserving physical
radius/width/mass/inertia/friction and drive conditions, then measured rolling
and regression of lift/landing. Do not treat smoother diagnostic geometry alone
as a validated robot model or crossing success. Still no training.
Placeholder2154675 stopped exactly,2174114 restored and verified.
