# Dynamic support and measured lift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Preserve the existing inline implementation method, followed by independent review.

**Goal:** 在实际10cm障碍中，边低速滚动边调整支撑，按实际轮高及支撑储备推进抬轮，最后真实经过并恢复。

**Architecture:** 纯函数模块计算载荷滤波、目标COM和抬轮增量；现有pose选择器增加可选COM排序，teacher负责阶段限定及原子提交。外层进度证据独立复算，不混入纯反馈事务审计。

**Tech Stack:** Python/PyTorch、pytest、隔离候选Isaac Lab/Isaac Sim原生诊断。

**Spec:** [已确认规格](../specs/2026-10-14-m1-dynamic-support-measured-lift-design.md)。用户已确认本计划，已实施并独立审查/实际10cm诊断。319相关CPU通过；4×186帧未跨越，1保护锁停3同批中断。五任务执行收尾完成，不等于物理目标达成；详见[结果](../../../notes/log/2026-10-14-m1-dynamic-support-implementation.md)和本计划SDD ledger。未提交（Git身份缺失），未改生产/训练。

## Global Constraints

- 仅slow_rolling实际障碍LIFT/PASS改行为；BALANCE、RESTORE、legacy/local保持。
- 正常轮面0.05m/s、斜率0.10m/s²；不改变PD、物理、奖励、地形或原始碰撞保护。
- 原包络4/6/8cm、IK2mm、关节目标2.5rad/s、分支连续性、三支撑原始Fz30N保护保持。
- 机身/轮Z参考速率均0.02m/s；轮Z领先实测上限0.02m；排序EMA时间常数0.10s。
- 储备连续带：Fz30–45N、COM余量0.01–0.015m；不能把滤波或预测当实际安全证明。
- 活动轮参考不得重置到地面；横向/差分滑移不得吸收入锚点；接受状态只在完整事务通过后提交。
- 直接同一10cm first-obstacle四环境视频，不新增单独支撑夹具；未真实跨越并恢复不启动BC/PPO。
- 使用现有dual-support-recovery worktree和/tmp隔离candidate；不覆盖生产、不删PT、不重启历史训练。
- Git身份目前缺失；提交步骤遇此限制仅保留改动及记录，不设置身份、不虚报提交、不夹带既有脏文件。

## Review Focus

1. 首帧/断帧/拒绝后的趋势历史：不得错误外推或消耗未提交进度（Task1/3）。
2. 轮实际下沉、参考领先超限：保持旧参考，不强制向下追踪或无限抬高（Task1/3）。
3. 无可行候选及活动轮切换：不得提交无效姿态、错用活动轮作支撑或沿用旧腿历史（Task2/3）。
4. 支撑原始载荷突然下降但EMA仍高：原始保护优先，不以平滑值放行（Task3）。
5. 诊断篡改及旧fingerprint：外层重算必须拒绝，纯反馈验证不能误接管外层字段（Task4）。

## 文件与职责

- 新建`Go2Pvcnn/ame_baseline/m1_teacher_dynamic_support.py`：无可变全局状态的张量算法。
- 修改`Go2Pvcnn/ame_baseline/m1_teacher_pose.py`：可选COM排序，不改可行性。
- 修改`Go2Pvcnn/ame_baseline/m1_reference_teacher.py`：参数、scratch状态、阶段接线和诊断。
- 修改`Go2Pvcnn/scripts/probe_m1_teacher.py`：独立外层证据采集与复算。
- 新建`Go2Pvcnn/tests/test_m1_teacher_dynamic_support.py`、`test_m1_teacher_dynamic_support_evidence.py`；调整原lift_decoupling测试中被新合同替代的帧数推进断言，保留原保护/legacy反例。

## 验证命令约定

CPU命令在服务器隔离candidate的`Go2Pvcnn`目录执行：`CUDA_VISIBLE_DEVICES='' PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest <test paths> -q`。只同步明确修改文件并核SHA，不安装本地torch。每个RED必须是行为断言/缺失接口失败，不能把导入路径错误当RED。

### Task 1: 纯载荷与抬轮计算

**Files:** 新模块和`test_m1_teacher_dynamic_support.py`。

