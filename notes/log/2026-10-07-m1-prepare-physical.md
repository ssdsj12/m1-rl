# M1 PREPARE physical diagnostics and corrections

Stage: contact-driven support preparation; related
[T306.contact-transfer.physical](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: `28e1c25`. Candidate Ref: commit containing this log.
Key files: `Go2Pvcnn/scripts/probe_m1_contact_prepare.py`,
`Go2Pvcnn/ame_baseline/m1_load_transfer.py`, `Go2Pvcnn/tests/test_m1_load_transfer.py`.

## Scope and resource safeguards

Only physical GPU7; exact hexinkun sleep.py PID verified before TERM. EXIT trap
restored placeholder after every diagnostic. Other user ldc PID3227360 remained
alive. Final placeholder observed PID466385. No driver/display changes, training,
policy model or actual swing. Eight environments, seed2, dt.02s, 32-step nominal
standing warmup. `amp/bin/python scripts/probe_m1_contact_prepare.py --device
cuda:0 --headless`, CUDA_VISIBLE_DEVICES=7, timeout300s. No broad process kill.
All four diagnostics exited native0. A safe diagnostic rejection is NOT success.
Logs below retained under `/tmp/` and copied to the local audit artifact directory.

## Results

1. `m1_contact_prepare_8x32_20261007.log`: inherited complex terrain, stopped at
   pre-action step0, four front-leg rows rejected with reason3 (displacement bound).
   One row also had zero support force. Initial FK-vs-live wheel-center residual
   about .20-.23mm, so gross M1 naming/FK mismatch is not indicated. Source audit
   confirmed disabling curriculum did NOT replace mixed terrain subtypes.
2. Corrected probe to explicit MeshPlaneTerrainCfg, 1 row x8 tiles, keeping
   semantic obstacles. Also corrected geometric transfer to nearest feasible COM
   point rather than a longer path toward triangle incenter. Regression RED
   reproduced avoidable rejection of a feasible <=.06m displacement; GREEN passed.
   `m1_contact_prepare_flat_8x32_20261007.log`: full32 steps, no stop, all IK proposals
   valid. Last readiness4/8 (rear legs); front margins remain -.0186..-.0114m.
3. Same controller speed.02m/s, `m1_contact_prepare_flat_8x100_20261007.log`:
   full100 steps/2s, no stop. Front final margins .00261.. .00853m, below hard.02m;
   rear margins .0363.. .0570m. Readiness4/8, so PREPARE acceptance fails.
4. Explicit diagnostic speed.04m/s (default remains.02), same .06m total bound
   and .5rad/s joint slew: `m1_contact_prepare_flat_speed04_8x100_20261007.log`.
   Stops at pre-action step53 (~1.06s), reason3 in rows0,1,4. Front margins only
   .00399.. .00997m. Selected rear rows ready; front not ready. No permission to lift.
   Wheel centers drifted roughly up to13.6mm X /9.2mm Y from fixed anchors; root
   height dropped around6.5..8.7mm although commanded height remained fixed.
   Thus ideal fixed-anchor/rigid-COM translation is not physical equivalence.

## Additional feedback defect and CPU verification

When margin was already satisfied, desired root was assigned the measured root,
which can recapture compliance/overshoot and slowly drift the target. Added RED
test showing .0004m unwanted target update, then retain previous commanded root
when margin is satisfied. **This final correction has not yet had a physical run.**

Combined command: existing amp Python `-m pytest -q` under Go2Pvcnn with
`test_m1_load_transfer`, `test_m1_support_observer`, `test_m1_prepare_gate`,
`test_support_geometry`, `test_crossing_event`, `test_probe_evidence_contract`,
`test_m1_foot_frame`, `test_m1_cache_foot_frame`, `test_m1_runner_wheel_parity`,
`test_m1_unreachable_teacher` (all `tests/*.py`): **67 passed in3.28s, exit0**.

## Follow-up / limitations

Front PREPARE failure is an open child, not a reason to start training or relax
hard .02m support margin. Need reconcile commanded root, compliant anchors and
measured COM response within bounded feasible motion/time; inspect final freeze
correction before any further tuning. Full state-machine reset/timeout ownership,
substep collision evidence, lift/traverse/land/settle, strict events, bypass and
policy-only verification remain open. Current probe is PREPARE-only and records
pre-action rows; no strict crossing, full collision-oracle or video claim.
