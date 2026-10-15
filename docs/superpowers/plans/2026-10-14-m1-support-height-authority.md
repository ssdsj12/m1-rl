# M1 Support Height Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans，已授权inline连续执行及最终独立review，不重复审批。

**Goal:** 消除几何机身姿态对弱支撑轮竖直目标的漂移，在实际10cm跨越中验证抬轮与恢复。
**Architecture:** 实测root/已下发q捕获支撑执行世界Z→仅替换支撑body_goal的世界Z→载荷反馈及一次回溯插值；RESTORE有界接回几何目标。
**Tech Stack:** PyTorch CPU测试、隔离Isaac、现有完整证据审核。
**Spec:** ../specs/2026-10-14-m1-support-height-authority-design.md

## Task1 执行目标竖直来源

Files: Go2Pvcnn/ame_baseline/m1_teacher_execution_targets.py；tests/test_m1_teacher_support_height.py。
Interface: execution_targets新增support_reference_w_z=None，[B,4]同device/dtype有限世界Z；只能mode1/2启用，活动轮不覆盖。

- [ ] RED：倾斜实测root、不同虚拟root、4种active及mode1/2；支撑世界Z等于reference+offset，世界XY保持旧几何，活动轮完全不变；fraction=.25从旧FK衔接。非法shape/NaN/mode0拒绝。
- [ ] Run `pytest tests/test_m1_teacher_support_height.py -q`，Expected缺少关键字参数FAIL。
- [ ] GREEN：在既有offset前执行以下世界Z替换，保留后续一次fraction插值：
```python
world = measured.pos_w[:,None] + torch.einsum('bij,bkj->bki',_rotation(measured.quat_w),goal)
mask = torch.arange(4,device=pos.device)[None] != active_wheel[:,None]
delta = torch.where(mask,support_reference_w_z-world[:,:,2],torch.zeros_like(support_reference_w_z))
vertical = torch.zeros_like(goal); vertical[:,:,2] = delta
goal = goal + torch.einsum('bij,bkj->bki',_rotation(measured.quat_w).transpose(-1,-2),vertical)
```
- [ ] 同测试Expected全部PASS，再跑旧execution_targets/load_feedback_transaction回归。

## Task2 教师完整事务与恢复

Files: m1_teacher_pose.py、m1_reference_teacher.py、tests/test_m1_teacher_support_height.py。
- [ ] 先写并运行教师首次捕获/失败不提交/单行reset/RESTORE限速及未完成不换腿测试，Expected缺字段或行为断言FAIL。
- [ ] backtrack_feedback_reference新增paired previous/proposed_support_reference_w_z，合法shape/finite/paired/mode；RESTORE候选与old差不得超.01dt。将完整proposal传目标构造器，已执行q作为插值起点，提交old+beta*(proposal-old)。
- [ ] LIFT/PASS scratch首次capture：`base=root[:,None]+einsum(R,body_feet(last_q))`，存其Z为support_execution_z。后续base不随root重捕获。RESTORE候选`old+clamp(geometry_world_z-old,-.01dt,.01dt)`；活动索引不参与恢复判断。
- [ ] 保存height_previous/proposed/selected/committed及capture输入、完整事务成功后提交。RESTORE finish增加支撑基准与本帧几何Z差<=.0001且offset0；reset/episode/完成清除。fingerprint更新v20。
- [ ] 跑Task1/2及v19全部相关测试，Expected通过；保留所有原保护及训练关闭。

## Task3 证据及实际障碍

Files: scripts/probe_m1_teacher.py、tests/test_m1_teacher_support_height_evidence.py、notes/log/2026-10-14-m1-support-height-authority.md。
- [ ] 原始root/q独立复算初始Z、同帧supportXY/Z、历史绑定与RESTORE速率；篡改基准/active/状态必须RED，随后审核实现GREEN。事务重放和outer重放分别完整接入，不能只核对日志自述。
- [ ] 冻结v19input129验证支撑RR目标不被虚拟姿态抬高，保存数值，注明非物理结果。
- [ ] 全部相关CPU、diff-check、最终fresh独立review；Important/Critical一次RED/GREEN修复。
- [ ] 核验文件SHA/GPU空闲及无训练native，唯一目录4env seed101 first-obstacle slow-rolling load-feedback真实10cm；全轨迹视频/JSONL/汇总/退出码归档。不能将失败轨迹用于训练。

## Review Focus与裁决

世界Z必须由实际root变换；活动轮不受支撑平面覆盖；旧q和已提交基准/偏置与beta一次一致；首次捕获只提交成功事务；RESTORE平滑返回并有实际恢复，不因目标连续性替代恢复。参数/安全/成功标准不改。
使用既有linked worktree，Git作者缺失保留文件SHA不伪造提交。用户直接执行授权覆盖普通实现决定；不覆盖生产训练/删除。自审已覆盖规格各项，Task1接口由Task2消费，Task3独立验证。
