# M1 lift-and-roll execution repair

> Execute within the existing `codex/m1-contact-crossing` worktree and the user-approved dynamic WBC design. Existing dirty changes remain intact.

**Goal:** make the same selected wheel rise vertically, remain clear while carried forward by the chassis, and land only beyond the obstacle; validate the command path before a new physical run and before training.

**Architecture:** one Cartesian wheel reference owns the selected leg target. IK, action encoding, decoding and limits must preserve that reference. WBC owns eventual 16-DOF total effort, with three-wheel support and rolling constraints independently verified. A world-fixed XY swing reference cannot accomplish rolling passage; hold yaw-relative XY and world clearance height instead.

**Tech stack:** PyTorch analytic M1 FK/IK; existing Isaac Lab action adapter; NumPy/OSQP WBC oracle; independent PhysX measurement.

## Evidence and scope

Current CPU teacher/decoder/FK reproduction for each of four legs: requested +0.156 m vertical lift turns into +0.32657 m lift and -0.05750 m horizontal displacement, with up to 0.07072 m horizontal deviation. The post-IK knee floor destroys the IK solution and per-component slew changes its Cartesian path. This is current-code evidence, not a historic failed simulation.

Existing WBC probes also fail rolling/support control. Diagnose that independently; do not infer that fixing Cartesian references alone proves balanced physical crossing. Current production remains implicit leg-position/wheel-velocity PD. There are no M1 train/eval/probe processes; user GPU7 placeholder remains active.

## Tasks and gates

- [ ] Add `Go2Pvcnn/tests/test_m1_cartesian_teacher_execution.py`: exercise all four legs through `reference_to_m1_action -> m1_action_targets -> m1_fk`, stationary and forward-moving roots for more than two old phase blocks. Assert <=20 micrometre XY error, exact requested final height, no stance target motion, existing joint slew and action limits. Run RED before edits.
- [ ] Add `ame_baseline/m1_cartesian_step.py`: solve the requested IK without modifying any component; bisect along the Cartesian segment from current wheel position to requested position until the original joint/action/slew limits hold. Reject unreachable full targets rather than certifying a clipped solution. Apply this helper at the teacher's final action boundary, after legacy blending, so later knee overrides cannot corrupt it.
- [ ] Add lift-and-roll reference generation and latch episode/leg/phase anchors in `ame_baseline/ame_env_wrapper.py`. During the event, preserve yaw-relative XY and world target Z. During confirmed far-edge landing, retain safe XY and descend. Tests must cover body translation/yaw/heave, phase wrap, per-environment reset, target wheel isolation and invalid targets.
- [ ] Trace WBC same-state inputs from recorded contact/force/acceleration logs; fix a reproducible contact/dynamics error with independent CPU counterexamples before actuating. Keep force application points and kinematic evaluation points explicit. Do not mistake CPU QP feasibility for measured physical motion.
- [ ] Validate actual four single-leg lift/hold/roll/land sequences in bounded one-env physics only after the deterministic gates pass; save exact revision/config, action, joints, wheel poses, substep contacts and failure frames. Then test real obstacle clearance/far-edge/landing and collision on all required front/rear wheel-obstacle pairs.
- [ ] Integrate verified WBC execution ownership with teacher/PPO, verify the actual teacher control fraction, then run training smoke and authorized long training. Policy-only crossing and large-obstacle avoidance remain mandatory acceptance.

## Verification commands

Run under the existing AMP Python from `Go2Pvcnn`:

```bash
OMP_NUM_THREADS=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_cartesian_teacher_execution.py
OMP_NUM_THREADS=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_teacher*.py tests/test_m1_ame_action_contract.py
```

CPU success certifies only the command contract. Physical lift, three-wheel support, full crossing, WBC production integration and policy learning remain open until direct evidence proves them. A timer expiring is not successful passage. No display/driver configuration changes or unrelated process termination are part of this repair.
