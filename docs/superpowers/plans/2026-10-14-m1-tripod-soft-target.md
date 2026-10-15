# Tripod soft target Implementation Plan
> REQUIRED SUB-SKILL: superpowers:executing-plans，inline执行。
**Goal:** 解除45N硬筛选导致的抬腿前死锁，同时保留30N与真实安全保护。
**Spec:** docs/superpowers/specs/2026-10-14-m1-tripod-soft-target-design.md
**Architecture:** 只改变候选载荷底线和独立审核，不改变实际储备公式/控制速度/PD/成功门槛。
**Tech Stack:** Python/PyTorch，隔离Isaac仿真。
## Global Constraints
沿用原v16完整设计，45N仅改为满储备优化目标，候选严格>30N。旧PT/证据保留，无生产训练。
## Review Focus
边界等于30；双三角形一侧不足；legacy无载荷路径；审核不得仍45硬筛；v17指纹及旧证据隔离。
## Task1 selector及接线
- [ ] tests/test_m1_teacher_tripod_selection.py加入130N可选、90N不可选与显式30边界；旧100N拒绝用例改为90N，预期新130测试RED。
- [ ] m1_teacher_pose.choose_support_pose默认tripod_min_load_n30，严格>；保留maximin成本索引。
- [ ] 指纹v17；probe独立selected门槛30；原实际reserve和support_min_force_n不变。
- [ ] 新旧4tripod+13相关文件pytest全通过；裸pytest收集限制如实记录。
## Task2 evidence及实测
- [ ] 同历史失败selection_context只读重算，确认原44.58/44.98N候选可选。
- [ ] fresh独立审查，仅修Important且RED/GREEN。
- [ ] GPU空闲后唯一soft-target-v1原生4env first10cm 1000步，记录每轮实际阶段/抬升/恢复/碰撞及视频。失败不当完成。
## Interfaces
Task1保持PoseChoice及全部诊断字段不变；Task2读同selection_context，版本指纹隔离。

