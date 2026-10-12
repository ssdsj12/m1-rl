# 参考 M1 对齐与三项自主学习信号

Parent：[T306](../todo/T306-m1-ame-long-train-stability.md)。用户已批准
[规格](../../docs/superpowers/specs/2026-10-12-m1-learning-signals-reference-robot-design.md)与当前镜像逐项执行。

## 当前状态（后续现场回执优先）

2026-10-12 04:26UTC：14个runtime已备份并部署，fresh PID4885已启动，正在核实2048环境首次更新。
新日志`/tmp/m1-ppo-reference-fresh-20261012.log`，无resume/checkpoint，旧模型不加载。
部署清单`/tmp/m1-reference-fresh-deploy.json`；备份`/tmp/m1-reference-production-before-20261012T042614Z/manifest.json`。
旧PID2303在CPU完整校验model100后SIGINT退出；checkpoint SHA256
`43b52dfda1f364ab2f47f4c1c60a37ec9a90931dedd4fb26972b66f78bf1b0a2`，
iter100/next101、39有限模型/33有限Adam/12正std与旧合同完整。全部PT/日志保留。
GPU释放至1MiB后才运行隔离4env探针。3268/3593初始化未完成已退出，不作通过。
3817诊断停留物理复制，SIGINT/TERM后未退出，仅该探针KILL清理，未删文件。
生产配置4093对照完成初始化；候选4202在scanner内等待，已退出。
对照发现并TDD修复原生scanner没有valid_mask的接口错误：以有限ray_hits生成validity。
4423因诊断目录缺源USD软链失败，修正测试目录而非机器人规则；4532候选初始化完成。
远程arrow_x.usd调试素材曾等待，正式headless探针关闭command debug_vis，不改网络。
最终4725原生测量完成且退出、GPU1MiB，才允许启动4885。TB2468暂仍指旧暂停run，待新run绑定。

## 原生验收回执

`/tmp/m1-reference-native-fixed.log` SHA256 `e1fd4c23c64409f8e7a973625868d7e5061a375c5dd5bc34f48ba6f86c02b43c`。
真实DCMotor/Implicit、120/5.5与轮Kd30、solver、四轮Y圆柱/停旧mesh、材料1/1/0与实际重量402.6546N均断言通过。
空地4env150步零重置，最大倾角.01108rad，前进.85996–.88050m；观测1621有限，wrapper新增反馈有限。
1.5cm顶面间隙不重置；实际接近后第17帧仅env0障碍碰撞终止，最终reward−20.20258，其他env不重置。
存在`REFERENCE_LEARNING_NATIVE_COMPLETE`。这是配置/测量/接线验收，不是学会抬腿。
实际成功五帧receipt的正反例CPU覆盖；本原生测试未制造完整自主成功轨迹，学习仍OPEN。

## 已实现

- 每轮5项可见障碍特征+接触/向上载荷/其余三轮最小载荷，共32维。
  policy85/critic88，地图1536与12动作不变；不向actor提供地形registry真值。
- 承重基线冻结，安全单轮卸载最多.10，真实离地经过单调进度最多.30。
  不补发不安全历史进度；stage0/mixed4不加该反馈。原抬升.3/.02m、恢复2及正奖励屏蔽保留。
- 裸M1参考8aeb845：DCMotor腿120/5.5、effort/saturation150/velocity20；轮Implicit0/30、effort200/velocity20；
  solver4/2，摩擦1/1/弹性0，无质量扰动，reset关节速度0。
  前HIP+.30/KNEE−.60，后−.30/+.60，rootZ.62替代585mm标定，.62不是整机总高。
  源USD不改，spawn实例停旧轮mesh并增加Y圆柱半径.0959/宽.0465。
- 合同version2记录物理/输入/学习信号版本，拒绝直接加载旧PT。
  保留AME+纯PPO、轮面.30/2048、额外净空0；无IK/teacher/swing/动作接管。

## 验证与取舍

