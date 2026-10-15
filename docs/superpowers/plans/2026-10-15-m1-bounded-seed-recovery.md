# Bounded seed recovery implementation plan

> Use superpowers:executing-plans inline. Final independent review after tests.

**Goal:** restore bounded initialization across pose IK while retaining output and physical gates.
**Architecture:** pure initialization helper and wrapper, pose-only import substitution; raw inputs unchanged, base solver unchanged.
**Tech Stack:** PyTorch CPU fixtures and existing isolated Isaac native probe.

- [ ] Create Go2Pvcnn/tests/test_m1_teacher_seed_recovery.py. Four legs × two dtypes: nominal q, active knee signed.0975, target FK of identical q with signed.15 knee; assert solve_pose_ik valid, final signed knee>=.1 and residual<=.002. Import helper lazily so absent implementation gives explicit feature RED, no collection failure. Invalid branch/zero/deep seed/NaN/limit tests require no input transformation. Snapshot q before call and require equality.
- [ ] Run new tests in separate /tmp/m1-v29-cpu with original package copied; observe RED before implementation.
- [ ] Implement recovered_pose_seed(q,target,branch,cfg) using per-leg finite/m1_joint_limit_mask/sign/positive/deficit mask and torch.where only knee. Implement solve_pose_ik to call unchanged solve_constrained_ik on recovered seed, forwarding tolerance_m. No extra iterations/threshold changes.
- [ ] Substitute pose import, set teacher fingerprint support-ik-transaction-v29-bounded-seed-recovery. Add real v28 fixture132/133/134/137 from raw dynamic snapshots after record available; assert132 same baseline,133/134 valid encoded audit,137 invalid. Preserve raw evidence hash.
- [ ] Run full existing788+new suite CPU, inspect failures; fresh final review and one C/I repair pass. Do not mutate v28 candidate while its process/audit live.
- [ ] Archive v28 source/evidence/log/exit and SHA when terminal. Verify fivefile/newhelper deployment hashes; unique flocked v29 native10cm run, inspect lift/support/passage/recovery/video. Update notes; no productiontraining.

No commits while identity absent. User authorization covers inline execution, not changes to success definition.
