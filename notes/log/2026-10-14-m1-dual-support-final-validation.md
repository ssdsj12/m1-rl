# 双几何与跨后恢复最终冻结验证

## 2026-10-14T06:24:16Z 用户改为实际跨越优先

用户要求在实际跨越中发现问题再修正，不再让前置验证占据主要时间。已确认服务器无训练/回放任务、GPU0仅1MiB，probe SHA仍为冻结02a70cf；直接启动 `first-obstacle`、4环境、1000步上限的10cm诊断，runner PID222721，输出 `evidence-first-obstacle-direct-02a70cf`。不另跑准备关或全套CPU回归。已知callback时钟量化只影响结果证据验收，不修改动作控制；本次可观察实际抬落与接触，但不据此宣称正式A通过或启动BC/PPO。生产、物理参数、奖励与控制源码均未变。下文NOT_RUN/停止状态是本次启动前的历史快照。

- Stage/Todo：T306/teacher-feasibility/dual-support-selection + crossing-recovery-outcome。
- Baseline Ref：abfdf0e52618b0e8aac8e55823374a82de05a03d。
- Candidate Ref：02a70cfcf0a9c16101f581c60f5193b1a17728a8。
- 目的：独立整分支审查修复后，对同一冻结源码完成全部相关CPU回归，再按原计划串行原生门禁；不得将CPU证据当作10cm能力。
- 主机：root@a21506654554025984756592；候选：/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn；生产未修改。
- 实施/审查：[实施记录](2026-10-14-m1-dual-support-crossing-recovery-implementation.md)。

## CPU条件与命令

### 第二轮实际结果：原切换卡点解除，支撑轮位移仍阻挡抬腿

`evidence-first-obstacle-capture-bridge-v1` 正常退出0/GPU0回到1MiB。4行均记录106帧，3行锁定失败、env0因同批失败被诊断中断（不能把env0计成功或失败锁定）。均未进入LIFT，没有记录到碰撞/物理失败；A仍FAILED_DIAGNOSTIC。此前frame41的capture事务这次通过，env1在frame97首次由支撑候选筛选拒绝，而非旧执行连续性拒绝；frame101达5次锁定。env0仍reference_valid、body_age24，未ready。

env1输入frame95→96的同快照CPU几何复算（非完整回放/非成功验收）：全部125格点中对实测三角形的最大裕量从.0108301844降到.0086895609m，均在x=-.04/y=-.06边界；此时两后轮相对固定锚点X分别-.0478058/-.0355492m。原生选择从candidate0有效变成-1无解，与此几何复算一致。已定位当前下一卡点为支撑调整期间实测轮位移导致批准包络内无可行三轮重心目标；没有将其误说成抬腿后摔倒。未扩大包络或降低支撑门槛，未动PD/奖励/物理/生产，未开BC/PPO。候选衔接改动及反例本地保留未提交；仅68针对性测试，不冒称新全套通过。后续应针对实际支撑位移查因并修正，不重回大批前置验收循环。

两次探针原始trace/video/result/source/log/exit已归档到本地 `.superpowers/sdd/2026-10-14-m1-dual-support-crossing-recovery/direct-crossing/`。第一轮归档SHA256 `97632d61838e2be4199a83584792f17db28bd684dadc622a7c4093f6880c341d`。

### 实际10cm诊断首轮与最小切换修正（2026-10-14T06:30Z）

`evidence-first-obstacle-direct-02a70cf` 已完整退出0，4条完整诊断各79帧，均在APPROACH→BALANCE后IK_INVALID锁定，未进入LIFT，无碰撞/物理失败；不是成功样本。首次无效为输出frame41（输入40）：已选出candidate50/101，env0双几何margin=.023281m，env1=.019114m；但回退8次均不能满足执行连续性。根因定位在制动capture把accepted替换为measured：实际HIP约.423rad而上一目标约.309rad，差.114rad超过每步.05rad，beta趋0仍从实测姿态出发，不能消除此差。四轮仍承重，此处不是摔倒。

