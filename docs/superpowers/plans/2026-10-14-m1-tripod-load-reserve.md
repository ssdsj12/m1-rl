# 三轮承载储备 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 修正四轮承重被当成抬轮后三轮承重的资格缺口，在真实10cm障碍中联合移重心与抬轮，获得完整经过/恢复证据。

**Architecture:** 独立纯计算模块求三轮份额与保守载荷标尺；现有选姿态函数增加显式可选载荷条件，rolling teacher负责捕获状态与进度接线；probe独立审核新证据。保留v15执行IK与所有实际安全检查。

**Tech Stack:** Python、PyTorch、pytest、Isaac Lab隔离候选；Windows编排、Linux CPU/串行GPU验证。

**Spec:** [已确认规格](../specs/2026-10-14-m1-tripod-load-reserve-design.md)。

## Global Constraints

- 原候选范围X±.04/Y±.06/降低0–.08m、双几何margin>=.01m、原IK/分支不变。
- 目标双几何最弱预测载荷>=45N；真实支撑30N底线不降低；进入LIFT预测须>30N。
- 预测储备clamp((min_load-30)/15,0,1)，与原真实储备取min，不替代真实安全。
- 四轮0.05m/s、加速度0.10m/s²，PD/物理/奖励/动作限速/恢复标准不改。
- 仅slow_rolling实际过障路径；legacy/独立诊断不启用，不增加单独卸载试验。
- 当前W隔离worktree与/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn候选；生产不改、不自动BC/PPO，不删历史。
- Git身份未配置时保留未提交变更和SHA，不伪造身份；提交仅精确任务文件且先确认无混入旧修改。

## Review Focus

1. 大世界坐标/float32导致退化误判或虚假正载荷：Task1平移及近退化测试。
2. 三角形外负份额被截断洗白：Task1保留负值测试，Task2不得合格。
3. 总载荷尖峰与准备捕获未提交：Task3事务拒绝及尖峰测试。
4. 单行reset/换目标借用旧标尺：Task3批次隔离与重新捕获测试。
5. 生产与重放共享错误自证：Task4共同篡改生产计算的独立方程拒绝测试。

---

### Task1：三轮载荷纯计算

**Files:** 新建ame_baseline/m1_teacher_tripod_load.py、tests/test_m1_teacher_tripod_load.py（均在Go2Pvcnn）。

**Interfaces:**
- tripod_load(com_w[B,3], wheels_w[B,4,3], active_wheel[B] long, total_load_n[B]) -> TripodLoad。
- TripodLoad字段support_indices[B,3]、fractions[B,3]、loads_n[B,3]、min_load_n[B]、valid[B]。
- capped_load_scale(raw_fz[B,4], captured_load_n[B]) -> Tensor[B]，逐行min(非负向上力和,捕获值)。
- 无效数值行valid=False、min_load_n=NaN，不整批崩溃；结构/dtype/device错误抛ValueError。保留有限负份额不截断。三角形两倍面积绝对值<=1e-10视为退化，与原support_margin一致。

- [ ] 写RED：test_triangle_center得到三等份；test_outside_preserves_negative、test_degenerate_and_nan_invalid、test_four_active_wheels、test_translation_rotation_float32_float64、test_zero_load_invalid、test_spike_is_capped。
- [ ] 运行 `python -m pytest tests/test_m1_teacher_tripod_load.py -q`，先证实缺模块/接口失败。
- [ ] 实现相对COM坐标2D方程，用安全掩码避免单个奇异行污染全批；不引入新依赖。
- [ ] 同命令GREEN；检查份额和1/XY重构、负值保留、捕获100/current200结果100。
- [ ] 记录测试日志/SHA；有有效Git身份时精确提交，否则记录未提交状态。

### Task2：候选载荷约束与排序

**Files:** 修改ame_baseline/m1_teacher_pose.py；新建tests/test_m1_teacher_tripod_selection.py。

**Interfaces:**
- choose_support_pose原签名追加keyword-only `tripod_total_load_n=None, tripod_min_load_n=45.`；默认None完全保留旧路径。
- 同时指定旧desired_com_xy和tripod_total_load_n时抛ValueError，避免两种排序暗中覆盖。
- 消费Task1 tripod_load；内部计算候选预测COM在两三角形下的min_load，先过滤>=45，再按较小的双几何min_load降序、原cost升序、索引升序排序。
- 原PoseChoice接口保持；probe可从选择结果原始reference独立复算新诊断。

- [ ] 写RED：test_geometry_pass_but_load_fail、test_maximin_before_motion_cost、test_ties_keep_cost_then_index、test_no_eligible_returns_invalid、test_default_legacy_unchanged、test_negative_fraction_never_eligible。
- [ ] 运行 `python -m pytest tests/test_m1_teacher_tripod_selection.py -q`，确认旧函数缺新参数/未过滤失败。
- [ ] 实现仅附加可选分支，保留125网格+旧参考125、原envelope/IK/双margin；无合格不回退为valid。
- [ ] 运行新测试和 `tests/test_m1_teacher_pose.py`、`tests/test_m1_teacher_dynamic_support.py`，全部通过。
- [ ] 日志/SHA与精确提交条件同Task1。

