# M1 Stall/Slip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline as previously selected. Steps use checkboxes.

**Goal:** 有界原地/当前承重轮打滑费用，经验证后从用户明确指定本run model200继续。
**Architecture:** 纯torch窗口核、纯torch滚动核；pre-step停滞快照送RewardManager，滑移在RewardManager自动reset前采样。wrapper负责逐行reset及日志；训练合同显式迁移保留权重/Adam/std/课程。
**Tech Stack:** Python/PyTorch/Isaac Lab/AME/PPO/pytest。
**Spec:** `docs/superpowers/specs/2026-10-12-m1-stall-slip-design.md`（用户已审阅确认）。
**Global constraints:** 本地10-12专用镜像逐项实施，服务器源码不热改；无训练/native并发；保留所有PT；不改2048/.30/参考物理/std/课程/成功标准。model200 stage0/streak1/last2048 pass1，经用户确认可重跑剩余stage0，不能冒充结束时249的PT。

### Task 1: Pure kernels and environment adapters

Files: create `Go2Pvcnn/ame_baseline/m1_stall_slip.py`, `Go2Pvcnn/tests/test_m1_stall_slip.py`.

- [x] RED: import模块并断言接口存在；窗口静止2秒后的rate=.5，正常.30m/s时0；纯滚动0/当前无力0/空转.25。
- [x] 核接口：`StallWindow(n,device,dt).update(x,identity,active,complete)` 返回 `rate,progress,warm,invalid`；`.reset(rows)` 清指定行。固定dt长度ceil(2/dt)+2环缓冲，H高水位，按两相邻旧样本插值2秒前H，浮点容差仅时间比较。
- [x] 核接口：`rolling_contact_speed(linear,angular,quat,radius)`；`bounded_slip(speed,forces)` 返回rate/current_contact/invalid。当前Fz>10，.03容差、.27尺度、平方、max轮、.25上限。
- [x] 适配器 `prepare_stall_snapshot(env, tracker, stage, course, required, recovered)` 使用课程原点、ids与stage身份；全receipt complete才豁免，pre-step保存rate和日志。
- [x] 适配器 `stall_penalty(env)` 返回负rate；`replace_slip(env,legacy)` 仅stage1–3返回新负费用折算到旧-0.1权重后的正term值，保存真实滑移日志。非flat-first返回legacy逐值不变。
- [x] GREEN并扩展异步reset、课程变更、回退、侧移、dt=.03、NaN、历史接触、排序、正反转等反例。命令：`../m1-learning-tests.ps1 -Tests 'Go2Pvcnn/tests/test_m1_stall_slip.py Go2Pvcnn/tests/test_m1_rl_reward_geometry.py'`，期望全绿。
- [x] 提交仅核/测试。

### Task 2: Reward lifecycle / explicit checkpoint contract

Files: modify `ame_env_wrapper.py`, `m1_ame_rewards.py`, `m1_ame_env_cfg.py`, `m1_ame_contract.py`, `ame_runner.py`; create `scripts/convert_m1_stall_slip_checkpoint.py`.

- [x] RED: 源接线与实际适配测试：预步snapshot在env.step前；done和全reset清窗口；stage0/mixed4旧term保持；新checkpoint有奖励合同，旧checkpoint直接加载拒绝。
- [x] 配置 `stall = RewTerm(func=stall_penalty, weight=1.0)`；原 `feet_slide` 仍-0.1，在原函数末尾调用 `replace_slip`，legacy公式不改。
- [x] wrapper初始化StallWindow，pre-step在现有required快照处prepare，post-step日志snapshot在reset前clone，末尾done清状态。奖励manager结算后再auto-reset，故滑移直接读取current力无需post-reset估算。
- [x] `m1_training_contract()` 增加 `reward_contract`（version stall-slip-v1及全部数值）；迁移函数只接受无此字段的完整参考v2/12动作/正确物理合同，递归有限检查，deepcopy后加contract和`m1_reward_conversion`来源SHA/iter，不改模型/优化器/课程。
- [x] runner保存加载conversion字段。转换脚本参数input/output，目标必须不存在，原PT哈希记录；CPU验证后保存显式新文件。
- [x] GREEN相关整组，完整/折扣轨迹检查新增费用上界及不诱导即时碰撞。仅测试离散费用差异，不声称总策略最优。
- [x] 提交runtime/测试/转换脚本。

### Task 3: Whole-branch review / native gate

Files: create `scripts/probe_m1_stall_slip.py`, diagnostic deployment helper and notes.

- [x] 以现有 `probe_m1_reference_learning.py` 为原生基线复用，通过runpy执行原配置/空地/碰撞验收；另外在同App验证当前奖励接线、stage1–3/stage0/mixed4隔离、窗口静止/滚动轨迹、离地历史接触、GPU核与CPU结果、reset无遗留。
- [x] 全分支fresh reviewer审查：重点tensor alias/pre vs post reset、课程身份、无valid padding、NaN、旧stage逐值保持、迁移拒绝不同物理、日志不重复算dt。
- [x] Critical/Important反例RED/GREEN后整组回归，保留结果。
- [x] 只在当前旧run最新完整CPU核验PT后SIGINT核实PID4885；等待退出/GPU释放，保留旧PT。
- [x] 隔离候选原生COMPLETE才允许部署，不修改现训练源码或降低env偷跑。

### Task 4: Deploy / restart / publish

- [x] 备份所有受影响生产文件并写SHAmanifest；复制通过CPU/native的候选并逐项SHA校验。
- [x] 转换原run12-26-20/model200到新独立初始化路径；核对原SHA不变，39model/33Adam/12std/iter200 next201/stage0/streak1/last2048 pass1，conversion来源完整。
- [x] 新log唯一且全机无同任务train/probe后，kernel flock入口启动 `CHECKPOINT=<converted200> M1_LOAD_OPTIMIZER=1 MAX_ITERATIONS=9799 NUM_ENVS=2048 M1_FIXED_WHEEL_SPEED_M_S=.30`，即next201到exclusive10000，keep_std/save100不变。
- [x] 核实真实cmdline/cwd/env_cfg、实际完成201更新、loss有限、新checkpoint合同/课程；TB改指新run但不碰本地隧道。
- [x] README和notes注明双费用与重新起点（非从零），服务器同步核验，普通push10-12与独立ref核实。更新heartbeat防重启旧4885。

## Review Focus

短暂抬轮历史接触误罚、接触力为零时无奖而非安全成功、滑移近似不能称精确PhysX；20秒不滑/空转/停滞费用及gamma折扣；跨stage自动reset时旧row快照；转换不能修改std/Adam或偷跳stage1；候选不覆盖生产直到GPU隔离验收。
