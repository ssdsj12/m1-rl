# M1 跨障后平地轮速同步：隔离候选设计

状态：用户已同意“保留原跨障阶段，单独修复平地轮速同步”的范围；本具体设计待书面审阅。父节点 T306.6h.6a。当前仅设计，不代表实现、物理通过或允许直接开始 10000 轮。

## 1. 已有证据与目标

- 正式参考 adapter 为 a86cbf5；run12 在 amp/GPU7 单进程完成 8×1600，native0。八个环境均完成 FAR/RAR 有序跨杆落地，但严格仅 4/8，失败项均为四轮全首回合均速差超过 0.08 rad/s。
- 唯一 gain3→0 消融 run13 也完整正常退出。七个完整首回合的尾段目标差分 RMS 从 0.848488 降到 0，但严格降为 1/8，出现后轮提前进入参考终止区域和横向错过跨杆走廊。不能全程关闭 equalizer。
- 根因证据支持瞬时高增益反馈造成目标交替；不证明零增益、任一滤波增益或新同步器一定安全有效。实际速度波动、载荷耦合和均速偏差仍需真实验证。

目标是提出一个只在已完成跨杆落地后的平地生效的同步候选，保留接近、抬轮、过杆及落地前的原始动作和时序。成功仍以冻结的完整首回合严格指标为准，不只看平地片段。

## 2. 方案比较与选择

1. **推荐：跨障后低通测量＋有界差动积分微调。** 没有瞬时比例项；慢速修正四轮相对速度偏差。保留名义平地前轮目标 1.0、后轮 feedforward +0.4，以微调补偿实际载荷差。增加独立逐环境状态，但不触碰跨障控制。
2. 仅在跨障后低通原有 gain3 比例反馈：状态更少，但单纯 P 反馈不能保证消除恒定偏置，当前均速失败未必改善。
3. 重做全程速度、姿态和路径控制：有利于后续通用场景，但会重新影响已验证跨杆链，不属于本次批准范围。

选择 1 做一个可证伪的隔离候选，不扫参、不叠加另一个候选。此版本仅覆盖单个固定横杆后的直行，不是通用地形控制器或 learned policy。

## 3. 实现边界与数据流

从 a86cbf5 正式参考 adapter 新建隔离副本，不复用已拒绝的 gain0 配置。参考目录 `/home/hexinkun/m1`、SDK、正式 AME、原始场景和验收模块均保持只读。

新增纯张量 `post_cross_sync` 状态机；最小接入点为隔离 adapter 的 `MeasuredWrapper._prepare_actions`：

1. 每步仍且仅调用一次原始 `super()._prepare_actions(raw_actions)`，原 prepare/IK 调用计数保持不变。
2. pre-reset recorder 同步向独立观察器提交深拷贝 packet，含 env_id/episode_id/step，按同回合顺序只消费一次。prepare(t)只允许使用本环境、本episode已完成的sample(t−1)所产生的状态；首步或reset后没有旧packet时保持ORIGINAL。重复、缺失、乱序或跨episode packet均拒绝验证。当前动作不能使用执行后才产生的数据。
3. super返回后先独立clone完整原始16列输出，最终动作使用另一份clone，original/final诊断不得共享可变view。未取得资格的环境返回原始16列动作逐元素不变；取得资格后仅替换按名字确认的四轮列12:16，前12列仍等于本次原始输出。
4. 原 `wrapper.step`、env.step、recorder、terminations、metrics 和正常关闭链继续使用，不重新实现它们。

新状态机不读取 `metrics.report()`、最终成功标记、全程均速统计或未来样本。接管判断只消费过去物理样本、原始 phase/wave 信号和独立事件记忆。固定横杆几何是已有 oracle 条件，必须继续标记 controller-assisted，不能声称 policy-only。

新控制状态通过 wrapper 持有；诊断只持有 CPU 拷贝。不得新增全局环境引用、后台线程或绕过既有 owner-release 流程。

## 4. 逐环境接管与 reset 合同

### 4.1 接管前

状态为 ORIGINAL，记录本回合是否见到 phase11，并以独立事件跟踪器记录 FAR/RAR 的 prelift→overbar→passed→touchdown。几何、轮半径、接触限值、有序步骤和边界舍入规则与冻结指标一致，但不读取评测对象；用离线 parity 测试证明一致。

仅当本环境同时满足以下条件，连续 5 个已完成样本后才成为 READY：

- 本回合已见 phase11，双轮有序 touchdown 均完成；不能只使用 `phase==-1` 或 `wave_gate=false`。
- 原始 wave_gate=false，原始 prepared leg actions 全零。
- FAR/RAR 当前轮心 x≥0.9759m，|z−0.0959|≤0.005m，generic ground-contact force>1N。
- root x>原配置 `wave_disable_obstacle_after_root_x=1.15m`，明确退出原 wheel-target 障碍分支（等于1.15时原mask仍保留障碍gate，不准接管）；height∈[0.53,0.61]m，tilt≤0.45rad；无 reference_collision、own-bar contact>1N、termination 或 timeout；全部输入 finite。

