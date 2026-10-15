# Active-leg measured IK Implementation Plan

最新执行回执：用户已确认且实施/审查/实际10cm完成，374相关CPU通过；4×123帧右后支撑失载保护、零跨越，详见[实施证据](../../../notes/log/2026-10-14-m1-active-leg-measured-ik-implementation.md)。下文审批语句为计划编写时历史。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, then one independent reviewer. Steps use checkbox (`- [ ]`) syntax for tracking. Preserve existing execution method.

**Goal:** 修复活动腿使用虚拟机身姿态的执行分配问题，并直接实测10cm过障，不新增卸载前置。

**Architecture:** 纯分腿目标构造器区分measured活动腿与command支撑腿；扩展现有IK事务的有限回溯以满足编码后连续性。Teacher只在slowrolling跨越/落地交接接入，probe同时认证几何目标与实际执行，不能把混合坐标目标冒充统一body参考。

**Tech Stack:** Python/PyTorch、pytest、隔离Isaac原生诊断。

**Spec:** [已确认规格](../specs/2026-10-14-m1-active-leg-measured-ik-design.md)。

## Global Constraints

- Baseline04133e0+已有未提交v14候选；当前linked worktree codex/m1-dual-support-recovery，不重建/清理。
- 活动腿同帧实测root位置/wxyz姿态；支撑腿保留command body；物理意图与执行中间目标分开。
- IK DLS .05/有限差分1e-4/最多32迭代/2mm残差/膝绝对角>=.10保持；编码后2.5rad/s×dt，20ms为.05rad。
- 事务最多8档，拒绝不提交。以最后实际下发关节FK衔接，不硬clip关节后假称达到IK目标。
- 不改PD/力矩/奖励/碰撞/真实支撑/净空/经过/恢复，不改生产/训练。仍4env/seed101/实际10cm，不独立支撑夹具。
- Git身份缺失不伪造作者；不能提交则保留diff/SHA/ledger，不stage既有无关改动。
- 全库pytest已知历史重复模块/pxr收集错误应再执行并具体报告，不能以相关测试通过代替全库通过。
- 核心算法改动限于ame_baseline与对应probe，不进入extension planner；只复用既有FK。

## Review Focus

1. 多环境中只有部分活动腿切换，reset/断帧不能污染其他行；Task2反例。
2. 两次抗积分饱和求解选择不同回溯档，最终证据必须绑定最终下发而非首解；Task3篡改反例。
3. 活动腿进入RESTORE时目标坐标切回可能跳变；Task1/2连续交接测试。
4. 测量时序/四元数错行或NaN导致错误世界目标；Task1拒绝/Task3输入绑定反例。
5. 微小回溯目标虽在2mm残差内但未实现抬起；Task1区分意图与执行、Task4必须实际轮高验收，不把IK valid当成功。

### Task 1: 纯分腿目标与有界执行事务

**Files:** Create `Go2Pvcnn/ame_baseline/m1_teacher_execution_targets.py`; modify `Go2Pvcnn/ame_baseline/m1_teacher_pose.py`; test `Go2Pvcnn/tests/test_m1_teacher_execution_targets.py`.

**Interfaces:**
- Consumes BodyPose/PoseReference、body_feet、world_to_goal_body、last_applied_q[B,12]。
- Produces `ExecutionTarget(body_goal, body_step, mode, fraction)` frozen dataclass，body目标[B,4,3]，mode[B]long(0legacy/1split/2handover)，fraction[B]。
- `execution_targets(command, measured, active_wheel, last_applied_q, fraction, mode) -> ExecutionTarget`：command/measured使用相同batch/dtype/device；活动轮long[B]范围0..3，fraction[B]在(0,1]，mode合法；非法结构抛ValueError，非有限或非单位quat不返回可执行合法目标。
- 扩展`backtrack_feedback_reference(..., execution_valid, body_x=False, measured=None, active_wheel=None, execution_mode=None)`；旧参数None保持旧算法/结果。FeedbackReferenceStep新增可选execution_target，默认None，兼容旧调用。

- [ ] 写测试，四活动腿×float32/64：mode1 body_goal活动腿等于measured变换，其余等于command变换；mode2全command。mode0旧结果不变。
```python
assert_close(result.body_goal[:,active], measured_target[:,active])
assert_close(result.body_goal[:,support], command_target[:,support])
assert_close(result.body_step, start + fraction[:,None,None]*(result.body_goal-start))
```
start=body_feet(last_applied_q)。同时测低根高+倾斜、不合法quat/NaN、错batch/dtype/activeindex。
- [ ] 先运行新文件CPU pytest，Expected:新函数缺失/接口不支持的RED；不接受因环境或测试拼写失败。
- [ ] 实现纯构造器与事务。每个现有beta档同时构造physical/command；mode1仅活动腿终点使用measured，mode2全command；全部腿执行body_step从last_applied FK向终点按beta衔接。实际execution IK以last_applied_q为seed，nominal IK仍原物理目标/原seed；校验编码后连续性及execution_valid，最大8档。不把world_to_goal_body(command)冒充mixed residual目标。
- [ ] 写大位姿误差的RED反例并修复：首档超过.05rad则选择较小档；全部档拒绝不提交；mode2从上一split目标交接仍<=.05rad。Expected:全部GREEN；动作合法小步，不要求一步到最终目标。
- [ ] 跑新文件+test_m1_teacher_pose.py+test_m1_teacher_feedback_transaction.py，Expected:相关通过；记录完整命令/数量。可用身份时仅显式stage本任务文件提交，否则记录SHA未提交。

