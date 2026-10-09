# Total effort/contact consistency audit

Parent:[T306 total-effort-contact-consistency](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:ce2861c; Candidate Ref:commit containing this log.
Key file:probe_m1_contact_prepare.py. Diagnostic-only additions, same control.

## Evidence

Named wheel sensor indices resolved once; each phase snapshot logs fresh-target
PD estimate, previous feedforward, desired static effort, joint velocity/names,
gravity minus measured net wheel force projected through wheel-origin Jacobians.
The last quantity is a proxy (wheel centers, no contact moments/acceleration),
not independently measured actuator torque.
Focused15-file112tests pass5.23s. Same flat8seed2,100PREPARE+100UNLOAD smoke onGPU7;
raw:/tmp/m1_total_effort_audit_20261007.log; native0. Control unchanged:unload timeout,
no lift. Effort clearing and restored placeholder verified.

Atfinal UNLOADstep99, maximum absolute per-row12-leg discrepancy between
PD+previousFF and contact proxy is16.60..22.26Nm. PD itself max11.84..17.59Nm.
Exampleenv0 FBLknee: desiredFF1.91, actualFF1.91, PD-7.59, contactproxy-3.04Nm.
RBLknee: desired/FF-17.70, PD-10.91, proxy-11.65Nm. Therefore simply assuming PD
opposes FF does not explain the full balance; do NOT cancel PD based on this.

## Source inspection / next

Installed articulation._apply_actuator_model copies effort by actuator.joint_indices
to _joint_effort_target_sim and write_data_to_sim sends it with set_dof_actuation_forces.
No confirmed overwrite found. PhysX API exposes get_dof_stiffnesses/dampings,
get_dof_actuation_forces and get_dof_projected_joint_forces. The last projects
incoming link force onto active joint direction, not necessarily identical to
motor drive effort. New child backend-effort-conventions: compare actual backend
parameters, sent forces and projected forces with telemetry, establish meanings
and omitted friction/contact moments before changing controller. Keep diagnostics
bounded and control unchanged for that comparison. Then correct load control and
repeat actual lift/crossing gates; no training or acceptance claim.
Own997933 placeholder restored1046531 alive; ldc3227360 alive/untouched.
No display/driver/reset changes or upload.
