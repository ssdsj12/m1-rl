# PREPARE bounded wheel holding: physical drift reduction

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), stationary-anchor child.
Baseline Ref:603349c (physical comparator faaba5f). Candidate Ref:containing commit.
Key files: m1_rolling_speed.py, probe_m1_contact_prepare.py, test_m1_wheel_hold.py.

## Scope and changes

Opt-in `--prepare_wheel_hold_only` applies the existing fixed-entry anchor
feedback during PREPARE and ends the diagnostic before UNLOAD. Fullcycle CLI
parameters are retained to preserve the identical reserve/preparation contract;
no later phase executes. No automatic transition from holding to rolling yet.
Uses named M1 wheel columns, current yaw, existing linear-to-angular scale.
Requires zero wheel stiffness/feedforward, predicts damping*(target_qd-actual_qd)
and rejects nonfinite/over-limit effort before action. No torque/pose limit changes.
Telemetry reports each command, error and predicted effort. Default stays off.

## Tests

Two new effort tests first RED missing helper; GREEN18 tests1.51s for wheel_hold
and rolling_speed, plus py_compile. Effort tests cover unit conversion, limits,
nonfinite input and invalid mapping. Physical exercise validates caller wiring;
unit tests alone do not prove stability. Scope label corrected to prepare-only
when this flag is active, even though fullcycle configuration is supplied.

## Matched physical experiment

GPU7,8envseed2,stage none,5msphysics,100PREPARE,root speed.04/maxshift.08,
frontreserve35/rear40,phase effort,sourceSDF128 with explicit1mmrest/2mmcontact,
fixed physics. Same prior fullcycle command plus `--prepare_wheel_hold_only`.
Raw:/tmp/m1_prepare_hold_20261007.log; session49112 exit0.
Stopped=prepare_hold_only_complete,100samples; noUNLOAD/LIFT/crossing executed.

Measured final wheel worldX drift relative fixed entry anchors:
- baseline:-39.3959..-24.3640mm;
- holding:-12.3732..-6.6821mm (improved, not zero).
Last PREPARE pre-action root-reference 3D errors now8.118..17.479mm versus
24.377..38.412mm baseline. All8 below25mm at that sampled frame; this does not
prove the subsequent world-frame/IK/slew gates will pass.
Minimum sampled four-wheel force48.132N; peak absolute roll/pitch0.005265rad.
Maximum requested speed0.026808m/s, peak predicted wheel torque3.854573Nm.
Native torque is not independently audited here; prediction is not torque proof.

## Outcome and next

Bounded longitudinal wheel correction causally reduces preparation drift under
matched conditions without relaxing25mm guard or changing assets/physics.
This is preparation only, not single-leg support or obstacle acceptance.
Next integrate continuous PREPARE→UNLOAD→LIFT holding with selected wheel
braking, and bounded release/transported reference onROLL/LAND. Preserve
contact/pose/effort/slew/time bounds; validate all4legs before real obstacles.
Do not hide residual drift by relatching anchors or launch long training.

Own placeholder3190750 stopped for probe,3276873 restored and verified.
No unrelated GPU/display/driver changes. Notes aligned. Local commit only,
not uploaded. Improvement vs last commit: helper now physically exercised;
full crossing/policy/obstacle/video/avoidance acceptance still open.