**Interfaces:** 张量均同device/dtype；B为batch。`filter_support_fz(raw_fz: Tensor[B,4], previous: Tensor[B,4], history_valid: BoolTensor[B], dt: Tensor[B], tau_s: float) -> Tensor[B,4]`；`desired_support_com_xy(wheels_w: Tensor[B,4,3], filtered_fz: Tensor[B,4], active_wheel: LongTensor[B]) -> Tensor[B,2]`；`measured_lift_step(accepted_z, measured_z, max_z, min_fz, margin, previous_min_fz, previous_margin, history_valid, dt, *, rate_m_s, lead_m, force_floor_n, force_band_n, margin_floor_m, margin_band_m) -> LiftStep`，所有位置/余量输入为Tensor[B]，history为BoolTensor[B]。`LiftStep`包含`next_z, increment, reserve, conservative_fz, conservative_margin, lead_error`张量与`freeze_code`整型张量。

- [ ] 写反例：dt=.02、Fz45、margin.015、充分跟随时`increment≈.0004`；Fz37.5或margin.0125时`increment≈.0002`；accepted_z=.12/measured_z=.09时`next_z==.12`；重复调用同输入结果相等且输入未改。
- [ ] 写首帧/断帧无趋势、下降趋势减缓、活动轮权重严格为0、其他三权重和为1、dt=.01增量减半、NaN/非法dt拒绝测试。运行新测试确认RED。
- [ ] 实现EMA `alpha=1-exp(-dt/.10)`；history无效直接用当前。正向Fz倒数使用dtype epsilon避免除零，仅用于排序。趋势为`2*current-previous`并与current取min；按规格三项min算非负增量。非法输入抛ValueError，由teacher转入原拒绝路径，不修补为安全值。
- [ ] 运行新测试GREEN。仅提交该模块/测试（身份可用时），不提交其他候选历史。

### Task 2: 有限候选动态排序

**Files:** `m1_teacher_pose.py`、新动态支撑测试。

**Interfaces:** `choose_support_pose`现有参数/返回`PoseChoice`保持；新增keyword `desired_com_xy: Tensor[B,2] | None = None`。None完整保留旧排序；非None用预测COM距离平方、原归一化移动代价、原索引三层稳定排序。

- [ ] 写测试：两可行候选下改变弱支撑位置改变排序；相等距离按移动量/索引；None返回旧结果；无可行点仍valid=False/index=-1；搜索数量/包络不扩。
- [ ] 写活动轮升高参考输入保持不变、实际横向滑移不重置wheel_anchors、非有限COM目标拒绝反例。运行RED。
- [ ] 仅在原eligible之后增加稳定字典序排序，禁止浮点加权和近似多级排序；不更改双几何/IK条件，不重新捕获锚点。
- [ ] 动态支撑测试及原pose相关测试GREEN；仅提交本任务差异，保留原脏改动。

### Task 3: Teacher接线与事务提交

**Files:** `m1_reference_teacher.py`、动态测试、`test_m1_teacher_lift_decoupling.py`。

**Interfaces:** TeacherConfig新增`dynamic_support_tau_s=.10, dynamic_body_rate_m_s=.02, measured_lift_rate_m_s=.02, measured_lift_lead_m=.02, measured_lift_force_band_n=15., measured_lift_margin_band_m=.005`；验证正有限。row新增`dynamic_support_fz`、`dynamic_previous_min_fz`、`dynamic_previous_margin`、`dynamic_history_valid`、`dynamic_active_wheel`，均随scratch事务提交；accepted轮高直接读取既有accepted.wheels_w，避免第二套可漂移Z状态。

