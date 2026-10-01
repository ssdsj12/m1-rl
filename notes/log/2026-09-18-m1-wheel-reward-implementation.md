# M1 semantic1 movement and articulated-wheel-lift reward

## Purpose / Stage / Related Todo

User explicitly approved the wheel-appropriate reward design on2026-09-18. M1 reward assembly and its direct scanner-validity upstream, child[T306.6g](../todo/T306-m1-ame-long-train-stability.md). [Approved design](../../docs/superpowers/specs/2026-09-18-m1-wheel-obstacle-rewards.md), [implementation plan](../../docs/superpowers/plans/2026-09-18-m1-wheel-obstacle-rewards.md).

## Changes / Contracts

New[tensor module](../../Go2Pvcnn/ame_baseline/m1_obstacle_rewards.py) computes semantic1-local signed actual progress and forward-coupled articulated wheel lift. Command XY is body-frame and rotates by root yaw. Use actual named LINK-origin states, not wheel angular speed or COM velocity. Lift subtracts root translation and`omega × arm`; require actual wheel upward motion too. Root/wheel forward motion must both be positive, so stopped chassis, spin-only wheels, static leg lift, rigid heave/pitch and sinking chassis earn no new lift bonus. It is a local bounded shaping term, not crossing success or a universal multi-step anti-gaming proof.

M1 disables old`feet_air_time`/`air_time_variance`, enables`small_obstacle_progress`weight1 and`small_obstacle_climb`weight0.5. Semantic2 in any sampled wheel patch vetoes both. Geometry collision remains-10; contacts, limits, energy, posture, roll/termination, action16 and policy1581/critic1584 unchanged. No PPO/AMP or reset/curriculum redesign. Two shared scanner conversion lines now intersect explicit valid masks with original finite ray/elevation data before nonfinite heights are sanitized.

The diagnostic probe adds optional`PROBE_COMMAND_X`for explicit fixed-forward reward calibration; absent this variable, its command configuration is unchanged. This is not a training command override.

## RED / GREEN / Review Evidence

- New tensor suite first failed25 cases because the new module did not exist; all then passed against the production math.
- Config/probe regressions failed2 tests because old airtime terms were active and probe command override absent; pass after wiring.
- Independent upstream validity task: RED2 failed/1 passed/7 deselected at assertions on NaN/Inf marked valid; GREEN full geometry test file10 passed.
- Initial full relevant M1/AME/collision regression:126 passed,1 skipped in12.78s,exit0. Diagnostic/new reward/config/scanner modules compile. Touched tracked code diff check emitted no whitespace errors; unrelated dirty-worktree CRLF changes were preserved.
- Independent spec review PASS: math, body/world frames, named LINK states, semantic2 veto and preserved safety constraints match plan. Nonblocking body-order test weakness strengthened with interleaved non-wheel999 sentinels and distinct wheel velocities; also added a sparse obstacle test proving query orientation follows command yaw. Latest focused suite42 passed,1 skipped in1.75s.
- Independent code-quality review PASS, no Critical/Important blocker; observe repeated terrain conversion in the two wrappers at runtime. They replace two old airtime wrappers that also converted terrain, so no cache refactor is justified without new evidence. Main directly verified remote finite-mask conjunctions and synced the local mirror.
- Final full relevant union after test strengthening:127 passed,1 skipped in10.82s,exit0. [Real8env×600 physical probe](2026-09-18-m1-wheel-reward-physical-probe.md) completes+exit0,all-wheel8/8,0reset/geometry/undesired contact,both new terms nonzero. [Fresh8env×2 smoke](2026-09-18-m1-wheel-reward-smoke.md) also completes exact0..1+exit0,all138 checkpoint tensors/35TB tags finite, saved config and TB confirm both new reward terms. No learned behavior claim is made from these gates.

## Runtime Plan / Follow-up

Run one Isaac process at a time in amp/physicalGPU4:8env×600 controlled0.05m probe, fresh8env×2 update smoke, then fresh1024×120 and fixed flat/small/large evaluations. Every run gets its own new log and requires completion marker+exit0. No old checkpoint resume or restart supervisor. Formal10000 remains behind actual behavior acceptance.

## Git Refs

Baseline4b5251f plus preserved prior M1 work. Approved spec/plan-only commit740f07e; runtime candidate is740f07e plus uncommitted reward changes. Only the two new documentation files were committed; no existing user edits were staged or committed. Key files:new reward module, M1 config, diagnostic probe and focused tests; scanner conversion/test owned by the bounded upstream fix.