### Task3：rolling捕获、准备与抬轮进度

**Files:** 修改ame_baseline/m1_reference_teacher.py、ame_baseline/m1_teacher_dynamic_support.py；新建tests/test_m1_teacher_tripod_control.py。

**Interfaces:**
- prepared首次成功事务捕获row.tripod_captured_load_n，来自该输入正Fz和；reset/换目标/结束旧准备时删除。无新TeacherState字段。
- _select_preparation_pose仅rolling且diagnostic=None传Task2有效标尺；LIFT/PASS同样使用，撤去该路径desired_support_com_xy排序调用。
- measured_lift_step增加可选external_reserve[B]=None，默认旧行为；启用时最终reserve=min(旧reserve,external_reserve)，先合并再算increment。
- 预测无效或<=30时external_reserve=0；有效按规格公式；现有真实支撑失败优先。BALANCE→LIFT增加实测三轮min_load>30条件。
- 输出tripod_前缀诊断：captured_total_n/current_total_n/effective_total_n、valid、三个support_index/fraction/load_n、min_load_n、reserve、selected_anchor_min_n/selected_measured_min_n。

- [ ] 写RED：test_four_loaded_18n_cannot_start_lift；test_reserve_30_37p5_45_is_0_half_1；test_no_reserve_keeps_body_and_rolling_updates；test_capture_rejection_not_committed；test_spike_no_extra_reserve；test_reset_one_row_and_target_switch；test_gap_drops_old_trend；test_legacy_and_restore_unchanged。
- [ ] 运行 `python -m pytest tests/test_m1_teacher_tripod_control.py -q`，确认现有进度/状态违反新断言。
- [ ] 实现同一输入快照、scratch事务捕获/提交；合并储备不得绕过lead、ceiling、IK或原始碰撞检查。更新teacher fingerprint标识新合同。
- [ ] 新测试及reference_teacher/dynamic_support/measured_ik/feedback_transaction相关测试GREEN；同帧108冻结预测约18.85N且抬升增量0，不篡改旧记录。
- [ ] 记录实现日志/SHA，提交规则同上。

### Task4：独立证据审核与直接10cm实测

**Files:** 修改scripts/probe_m1_teacher.py；新建tests/test_m1_teacher_tripod_evidence.py；创建notes/log/2026-10-14-m1-tripod-load-reserve-implementation.md并更新index/todo/T306及ai/human17。

**Interfaces:**
- probe捕获/重放增加标尺状态和新选择keyword；归档所有新增源码。
- 独立审核从preparation_input、捕获帧和候选原始姿态重建重心坐标方程及双几何载荷，使用独立代数路径而非调用生产tripod_load。
- 捕获帧通过episode/env/step绑定、拒绝不推进；核对45候选条件、30进度条件、最终合并储备及诊断元数据。

- [ ] 写RED：test_tampered_capture_or_minimum_rejected、test_joint_producer_replay_corruption_rejected、test_reset_identity_mismatch、test_valid_tripod_receipt_passes。共同篡改生产计算仍须被独立审核抓住。
- [ ] 运行 `python -m pytest tests/test_m1_teacher_tripod_evidence.py -q`，确认旧验证器不能拒绝反例；补审核后GREEN。
- [ ] 运行四个新测试文件及v15十三文件相关集合，逐项保存命令/日志；全库收集限制单列。
- [ ] 以主代理inline执行方式完成一次独立最终review；有Important/Critical先反例修复再复审，不将review当物理成功。
- [ ] SHA同步仅隔离候选；核实当前主机cmdline无训练/native、GPU空闲；沿既有flock启动新唯一目录 `evidence-first-obstacle-tripod-reserve-v1`，teacher/first-obstacle/slow-rolling/4env/seed101/1000控制步上限/headless cameras。禁止覆盖旧目录，禁止并发训练。
- [ ] 等实际进程完成并核验result/exit/GPU；审计每轮实际轮底、Fz、COM、碰撞、经过、远侧稳定恢复及整机0.3秒恢复，下载视频和完整证据核SHA。
- [ ] 失败记录最早物理因果与未运行范围，继续目标诊断；仅局部轮离地/CPU绿灯不算跨越成功。若第一障碍成功，继续既有完整目标范围验收，不宣称未跑部分已掌握。
- [ ] 更新notes和用户结果：区分实现、软件验证、实际能力；不自动训练/发布。

## 执行环境与自审

CPU验证在隔离候选下使用 `CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest ...`。所有首次RED均先同步测试而不提前同步对应实现。SSH沿用指定主机及ClearAllForwardings，不改网络/显示配置。

自审完成：纯计算/候选/状态接线/独立证据分别有对应接口和RED→GREEN；五项Review Focus均映射测试；原保护/legacy/预测局限和真实最终验收不缺项。使用既有主代理inline＋最终独立审查方式。书面规格已获确认，本计划待审阅后执行。
