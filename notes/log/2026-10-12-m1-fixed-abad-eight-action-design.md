# 固定ABAD、8维PPO设计记录

## 最新：fresh覆盖与隔离验收（2026-10-12 UTC）

用户执行中改为“从0开始训吧还是”：撤销200迁移，改为新网络/Adam/std/课程stage0。固定ABAD目标0rad、8维HIP/KNEE PPO、四轮.30m/s不变；所有旧PT/日志保留。

实现分步提交1a613ec/613ca31/04414d3/7911469，审查补强399cf7b：
- 真8维策略与8个std，按关节名字展开16执行列；ABAD位置PD目标0，非物理锁定。12腿/16执行历史、85/88 state维度保持。
- 动作合同v2、训练合同v3，保存/恢复拒绝旧12/16及角度/速度/顺序错配；无旧PT转换器或初始化读取。
- 演示先从检查点合同选择模式，再创建环境；移除每步额外app.update物理推进。
- 新term补齐8维控制日志接口。probe聚合前检目标有限值、检查净化前奖励/critic/真实状态，避免NaN被max或奖励净化掩盖。

TDD反例：映射RED14→GREEN23；运行时RED4→GREEN40并stall-slip32；保存恢复RED1→GREEN32；入口RED8→GREEN37（另2个旧通用入口在正确Go2Pvcnn cwd通过）。旧方向静态测试已从过时硬编码转为当前命令配置分支。新probe RED14→GREEN14，审查反例RED后GREEN20。

独立全分支审查发现2项Important（trace接口、probe非有限漏报），399cf7b修复后同审查者只读闭环解除。未审查项裁定：原生/fresh容量与PT由主代理实测；200迁移用户撤销；学习能力仍OPEN；旧课程加载事务性为已有行为，不扩大“所有异常均零变更”的承诺。

原生目录`/tmp/m1-fixed-abad-candidate-20261012`，非生产热改。修复后`M1_CONTROL_TRACE=1`复验完成：
- `/tmp/m1-fixed-abad-native-review-20261012.jsonl`：250控制步×4env=1000环境帧，251行含唯一COMPLETE；5stage接线及单行terminal/reset通过。
- 每子步下发共1000次，ABAD目标误差0、轮目标误差0，原始/最终奖励、actor/critic有限。
- 空地零动作100控制步=1.9999999553秒，前进.571159–.583153m、最大倾角.009303rad、0reset。
- ABAD实角最大偏差.009326rad，证明固定目标不等于机械锁死；非PPO已学会的证据。
- probe已退出，GPU释放至1MiB，未和训练并发。

扩展回归的2个旧launcher测试在未部署生产基线同样失败（cuda7/4旧默认、旧1585维metadata），与此次使用的run_m1_pure_ppo入口无关，保留不修；不声称全库测试全绿。新合同相关最终回归及部署结果在下方追加。

### 实际部署与fresh优化

最终相关回归235passed/6.02s（`/tmp/m1-abad-final-green.log`）。12:55:28UTC部署11runtime，备份`/tmp/m1-fixed-abad-production-before-20261012T125528Z/manifest.json`，回执`/tmp/m1-fixed-abad-fresh-deploy.json`；本地预期SHA=候选=生产逐项相同。生产git旧bb57e7d仅run目录标记，不代表部署代码未更新。

新PID10660，cwd生产目录，cmdline `--num_envs 2048 --max_iterations 10000 --device cuda:0 --headless --course-profile flat-first`，环境`M1_FIXED_ABAD=1/M1_FIXED_WHEEL_SPEED_M_S=.30/SAVE_INTERVAL100`。无`--resume/--checkpoint/CHECKPOINT/M1_LOAD_OPTIMIZER`。run `2026-10-12_20-55-34/bb57e7d`，日志`/tmp/m1-ppo-fixed-abad-fresh-20261012.log`。已实际0–3更新：value .0977/.1071/.0916/.0731，surrogate -.0010/-.0008/-.0007/-.0009有限；GPU23021MiB（nvidia-smi宿主命名空间PID与容器10660不同，不当成额外训练）。

model0审计`/tmp/m1-fixed-abad-model0-audit.json`：SHA `4673610b4eb54486143ce4c7dc03a1742b7713489e9ebdfb6493fef381c882a8`；39有限模型/33Adam且step均20/8正std .04961965–.05028835/iter0 next1/stage0 streak0/训练合同v3/动作v2。没有action_conversion或reward_conversion；不是200改名。这是实际优化后的保存点，不是初始化文件。

旧TB6768已核实cmdline后退出，新TB10838指新run，remote127.0.0.1:6006/data/logdir独立核实。6007旧实例未动；local16006不改隧道且未重验。原训练6598不恢复；所有旧PT保留。stage0无障碍时strict NaN表示无样本，不是成功。接线与平地零动作验收不证明PPO学习完成；持续观察推进/偏航/抖动/三轮载荷/真实跨越完整事件。

以下为历史设计，不作为当前训练起点或状态。

最新：用户已确认书面规格；[实施计划](../../docs/superpowers/plans/2026-10-12-m1-fixed-abad-eight-action.md)已完成自检，等待计划审阅。沿用“当前镜像内逐项执行”选择，不重复审批方向/模型。6任务覆盖动作、历史、迁移、入口时钟、原生、部署；未改runtime/启动训练。

- Purpose/Stage：T306/pure-ppo-learning/action-contract/fixed-abad，关联空地策略退化，非已证实根因修复。
- Baseline Ref：83aa11d（GitHub10-12已独立核实）；Candidate Ref：本规格提交；Last Feature/Verified仍6d90e80。
- Input：用户选择固定ABAD目标0、8维HIP/KNEE，最新“直接从200pt开始续训”覆盖此前从零。
- Procedure：只读动作展开/16列历史、85/88观测、runner合同和checkpoint迁移；将200来源与按关节裁剪Adam明确写入规格。
- Key Files：[书面规格](../../docs/superpowers/specs/2026-10-12-m1-fixed-abad-eight-action-design.md)。
- Result：架构级规格已写；新合同/策略未实现，训练保持停止。固定目标不保证绝对直行，大障碍绕行和平衡有损风险保留。
- Verification：文档自检来源、维度、状态保留、加载拒绝、安全部署和评价时钟一致性；未运行新CPU/native，不宣称实现通过。
- Follow-up：先书面规格审阅，再writing-plans与执行方式选择；不重复询问已确定的约束方式或模型起点。
