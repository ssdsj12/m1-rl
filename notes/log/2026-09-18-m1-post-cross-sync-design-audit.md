# M1 跨障后轮同步设计与只读审计

## Purpose / Stage / Todo

T306.6h.6a，承接 [gain0消融失败](2026-09-18-m1-wheel-equalizer-ab.md)。用户回复“是”，同意保留原跨障阶段、单独处理平地同步的范围。本轮产出 [具体设计](../../docs/superpowers/specs/2026-09-18-m1-post-cross-wheel-sync-design.md)，不是实现或仿真。

## Input / Procedure

读取正式 adapter a86cbf5 的 runtime/run/metrics、只读 reference wrapper 的动作组装/phase/reset、contact-free cfg，以及已安装 IsaacLab45 的 RecorderTerm/RecorderManager/环境 reset 调用点。独立子代理只读审计事件与插入边界；主线程另用 NumPy 对 run12 原始50个NPZ重算完整接管条件。没有启动 Isaac、CUDA workload、改SDK或发送进程信号。

数据源：run_logs/m1_reference_validation/20260918_gpu7_8x1600_12_normal_clone 和 20260918_gpu7_8x1600_13_equalizer_off。轮序 FAR/FBL/RAR/RBL。全条件包括：同回合phase11记忆、双轮有序touchdown、wavefalse、腿动作全零、当前杆后ground-contact、root>1.15、height/tilt、无contact/termination/timeout、连续5samples。严格指标不变。初次离线筛选用≥1.15，但命中的root均>1.402m；改正严格>边界不改变下表。

## Source findings

- `instrument_reference_wrapper` 的 subclass `_prepare_actions` 是最小边界：只调用一次原prepare，再只替换 eligible 环境轮列。不能临时改共享 cfg gain 或调用两次 prepare。
- phase11短暂；起点与跨障后都可phase=-1。m1_wave_gate 是leg gate，phase5也可能false，不能单独用于接管。
- 原 wheel-target 障碍分支还有root-disable边界1.15m；源码保留root≤1.15时的gate，因此设计必须是严格>，已由独立审查发现并由主线程源码确认修正。
- 独立有序事件观察器必须保留：run13 env2/5虽在action185可满足“见过phase11＋当前杆后接地”，却从未合法RARoverbar。缺事件链会错误接管。
- RecorderTerm.record_post_reset(env_ids) 为已有接口；ManagerBasedRLEnv自动reset及ManagerBasedEnv显式reset均调用。可作为逐环境清状态来源，wrapper done为幂等兜底；不能只看episode_length_buf下降猜reset。
- 不读取 evaluator/report/累计均速控制动作。事件观察器与指标各自拥有状态，CPUparity仅检查几何/时序相同。

## Offline metrics

独立审计先计算基本gate，主线程加入height/tilt/contact/root完整草案条件复算，首接管点一致：

| env | 首可接管action（0-based） | 保留前缀对1600轮均速差贡献 rad/s |
| --- | ---: | ---: |
| 0 | 249 | .004791827 |
| 1 | 253 | .018531829 |
| 2 | 248 | .009186261 |
| 3 | 251 | .006015592 |
| 4 | 245 | .008286467 |
| 5 | 248 | .014292032 |
| 6 | 248 | .006727525 |
| 7 | 247 | .020847319 |

贡献定义为 `ptp(sum(wheel_velocity[:first_override],axis=0))/1600`。若之后四轮均速完全一致，前缀最大贡献0.020847319仍小于冻结0.08门槛；这只证明代数上存在修复空间，不证明真实控制器会达到。root gate样本x=1.40236..1.49991m，均已越过原wheel-mode边界。

## Proposed candidate / Result

低通τ0.20s、差动积分Ki0.5s^-1、零均值有界bias±1rad/s，保留名义[1,1,1.4,1.4]，接管首输出等于上次真实wheelcommand，随后每轮限速0.02rad/s/step，限速/支撑异常暂停积分。只在完整跨障后启用；全程gain0已拒绝。具体公式、错误/reset、sidecar证据、原严格门槛与额外平滑验收见设计。

本轮没有生产代码、控制器候选、物理测试或10000训练。正式adapter相对a86cbf5仍diff0。自审及独立审查要求补全root严格边界、packet一次消费/episode身份、原始和最终输出独立拷贝、live动作单位/offset/速度上限、独立sync_verdict失败出口。已修订这些合同，并明确逐env积分暂停/更新顺序。独立复审PASS，无剩余明确阻断项；这只是设计审查。候选仍需用户审阅具体设计；之后才写实施计划。占位与其他进程保持不动。

## Git / Follow-up

Baseline Ref:a86cbf5，设计前HEAD7c9dac9；Design Commit:6c53e32，仅新增125行设计文件；无代码Candidate Ref。提交前git diff --cached --check通过，暂存区只有该设计；无占位符，三个相对链接均存在，严格边界和合取验收合同已检查。正式adapter仍diff0。Key Files:设计、runtime.py动作/采样边界、参考m1_rsl_rl_wrapper.py和IsaacLab45 recorder/reset调用点。T306.6h.6a下步为用户审阅具体设计，再TDD实现一个隔离候选和一次amp/GPU7 8×1600。AME/桥接/learnedcross/largeavoidance仍独立未完成。dashboard/branch/log/index同步本轮设计状态；未改变human/AI主线接口。