最小候选修正只保留原accepted作为插值起点，实测世界支撑锚点仍一次捕获且固定；branch用实测q，tracking重新实测，不放宽限速/IK/支撑/碰撞规则。新增 `test_braking_capture_bridges_loaded_pose_without_target_jump` 在旧代码断言reference_valid失败，修后reference_commit+feedback_transaction共68通过（15.79s）。未跑全套/未宣称完成；已立即串行复跑同一10cm第一障碍，输出 `evidence-first-obstacle-capture-bridge-v1`，runner223920，启动06:30:13Z。Teacher源SHA `dfc9358dacb2384ba62bd6002038f7dc88a1afe84ad49a428383ce5928f745ec`。生产/训练未改，时钟验收问题仍OPEN。

工作目录为上述候选，Python /opt/conda/envs/env_issacsim/bin/python；torch2.7.0+cu128/pytest9.0.3。CUDA_VISIBLE_DEVICES为空，OMP_NUM_THREADS=1、MKL_NUM_THREADS=1均仅进程级。

全量14文件收集532个node；分组530+1+1的排序node并集与全量cmp一致，两个慢测试各保留完整200回合分母。各组独立basetemp，运行期间不修改源码/测试。

```sh
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest tests/test_m1_teacher_pose.py tests/test_m1_reference_teacher.py tests/test_m1_teacher_ik.py tests/test_m1_teacher_reference_validity.py tests/test_m1_teacher_reference_commit.py tests/test_m1_teacher_feedback_transaction.py tests/test_m1_teacher_feedback_evidence.py tests/test_m1_teacher_replay_backend.py tests/test_m1_teacher_geometry_replay.py tests/test_m1_teacher_selection_evidence.py tests/test_m1_crossing_recovery.py tests/test_m1_teacher_recovery_evidence.py tests/test_m1_teacher_recovery_lifecycle.py tests/test_m1_teacher_probe_contract.py -q -k "not suite_requires_unique_20_per_seed_and_both_stages and not failed_early_attempt_stays_in_fixed_200_episode_denominator" --basetemp /tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn/validation-final-02a70cf/fast-temp

env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest tests/test_m1_teacher_probe_contract.py::test_suite_requires_unique_20_per_seed_and_both_stages -q --basetemp /tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn/validation-final-02a70cf/slow-a-temp

env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest tests/test_m1_teacher_probe_contract.py::test_failed_early_attempt_stays_in_fixed_200_episode_denominator -q --basetemp /tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn/validation-final-02a70cf/slow-b-temp
```

远端日志与退出码：validation-final-02a70cf/{fast,slow-a,slow-b}.{log,exit}；全量/分组收集及union.nodes同目录。持久任务shell PID160634/160635/160636，测试Python PID160639/160637/160638。

- fast：530 passed, 2 deselected in391.07s，exit0。
- slow-b（失败回合保留固定200分母）：1 passed in374.81s，exit0。
- slow-a（唯一seed/episode及双stage完整集合）：1 passed in1108.76s，exit0。

05:50UTC三组完整退出，532/532相关CPU通过；启动原生前再次核对三组exit0、节点并集、无pytest/train/play/probe以及GPU1MiB，探针/监视器SHA不变。此为相关套件通过，不是全库通过。

全仓库pytest收集存在已知两处环境/收集阻塞：pxr缺失和同名test_m1_teacher_obstacle_hold.py冲突。本轮不安装依赖或改无关测试，不能声称全库通过。

## 冻结清单

以下10个改动文件本地与远端逐SHA相同：

