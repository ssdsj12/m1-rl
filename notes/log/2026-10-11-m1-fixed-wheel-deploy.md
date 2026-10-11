# 固定轮速与12腿PPO实施/验证

Parent：[T306](../todo/T306-m1-ame-long-train-stability.md)。
Spec：[已确认规格](../../docs/superpowers/specs/2026-10-11-m1-fixed-wheel-leg-only-design.md)。
2026-10-11 UTC。当前为原生/部署前记录，后续追加现场结果优先。

最新09:40UTC：隔离原生9259完整通过并退出/GPU1MiB后，11个runtime/入口文件按SHA备份部署；
新训练进程9450已启动2048/cuda0，日志/tmp/m1-ppo-fixed-wheel-model300-20261011.log，首更新待核实。
初始化PT另存生产logs/rsl_rl/m1_cross_large_complex_ame/fixed-wheel-initialization/model_300_fixed_wheel.pt，
SHA同候选bffc5fbb；原300/旧700/所有历史run保留。备份/tmp/m1-fixed-wheel-production-backup/manifest.json。

原生结果/tmp/m1-fixed-wheel-native-result.json：100空地控制步/400物理调用后4env实际前进
0.4901047/0.4963684/0.4903412/0.4949799m，实测四轮各自正向；不是精确速度跟踪。
再逐阶段0/1/2/3/mixed运行1600环境帧随机12维动作，20terminal，累计2000物理调用全部固定轮目标；
12策略/16历史、1589/1592观测、实际奖励有限，mixed实际levels8/6/6/5。
这证明接线/实际前进方向，不证明学会折腿跨越或绕过大障碍。

用户确认固定轮面目标0.30m/s，PPO仅12腿动作，实际机身跟速允许偏差。
不加差速/teacher/IK/swing/WBC，不更改轮PD、585mm姿态、std、地形或成功阈值。
真实小障碍跨越及大障碍避让仍OPEN；固定驱动不等于实际恒速或必然会转向。

## CPU与显式迁移

- 7343cd6：12动作扩展成16执行历史，轮槽固定.30；action-rate保持原12腿平方和。
- b769220：Isaac动作选择12腿，四轮独立命名映射并每substep写入固定角速度。
- 501f246：地形配置不覆盖固定命令；actor/std/Adam按命名腿列显式转换，普通load校验合同。
- 反例先失败后实现；独立审查发现eval16硬编码/.35覆盖和NaN恢复缺口。
  六个反例复现后统一修复，训练日志同步输出实际维数和固定速度。
- 最终相关344CPU通过6.04s。裸pytest收集受test_m1_sdf_probe缺pxr阻断，
  不声称仓库全套通过；原生另验。早期两处缺候选源文件已补归档，非产品失败。
- 真实源18-49-19/model300 SHA4437ed429f6c2339284efb567b1dda5aabab83f59823bc376f80d23ebccdc075不变。
  新候选/tmp/m1-fixed-wheel-20261011/model_300_fixed_wheel.pt，
  SHAbffc5fbbe268e8d75c8eeae6c70eb942798d75fef5e66099282587426fd07fc6。
  iter300/next301、12std、33Adam、stage1保持；同旧观测的新actor与旧腿列输出一致。
  这是新动作合同的初始化，不是16维整机策略的精确续训。

## 当前运行与安全边界

09:36UTC旧PID7960/cwd/source300/2048/optimizer1核实，至697、loss有限。
等待其本run15-51-33/model700完整CPU校验；尚未发停信号或改生产。
准备隔离4env原生：空地四轮方向、12策略/16历史、随机腿动作不改轮目标、
stage0/1/2/3/mixed、强制terminal与有限奖励。训练/probe不并发。
候选接线通过不等于学会；原生未完前不部署、不宣称新训练运行。

## 审查裁定与限制

09:37UTC本run700出现，CPU权重39/Adam33/std16正有限/stage1核验；
SHA4a23caf90a1eee4c96020865a8216af46761e4b0b6052e677f09a6903e90faee。
仅对重新验证cmdline/cwd/starttime的7960发SIGINT，退出/GPU空闲核实后启动9259原生。
`/tmp/m1-fixed-wheel-pause-evidence.json`保存边界证据；旧训练停止，候选尚未部署。

- Windows宿主测试使用显式tar/OpenSSH路径，避免Git Bash PATH误选GNU tar；不改全局设置。
- 用现有实际测试文件名替代计划简写；runtime线性尺度测试动作限定在原关节范围，限位不变。
- terrain配置也需支持12并保留恒命令，故扩展到m1_mixed_course控制配置；几何没改。
- 启动日志维度问题按验收证据重要性升为Important，加入反例与实际action-manager一致性断言。
- 审阅者未判原生接口/轮轴方向，由现场原生补证；未判源PT/保存边界，由主代理CPU与进程核验。
- 动态能力未判继续OPEN；测试结果依据主代理真实运行，不以审查替代执行。
Deferred minors：无。原PT/旧run保留，无新增删除。

Baseline84c8bcf；Feature501f246及审查修复；当前分支codex/m1-ppo-repair-upload。
