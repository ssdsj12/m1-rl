# 旧 wave/IK 与当前自主 PPO：只读对照

Parent：[T306](../todo/T306-m1-ame-long-train-stability.md)。用户要求评估旧方案与
https://github.com/ssdsj12/m1 的可取之处；本轮不修改生产、不停训、不运行GPU probe。
使用系统化诊断/方案梳理，仅提出候选，不将建议当已实施设计。

## 来源与范围

- GitHub main现场ref `8aeb845f73e39fd1e121758522ef05ee2378150f`。
- 直接读取其`Go2Pvcnn/go2_pvcnn/tasks/m1_curriculum.py`、`m1_rsl_rl_wrapper.py`、`m1_wave_env_cfg.py`。
- 用户粘贴本地Linux路径不可直接访问；对应GitHub文件行号与代码可核对，未声称访问该本地工作树。
- 当前对照本地`8160d90`（实现c7af587/91f104c）；进程2303/run11-20-43现场仍2048训练。
  只读stdout至37/stage0/value .0177有限/strict0；处于空平地，不能拿此0判新越障学习失败。

## 已核实差异

1. 旧compose_sequential_leg_actions L497支持teacher+residual，也支持policy_control
   与policy_weight1的纯policy输出。不能把整个仓库所有模式统称动作接管，更不能在没有
   原高成功率run配置/轨迹时确认是哪一分支造成高率。
2. wrapper L475真实semantic1/前方-.35~.80/横向.25扫描门控；L805 IK参考接线；
   L940支持wave_task_space_stop_during_wave，默认回退True。旧模式可以暂停驱动，
   当前持续.30轮目标不具备这个动作权限，旧效果不能直接等价迁移。
3. curriculum L907+有支撑/平衡准备、lift/restore ramp、横向/纵向位移参考；
   L1285连续lift/forward进度，L1397 signed potential delta。可借用测量/进度思想，
   不能照抄参考动作、固定腿序或静态锁支撑轮（当前支撑轮应继续滚动）。
4. 旧strict_sequential_crossing_success L1335自身仅检查phase>=11和root越终点；
   额外碰撞约束若存在须查run其他接线。函数名strict不是与本项目完整事件同口径的证明。
5. 当前actor输入是6x16x16地图+53维本体，未显式输入四轮载荷/接触、每轮障碍距离。
   这些在wrapper奖励/成功判定有用，但不是独立actor特征；不能说策略完全没有障碍信息。
6. 当前已有真实单轮before阶段高水位增量，.3/.02m，未完成义务期间屏蔽正基础项；
   before/matches_lane/离地/恰好三轮支撑/无failed等同时满足才领奖。完整恢复奖励2。
   并非完全稀疏奖励，但尚无等价的卸载准备与空中安全向远侧推进的连续信号。
7. 去掉额外3cm后，仍在水平轮包络overlap时要求整轮最低点>=top。对圆轮初始边缘
   overlap，这比实际形状不相交保守，不能称完全等价于无碰撞；需几何反例验证其
   是否提前锁failed。尚无当前策略逐帧证据证明它是实际失败主因，不改生产。
8. fresh初始化仍std.05与lr2e-5；腿目标scale1.5，对应初始每维噪声std约.075rad。
   这是现有配置，不能仅凭数值断言探索失败；用户禁止手改std，保持不动。

## 推荐候选（待用户选择/设计确认）

优先保留AME+纯PPO/12腿/.30固定轮驱动，不导入IK、参考动作或固定腿序。
- 从真实扫描与本体量生成wheel-relative障碍距离/高度/有效性，接触/载荷使用可获得
  的传感/估计定义，防止从课程registry向actor泄露部署时不可得真值。
- 以有限、不可循环刷新的进度奖励覆盖安全卸载/载荷转移→真实离地→安全越过→稳定落轮。
  “事件阶段”仅用于计分和诊断，不输出角度/轮目标、不规定抬腿顺序或轨迹。
- 支撑轮允许正常滚动；倾斜/载荷评价不强制特定机身横移方向或幅度。
- 先几何反例检查保守overlap门控，再做各阶段失败率/最终PPO奖励分解；不要盲加抬腿权重。
- 课程简化（少障碍/低速）与teacher蒸馏是备选，但分别改变用户密度/固定速度或纯PPO要求，
  本轮不实施。成功标准不引入固定额外净空。

## 下一步 / 限制

可先做CPU/离线证据审计和小型设计，任何actor观测维度、奖励、课程或探索变更须形成
明确新合同再测试部署，不热改运行进程。历史高成功率未独立复现，不能保证上述候选必然学会。
当前实现/README/GitHub均不变，仅本地任务知识记录。
