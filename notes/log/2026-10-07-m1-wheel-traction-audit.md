# Wheel drive and collision-model audit

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),effective-rolling-progress.
Baseline Ref:6616347. Candidate Ref:commit containing this log.
Key file:probe_m1_contact_prepare.py (read-only backend/drive telemetry).

## Runtime evidence

Same8flatseed2GPU7retimed/rampedcycle. Raw:/tmp/m1_wheel_effort_20261007.log.
Native0,landing_complete true; existingflatlanding result reproduced.
Allwheels:jointfriction0,armature0,stiffness0,damping5,effortlimit50Nm.
Step100loadedwheel estimateddrive~.95..2.61Nm;computedandclippedvaluesmatch.
Thusnot torque-limitclipping orwheelposition-servo lock. Generalizedwheel
gravity/contactnormal effortfrompriorallocation is~1e-6Nm,notlarge missing
wheelgravityfeedforward. Theseareimplicitdriveestimates,notexternalforceproof.

## Read-only USD inspection

LoadedUSD withbundledpxr libraries onCPU(noSimulator,noGPUplaceholderchange).
TraverseInstanceProxies isnecessary:ordinaryTraverse stopsatinstance roots.
FBLwheelcollider is194634-pointMesh withPhysicsCollisionAPI andconvexHull
approximation. Bounds X[-.0959013,.0959013],Y[-.0159494,.0305494],
Z[-.0959581,.0959581];maximumXZradius .0959630m. RevolutejointaxisY.
Noauthoredhullvertexlimitobserved. NVIDIA schema documentsdefaultcookinglimit64:
https://docs.omniverse.nvidia.com/kit/docs/omni_physics/107.3/dev_guide/schemas/physxschema.html
Thatdocumentationdoesnotexposethisruntime'sactualcookedhullshape. Faceting-induced
rollingresistance isahypothesis,NOTconfirmedrootcause. Do notreplacegeometry
orchangefriction/torque limits justtogetmotion.

## Next

Separate loaded-wheel drive/traction response from three-support balance:
boundedflatfour-support direction/velocity control withsamegainsandgeometry,
then compareheld-legcase. Inspectcookedshape/debuggeometry ifavailable before
geometryedits. Ifdriveforceisnecessary,coordinateitsloadtransfer withsupport
wrench ratherthanindiscriminatelyraisinggain. Realobstacletravel remainsopen.
No training. Placeholder1934277stoppedexactly,1964482restoredandverified.