各模块先RED再GREEN。原生scanner接口修正后相关整组CPU **301 passed / 1 skipped**，6.45s；
skip为普通Python未启动Isaac App的配置导入，不是全仓库通过。
独立审查两项Important均反例修复：空地padding零尺寸误入几何；水平分离误当经过。
侧边相切6mm/步、轮底只抬1mm不再获得推进或成功；真实上方经过保留五帧恢复。

- 有限分离平面证明圆柱不相交，但任意倾角可能保守漏判安全。
- 实际圆柱点XY内部重叠才算经过；有限采样可能漏极小角落，不会制造侧绕成功。
- 可见patch范围±10cm纵向/12cm横向，远缘不是不可见真实后缘，近邻表面可能合并，原地图保留。
- 新奖励支撑要求其余各轮>10N且>=.1体重、合计>=.5体重、横向力<=向上力、tilt<=.15/rate<=.20。
  这是保守反馈门槛，不改既有严格成功门槛；可能减少早期反馈，后续按实测诊断。

原生/2048容量及真实学习不以CPU替代。新训练首轮及checkpoint核验回执将在下方追加。

## 新训练首轮核验

PID4885 cwd/cmdline/environ现场确认12腿/.30/2048/cuda0/save100/max10000；无CHECKPOINT/M1_LOAD_OPTIMIZER/--resume。
run`2026-10-12_12-26-20/bb57e7d`（生产git旧目录名不代表部署代码），已完成0轮，value loss.0820/surrogate−.0014有限。
GPU23134MiB；此后严禁并发native。model0 SHA256 `2d242a9e7c53e3869c5a75642f3009bd1acc878d0426bfa7962bf0e8955ba0ff`。
CPU39有限模型/33有限Adam、step20、12正std .0496483–.0502175、iter0/next1/stage0/window0，
无action_conversion。version2/参考commit/85与88状态/物理参数/root.62/零额外margin合同逐项验证通过。
TB旧2468已核实旧logdir后退出，新5041 remote127.0.0.1:6006/data/logdir独立确认指新run；未改隧道/local16006未重验。
实现1d4d1ad，发布状态待独立remote ref回执；全部旧PT保留。无样本NaN不是跨越成功。

## 收尾现场复核与发布

04:30UTC附近实际完成0–5轮，最近value loss .0593/.0485/.0401、surrogate−.0013/−.0011/−.0016有限；PID4885/cwd/2048确认，GPU23134MiB。
14个本地runtime SHA与部署manifest逐项完全一致；README/notes/规格/测试/脚本同步服务器并tar-diff为零，
同步包SHA `40e8426034c8d1b241ae936c50d6de4032018db2555a4f10e49afb924b238ee9`。
实现及运行文档已本地提交至97ccab0。两次普通push分别connection reset、443约21s连接失败；
**本轮GitHub发布未完成**，不影响已验证部署和训练。既有10-12普通push授权保留，不改网络/全局Git、不force。

本轮额外判断：原生验收依批准规格验证配置/感知接线/空地稳定/间隙与碰撞；
五帧成功完整正反例由CPU轨迹验证，未强加动作生成器制造原生抬腿成功。代价：真实物理越障仍需后续策略视频与完整事件验收。
其余几何、可见patch、测试基准、保守支撑取舍见上文；无延后Minor审查项。

## 05:33 / 06:35 UTC 监控与发布回执

05:33 UTC 普通 push 已成功，独立 ls-remote 确认 GitHub `10-12` 为
`e45a007b85a027e766e92b90948c1727e136a485`；上述上传失败仅为历史，不再待发布。

06:35 UTC PID4885 的 cwd/cmdline 现场复核仍为本 run、2048env/cuda0；GPU23136MiB。
stdout 第249轮首次出现 stage 转换快照均值 .025，第299轮已为 stage1（3cm障碍）。
第299轮 value2.3020 / surrogate−.0010 有限，平均回合72.43步；obstacle_collision终止指标.9989，
bad_orientation .0015，base_contact0。各指标是聚合统计，不能据此认定每次抬腿失败原因或相加视作互斥比例。
安全卸载奖金打印.0002、原抬升增量奖金.0001，稳定落轮与严格成功仍0；不宣称已学会跨越。

