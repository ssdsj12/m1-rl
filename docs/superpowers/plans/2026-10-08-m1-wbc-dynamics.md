# M1 WBC 完整动力学快照 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Inline execution is used in the existing isolated worktree.

**Goal:** 建立后续动态 WBC 必需的完整、按名排列且不引用可变后端缓存的动力学输入。

**Architecture:** 从已安装 PhysX full generalized 接口读取 22×22 M 和 22 维重力/速度补偿项。输出只读语义快照及 episode/step 身份，不设置 actuator，不宣称坐标或补偿符号已通过物理验证。

**Tech Stack:** Python 3.10, PyTorch, pytest, installed PhysX tensor view.

---

用户已回复“按此设计实施”。本计划是[完整设计](../specs/2026-10-08-m1-dynamic-wbc-design.md)的第一批，不缩减最终目标。
执行记录：Task 1 的测试与实现已完成，21项CPU测试通过；提交与证据同步见本批提交。原生物理验证尚未执行。
后续依赖顺序：native shape/frame/sign/finite-difference 验证→滚动接触及逆动力学 QP→总力矩执行所有权→恢复/逐腿物理验证→单障碍与六障碍/绕行视频→teacher/PPO 接线及重训。各批根据前批实测接口编写可执行计划，不提前假定仿真通过。

## Files and boundaries

- Create `Go2Pvcnn/ame_baseline/m1_wbc_dynamics.py`: full API snapshot, named permutation, finite/SPD guards and explicit freshness check.
- Create `Go2Pvcnn/tests/test_m1_wbc_dynamics.py`: isolated boundary view fixture and real torch matrix operations.
- No edit to training, source USD, actuator, X/VNC, or existing probe in this batch.
- Update design approval status, T306, dashboard, log index and one evidence log.

## Task 1: snapshot contract (TDD)

- [ ] Write fixture view exposing only `get_generalized_mass_matrices`, `get_gravity_compensation_forces`, `get_coriolis_and_centrifugal_compensation_forces`; deprecated methods are absent.
  Fixture uses SPD `M=A@A.T+eye(22)`, distinct gravity/coriolis vectors and 16 distinct names.
- [ ] Add tests for both-axis matrix permutation, vector permutation and summed compensation, output buffer independence, missing/duplicate names, 16-only truncated backend data, NaN, asymmetric/indefinite M, stale episode/step, and negative step.
  Matrix assertion uses independent tensor permutation:

```python
p = torch.tensor(list(range(6)) + list(range(21, 5, -1)))
torch.testing.assert_close(snapshot['mass'], view.mass[:, p][:, :, p])
torch.testing.assert_close(snapshot['bias'], (view.gravity+view.coriolis)[:, p])
```

- [ ] Run RED: `PYTHONPATH=. OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q tests/test_m1_wbc_dynamics.py`; expect explicit missing-module assertion.
- [ ] Implement `generalized_snapshot(view, native_names, ordered_names, episode_ids, step)` with this calculation:

```python
p = torch.tensor(list(range(6)) + [6 + native_names.index(n) for n in ordered_names], device=mass.device)
mass = mass.index_select(1, p).index_select(2, p).clone()
gravity = gravity.index_select(1, p).clone()
coriolis = coriolis.index_select(1, p).clone()
return dict(mass=mass, gravity=gravity, coriolis=coriolis, bias=gravity+coriolis,
            joint_names=tuple(ordered_names), episode_ids=episode_ids.clone(), step=step)
```

  Before calculation require exactly 16 unique matching names; tensors same floating dtype/device;
  shapes B×22×22 and B×22; all finite; positive-definite M checked with cholesky_ex in float64;
  symmetry max error <=1e-5*max(1,maxabs(M)) per row. No symmetrization of returned M.
  step must be nonnegative integer, episode_ids a nonnegative integer B-vector on same device.
  Reject invalid contract with ValueError and no commands. Do not regularize an invalid matrix to pass.
- [ ] Implement freshness check:

```python
def require_current(snapshot, episode_ids, step):
    if snapshot['step'] != step or not torch.equal(snapshot['episode_ids'], episode_ids):
        raise ValueError('stale dynamics snapshot')
```

  Also reject mismatched identity shape/dtype/device and invalid step types.
