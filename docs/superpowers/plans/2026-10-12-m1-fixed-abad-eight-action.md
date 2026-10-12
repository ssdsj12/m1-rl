# Fixed ABAD / Eight-Action Fresh Implementation Plan

## 用户最新覆盖决定（执行中）

用户改为“从0开始训吧还是”。以下历史model200迁移步骤被撤销：不实施12→8转换器、不读取200作为初始化、不继承权重/Adam/std/课程。Task3仅实现8维保存/加载合同及错配拒绝。Task5使用随机8维wiring与零动作参考空地测试验证物理接线和时钟，不将随机策略稳定性当学习验收。Task6为fresh/no CHECKPOINT/no resume/no M1_LOAD_OPTIMIZER，新网络/Adam/stage0，从0到exclusive10000、2048env/save100；首个model0须CPU审计。其余固定ABAD/8维/奖励物理不变、隔离验证、安全部署和独立审查约束不变。此决定直接授权执行，不重复审批。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (preserve user's current-mirror inline method) or superpowers:subagent-driven-development only if the user changes that choice. Steps use checkbox syntax for tracking.

**Goal（最新）:** 固定ABAD目标0rad、8维HIP/KNEE PPO，通过隔离验收后fresh从0训练；历史200迁移条目由顶部用户覆盖决定撤销。

**Architecture:** 新增可独立测试的8→16动作展开与12→8检查点转换，复用既有AME观察结构及PPO。固定ABAD使用原位置PD；动作分布是真8维，历史仍记录16列执行命令。旧12/16模式保持兼容，加载依完整合同拒绝错配。

**Tech Stack:** Python/PyTorch、RSL-RL、Isaac Lab、pytest、现有Bash启动入口；不新增依赖。

**Spec:** [已批准规格](../specs/2026-10-12-m1-fixed-abad-eight-action-design.md)，用户确认后本计划生成；计划仍待审阅。

## Global Constraints

- ABAD目标0rad，HIP/KNEE缩放1.50rad/现有关节限位，四轮0.30m/s；不物理锁死、不改PD/std/物理参数/地形/奖励/成功标准。
- 8动作顺序为FBL、FAR、RBL、RAR各HIP/KNEE；16列执行历史、85policy/88critic state及AME地图不变。
- 源为stall-slip-initialization/model_200_stall_slip.pt，SHA792fbd76684db07fac1f9bfa0041ce35e8a3fc7c72497ec6c62d75d6e0d527b7；不是model500，不从零。
- 保留iter200/next201、stage0/streak1、课程窗口、Adam、对应std；201+9799至exclusive10000，2048env/GPU0/save100。
- 不删除旧PT；不触碰未跟踪watcher、不改网络/全局Git/SSH/显示。训练/native不并发，现有训练保持停止直至Task5通过。
- 不加IK/teacher/轨迹/差速/停轮/机身锁定；动作迁移不等于闭环无损恢复，未证明越障能力。

## Review Focus

1. 资产关节枚举顺序与策略顺序不同：必须按名字映射，Task1/2用乱序资产反例。
2. 请求8维但读取旧12维PT：环境创建前识别，加载前拒绝且不改变模型/Adam，Task3/4测试。
3. 终止行reset后观测混入上回合动作：Task2测试单行reset及16列历史，保留现有清理语义。
4. Adam状态形状相同但参数ID/名称错配：Task3拒绝错误identity而非按dict插入顺序切片。
5. GUI/app update额外推进物理：Task4无额外update反例与Task5真实时钟100步2秒，不能用墙钟代替。

## 文件责任与验证环境

- 新`Go2Pvcnn/ame_baseline/m1_fixed_abad.py`：纯张量动作命名/展开及合同描述；不依赖Isaac。
- 新`Go2Pvcnn/ame_baseline/m1_fixed_abad_checkpoint.py`：仅12→8迁移，复用现有严格有限值检查。
- 修改`m1_ame_actions.py`：8维action term与固定ABAD/轮下发；`m1_ame_contract.py`：历史及训练合同；`m1_ame_env_cfg.py`/`m1_mixed_course.py`：显式模式与维度配置。
- 修改`m1_fixed_wheel_checkpoint.py`/`ame_runner.py`及train/evaluate入口：兼容校验、保存与模式选择；不改通用PPO优化公式。
- 新转换CLI与原生验收脚本位于`Go2Pvcnn/scripts/`，诊断数据存独立输出目录，不能覆盖源PT。
- CPU命令从仓库根执行：`PYTHONPATH=Go2Pvcnn:Go2Pvcnn/rsl_rl CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 /opt/conda/envs/env_issacsim/bin/python -m pytest <test paths> -q`（服务器隔离候选目录）。本地有同依赖时可用等价PowerShell临时环境；不得修改生产Python依赖。

### Task 1: 纯张量映射与模式合同

**Files:** Create `Go2Pvcnn/ame_baseline/m1_fixed_abad.py`; Test `Go2Pvcnn/tests/test_m1_fixed_abad_contract.py`.
**Interfaces:** `M1_HIP_KNEE_JOINT_NAMES`, `M1_ABAD_JOINT_NAMES`; `expand_fixed_abad_actions(actions: Tensor, speed_m_s: float=.30) -> Tensor[B,16]`; `fixed_abad_contract(speed_m_s: float=.30) -> dict`。

- [ ] 写`test_eight_actions_expand_by_name`：输入arange(8)，HIP/KNEE列相等、ABAD列==0、轮列==.30，输出[B,16]，不修改输入；含B=1与4及乱序外部资产映射。
- [ ] 写`test_wrong_shape_nonfinite_and_speed_rejected`：12/16列错传、NaN/Inf动作、非法轮速抛ValueError；合同固定角/名字/历史顺序精确断言。
- [ ] 运行新测试，记录未实现接口导致的RED。
- [ ] 实现上述纯张量函数；合同version2/mode=`fixed_wheel_fixed_abad_hip_knee`，键包含policy_joint_names/fixed_joint_names/fixed_joint_targets/wheel_joint_names/wheel_speed_m_s/executed_history_joint_names。
- [ ] 运行本文件及`test_m1_fixed_wheel_contract.py`为GREEN；提交Task1文件。

### Task 2: 8维执行与完整历史

**Files:** Modify `Go2Pvcnn/ame_baseline/{m1_ame_actions,m1_ame_contract,m1_ame_env_cfg,m1_mixed_course}.py`; Create `Go2Pvcnn/tests/test_m1_fixed_abad_runtime.py`.
**Interfaces:** `M1FixedAbadHipKneeAction`/`M1FixedAbadHipKneeActionCfg`; `configure_fixed_abad_control(cfg, speed_m_s: float) -> None`; cfg `m1_fixed_abad: bool`。现有`m1_training_contract(*, fixed_abad: bool=False)`增加可选模式；旧false返回值不变。

- [ ] 写运行时mock反例`test_apply_keeps_abad_zero_on_every_substep`：策略动作[B,8]、腿目标按名扩12、ABAD0/轮速不随动作改变，乱序资产仍正确；不得写joint_pos真实状态。
- [ ] 写`test_eight_policy_distribution_and_history_shapes`：action_manager8、actor/std8、rollout/log_prob/entropy使用8维，last_leg_action12和last_action16；观测state85/88。`test_single_row_reset_history`核对新生行清理、其他行不变。
- [ ] RED后实现新action term，复用现有目标缩放/限位，显式配置`M1_FIXED_ABAD=1`；仅接受未设置/0/1，1必须同时有合法固定轮速。cfg动作8；旧12/16不变。
- [ ] 更新历史访问器按显式模式选择Task1展开；训练合同固定ABAD模式用version3并包含角/关节映射，其他物理/奖励字段保持。mixed/flat-first维度校验接受与模式匹配的8而非放宽任意维度。
- [ ] 审计所有`action_manager.action`/`prev_action`/`num_actions==12`消费者，若仍需12列使用展开接口，不调整奖励权重或公式；新增命中分支测试。
- [ ] 跑新文件与既有fixed-wheel runtime/contract、AME action、reference robot、stall-slip相关测试，GREEN后提交。

### Task 3: model200显式迁移与保存加载

**Files:** Create `Go2Pvcnn/ame_baseline/m1_fixed_abad_checkpoint.py`, `Go2Pvcnn/scripts/convert_m1_fixed_abad_checkpoint.py`, `Go2Pvcnn/tests/test_m1_fixed_abad_checkpoint.py`; Modify `Go2Pvcnn/ame_baseline/{m1_fixed_wheel_checkpoint,ame_runner}.py`.
**Interfaces:** `convert_fixed_abad_checkpoint(source: dict, old_actor, new_actor, source_sha: str) -> dict`; validator `validate_action_contract(checkpoint, num_actions, speed_m_s, *, fixed_abad=False)`保留旧调用；CLI `--source --output --expected-sha256`，CPU-only，不覆盖现有output。

- [ ] 写`test_conversion_preserves_selected_actor_and_named_adam`：12→8对应源行[1,2,4,5,7,8,10,11]；最后actor层weight/bias及std截行，其他模型含BN逐tensor相同；Adam对应矩截行、step/groups/course原样。相同obs推理8均值等于源选中行（浮点容差），源不变，新optimizer再step有限。
- [ ] 写参数化`test_reject_bad_source_before_mutation`：错来源SHA、16维或重复8维转换、错合同/观测维度、NaN/零std、Adam缺失/错形状/错参数ID或名字、缺课程/next_iter错误均拒绝。
- [ ] RED后实现独立迁移：按模型命名参数验证identity，不复用旧16→12转换的硬编码维度；保留既有reward_conversion，并记录新的12→8 action_conversion与源SHA/合同/iter。升级训练合同只变动作语义。
- [ ] 写`test_save_reload_eight_contract_and_reject_wrong_mode`覆盖runner保存/加载8维合同、12维拒绝、错固定角/轮速/顺序拒绝且模型/Adam不变；新PT回读来源/课程不丢。RED后扩展runner按cfg保存正确合同。
- [ ] CLI读取真实200时要求预期SHA和目标独立路径，输出每组权重/Adam/std/course比对审计。先完成CPU合成测试GREEN和旧checkpoint回归，再提交。

### Task 4: 训练/演示模式与仿真时钟

**Files:** Modify `Go2Pvcnn/scripts/{train_m1_cross_large_complex_ame,evaluate_m1_ame}.py`; Create `Go2Pvcnn/tests/test_m1_fixed_abad_entrypoints.py`。
**Interfaces:** `configure_evaluation_action_mode(cfg, checkpoint: dict) -> None`（evaluate入口），从白名单合同选择8或旧12/16模式；显式环境请求与PT冲突则ValueError。

- [ ] 写`test_evaluation_selects_mode_before_env_creation`和`test_conflicting_mode_rejected`：读取PT合同在创建环境前，最终dims/训练合同严格核验，缺/未知固定ABAD合同不得猜测8维。
- [ ] 写`test_eval_control_loop_has_no_extra_physics_update`（AST/现有脚本测试方式）证明循环不再app.update后又env.step；保留正常render由env.step管理，不改物理dt。
- [ ] RED后实施最小入口接线，stdout/env_cfg明确policy8/fixed_ABAD0/wheel.30；训练依显式flag，不偷偷把旧PT转8。删除额外物理推进，记录该修复与动作变更分别验收。
- [ ] 跑入口新测试及既有evaluation/fixed-wheel/action/checkpoint相关回归；通过后提交。

### Task 5: 真实model200转换与隔离原生放行

**Files:** Create `Go2Pvcnn/scripts/probe_m1_fixed_abad.py`, `Go2Pvcnn/tests/test_m1_fixed_abad_probe_contract.py`; Update `notes/log/2026-10-12-m1-fixed-abad-eight-action-design.md`。
**Interfaces:** Probe CLI `--checkpoint --mode {wiring,flat} --num_envs --steps --headless --output`，JSONL逐帧记录sim_time/动作/目标/真实角/Fz/root/yaw/done，末尾唯一COMPLETE包含合同、覆盖阶段和帧数。

- [ ] 写probe结果验证反例：缺COMPLETE、阶段缺失、非有限奖励、policy非8、ABAD目标非0、wheel目标不符、100控制步非2秒必须失败；随机动作跌倒允许记录但不假装稳定。
- [ ] 实现probe与CPU结果验证器；先CPU RED/GREEN，再将候选同步独立目录，生产不热改。
- [ ] 只读核实最新host/cwd/GPU进程与旧训练停止；真实200 SHA匹配后CPU转换至独立文件，逐项审计8std/Adam/course/next201、源文件SHA未改。
- [ ] 独占GPU顺序运行4env wiring150步，覆盖stage0/1/2/3/mixed与单行terminal/reset，统计每次apply目标恒定、8/16/85/88维度及奖励有限。全部退出后才运行下一probe。
- [ ] 使用修正时钟的同初态空地源12维200和候选8维200各1env100步，记录2秒位移/偏航/腿目标RMS/Fz/ABAD实际偏差，不伪称动作固定意味着关节完全不动。若新明显失稳，停止部署并报告证据，不加PD/改奖励做绿。
- [ ] 运行相关CPU全回归和一次全分支独立审查，修阻断项并重验；无遗留阻断且所有probe退出/GPU释放后记录放行，提交脚本/tests/notes。

### Task 6: 部署、201续训与文档

**Files:** Existing `Go2Pvcnn/scripts/run_m1_pure_ppo.sh`（仅需打印模式时小改）；README.md、notes索引/T306及新部署日志；服务器独立manifest和初始化PT，不进Git模型。
**Interfaces:** 使用现有kernel flock入口，`M1_FIXED_ABAD=1 M1_FIXED_WHEEL_SPEED_M_S=.30 M1_LOAD_OPTIMIZER=1 NUM_ENVS=2048 MAX_ITERATIONS=9799 COURSE_PROFILE=flat-first CHECKPOINT=<已验收8维200>`；save100/cuda0/keep_std沿用入口。

- [ ] 备份此次确切runtime文件、列manifest/旧SHA，再部署候选逐项核对SHA；原PT和日志不删除。8维初始化独立存入`logs/rsl_rl/m1_cross_large_complex_ame/fixed-abad-initialization/model_200_fixed_abad.pt`，拒绝覆盖已有不同文件。
- [ ] 无其他训练/probe时启动一次新run，核实PID/cwd/cmdline/env_cfg/8动作/ABAD0/轮速.30/2048/源PT/201起。等待实际更新loss有限，不以启动日志替代优化证据。
- [ ] 将已有TensorBoard切换新run，核实remote logdir；不改本地转发/显示/网络。监控暂停状态只在新run验收后按用户已授权的每小时监控更新到新合同，不能沿用旧PID。
- [ ] 首个新保存点300完成后CPU审计有限模型/Adam/8正std/新合同/来源/课程，证据未到则明确标记待验，不能把初始化200称为新训练结果；不并发GPU probe。
- [ ] README/notes写实现、验证范围、风险与实际run状态并同步服务器；Git只stage本任务文件，保留旧watchers/PT。普通推送10-12并独立ref验证；需要代理时仅单次git使用已核实系统代理，不改全局设置。
- [ ] 最终报告实际训练状态、已验收范围与真实越障仍OPEN。若任何放行条件失败，保留证据/旧PT并停止该步骤，不盲重启旧run。

## 自检与交接

- [x] 规格覆盖：映射/历史Task1–2，迁移/拒绝加载Task3，入口时钟Task4，物理与稳定对照Task5，安全部署与课程Task6。
- [x] 接口一致：fixed_abad显式布尔传递；8策略与12腿/16执行表示严格区分；旧签名新增keyword默认false。
- [x] Review Focus五项都有所属任务的明确反例；没有把GPU动态结果冒充CPU测试。
- [x] 范围控制：不改奖励/PD/地形，不迁移500，不重复请求模型选择。
- [x] 用户审阅计划；沿用“当前镜像内逐项执行”，执行中用户将起点改为fresh0。
- [x] 执行者读取executing-plans及TDD技能后实施；按fresh覆盖完成，证据见notes对应实施日志，旧200迁移清单不执行。