随后已保存当前 run `model_300.pt`，CPU读取完整且全部张量有限、12个std均正（.02550–.03581），
iter300/next301，version2/85policy/88critic/参考物理与零额外margin合同在文件内保持。
SHA256 `a66d20440e75f4d3568216b5504cf99391b76844513a01bf298cf1b315cf09dd`。
课程stage1/streak0；last完整2051回合：前进pass0、strict attempts2051、success0；
pending255另列，不混入last。CPU审计CUDA未初始化。
保持长训；未改生产/奖励/std，未停止训练或并发原生回放。刚进入障碍阶段的失败不自动触发停训。

## 07:40 UTC 小时监控：姿态与承重指标恶化，根因尚未闭合

PID4885 cwd/cmdline仍为当前run/2048/cuda0，stdout438，GPU23136MiB，value .8650 / surrogate -.0018有限。
model400 CPU所有张量有限、12正std .03198–.05684，iter400/next401，stage1/streak0；
SHA `a9e2b84b2307738176216f7eb62bbe9f4cd424074ba26ea1fc5af4252421ed96`。
last完整2052回合pass0/2070attempt/0success；pending684回合/694attempt另列。CUDA未初始化。

原始TB比较280–300共21轮与400–438共39轮，各数值为这些rollout的等权均值，非完整回合窗口率：
- bad_orientation终止指标 .000954 → .236809；obstacle_collision .999084 → .764947；非互斥分类。
- loaded_touchdown_fraction .533172 → .049047；recovery_ready_fraction .109438 → .001306。
- route_penalty_rate .035270 → .198834；此tag实际为归一化轮轨代价值均值，不能直接解释成偏离环境百分比。
- unload_bonus .000275109 → .000001125；passage_bonus约9.88e-8 → 0。
- prelift_progress_delta .000209291 → .000202058，非米；并非完全无抬升增量。
- mean_episode_length 72.41 → 226.62，不是越障进步证据；预抬>=2cm诊断和stable_landings自249至本次读取全0，strict全0。

代码追踪：bad_orientation来自实际projected_gravity阈值；loaded_touchdown为目标轮和支撑的载荷门槛，
recovery_ready还包含倾角/角速度/名义关节姿态/高度。两者不是实际落轮事件成功率，不能把下降直接当作全部三轮失载。
已证实失败构成发生变化：姿态超限增多、承重/恢复条件更少、轮轨代价增加；参数非有限或训练退出并非当前解释。
尚不能从聚合数据判断“抬腿先造成失稳”，或“撞击/腿部侧移先造成失稳”，也不能以std正值判定探索充分。
缺同env同attempt逐帧载荷/轮底/姿态/碰撞先后证据；下一步因果诊断需当前PT隔离回放，必须独占GPU安全边界，
不能在约23GB训练旁启动native，也不能因本次监控擅自暂停长训或调整奖励。根因调查保持OPEN，未声称修复。

## 08:39 UTC 常规监控：延续已告知的超时状态

此前用户查询时已核实stdout553/TB554、model500的last完整2049回合pass0/1907attempt/0success，
pending1649回合/1867attempt另列；最近20轮passage与有效overlap样本均0，raw抬升delta均值4.18152e-6非米。
该状态已回复用户，本次不重复通知。

本次现场PID4885/cwd/cmdline仍为当前run/2048/cuda0，stdout576，stage1/streak0，GPU23136MiB。
value .1494 / surrogate -.0009有限；均回合961.61步，timeout .9068，collision .0508，bad_orientation .0387。
strict成功/稳定恢复仍0、有效净空样本0（NaN非成功），route代价均值.3664。
非严格proxy crossing .007不作为真实跨越证据。延续此前超时多、有效跨越暴露少的状态，
不能由此区分停滞/偏航/侧移，更不能称碰撞减少等于学会。未改训练、未暂停、无并发native。
