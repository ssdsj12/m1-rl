# 参考 M1 机器人配置差异与学习信号设计

Parent：[T306](../todo/T306-m1-ame-long-train-stability.md)。
Baseline 8160d90；参考 ssdsj12/m1 8aeb845f73e39fd1e121758522ef05ee2378150f。
用户已授权三项借鉴及robot设置对齐；当前完成只读核查与书面设计，未改runtime。

## 方法与证据

直接读取锁定 commit 的 assets/__init__.py、floating.usda、m1_smoke/roll/wave/small_obstacle cfg
与 test_m1_asset_static.py；读取当前生产 run11-20-43 的 env_cfg.yaml，不只比本地默认类。
参考资产不是 go2_pvcnn/assets/m1.py（该路径404），实际定义在 assets/__init__.py。

生产4源USD SHA与参考仓库 m1_panda/source_files.sha256 的裸M1源条目全相等：

- entry 43cb116ba2a081a3a215d45fb2796895df9d8b201cd5c26bc311cbd5f005e648
- base 6a0c981c56ff28f6ebee47f3d3aa6d31a8ca530ecd9604d29e591a62cd31ac6b
- physics 61ed49556994f339e488ebb85f0bafb36cdc7009569e6c4388087b7559c035b4
- sensor 204f805d72bace786a83c7a19f49976608e4458ec87f38ceb17e2447ce4bb934

这是基础资产一致性，不是旧高成功率run配置或实际效果复现。
参考floating overlay读原作者机器绝对路径，不可原封部署；轮原collision被停用，
改Y轴圆柱r.0959/宽.0465，root fixed joint停用，轮关节无限旋转。
当前spawn只释放根/调整关节限位/轮无限旋转，并未替换轮collision。

实际当前腿Implicit800/40，参考DCMotor120/5.5/150Nm/20rad/s；
轮当前Implicit0/5且effort_limit_sim null（继承USD，不是无限力矩），参考0/30/200Nm/20rad/s。
solver4/0对4/2。当前摩擦随机.3–1.2/弹性0–.15/质量附加−1…+3kg/reset关节速度±1；
参考裸M1固定摩擦1/弹性0/无附加质量/零关节初速度。dt.005/decimation4一致。
参考root.62/前hip+.3 knee−.6/后镜像，与当前585mm标定并非相同；这是书面审阅关键差异。
固定轮速/纯12腿PPO不导入参考wave暂停驱动/锁轮/IK/残差接管。

## 状态与后续

PID2303现场cmdline/cwd一致，最新stdout65/10000；未停止/未生产改动/未并发native。
未将stage0无障碍的NaN跨越统计当成功或失败。
[书面规格](../../docs/superpowers/specs/2026-10-12-m1-learning-signals-reference-robot-design.md)
拟加入32维显式感知/载荷和有界卸载/推进奖励，并全新合同fresh训练。
需要审阅姿态是否随参考变更；不是再次请求三项方向授权。
未验证新电机/圆柱下的原生稳定性，不承诺这些修改必然学会。
