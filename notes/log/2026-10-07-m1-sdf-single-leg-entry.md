# SDF single-leg entry: stationary wheel-anchor assumption fails

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), moving support / wheel holding child.
Baseline Ref:a149af2. Candidate Ref:containing commit.
Key files:m1_sdf_probe.py,probe_m1_contact_prepare.py,test_m1_sdf_probe.py.

## Change / verification

Allow opt-in SDF diagnostic for a complete lift/land cycle in addition to
standing. Fixed physics required; prism combination/incomplete cycles rejected.
Existing phase/effort/time/joint/pose protections unchanged. RED missing helper,
GREEN15focused realUSD/contact/substep/wheel tests1.78s.

Physical command same stable rear-reserve cycle as earlier shoulder comparison:
GPU7,cuda0,8envseed2,obstacle stage none,5msphysics,100prepare,.04m/s root speed,
.08m root shift,frontreserve35/rear40,phase effort,100unload/verticalworldpose,
target selectedforce0,min contactspeed.003,90lift/.16m/.12mps,20rollingramp/.1cap,
90land/.005search,100settle. Replace diagnostic shoulder with sourceSDF128,
rest1mm/contact2mm/fixedphysics; native32wheel margin readback required.
Raw:/tmp/m1_sdf_full_cycle_20261007.log, session36341 terminalexit0.

Result: stopped=unload_world_pose_rejected, landing_complete=false.
100PREPARE samples, zero executed UNLOAD and LIFT actions. At UNLOADstep0
all IK reachable/joint limits true, but full frame translation safe=false
for6/8rows. The25mm bound rejects actual-reference xerrors24..37mm plus lateral
errors, not merely a missing knee lift or CUDA failure. Two rows pass frame
bound but batch conservatively stops. No bound changes authorized by this test.

FinalPREPARE wheel-center x displacement from initial anchors spans roughly
-24..-39mm. Row0 fourwheel displacements[-34.71,-36.21,-34.18,-36.08]mm;
root-reference xerror-34.69mm. Reference-ready remains true because it certifies
commanded load-transfer geometry, not actual anchor retention. Mean sampled row0
wheel velocities [FAR,FBL,RAR,RBL]=[-.1557,-.0501,-.2052,-.0814]rad/s despite
zero requestedwheel velocity. These sampled speeds are not integrated angle
proof; nevertheless actual world anchor drift is measured directly.

## Interpretation / next

Previously jammed colliders masked stationary-anchor control assumptions. With
rolling enabled, PREPARE's position targets and zero-velocity-only wheel drive
do not preserve contact anchors. Need bounded wheel holding/coordination during
PREPARE/UNLOAD, with a continuous release into intended rolling and relatch at
landing. First instrument/latch actual wheel positions and enforce existing
effort/slew protections; compare actual anchor/root tracking, not only target
readiness. Do not raise25mm frame limit, pretend reference readiness is actual
readiness, or redefine four-support rolling as crossing. Full three-support,
original-envelope obstacle/landing/bypass/video/policy acceptance remains open.

Own placeholder3162948 stopped,3190750 restored and verified. No training,
driver/display/unrelated-process/originalasset changes. Notes synchronized;
commit local only, not uploaded.
