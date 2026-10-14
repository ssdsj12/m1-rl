# Teacher 显式后端复核与后续原生验证

## 授权及边界

用户已确认前一轮提出的最小有界修复：只修数学复核后端，保持控制器、物理标准和逐位执行核验，之后继续准备、抬落腿及10cm跨越验证；不启动训练。

- Stage / Todo：[T306](../todo/T306-m1-ame-long-train-stability.md) / bounded-feedback / native-verifier。
- 前置证据：[同GPU冻结记录复核](2026-10-14-m1-feedback-gpu-replay-diagnosis.md)，211/211通过，原28文件不变。
- Baseline Ref：`efd38c846896d167c67b377c573235aef063f481`；控制器runtime：`39a659032239cdb87edf096b4efe1231d58b142a`。分支`10-13`，未创建新日期分支。
- 只允许修改probe及其直接测试；不改Teacher/IK/PD/碰撞费用/20s/COM和支撑门槛，不写生产，不删旧PT或轨迹。
- 执行顺序：TDD负例→最小修复→窄范围独立审查→冻结记录复算→新目录串行原生合同/准备/抬落/跨越；首关键失败停，不自动调参重试。

## 当前进度

原实现子代理负责probe/tests修复与CPU测试；主代理保留原生独占执行权。旧SDD资料已完整归档在仓库外`.native-probe-artifacts/m1-feedback-v3-20261013/sdd-archive`，不重复执行旧计划实现。

## 实现与独立验证（2026-10-14 UTC）

- 已提交 `de46186424e0db220f6a1236f32c8f68559ac1bf`，仅probe及直接测试三个文件；Teacher/IK/反馈/adapter源码SHA保持不变。
- trusted caller显式指定复核backend；native严格核验record/sample的producer设备、Torch/CUDA及数学模式来源，不允许缺失、错配或CPU fallback。纯复算使用局部device context，缓存包含backend，不改全局数学模式或真实执行路径。
- 原数值容差和request/process/四次apply精确核验未改变。历史无metadata的CPU测试默认兼容，native没有兼容旁路。
- TDD旧实现负例8失败/1通过；修正测试夹具后另一个metadata错配负例独立RED。最终相关四文件76通过、补充probe gates 10通过、backend最终19通过。全库仅收集：3080项、2错误（缺pxr及候选根目录同名测试冲突），不声称全库通过。
- 独立审查无新增Critical/Important/Minor；继承的abort深层输入审计待办不因此关闭。
- 主代理独立GPU验证：旧211条冻结记录在内存附加当前可信GPU metadata后复算通过，仅作为迁移测试，不能追认证明旧记录原生来源；28原文件未改。新生成CUDA Teacher事务通过，动作/执行回执/诊断关节/错设备/缺metadata五类反例均被拒绝。

## 原生 v4

- `m1-feedback-contract-v4` exit0，`native_contract=true`；100控制步=1.999999955秒，四行各推进0.571159363米，flat与collision passed，errors空。进程退出且GPU恢复1MiB后才启动下一scope。
- `m1-feedback-flat-v4` 已串行完成wheel0的1000控制步；env0于49帧完成局部准备，其余三行到20s仍没有ready，末帧实测COM余量0.009598189m（不足0.010m）。完整证据复核结束/exit0，进程520103已退出、GPU0恢复1MiB/0%；尚未抬腿/跨越，Teacher A仍BLOCKED，BC/PPO未启动。
- 所有结果在候选目录新v4路径，未覆盖旧v3失败证据，未写生产。

### 最终物理窗口及逐记录审计

主代理用标准库独立读取四个保存record与原始trace/video SHA：共3049帧（49+1000×3），四条verification errors均空，request匹配/逐样本backend来源一致，八个trace/video SHA均匹配。无collision/support_lost/penetration/failure/failure_locked/measured_local_lift_seen事件。

env0实际局部准备完成保留于49帧的scope_observation_complete；批次停止收尾将其record.end从scope_observed改标diagnostic_interrupted，不能把局部准备当完整回合或跨越成功。env1自然timeout在1000帧结束，env2/3同样走满1000帧且timeout=true，batch归类diagnostic_interrupted。三行全程ready为0，末帧及最大实测COM余量均9.598189mm，不足10mm；预测最大11.161624mm。绝对sim_time22.2499995包含此前合同步，当前回合1000×.02=20s，未延长。

最终batch为`FAILED_DIAGNOSTIC`，stop定位env1/episode0/frame1000，reason=`diagnostic_goal_unmet`、physical_failure=false、errors=[]。四record仅1个complete_episode（env1自然结束），并非四个正式独立完整回合；flat_success/stage3_success均0。wheel1/2/3的准备NOT_RUN；单轮抬落、10cm跨越、完整课程及200回合正式验收均未跑。无自动调参/延长窗口/继续下一scope。

主代理最终只读审计保存在仓库外`.native-probe-artifacts/m1-feedback-v4-20261014/completed-audit.json`，env0/env1录像已取回同目录。下一步只读隔离真实支撑轮位移、COM与参考不一致的动力学来源，再提出有界控制修订；需新修订授权，不擅自放宽10mm或20s。

## 进行中的只读物理对照（非完成结论）

独立子代理读取v4原始JSONL；四行当前均为wheel0，不是四种目标腿。env1/2/3共同前292帧的action/processed/applied/joints/Fz逐位相同，不能当三个独立实验。

| 行/帧 | 实测COM余量mm | 预测COM余量mm | 物理root误差范数mm | ready |
|---|---:|---:|---:|---:|
| env0/49 | 12.806701 | 13.099260 | 7.403293 | 1 |
| env1/49 | 5.717083 | 10.868201 | 7.659564 | 0 |
| env1/180 | 0.587622 | 10.725421 | 6.163557 | 0 |
| env1/426 | 3.808841 | 10.816877 | 1.947529 | 0 |

- env0第40帧input ready但output速度0.05363955m/s超过0.05，只有44–49完成连续六帧；49的record errors空/end=scope_observed，但success=false且不可BC。
- env1第180帧三支撑轮载荷106.05484/114.31419/84.17935N，input线速度0.00276542m/s、角速度0.00292676rad/s；姿态/root跟踪达标，真实COM余量明确不达10mm。freeze_reason8是PREPARATION，不是TRACKING或反馈完全冻结。
- 四行第1帧可见输入、动作和actuation数值一致，env0与env1第2帧落地后的物理量首先分歧，当时目标还一致，第3帧命令才分歧；不代表隐藏接触/solver状态已证明一致，差异起点早于active PI。
- env1第180帧真实支撑轮相对参考锚点XY偏差22.760/62.986/43.372mm。49→180的余量下降5.129484mm可作几何分解：只换COM下降3.348873mm，再换三角形下降1.780611mm；不是动力学因果证明。
- env1第405帧起Z积分限幅；426帧I_z=0.009990056、O_z=0.010722210m，无输出或轮速余量限幅。root接近参考不保证真实支撑三角形和COM余量符合预测。至390帧reference有效、request匹配、computed/applied effort相同，无effort裁剪；正确关节映射下49/180/292帧最大关节跟踪误差0.065089/0.091136/0.098351rad。
- 可支持“真实支撑几何跟随不足，root补偿不足以保证实际COM”的线索；接触/solver起因、PD误差与轮位移因果尚未隔离。本次不调PD、参考或门槛。

## 发布

实现已普通push，独立ls-remote确认`10-13=de46186424e0db220f6a1236f32c8f68559ac1bf`；当前追加运行记录尚未提交。
