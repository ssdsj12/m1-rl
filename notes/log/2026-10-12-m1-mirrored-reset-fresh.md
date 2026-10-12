# 前后镜像姿态、撞障碍结束回合、从零训练

Parent：[T306](../todo/T306-m1-ame-long-train-stability.md)。
已确认[规格](../../docs/superpowers/specs/2026-10-12-m1-mirrored-stance-collision-reset-design.md)与
[计划](../../docs/superpowers/plans/2026-10-12-m1-mirrored-stance-collision-reset.md)。

## 当前状态（后续部署追加优先）

### 03:22UTC 首轮更新与完整PT已核实（当前状态）

PID2303实际完成iteration0和1，value loss .0437/.0380、surrogate -.0022/-.0024均有限。
2048env，GPU21866MiB。日志明确`ActorCriticAME`、12actions/.30m/s、stage0且所有2048环境
active_obstacles0；这是AME感知策略+PPO，不是AMP（无判别器/示范动作模仿奖励）。
model_0.pt CPU核验：iter0/next1、39模型tensor有限、33Adam状态有限且step均20、
12正有限std .04959956–.04975610、课程stage0/streak0/window0。
新姿态/碰撞重置/required_top_margin_m0合同完整，无旧action_conversion来源。
SHA256 `2991f8c206462e2b59dfbe6fd707304c12a464c1efc2d7d0b247f91786f68967`。
cmdline无resume/checkpoint，environ无CHECKPOINT/M1_LOAD_OPTIMIZER；.30/2048/save100/10000已核实。
TensorBoard PID2468指向11-20-43，remote127.0.0.1:6006/data/logdir独立核实。
未修改隧道，local16006本轮未验证。实际学习/10cm完整越障仍OPEN。

### 03:20UTC 已部署并启动 fresh 初始化（首轮更新待核验）

实现`91f104c`+`c7af587`。新PID2303，cwd为当前生产目录，cmdline明确
`--num_envs 2048 --max_iterations 10000 --device cuda:0 --headless --course-profile flat-first`，
没有resume/checkpoint。run `2026-10-12_11-20-43/bb57e7d`（目录后缀为生产历史git，
不等于部署版本），日志`/tmp/m1-ppo-mirrored-fresh-20261012.log`。
9个runtime文件逐一备份/部署并hash验证，manifest:
`/tmp/m1-mirrored-production-before-20261012T032037Z/manifest.json`；
执行回执`/tmp/m1-mirrored-fresh-deploy.json`。不加载旧PT，不删任何旧模型。
原生最新日志COMPLETE：实际wrapper两tracker参数0断言生效；空地150步4env重置0，
1.5cm间隙done全0，碰撞frame17只env0重置/最终奖励-20.0191746。
SSH前台连接最后被远端断开，但重新连接确认COMPLETE、probe已退出、GPU回到1MiB后
才启动训练；没有将SSH断线当作仿真失败，也没有并发probe/训练。

最新用户变更：不要求额外净空，收腿或摆腿均允许、PPO自主学习。部署前已纳入：
两处生产tracker required_clearance=0，感知proxy不再隐藏5cm门槛，PT合同记录0额外margin。
保留不穿透/无碰撞、三轮支撑、实际重叠经过、远侧落轮和5帧恢复；不指定swing动作。
新增11项反例先6失败5通过，再实现后合并216相关CPU全部通过4.30s；
1/10/29mm实测间隙均可完成完整事件，碰撞/穿透/失支撑/无重叠/无落轮仍失败。
最新原生接线复验日志`/tmp/m1-no-margin-native-20261012.log`，完成后追加；未启动新长训。

用户确认“对的，然后重新训练，不接着训练”。旧训练已按用户要求停止，
当前新主机 `a21484122541518848761613`；旧演示已退出，原生开始前 GPU 1MiB。
以下为部署前历史：本地 `10-12` 分支实现 `91f104c`，当时尚未部署/启动新长训，不可复用旧host/PID。
保留旧PT/日志，两项未跟踪旧watcher不动。

## 修改与边界

- 原先四腿同HIP/KNEE默认角度，FK膝部X偏移都为+0.2008m。前两腿HIP/KNEE翻转后，
  前膝向后、后膝向前；仍由PPO自由折腿，观测/动作偏移/恢复比较共享default joint pose。
- 新非timeout `obstacle_collision`终止项用当前扫描与FK几何，不读上一步reward。
  semantic0地面排除；小障碍轮底接触不再豁免；margin0，不把不足3cm净空直接判碰撞。
- 严格查询的轮轴按源模型Y方向，32角度采样；旧planner使用X轴柱体。
  仅新终止查询修正，旧planner/奖励采样保持。新Episode_Termination/obstacle_collision为
  该重置事件的权威计数，旧碰撞奖励统计可能不同。仍是扫描/采样几何，不是精确PhysX碰撞对真值。
- checkpoint新增姿态/重置合同；真实训练和eval入口拒绝旧无合同PT，防止默认角偏移不兼容。
- 新训练必须网络/optimizer/课程stage0从零，不加载300/4100或其他PT；固定.30m/s轮速、
  12腿PPO、2048env/GPU0、save100/10000保持。不手改std/PD、不加teacher/IK/swing等。

## 验证

- 4个反例先RED（同向膝部/缺终止/缺接线/缺合同），实现后52相关CPU通过；扩展含奖励、
  防刷门控及真实runner加载前无突变检查，90CPU通过3.31s。不是仓库全套通过。
- 独立34源网格FK：镜像姿态总高0.5849999999999952m，最低Z约0；root保持.45600081146m。
  CPU独立python缺pxr，已在Isaac AppLauncher之后完成该审计，没把导入失败当通过。
- 隔离候选 `/tmp/m1-mirrored-reset-20261012`，日志 `/tmp/m1-mirrored-native-20261012.log`。
  3秒4env空地零腿动作：0重置、最大倾角.0055796rad，前进.79139–.79784m。
  stage1首个实际方块碰撞frame17：done[1,0,0,0]、obstacle_collision[true,false,false,false]，
  最终wrapper reward第0环境-20.0191746，回到rootZ.456且新姿态不再碰撞。
  这证明接线/重置，不证明策略已学会抬腿或越障。
- Windows旧PowerShell执行策略不允许脚本运行；未改策略，使用当前Codex提供的pwsh运行测试。

## 后续

原生近障反例、最终审查、备份部署、fresh首轮更新、model0和课程/优化器核验已完成。
旧模型不得自动恢复。真正越障/自主三轮运动仍OPEN，测试不证明已学会。
