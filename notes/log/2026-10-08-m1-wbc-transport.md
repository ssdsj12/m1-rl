# 2026-10-08 M1 contact transport and native static QP

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), WBC rolling contact child.
Baseline Ref:fcfd151. Candidate Ref:this transport commit.
Key files: [transport](../../Go2Pvcnn/ame_baseline/m1_wbc_transport.py),
[tests](../../Go2Pvcnn/tests/test_m1_wbc_transport.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-transport.md).

## Formula and numerical verification

For world rigid velocity field evaluated at geometric contact c(t), material
point acceleration alone is insufficient. Material bias=bCOM+alphaBias×r+
omega×(omega×r). Add omega×(c_dot-v_material) to obtain the transported bias.
No default c_dot: absent/invalid migration rejected; caller must derive it from
verified shape/contact mode, not differences of transient patch IDs.

RED8tests due missing adapter, then GREEN. Circular rolling radius.1m at2rad/s:
material upward bias.4m/s² canceled by migration-.4m/s², so constant-speed motion
is permitted. A fixed polygon vertex has no such cancellation. Independent3D
velocity-field central difference includes slip and nonzero angular/COM bias,
dt1e-5, tolerance1e-8; analytic/Galilean cases1e-12. Coupled QP allowsforward
accel.05m/s² with wheelaccel.5rad/s²; incorrect zero-material-acceleration
constraint rejects that case. This is synthetic, not actual M1 wheel rolling.

## Native static counterfactual

Additional RED observer wiring, fullGREEN86tests in2.08s across WBC transport,
materials/kinematics/contacts/QP/free/dynamics/probe and existing pointJacobian.
Native bounded --wbc_snapshot now evaluates a read-only zero-velocity/qdd static
QP at env0 measured pose. Uses full nativeM/gravity (explicitly omits C because
counterfactual v=0), real nine pointJacobians/normals, measuredmu, and minimum
of actual backend/configured effortlimits. Per-wheelmin35N, pointmin0, no repeated
35N perpoint; point/groupmax currentbodyweight. No simulator effort commands added.

GPU7 soleplaceholder706235 verified, stopped, then EXIT restored736509.
Raw:/tmp/m1_wbc_static_qp_20261008.log. Command existing bounded300s snapshot,
--num_steps1 --wbc_snapshot --device cuda:0 --headless. Final read_only_complete.

- QPvalidtrue,75iterations,reportedsolve.000639s (not real-time certification).
- Maxhardviolation3.552713678800501e-15; dynamics residualsameorder.
- Weight412.6674499511719N for current randomizedmass.
- Groupnormal loads101.560596,118.920637,105.745900,86.440317N.
- Maxeffort14.246618Nm; measuredlimits legs150Nm,wheels50Nm.
- Actual WBC effort not applied; qddzero static feasibility only.
- Finalplaceholder736509 exactsleep.py, no longtraining/display/otherGPU change.

## Remaining physical gate

Native cooked wheel is a multipoint convex hull, not proven smooth circle.
Keeping all material contacts fixed during rolling can prohibit rotation; native
active contact/point-release transitions need explicit unilateral treatment.
This is an open child of rolling support, not permission to remove force/margin
guards or discard moment arms. Need derive native migration/active modes then
actual sole-owner torque stance/rolling, all4 single-leg cycles and true obstacle
crossing. No crossing or training success claimed.
