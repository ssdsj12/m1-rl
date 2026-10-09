# Backend effort and contact data semantics

Parent:[T306 backend-effort-conventions](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:59b4db0; Candidate Ref:commit containing this log.
Key file:probe_m1_contact_prepare.py; diagnostic-only changes.

## Important correction

Installed contact_sensor_data.py lines50..58 explicitly states net_forces_w is
sum of NORMAL contact forces, excluding tangential friction. Prior17..22Nm
proxy residual was not a complete inverse-dynamics balance and cannot justify
canceling PD. Rename diagnostic field to normal_contact_effort_proxy and emit
normal_only_no_tangential_force_or_contact_moment scope. Old logs retain provenance.

## Runtime check

Focused15-file112tests pass5.00s. Same flat8seed2/100PREPARE/100UNLOAD experiment,
GPU7; raw:/tmp/m1_backend_effort_20261007.log; native0,unload_timeout,0liftsteps.
Backend stiffness/damping minus cached parameters exactly0 in all8rows.
Backend get_dof_actuation_forces minus effort target buffer exactly0 in all8rows.
No confirmed parameter loss or effort overwrite. get_dof_projected_joint_forces
is an incoming joint reaction projected on motion direction, not independently
measured motor output. Its difference from PD+FF14.7..19.9Nm does not establish
drive error. Do not blindly equate them. Effort clear confirmed by phase report.

## Next actionable control step

Close basic parameter/sent-force audit; do not repeat it. Current fixed-position
open-loop static feedforward does not unload selected contact. Next child
measured-unload-control: bounded contact-force feedback on the selected-leg
reference with existing stance/pose/IK/slew and load-feasibility guards, explicit
timeout/recovery. Preserve body support; no blanket PD cancellation or drive gain
change. Establish selected-contact reduction before allowing further swing, then
actual lift/crossing/landing/collision/bypass gates and learned policy. If using
force-projection diagnostics, obtain friction/contact point contributions rather
than relabeling normal-only data as total force.
Own1046531 placeholder restored1081679 alive; ldc3227360 untouched/alive.
No training, upload, display/driver/reset changes. Full goal remains open.