| 文件 | SHA256 |
| --- | --- |
| Go2Pvcnn/ame_baseline/m1_crossing_recovery.py | c498338afa84839df0c999ee287f66a4f751bdc36b0f7ce526f3a798aa5e8bea |
| Go2Pvcnn/ame_baseline/m1_reference_teacher.py | 6c3195493b865fb64937c68492582c8ea922cfe8ababdfbc4d387d7568ef082e |
| Go2Pvcnn/ame_baseline/m1_teacher_pose.py | 5feb2dc9e799225f77f8603afb87da1c7e720b55c58d86f81532a1fa38e3b37e |
| Go2Pvcnn/scripts/probe_m1_teacher.py | 6f26b34a6a8e89cba809b9a2e9e53abb72b7bc4c1b6ce406b1896bb614abd2c7 |
| Go2Pvcnn/tests/test_m1_crossing_recovery.py | fc66b65c18103413611d5dbb409b43cd171edf60648ad858f4fb5d79ff057f3d |
| Go2Pvcnn/tests/test_m1_teacher_pose.py | ed9165f8040cc95b848302949028e2f680a9c00433173cedfb2836662dd746d7 |
| Go2Pvcnn/tests/test_m1_teacher_probe_contract.py | 69427386cf54b757809e94c27c123a44cd6426ac344737a70e61691effe34bea |
| Go2Pvcnn/tests/test_m1_teacher_recovery_evidence.py | c664cb6ec26406a6c7000e584edd292d32982d708d9e5ae7d1659e72a78b5d1c |
| Go2Pvcnn/tests/test_m1_teacher_recovery_lifecycle.py | 1a39a31c6f9d1b0e298562675a233e19666cad6dae1f9138aca80b9ee9153316 |
| Go2Pvcnn/tests/test_m1_teacher_selection_evidence.py | b5b8e9805d574d4371b34d2fedfe259158188144bf6c61e68fff0c5b48101591 |

## 原生门禁

05:51UTC启动第一关控制合同，runner PID221381；输出evidence-contract-02a70cf，日志与.exit在候选同级。独占flock /tmp/m1-teacher-bounded-feedback-native.lock；CUDA0、候选及六个Isaac源码根目录仅本命令PYTHONPATH。尚无原生通过结论。后续依次四轮准备、独立单轮、首障碍、衔接、完整课程、正式A；任一关键失败停止后续并标记NOT_RUN，不改参数/包络/门槛，不启动BC/PPO。

05:47UTC只读预检：实际hostname szu-a21506654554025984756592；GPU0 RTX4090为1MiB/24564MiB；无train/play/probe Python；Python实际为env_issacsim/bin/python3.10，六个Isaac源码根目录均存在。USD SHA43cb116ba2a081a3a215d45fb2796895df9d8b201cd5c26bc311cbd5f005e648与本地一致。该快照不是GPU持续空闲保证。

控制合同exit0，result.native_contract=true（milestone_a仍NOT_RUN）；flat100控制步elapsed1.9999999552965164秒，四行advance均.5711593627929688m；碰撞检查passed/errors空；视频warmup非黑、单机器人可见性及物理时间不变均通过。进程退出，GPU回到1MiB。实际导入140个source模块路径均在隔离candidate且SHA逐项匹配本地。地面MDL材质缺失产生警告/错误日志，但可见性检查和控制合同已通过；该渲染告警保留，不冒充物理异常或跨越成功。

准备关使用独立evidence-flat-preparation-02a70cf，--mode teacher --teacher-scope flat-preparation --diagnostic-steps 1000；启动前再次确认无pytest/train/play/probe及GPU1MiB。待实际四轮记录和结束结果。

## 原生停止：physics-callback-clock-quantization OPEN

准备关发现关键时间证据错误后，核实runner221853/Python221855的cmdline和candidate cwd，对唯一自身探针发送SIGINT。进程退出、GPU回到1MiB，无train/play/probe/pytest残留。Isaac处理信号后shell exit0，但没有result.json/imported_modules.json/完成episode JSON，故明确为**主动中断的部分证据，不是准备关通过**。

