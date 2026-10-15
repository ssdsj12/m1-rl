# v36 coherent support pose — isolated native result

User authority: directly continue isolated 10 cm crossing diagnosis and repair; no production training.

## Implementation and verification

Two candidate runtime files only: teacher SHA a9ef2ded7cb916ac3797fd6b4381dc53ae6361972adb6f1ee81f273352093827; probe SHA 66b47e574c29f65e0648951e9fe7ef789190608ff9b5424b48963e8fd32e6975.
Coherent support XYZ follows selected body pose, retains bounded load correction, bypasses competing legacy height/heave/indirect-attitude channels. Active measured-world target and physical guards retained.

Final review C0/I1/M1 identified RESTORE completion erroneously requiring absent legacy height state and missing four-leg/dtype coverage. Two RED completion failures reproduced. Mode-specific completion fix retains physical recovery, full execution fraction and zero load offset. Four active legs x float32/64 scalar XYZ+load transaction tests added. Targeted 50 passed; final related suite 1057 passed in326.13s, exit0. Bare collection remains3897 collected/13 environment errors, not full repository pass.

## Native evidence

Launch2026-10-15T02:00:40Z, runner445753/native445755, now exited, exit0. Prefix `/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn/evidence-first-obstacle-coherent-pose-v1`. Kernel flock retained; idleGPU1MiB before launch; production untouched.

Result FAILED_DIAGNOSTIC; recorded4, complete0, lockedfailures3, stage3success0, full denominator false. Env0 interrupted in BALANCE; env1-3 failed support. Diagnostic stop reports control_step142; trace frame143 is first invalid (frame numbering differs). Do not call exit0 a crossing success.

Same-env1 input evidence:
- First LIFT frame119; first invalid143 reason3 SUPPORT_LOST, locked147.
- Input143 Fz=[12.62659,182.27406,195.57701,26.69960]N. Wheel3 below30N; these are input forces, not poststep values.
- Maximum active wheel bottom .0000509918m (~.051mm): no meaningful lift.
- Frame142 desired active centerZ .1019095m, solved .1018999m, measured .0961893m, fraction1.
- Frame142 actual input RPY[-.16348,.19350,.09596]rad; desired support orientation is approximately roll-.1/pitch+.1/captured yaw. Actual orientation does not track it.
- Maximum poststep named leg target error rises from.10063rad(frame119) to.22502rad(frame142). Final-substep computed/applied effort difference0 does not establish absence of saturation at every substep.
- Load wheel3 offset-.00208066m at142 is downward, but does not prevent loss of support. Do not infer a sign error or sufficient correction from that alone.

Visual extraction inspected final raw frame30 of env1 video (31frames,10fps): body tilted near obstacle, no completed crossing. Image alone cannot quantify contacts; trace above is authoritative.

Original archive `/tmp/m1-coherent-v36-original-evidence.tar.gz` SHA b2b927a47f99610cb3be59e4ecb8460025a0fc5fe871d1babde9658f01075e1d independently matches downloaded local archive in `.superpowers/sdd/2026-10-15-m1-coherent-support-pose`. Original traces, videos, source and result preserved. Prior candidate runtime archive SHA049ce172fefbc5ea02b3fe6735b5eb42fb3db55952a4c0837ab90df4dd0cf8eb.

## Next investigation, not an implemented fix

The v35 split-geometry defect is removed, but that alone does not produce physical lifting. Next inspect coherent body-orientation command transitions, actual angular velocity, support-joint deflection and measured load timing. Existing body feedback is position-only; bounded dynamic orientation directly selects quat_goal. Whether command rate/damping, static actuator deflection, or support redistribution dominates remains unproven. Do not blindly increase lift speed/gains or relax support thresholds. No production/BC/PPO restart authorized by this diagnostic result.