下一次 prepare 才可切换。5 样本为新增接管稳定条件，不改变任何正式验收门槛。额外 height/tilt 条件可能把首次接管继续推迟；日志需给每项原因。

只用 phase11＋当前落地条件会错误放行 run13 env2/5，所以独立有序事件历史不可省略。原始起点 phase=-1、wave=false 不得放行。run12 完整gate（含height/tilt/root条件）离线重放，首可接管 action 为 [249,253,248,251,245,248,248,247]；保留前缀对1600样本轮均速差的最大贡献为0.02084732rad/s，小于0.08，但这只是尾段若能同步时的代数空间，不是成功保证。

### 4.2 接管后

进入 SYNC 后不因 phase11→-1 或正常接触抖动反复切回。积分的支撑/姿态谓词明确为：最近同回合样本中FAR/RAR仍满足§4.1杆后接地条件、root x>1.15、height∈[0.53,0.61]、tilt≤0.45、无reference/bar接触或结束标记。慢积分只在该谓词为真且该环境上一周期四轮均未限速/物理限幅时更新，否则暂停积分并保留有界状态；不得一台env受限而冻结整批。滤波仍更新，输出仍限速。

若原控制器重新进入 wave、产生非零腿动作、不允许前进，或当前root x≤1.15，则该单横杆候选的适用条件失效：在施加新覆盖动作前记录明确原因，拒绝该次验证并走既有正常清理，不静默抢夺新的跨障动作、不发强杀信号、不自动重试。非 finite 输入或状态同样明确失败。

正常 episode termination/timeout 仍由原环境处理；pre-reset 样本先记录完整旧状态，但结束样本不得新授予资格。明确的逐环境 reset 通知只清该环境的新事件、phase11记忆、资格计数、滤波、积分、上一输出和接管标志，同时使pending packet、上次实际action快照及消费标记失效。通过recorder的post-reset回调覆盖直接/局部env reset，并推进episode代号；wrapper done仅在本步缺少对应回调确认时兜底，不对已确认reset重复推进episode。显式wrapper.reset也使用同一幂等机制清全部新增状态。构造时观察器未绑定的首次reset不得访问未初始化状态。episode计数意外回退且未见reset通知时fail closed，不拿计数启发式替代明确通知。失败回合永久污染该次严格评测，不因后续新回合重新接管而洗白。

## 5. 平地同步候选的固定参数与公式

仅接受当前合同：dt=0.02s，轮顺序FAR/FBL/RAR/RBL，方向全+1，原始策略残差全零，flat base前后均1.0，rear feedforward=0.4。轮动作项必须为JointVelocityAction、scale=1、实际offset=0、preserve_order=true，映射到对应FOOT_JOINT；live default_joint_vel也须全零（配置use_default_offset=true，不能只检查配置offset=0）。物理轮速上限20rad/s、隐式驱动damping30/stiffness0与基线相同。接管前同时验证配置和实际动作项/关节映射，合同不符则拒绝启动，不混用action单位与rad/s。

符号 v 为四轮带方向实测速率；名义目标 u_ff=[1,1,1.4,1.4] rad/s。新微调 b 为四维零均值向量，初值 0。

- 测量滤波：v_f←v_f+α(v−v_f)，τ=0.20s，α=1−exp(−dt/τ)。首次接管以当前实测速率初始化，不从零制造误差。
- 差动误差：e=mean(v_f)−v_f。只调相对速度，不从位置、评测均值或目标通过率构造误差。
- 积分候选：b_raw=b+K_i·dt·e，K_i=0.5 s⁻¹；不加瞬时比例项。
- 有界投影：先减 b_raw 的四轮均值，再以同一个比例缩放到 max(abs(b))≤1.0 rad/s。投影后的 b 才是下一步积分状态，不藏未限幅积分。
- 稳态请求：u_des=u_ff+b。范围自然在 [0,2.4]rad/s；名义四轮平均请求保持 1.2rad/s，微调零和。不能说这保证实际平均速度不变。
- 接管首个输出独立复制上一个物理packet中实际`action_manager.action[:,12:16]`，不取当前super重新生成的原目标；积分暂不更新且设置上一周期hold标记。之后每轮相邻输出变化≤1.0·dt=0.02rad/s，朝u_des移动。限速过渡暂时不保证输出零均值微调；上一周期hold、任一轮限速或物理限幅时暂停该env积分。输出始终维持原forward-only和物理速度上限。

更新次序固定：检查packet/合同→读取当前v并更新v_f→用上一次限速/hold标记及最近支撑谓词决定积分→零均值有界投影→计算u_des→逐轮限速/安全边界→保存新标记和输出。接管首步单独只初始化并hold；不得用本次更新出的限速结果循环重算积分。reset全部相关状态，禁止遗留上回合previous output。

以上数值是一次预先固定的慢速候选，不是通过真实试验证明的稳定增益。CPU 简化被控对象测试只证明公式/边界，不替代 Isaac 物理验证。失败后回到原因分析，不在同一次批准内改 Ki、τ、feedforward 或阈值重跑。

## 6. 必须记录的证据