- [ ] Run GREEN plus existing `tests/test_m1_dynamics.py`; all tests pass without GPU simulation.
- [ ] Verify diff and commit only new code/tests, approved-spec status and linked evidence/notes.

## Acceptance and explicit limits

## Task 2: Native read-only adapter smoke

- [ ] Add `tests/test_m1_wbc_probe.py` asserting a default-off `--wbc_snapshot` block,
  full snapshot call and no setters, with `stopped='wbc_read_only_complete'` before PREPARE.
- [ ] Run RED, then add observer before `dynamics=None` in `scripts/probe_m1_contact_prepare.py`:

```python
native = generalized_snapshot(robot.root_physx_view, robot.joint_names,
    robot.joint_names, zero, 32)
jac = robot.root_physx_view.get_jacobians().clone()
masses = robot.root_physx_view.get_masses().to(device)
gravity_oracle = (jac[:, :, 2] * masses[:, :, None]).sum(1)*9.81
translation_oracle = masses.sum(1)[:, None, None]*torch.eye(3, device=device)
```

  Log all M/gravity/Coriolis data and name order, gravity max absolute error,
  translation-block mass error, minimum eigenvalue and symmetry error, then stop
  further PREPARE steps. No effort or drive setters. Existing32step warmup remains.
- [ ] Run CPU wiring+snapshot+Jacobian tests. Native run only GPU7, original collision
  and actuator settings, `--num_steps 1 --wbc_snapshot --device cuda:0 --headless`.
  Exact own placeholder checked/stopped and EXIT-trap restored. Hard300s timeout.
- [ ] Compare8rows: gravity error<=1e-3 N/Nm and translation mass error<=1e-3 kg,
  finite SPD matrix; report native values even if rejected. These are static
  consistency checks, not full velocity/Coriolis or actuator sign proof.
- [ ] Save full log, verification note and commit observer only after evidence review.

## Remaining limits

## Task 3: Independent full-matrix energy oracle

- [ ] RED tests for `mass_from_links(jac,mass,inertia_world,armature)` and invalid inputs.
- [ ] Implement `M = sum(m*Jv.T@Jv + Jw.T@I_world@Jw) + diag(0_6,armature)`;
  tensor shapes B×L×6×22, B×L, B×L×3×3, B×16; reject shape/dtype/device/nonfinite,
  nonpositive body masses and negative armature. Output actual full22×22 matrix.
- [ ] GREEN kinetic-energy equality with independently computed link velocities.
- [ ] Extend opt-in native observer using `get_inertias` in COM-local frame,
  `matrix_from_quat(robot.data.body_com_quat_w)` to rotate into world, and native
  armatures. Compare full M and measured body velocities to `J @ [root_com_vel,qdot]`.
- [ ] Bounded GPU7 read-only run, same32warmup and immediate stop; no drive edits.
  Full M absolute residual <=1e-3 (mixed generalized units, report raw blocks),
  body velocity residual<=1e-4, energy absolute residual<=1e-4 J.
  Failure triggers frame/armature diagnosis, never tolerance relaxation.
- [ ] Save evidence and commit; this still does not prove Coriolis or actuator response.

Task3 outcome:28tests pass; native oracle first exposed an inertia-frame mismatch.
Installed get_inertias returns actor-axis inertia about COM, contrary to the
COM-local doc wording. Use body_link_quat_w rotation; comparison with COM principal
rotation remains in diagnostic output. FullM/velocity/energy now pass unchanged
thresholds. Evidence: notes/log/2026-10-08-m1-wbc-energy.md. No actuator integration.

This batch proves contract-level data integrity only. View fixture is unavoidable at backend boundary;
real torch operations, not mock call counts, are asserted. No test is labeled physical WBC success.
Native floating-base ordering, frame, sign, backend availability and residuals must be independently
validated next before this snapshot is consumed by a controller. Preserve existing safety/phase budgets.
GPU7 placeholder remains running throughout CPU-only batch; no GPU process is stopped.