### Task 2: Teacher接线及跨阶段原子交接

**Files:** modify `Go2Pvcnn/ame_baseline/m1_reference_teacher.py`; test `Go2Pvcnn/tests/test_m1_teacher_measured_ik.py`。
**Interfaces:** consumesTask1可选参数/result；produces执行mode、fraction、body_goal/body_step诊断和必要的行内交接标志。

- [ ] 写RED：同帧measured实际姿态传入slowrolling LIFT/PASS，活动腿选对；BALANCE/APPROACH/legacy无新路径；RESTORE走mode2 bounded handover。
- [ ] 实现选择：slowrolling LIFT/PASS=1，进入RESTORE保留有界执行路径mode2直到完整command终点(beta1)执行成功。交接完成前不得因局部stable计数跳过最后可执行交接；finish/换腿必须同时满足原恢复证据与交接完成。下一准备重新mode0，但last_applied连续性始终保留。
- [ ] 新状态仅scratch工作；完整IK+编码+原安全校验成功才commit。重复调用返回缓存；reset仅本行清；失效测量/跳帧不使用陈旧measured。两次反馈求解均消费同帧输入和同一mode，最终返回第二次所选execution_target。
- [ ] 写并运行RED→GREEN：两行单行reset、四腿切换、重复/断帧、编码拒绝、IK失败不提交、RESTORE交接未完不得finish。断言完整row状态而非只单个flag。
- [ ] fingerprint升级描述measured-active-execution-v15，诊断字段单独execution_前缀，记录意图/实际执行不同；不改旧accepted physical字段语义。跑Task1+2及reference/dynamic/lift/slowrolling相关测试，Expected:GREEN。提交或记录未提交SHA。

### Task 3: 外层证据与独立复算对齐

**Files:** modify `Go2Pvcnn/scripts/probe_m1_teacher.py`; create `Go2Pvcnn/tests/test_m1_teacher_measured_ik_evidence.py`。
**Interfaces:** consumesTask2 mode/fraction/body_goal/body_step与同帧measured输入；produces输入绑定、IK几何、真实apply receipt审计，不替代物理成功。

- [ ] 写RED：篡改measuredquat、activewheel、mode、fraction、执行目标或最终二次反馈结果必须被拒绝；未改原样本应通过。
- [ ] observer保存完整同帧measured位置/quaternion和执行mode，绑定preparation_input/teacher_input_frame/episode，不能只信context；更新replay_feedback_transaction与outer whitelist/诊断前缀以消费Task1同签名并记录真实结果。
- [ ] 对每腿复算body_step对应IK残差；同时核实mode1活动腿终点在measured世界下等于期望轮目标，支撑腿终点等于command变换；交接beta中间点不冒充最终轮目标。保持对实际编码/action/process/4次apply的精确验证。
- [ ] 验证legacy context兼容、missing metadata必须拒绝新mode、CPU/producer后端信息不丢、二次求解和失败回滚证据。Expected:new+feedback_evidence+dynamic_support_evidence全部GREEN。
- [ ] 冻结frame165只读CPU对照：原证据不覆盖，另保存新求解。终点应向上、所选执行步合法且向终点改善；不把它当已离地。全部原始SHA保留。

### Task 4: 参数复核、独立审查及实际10cm

**Files:** new `notes/log/2026-10-14-m1-active-leg-measured-ik-implementation.md`，更新notes索引/dashboard/T306/ai-human17；测试证据在本计划SDD目录，原生输出使用全新名称。
**Interfaces:** consumesTask1–3通过的候选和证据，produces软件结果与真实跨越结果分别报告。

- [ ] 执行Task1–3所有相关测试+裸pytest，读取输出。Expected:相关GREEN；全库若仍历史收集错误逐项列出，不删历史资料/装无关依赖。
- [ ] 参数核查：命名映射、编码往返、实际PD/动作范围/关节限速/四子步dt保持；无新证据不改PD。整分支独立review重点逐项检查Review Focus，Important/Critical反例RED→GREEN修复。
- [ ] 无并发训练/native且GPU空闲后备份候选源码SHA，只同步隔离candidate。原生4env seed101 stage3/10cm first-obstacle slowrolling，1000控制步上限；使用新输出目录，保留原诊断。
- [ ] 记录真实轮底离地/相对障碍净空/支撑/碰撞/经过/远侧落轮/恢复。Expected:生成可审计完整失败或成功证据并进程退出；不预设成功。不能仅因测试或阶段PASS标志宣布掌握。
- [ ] 如仍失败，同env逐帧定位目标分配/IK/编码/下发/实际关节和姿态卡点；不得自动扩大PD/奖励/轮数。归档源码/JSONL/视频/结果/exit，双方SHA核实，GPU释放，notes同步。
- [ ] 本计划只完成候选修正与实测，不自动进入教师采集/BC/PPO/生产部署。交付说明剩余问题与验证边界。

## Self-review / handoff

规格目标、分腿语义、连续衔接、回滚、恢复、参数核查、证据和实际10cm均有对应任务；Task1接口由Task2消费，Task2诊断由Task3认证，Task4消费候选与证据。旧接口None保持legacy，混合残差不使用旧单body假设。执行方法沿用主代理inline＋最终独立审查。本计划待用户审阅后实施，不重复规格审批。