保持原 `samples_*.npz`、strict report 和外部 native-exit finalizer 不变。另存 `sync_*.npz`，每环境每步包括：episode代号、当前状态、首次接管步、独立事件时刻、资格计数/原因、original wheel action、最终 wheel action、v/v_f、e/b、限幅与限速标记、暂停积分原因。

配置与 provenance 明确记录候选名称 `post_cross_sync_v1`、所有固定参数及新增控制器文件哈希；不能靠“原 reference 绑定相同”冒充输出未改。action-manager实际动作必须与记录的最终输出相等，并验证物理processed轮速target的单位/方向。非接管环境及所有腿列的diff必须为零。

原report.json和native/strict finalizer完全不改。独立CPU离线验收生成`sync_verdict.json`，`accepted = original_report.passed AND sync_checks_passed`；缺失、重复、错episode/步号、不完整sync证据一律拒绝。独立验收命令仅accepted时exit0，其余exit3；原wrapper/native真实退出码原样保留，不能因原strict0忽略新增合同失败，也不能把新增验收失败叫Isaac崩溃。

## 7. 测试与唯一一次物理验证

实现前先写失败测试：

1. ORIGINAL 状态完整动作 bitwise parity；一次 prepare/IK；异步环境不同阶段不串状态；禁止临时改共享 cfg gain。
2. 初始 phase=-1、phase5 wavefalse、phase11后瞬态、缺 prelift/overbar、已终止、前/后reset顺序、连续条件中断等 gate 测试。
3. run12 原始数据离线识别所有八环境的合法接管点；run13 env1/2/5 永不放行首回合。新 gate 不依赖 report 或 evaluator 实例。
4. 四轮相等无差动积分；有恒定差动偏差时方向正确；投影零和/有界；非 finite 拒绝；接管首输出连续、每步限速、anti-windup、局部/全部 reset。
5. 简化无延迟/一拍延迟单位响应加固定扰动的 CPU 回归；若已发散、不能收敛或出现持续两拍交替，不运行 Isaac。不得从该测试外推真实机械稳定性。
6. 隔离副本全量既有 CPU 回归、bash 语法与独立规格/质量审查。指标、正常关闭、场景、来源 guard 不得退化。

以上通过后，仅执行 **amp / 物理 GPU7 / 8env ×1600steps 一次**，全新唯一目录，无自动重启或恢复。新控制不在前32步生效，所以不把单独32步 smoke 当成新同步器的物理验收。

物理成功需同时满足：

- 单进程 exact1600、全部必要采样、正常 cleanup+native0、无测量/结束错误。
- 原冻结完整首回合严格8/8，包括均速差≤0.08rad/s、全部跨杆事件、接触、姿态、高度、前进、无reset等；不得缩短分母或仅选尾段。
- 八环境均实际进入新同步状态；接管前完整动作/物理轨迹与相同基线条件对照，腿输出每步等于原控制器本步输出。物理前缀差异按字段报告；任何事件顺序退化或无法解释的前缀分歧都不推广。
- 原始基线源、场景、初始随机化一致；额外元数据只说明受控输出替换。
- 对每个env分别在tail800=steps800..1599，对四轮及799个窗口内相邻差分计算实际wheel-target差分RMS≤0.05rad/s；禁止跨env池化掩盖失败。该阈值弱于新输出逐步0.02限速，主要验证接线/记录，不是额外物理稳定性证明。报告实际轮速差分、轮均值、偏置饱和比例及位移，不能只凭平滑目标宣告物理同步成功。

失败保留证据并结束此候选；不直接推广、不追加扫参、不扩大1024、不启动10000。即使本次通过，仍需原计划剩余严格重复、1024容量/行为门槛及独立 AME 接入；不能把控制器oracle通过当成策略已学会跨越/大绕行。

## 8. 资源、安全与交付

GPU7唯一目标。原15GiB占位若8env仍能容纳则保留；必要时仅在重新核验 PID/用户/脚本后停止用户已授权的占位，计算进程结束后按授权恢复。不得停止别人的任务或转GPU4。

交付包含隔离候选、RED/GREEN证据、独立审查、run14原始记录/严格报告及新旧对照、todo/branch/log/index同步。正式参考、SDK、AME和阈值不变。本设计未解决 AME 生命周期接入、物理动作桥、learned crossing 或大障碍绕行。

## 9. 设计工作清单

- [x] 读取入口、当前笔记、run12/13证据和动作/reset源码。
- [x] 用户同意保留跨障、只改跨障后平地的范围；视觉展示不适用。
- [x] 比较三种路线，给出单个固定候选及失败边界。
- [x] 写出组件、输入输出、逐环境时序、错误处理与验证合同。
- [x] 规格自审及独立只读边界审查；4项修订后复审PASS，仅代表设计。
- [ ] 用户审阅本文件的具体参数、接管/reset和验收合同。
- [ ] 用户审阅通过后，使用 writing-plans 编写实施计划；此前不实现或启动仿真。

相关证据：[gain消融](../../../notes/log/2026-09-18-m1-wheel-equalizer-ab.md)、[run12](../../../notes/log/2026-09-18-m1-reference-strict-run12.md)、[T306](../../../notes/todo/T306-m1-ame-long-train-stability.md)。