- [ ] 写集成反例：LIFT/PASS身体位置误差.015m仍允许纠偏，位置步长<=.02*dt；旧BALANCE/RESTORE不变；active轮参考不回地面；轮未跟随时达到lead上限后保持。
- [ ] 写IK/编码/连续性拒绝后所有新增状态及accepted不变，duplicate幂等、单行reset不影响邻行、断帧和换腿清趋势；rawFz<30即便EMA高仍原SUPPORT_LOST、碰撞仍原锁定；无候选保持并累计原invalid计数。运行RED。
- [ ] 只在rolling实际障碍LIFT/PASS接Task1/2。运输后复制accepted轮目标，支撑轮使用既有运输锚点、活动轮保留acceptedZ。有可行选择时朝新body目标作欧氏范数限速的位置步进；姿态沿原level/heading插值，保留后续IK/回溯约束。轮Z使用LiftStep替代age比例，age只诊断；安全门关闭时不增加Z。
- [ ] 历史只在相邻已接受连续输入有效；首次/换腿/reset/断帧/跨拒绝帧后不外推。完整编码/连续性成功才row.update。错误不提交滤波、目标或进度。PASS/RESTORE转换仍只读实际清障/远侧与原恢复检查。
- [ ] GREEN：新测试及原reference、feedback、feedback_transaction、reference_commit、slow_rolling、lift_decoupling回归。仅更新因已批准新公式而过时的断言，不能删保护反例。提交本任务差异。

### Task 4: 可独立重算的外层证据

**Files:** `probe_m1_teacher.py`、teacher诊断、`test_m1_teacher_dynamic_support_evidence.py`。

**Interfaces:** 新增`verify_dynamic_support_sample(sample: dict, cfg: TeacherConfig, *, replay_backend: str='cpu') -> list[str]`。sample独立`dynamic_support`命名对象包含enabled/phase/active轮、输入root/COM/wheels/rawFz/dt/连续性、pre-state及candidate选择所需anchor/accepted/q/branch、filteredFz/desiredCOM/candidate_index、conservativeFz/margin/reserve、accepted/measured/requestedZ/increment/lead/freeze_code、transaction accepted标志及post-state。保留原feedback对象及验证职责。

- [ ] 写真实teacher→observer→序列化→verify集成测试；篡改目标COM、候选索引、原始输入相邻历史、增量、freeze和post-state分别必须errors非空；旧fingerprint不能称新证据。运行RED。
- [ ] 从实际输入与pre-state复算Task1/2及限速结果，再核成功/拒绝后的post-state；verify_episode逐帧核历史衔接/reset/gap。不得只相信记录内computed字段。数值容差沿现有后端审计标准、不放宽。
- [ ] fingerprint升为`support-ik-transaction-v14-dynamic-support-measured-lift`，新增配置/证据字段全部纳入。纯feedback验证保持明确字段列表，不扩大wheel_等泛前缀。
- [ ] 新证据测试及原feedback_evidence/transaction回归GREEN；独立审查实现、回滚、证据与规格，阻断问题RED/GREEN修复后再原生。提交本任务差异。

### Task 5: 直接10cm实测与交付

**Files:** 本次动态日志、notes/index.md、todo.md、T306、log/index.md、ai-17/human-17执行合同；新独立证据目录`evidence-first-obstacle-dynamic-support-v1`。

- [ ] 核相关CPU全部通过及审查完成，冻结源码/测试SHA；旧v2视频/原始记录保持不可改。核最新主机a21506654554025984756592、进程身份、GPU和flock，无训练/native并发后仅同步candidate。
- [ ] 沿用既有四环境/seed101/真实stage3 10cm/first-obstacle/slow-rolling/1000控制步/摄像头诊断入口。先读现有启动脚本核CLI再执行，不改环境数量、物理或时长，不跑孤立支撑夹具。
- [ ] 运行中检查日志推进，结束核exit及record完整性；启动卡住不当物理失败、不盲改显示网络。记录每行终止原因，批量中断的同行不可当独立失败。
- [ ] 逐env/frame比较实际轮底、原始三轮Fz、COM余量、身体目标/实测、Z领先/增量与freeze、碰撞、真实PASS/远侧/落轮恢复；验证外层及反馈证据。目标升高或LIFT标签不能冒充实际跨越。
- [ ] 归档视频/源码/配置/结果、核SHA并更新上述notes；报告成功或失败链和仍未验证内容，不自动开训/调PD/放宽门槛。Git身份仍缺时明确未提交，不自动发布脏树。

## 自审与交接

规格第2–5节分别覆盖Task1–4，直接过障和证据闭环覆盖Task5。五项Review Focus均有归属反例；helper接口/row状态/证据类型一致。参数为首次实验初值，不是已证明有效。当前只写计划，未运行测试/原生，未修改控制或服务器。计划审阅后沿用主代理实施＋独立审查方式。