四个env各91帧，首帧incomplete_scope，第2–91帧各90次invalid_interval（共360/364样本）；首两时间为2.269999949261546、2.2899999488145113，实际差0.019999999552965164，而control_dt_s为0.02，差-4.470348362317633e-10。四个实际physics substeps均有write_seen/physics_seen，时间每次增加0.004999999888241291，恰为float32(.005)；4倍精确等于观测控制间隔。

来源链：IsaacSim simulation_context.py:1339订阅physics事件，:1361以callback step_size累加_current_time；NativeProbe.sample取该current_time，却以env.step_dt配置值记录dt；结果监视器按float64 eps比较delta与dt。此前实际sample CPU测试仍人为设置current_time=start+step*.02，因此没有覆盖真实PhysX callback量化。**根因是时间源/精度合同不一致，不是本次观察证明Teacher摔倒或跨越失败。**

env0第91帧scope_observation_complete=true仅是当前活动轮局部准备信号；另外三行false，且中断前没有完整审计episode。不能称四轮准备通过，也不能根据短记录声称原物理问题已修好。原地面材质告警与本时间差分开记录。

15个实测区间为.29999999329447746秒，故仅替换dt为相邻差仍不足以完整解决0.3秒表示/精度合同；更不能用相邻差自证而漏检缺失控制步。下一轮需明确绑定物理回调步数及其原始精度，覆盖真实量化时钟、15区间/14区间、缺帧和大绝对时钟，再审查和重新完整验证。当前不修改runtime、不放宽物理/支撑门槛。

| 门禁 | 本轮结果 |
| --- | --- |
| 相关CPU532项 | PASS，冻结02a70cf |
| 控制合同/空地/碰撞/终止/相机 | PASS；exit0、140模块SHA匹配、GPU释放 |
| 四轮准备 | BLOCKED，时间证据错误，主动中断/部分记录 |
| 四个单轮抬落、首障碍、衔接、课程、正式A | NOT_RUN |
| BC/PPO、生产部署 | NOT_RUN/未修改 |

原生两关完整现有文件已归档于validation-final-02a70cf/native-gates-02a70cf.tgz，SHA256=64f0905980f0a3d7c75dcf77279cb36950f1c2f95b8c46c24b7e17ac3f5ac6aa；本地同SHA副本与解包位于本工作树.superpowers/sdd/2026-10-14-m1-dual-support-crossing-recovery/，不覆盖原始文件、不删除历史证据。

## 过程裁定及代价

1. 应用worktree工具不能解析子仓库ref，改用已忽略的手工worktree；代价：应用附件不可用，Git工作树保留可恢复。
2. 各实现任务串行，避免共享索引和探针冲突；代价：执行时间增加。
3. Task1连同Teacher必填参数调用点机械迁移；代价：Task1审查面略扩大，生产证据仍归Task2。
4. 本地缺torch，CPU测试用已核实的远端隔离环境；代价：网络延迟，不能称本地或GPU验证。
5. reset明确消费选中行子批，long按给定顺序、bool按true顺序；代价：调用者必须显式构造子批。
6. CPU测试仅进程级OMP/MKL单线程；代价：与默认线程调度不同，不推断GPU等价。
7. 结果监视器精确提升实测float32为float64，保留double时钟并一次归一化固定方向；代价：结果计算dtype不同于源张量，须显式记录/重放，Teacher不变。
8. Task4最小扩展纯监视器所有权，修复大绝对时钟的表示舍入；代价：跨任务审查面增加，容差仍限8eps与dt/10000，不补缺帧。
9. 最终完整套件集中到所有审查修复后的冻结版本；代价：集成故障较晚显现，因此必须在native之前完成。断线/停止的旧部分运行不计通过。
10. 最终14文件分三组、独立basetemp、节点并集精确核对；代价：跨组同进程顺序相互影响未测，不冒充全库验证。
11. 原生沿用已核实的--enable_cameras以获取真实视频；计划中的COMPLETE按实际程序result/原始产物/退出码和GPU释放核验，因为程序没有该字面输出。代价：启用渲染增加资源/启动时间，不能只凭日志标记判通过；未改控制和物理参数。
