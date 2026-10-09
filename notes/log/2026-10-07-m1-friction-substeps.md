# M1 friction moment explains missing dynamic support load

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), dynamic-support child.
Baseline Ref: dc53ae0. Candidate Ref: containing commit.
Stage: UNLOAD diagnostics, not a controller fix or training acceptance.
Key files: m1_contact_snapshot.py, probe_m1_contact_prepare.py,
test_m1_contact_snapshot.py, test_m1_unload_telemetry.py.

## Improvement relative to last version

Read actual friction patches rather than mistaking normal-contact XYZ for
friction. New default-off unload_friction_audit creates explicit named views
for all four wheels in rows0/1 against terrain, capacity128 each, records
summed force and moment about measured whole-robot COM at5ms.
Pure aggregation respects pair offsets, empty pairs, buffer capacity and finite
active values. No actuator changes. Installed tensors API get_friction_data
documents force, world point, count, start buffers and dt conversion.

## Verification

Two new aggregation tests failed before implementation; then7 contact,
observer and telemetry tests passed1.41s. Includes shuffled named wheels,
nonuniform body masses, actual nested observer and known moment arm.
GPU7 physical command identical to prior COM substeps plus unload_friction_audit.
8env sourceSDF128/1mmrest/2mmcontact,100PREPARE/100UNLOAD budget, phasewheelhold,
settledheightonly; session50096 terminalexit0.
Raw /tmp/m1_friction_substeps_20261007.log.
All unload_samples exactly match dc53ae0 physical baseline; same rejection53.
Own3835014placeholder stopped;3932345 restored. No training/otherGPU/display changes.

## Quantitative evidence (action52, four-substep mean)

Mass41.045319557kg. Rows0/1 selectFBL/FAR respectively.
Row0 friction[-3.789726,-9.657712,~-0.000001]N;
mass*COM acceleration[-3.789737,-9.657710,+0.552133]N.
Row1 friction[-4.796781,+11.856902,~+0.000003]N;
mass*COM acceleration[-4.796785,+11.856901,-3.586974]N.
Thus horizontal friction independently matches momentum change over20ms;
this is not inferred from root acceleration or assumed wheel motor torque.

Friction moments about COM (Nm):
- row0[-4.176255,+1.638662,+0.833068];
- row1[+5.121735,+2.072788,-0.427590].
Static vertical-only lowwheel prediction using final measured geometry:
row0 RAR34.02455N, row1 RBL34.56943N.
Solving normal-force sum=mg and roll/pitch moments opposite measuredfriction
gives21.42637N and19.02616N respectively. Actual means26.55382N/22.65382N.
This friction-adjusted calculation is diagnostic, not exactinverse dynamics:
it omits angular-momentum derivative and vertical acceleration, uses final
geometry with step-average friction. Residual fewN must not be hidden.
It demonstrates omitted friction moments are sufficient in direction/magnitude
to explain much of the static-versus-measured load deficit, not sensor noise.

## Architectural next action

Current vertical_support_solution explicitly excludes acceleration and contact
moments; transfer_target uses instantaneous COM geometry and can start/stop
root commands without acceleration coordination. Height activation only checks
effort/geometric readiness, not dynamically settled support.
Do not merely subtract friction from gravity in the static solver: nonzero
horizontal wrench cannot be balanced with world-Z-only forces, and measured
friction is a response, not automatically a desired command.
Next inspect commanded COM acceleration/braking across PREPARE/UNLOAD and
coordinate smooth transfer plus dynamically settled unloading under existing
80mm/2s/contact/effort bounds. If these limits are infeasible, report and
redesign support/wrench control rather than silently relaxing them.
Fullsingleleglift/rolling/landing,5cmclearance,4cmlanding,sixobstacles,bypass,
video and policy-only model acceptance remain open. Local commit, not uploaded.
