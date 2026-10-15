# M1 Support Heave Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans；用户直接执行授权，inline与一次最终独立review。

**Goal:** 恢复三轮支撑的机身高度负反馈，实际验证10cm跨越后恢复。
**Architecture:** 有界公共升降proposal与零和载荷分离，完整事务一次beta与证据绑定。
**Tech Stack:** PyTorch/pytest/隔离Isaac。
**Spec:** ../specs/2026-10-15-m1-support-heave-design.md

## Global Constraints
仅教师load_feedback路径；.02m幅度/.02m/s速率；三支撑同值、活动腿不变；原物理安全门槛/PD/训练关闭不变。

## Task1 pure heave及执行目标
Files create ame_baseline/m1_teacher_heave.py, tests/test_m1_teacher_heave.py；modify m1_teacher_execution_targets.py。
Interface `propose_support_heave(command_z,measured_z,captured_error,previous,dt,restore,valid)`，前五为同dtype/device浮点[B]，后两bool[B]；返回HeaveProposal(offset,valid)。旧状态有限±.02，dt>0；输入命令/测量非法行冻结old并validfalse；restore仍要求有限输入。candidate=old+clamp(clamp(-(command-measured-e0),±.02)-old,±.02dt)，restore目标0。
- [ ] 写正负误差/首捕获零/饱和/rate/restore/NaN/shape/dtype测试，pytest Expected缺module RED。
- [ ] 最小实现再同pytest ExpectedGREEN。
- [ ] execution_targets新增support_heave_w_z=None [B]；需support_reference_w_z且mode1/2，有限±.02，支撑Z加共同项，活动排除；先4active×2mode×beta测试RED再实现GREEN。

## Task2 paired事务与教师生命周期
Files m1_teacher_pose.py/m1_reference_teacher.py/tests/test_m1_teacher_heave_transaction.py。
- [ ] 首capture/拒绝/多行reset/RESTORE未归零不退出测试RED。
- [ ] pose新增previous_support_heave/proposed_support_heave [B]，paired/context/rate/幅度校验，完整proposal入builder。teacher solve捕获command.rootZ-measuredZ，纯函数proposal，最终beta提交、诊断、reset/finish清理，退出要求heave0；fingerprintv21。Expected对应测试GREEN。

## Task3 独立证据与native
Files probe_m1_teacher.py/tests/test_m1_teacher_heave_evidence.py/notes log。
- [ ] context历史与rawroot绑定、独立scalar公式及worldZ审核篡改RED→GREEN；原外层/事务重放接入。
- [ ] 冻结v20敏感度比较（非物理），全相关pytest ExpectedGREEN，gitdiffcheck，最终freshreview及一次REDGREEN修复。
- [ ] SHA/无训练GPU空闲后唯一4envseed101真实10cm；完整退出/视频/轨迹归档，不因未成功扩大安全阈值。

## Review Focus
捕获误差不得每帧更新；NaN不污染历史；beta只一次且编码失败不commit；RESTORE和身份切换不留旧共同项；独立审核绑定rawroot和前态而非自述字段。各项由Task1/2/3对应反例覆盖。
