# 自主抬落时机：实现、验证与 model300 新训练

Parent [T306](../todo/T306-m1-ame-long-train-stability.md)，
pure-ppo-learning/autonomous-lift-timing；[已确认规格](../../docs/superpowers/specs/2026-10-11-m1-autonomous-lift-timing-design.md)。

## 用户授权及范围

用户确认实施，不固定水平起抬距离；取消误解为用户要求的竖直2cm成功前提，
让PPO自行学习抬腿/落腿。随后明确从18-49-19/model300开新训练，
保留其optimizer/std/course。再次精确确认只删除13-17-21的400/500/600/700，
以及15-16-31切换前PT；保护指定300、其他历史run和全部日志。
删除应在新训练实际运行验证后进行，不能把批准当作已删除。

## 实现与不变量

实现1fde9d1/c7ed76f：EncounterCrossingTracker独立flight_active与crossing_started，
逐环境autonomous_lift仅flat-first stage1–3且非done启用；legacy默认、stage0/mixed4不变。
进入遭遇前已抬起可凭后续完整实测过程成功；没有承重基线不补发高度奖励。
障碍前安全落轮可重试，不刷新高水位/预算，不清除碰撞或失支撑失败。
不足2cm的真实升高同样检查三轮支撑；承重重叠、低于top+3cm、中途落轮、
侧向逃逸/无重叠仍失败；同轮远侧真实承重落轮及5帧稳定恢复保留。
旧prelift_events仍统计竖直>=2cm，只是诊断，不再是自主模式成功门槛。
`.3/.02m`仍为连续增量斜率，奖励上限/防刷/持久屏蔽和轮轨义务不变。

不改8目标+70填充/XY/3、6、10cm、控制器、std、585mm、2048、边界。
没有swing/teacher/IK/MPC/WBC/额外servo/动作接管。

## 已完成验证

- 初始反例11失败；140通过后新增侧向绕过反例1失败，再修复；wrapper/mask反例7失败。
- 153相关CPU通过；扩大到布局/课程/恢复/checkpoint等19测试文件，**307通过，5.36s**。
  并非全仓所有历史实验的测试。扩大套件最初2失败均为隔离快照缺源码文件，
  补齐原文件后通过，未修改生产来掩盖测试。
- 一次fresh-context独立审查无Critical/Important/Minor；diff-check通过。
- 保存trace700中env283的真实支撑输入复算：51帧三轮承重，52帧四轮载荷皆0，
  支撑失败持续到55帧，0重叠/0成功。trace未保存全部轮四元数及捕获前完整状态，
  **只声称精确支撑阶段复算，不声称完整历史几何反事实回放**。
- 500步×4环境生成帧，新旧legacy模式8000输出tensor逐值相同（含NaN位置）。
- 原生隔离检查状态及实际部署见下方现场结果；不以CPU通过宣称学会。

## 安全切换证据

仅现场确认的PID6507（cwd/cmdline/进程starttime均匹配）在model800完整CPU校验后SIGINT。
800 SHA59c579071ccd21abd0f457eee6a26d59b9a1bb170933382a645e46025ef3ce30，
39有限权重/33optimizer/16正std/stage1；随后进程不存在、GPU0=1MiB。
所选300再次CPU核验39/33/16/stage1、iter300/next301，SHA
4437ed429f6c2339284efb567b1dda5aabab83f59823bc376f80d23ebccdc075。
800仅用于旧训练安全停止，不是新训练起点。

## 原生现场结果

原生4env candidate-only按1/2/3/0/4检查，真实策略输出，无PPO更新。
CPU影子tracker与GPU逐输出对照，奖励CPU/GPU对照，主动超时覆盖terminal。
首轮1/2/3/0通过1024环境帧，mixed4前脚本退出无完成标志；保留原始日志。
加诊断后复现：mixed4实际行号[8,6,6,9]，错误断言levels==4失败；
m1_learning_curriculum原有合同是随机行号>=4。只修复诊断断言为>=4，
不改生产mixed规则。最终重跑**1280环境帧/20terminal**，覆盖1/2/3/0/4；
所有tracker输出CPU/GPU在2e-5浮点容差内相同，奖励1280次对照最大差0。
实际strict事件0，只证明接线/重置一致，不是能力验收。完成标志与result JSON齐全，
PID7782退出/GPU1MiB后才部署。早期7331/7580退出，未并发长训。

## 部署与新训练

只替换dynamic/wrapper两个runtime文件，原文件备份
`/tmp/m1-autonomous-production-backup-20261011`及manifest；本地/候选/部署SHA一致：

- dynamic：0ee97f282a4cecb086e61e3b586fd26f0dad6e28a4fc03dd98811052132df01f
- wrapper：21c2553e5c92d4303fdbc7d8e70d0d919596fc9e91e9d21c3b2571a7a83708b2
- 地形仍0af49f5c8dd0edaa809847241ad9a7f0928e9cc31484b469c627e6184e8f5395

