# Fixed-wheel leg-only PPO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. User already chose current mirror; do not ask again.

**Goal:** True12dim PPO with fixed0.30m/s wheels and explicit16-to12 checkpoint conversion.
**Architecture:** Tensor contract owns expansion and metadata; action term only exposes12legs but drives4wheel targets each physics step. Runner validates saved contract; offline conversion slices actor/std/Adam states by named parameters. Preserve observation layout and physical crossing rules.
**Tech Stack:** Python, PyTorch, Isaac Lab, RSL-RL, pytest, CPU-only remote candidate.
**Spec:** ../specs/2026-10-11-m1-fixed-wheel-leg-only-design.md

## Global constraints

Mirror C:/Users/xk/Documents/project/m1-ppo-recovery on codex/m1-ppo-repair-upload; preserve two old untracked watchers.
No hot production edits; current training keeps running until candidate CPU/review ready and verified save boundary.
No simultaneous GPU native/train. No teacher/IK/swing/std retuning/hardware change. All signed wheel targets fixed.
Keep legacy mode default for historical tests/checkpoints; explicitly select new mode for candidate and new training.
Speed error not a promotion gate. No reward weight/terrain/strict threshold changes. Nonfinite or mismatched checkpoint fails closed.

### Task 1: Tensor action/history/reward contract

Files: modify Go2Pvcnn/ame_baseline/m1_ame_contract.py and m1_ame_rewards.py;
create Go2Pvcnn/tests/test_m1_fixed_wheel_contract.py.
Interface: expand_fixed_wheel_actions(actions12,speed_m_s=.30) -> normalized16; m1_last_action returns16 in either mode; action_rate uses12legs in newmode.

- [ ] Write tests for missing function, wheel columns3/7/11/15 always.30, leg columns preserve values, wrong shape/nonfinite speed rejection,12dim history and reward.
```python
out=expand_fixed_wheel_actions(torch.zeros(2,12))
torch.testing.assert_close(out[:,[3,7,11,15]],torch.full((2,4),.3))
assert out.shape == (2,16)
```
- [ ] Run via CPU candidate pytest test_m1_fixed_wheel_contract.py; expected RED missing behavior.
- [ ] Implement expansion assigning named leg/wheel columns, strict finite scalar speed0<speed<=2; history expands only cfg.m1_fixed_wheel_speed_m_s enabled; reward sums squared12dim delta.
```python
out=actions.new_zeros((*actions.shape[:-1],16))
out[...,leg_columns]=actions
out[...,wheel_columns]=speed_m_s
return out
```
- [ ] Run new tests plus test_m1_ame_contract.py/test_m1_ame_rewards.py where present; GREEN; commit exact files.

### Task 2: Runtime action/config/wrapper integration

Files: modify m1_ame_actions.py, m1_ame_env_cfg.py, ame_env_wrapper.py;
create tests/test_m1_fixed_wheel_runtime.py.
Interface: M1_FIXED_WHEEL_SPEED_M_S opt-in; action_dim12; named legs configured, fixed physical wheel targets; history16 and policy1589/critic1592 preserved.

- [ ] Write CPU action-term fixture against real class with external Isaac import stubs only; test process/apply/reset preserves wheel targets and rejects16dim inputs. Test config helper on concrete namespace.
```python
term.process_actions(torch.zeros(2,12));term.apply_actions()
torch.testing.assert_close(robot.last_wheel_target,torch.full((2,4),.3/.095958))
```
- [ ] RED then minimal subclass with superclass selecting12leg IDs, independent named wheel IDs, process decoded legs, apply constant wheel targets each substep. Keep legacy class untouched.
- [ ] Apply opt-in after existing env post-init assignments, set command ranges/limits(.3,.3),standing0, disable command curriculum; new action cfg and action_dim12. Reject teacher/planner-owner in fixed mode.
- [ ] Audit wrapper neutral actions/debug target decoding for12vs16; use expanded normalized action only where physical16 required, not inPPO distribution.
- [ ] CPU suite GREEN; commit. Native actual wheel sign/dimension/reset remains Task4.

### Task 3: Explicit model300 migration and checkpoint guard

Files: create ame_baseline/m1_fixed_wheel_checkpoint.py and scripts/convert_m1_fixed_wheel_checkpoint.py;
modify ame_runner.py; create tests/test_m1_fixed_wheel_checkpoint.py.
Interface: conversion(source,old_actor,new_actor,speed,source_sha) -> copied payload; saved m1_action_contract includes version/mode/speed/joint order. Runner matches contract before loading.

- [ ] Tests instantiate real small ActorCriticAME16/12 and Adam; produce one update; verify converted inference equals old named leg rows, all unchanged tensors equal, optimizer shape values sliced, parent unmodified, malformed signature/state/optimizer fails.
```python
torch.testing.assert_close(new.act_inference(obs),old.act_inference(obs)[:,[0,1,2,4,5,6,8,9,10,12,13,14]])
```
- [ ] RED; implement deep-copy, validate current architecture/dims/finite/std, map Adam param IDs by actual named_parameters order with parameter-shape checks, slice only std/actor final weight/bias. Save provenance SHA and next_iter unchanged.
- [ ] Runner records/matches contract on save/load;12dim requires contract;16dim legacy accepts absent contract. Wrong speed/order/mode fails before mutation.
- [ ] CPU suite GREEN and real original300 SHA check/conversion in isolated CPU candidate; no source overwrite; new file separate path. Commit.

### Task 4: Review, original physics checks and deployment

Files: isolated diagnostic scripts outside runtime, notes/log/2026-10-11-m1-fixed-wheel-deploy.md,README.

- [ ] Run relevant full regression plus CPU-only repository pytest collection/execution, record unrelated environment limitations by name. Run fresh-context whole-change review (skill-required reviewer), fix important findings with RED/GREEN tests.
- [ ] Inspect current training identity/save list; CPU validate newest complete PT then SIGINT only exact matchingPID; confirm exit/GPUfree. Preserve allPT.
- [ ] Isolated native4env candidate: physical wheel axes forward,12dim stochasticpolicy, fixed target each substep,16history, finite all rewards, forcedterminal; stages0/1/2/3/mixed>=4, real scan geometry. No success claims from wiring.
- [ ] On native failure, do not deploy; preserve diagnosis and restore old training only from verified boundary/old code, record reason. On pass backup exact runtime files/hash then deploy candidate, convert approved300 offline and launch2048withkernel-flock,next301+9699/save100/optimizer/keep_std.
- [ ] Verify cmdline/cwd/12actions/config/firstupdates/finiteweightslosses, TBnewrun; update README/notes/automation, sync explicit files, ordinary authorizedGitHub m1-10-11 push with independentref. Uploadfailure separate from traininghealth.

## Review focus

Isaac JointAction action_dim derived from selectedjoints; reset tensors must have12 not16. Wheels still driven each decimation step and unloaded frames. Observation16 is executedhistory not policy16. No runtime teacher debug paths accidentally call16decode on12. Adam IDs and state-shape correspondence must be established, not assumed from arbitrary dictionary ordering. Large-obstacle route penalties must not create small-target obligations; no unsupported yaw-steering claims. Continuous speed tracking not hard-gated. Source300 immutable and all historical runs retained.