已调用既有kernel-flock启动包装，PID7960，日志
`/tmp/m1-ppo-autonomous-model300-20261011.log`；指定300/next301+9699/2048/cuda0/
save100/M1_LOAD_OPTIMIZER1/keep_std/课程保留。
新run `2026-10-11_15-51-33/bb57e7d`，实际policy(2048,1589)/critic(2048,1592)，
controller=ppo/teacher disabled/imitation0，日志明确加载18-49-19/model300。
实际完成301–304，value loss .175/1.8042/1.233/4.2778，surrogate
.0258/.0262/.0514/.0338均有限，GPU0=21868MiB。现场/proc核对cwd、checkpoint、
2048/cuda0/9699、M1_LOAD_OPTIMIZER1/SAVE_INTERVAL100/NUM_ENVS2048/keep_std。
env_cfg selector=m1_lift_roll；train_cfg save_interval100。旧git目录bb57e7d不是部署版本。

TensorBoard仅替换已核实6661，当前8190指15-51-33父run；remote6006/data/logdir独立核实。
local16006未重验，未改网络/隧道。小时监控已更新新身份/新合同/删除清单；无变化安静。

## 已完成的精确PT清理

在上述新run完成实际更新后，先枚举绝对路径、确认所属目录/非符号链接并记录SHA，
再次比对清单后逐文件unlink，**共5文件/29,555,095字节**：

| run | PT | SHA256 |
| --- | --- | --- |
| 13-17-21/bb57e7d | model_400.pt | 47889a881362023852693fb5b999ba48a0ee3bab7515e6e42240b086317d53ac |
| 13-17-21/bb57e7d | model_500.pt | 9cef639ed8ae8dc1ed82f59e08de881cf6a0e9a85697523021559cca29121fdf |
| 13-17-21/bb57e7d | model_600.pt | c4bd276ee7202a50c4fc15840df09032c2c01043a3de64ef59d42c388864ee59 |
| 13-17-21/bb57e7d | model_700.pt | ef9e9833040ca93a6932a24001cc5ddddb817007cfec574ef1cfb2ac1fe40d7d |
| 15-16-31/bb57e7d | model_800.pt | 59c579071ccd21abd0f457eee6a26d59b9a1bb170933382a645e46025ef3ce30 |

两个run的6个非PT文件逐字节hash未变；/tmp训练/诊断日志未删除。
指定18-49-19/model300再次SHA核对未变；其他历史run/model1400未触碰。
未为这5个失败模型另作备份，不能承诺恢复；清单并不是模型备份。
manifest `/tmp/m1-autonomous-failed-pt-deleted.json`已复制到本地ignored
`results/diag_autonomous_timing/`。历史700轨迹/日志保留，但原PT已按要求删除，
不能再用旧恢复命令加载它。

## 发布与后续

README/notes/human-ai合同和监控已更新；服务器文档/19测试文件共34项归档同步，
archive SHA dc6a1b56cf1229c54f9725735328a51bb128b02dfa23fe6cf4d038229954ee7c，
两端一致且tar-diff通过，没有热改runtime。实际训练已至314/loss有限，PID7960仍运行。
本轮实现和README/记录本地提交233d68b；首轮GitHub普通push因443连接超时失败，
不声称该次已上传。最后独立确认远端仍900f249；后续上传回执优先，禁止据旧失败重复发布。
307相关CPU和原生接线通过；真实跨越/三轮支撑学习、动态10cm视频验收仍OPEN。

## 证据路径与保留事项

服务器/tmp：m1-autonomous-pause-evidence.json、m1-autonomous-replay-result.json、
m1-autonomous-native-20261011.log及后续probe-diag/probe-final日志。
本地验证脚本在镜像外m1-autonomous-*-20261011.py；隔离候选/tmp/m1-autonomous-timing-20261011。
代码接线通过不证明策略解决了三轮失载；真实学习/10cm视频与完整严格跨越仍OPEN。

## 执行裁定

- 用户指定300覆盖旧latest-only约定，代价是舍弃后续学习，属明确选择。
- 生产目录旧测试4/6/8不匹配已部署8/8/8，使用本地已提交测试快照核验，不据此改生产。
- 自主模式首次重叠后未到远边就横向逃逸判失败，避免旧净空证据被绕过复用；代价是保守拒绝边缘退出。
- 保存轨迹缺字段只报告可复算部分，不虚构全轨迹；实际几何改用原生CPU/GPU影子核对。
- 审查不评估学习、启动、删除和文档现场状态；这些由本次实测闭合，未闭合能力维持OPEN。
- Task-done使用显式Windows OpenSSH与进程级ExecutionPolicy Bypass，修正脚本宿主差异；未改全局SSH/系统策略。
- mixed4诊断断言从==4纠正为课程既有>=4随机行；生产不改，代价是必须重跑整套原生而非拿部分通过作数。

Deferred minors：无。

Baseline Ref5b80c9e；Last Feature/CPU Verified Ref c7ed76f，实际两个模块hash如上。
Current Work Ref codex/m1-ppo-repair-upload；Key Files m1_dynamic_crossing.py、
ame_env_wrapper.py、test_m1_autonomous_lift_timing.py、README与本记录。
