# Teacher 空地准备：跟踪冻结与承重静差调查

日期：2026-10-13（UTC）。关联：[T306](../todo/T306-m1-ame-long-train-stability.md) → teacher-to-ppo/teacher-feasibility/support-ik-redesign/physical-tracking；依赖[原生 v2 记录](2026-10-13-m1-support-ik-native.md)。

Baseline / Candidate Ref：`4f5a875a9d82374c31e7e2be17f00d22d0fb0d95`；物理数据版本仍为 `de423a7`，不是新候选的原生验收。用户要求“继续”后，本轮仅做源码、原始轨迹和 CPU 结构反例调查，没有改变 runtime、物理、PD、奖励或成功门槛，没有启动 native/BC/PPO。

## 目的与现场

区分：准备跟踪不达是 IK 拒绝、动作映射错误、承重下几何目标的静差，还是没有机身偏差纠正通道。只使用当前候选与已有同 env/episode 输入和实际动作证据，不套用旧 PPO 的失败原因。

12:19:39 UTC 主代理只读核实 `root@a21495354824192000872439`：GPU 1MiB / 0%，compute 列表空，train/play/probe 无匹配进程。生产目录未改、所有 PT 保留。两位独立子代理分别审计源码链与原始四行轨迹；没有分派原生任务。

## 已证实的控制结构

`m1_reference_teacher.py` 的 `_tracked` 计算机身实际位姿相对 accepted 的偏差，但仅作为布尔门控。超过原 10mm 位置阈值后，插值 `alpha=0`，年龄及 accepted world 机身/四轮参考冻结。

之后 IK **仍运行**，关节 PD **仍工作**。`m1_teacher_pose.py::world_to_goal_body` 求 `R_goal.T @ (wheel_goal_world-root_goal_world)`，实际关节角作为 seed；冻结后该几何目标不包含连续实际机身误差纠偏。不能称为“完全无反馈”或“IK 停止”，准确说是关节闭环加机身门控，缺少冻结阶段的连续机身误差纠正通道。

`de423a7..4f5a875` 的 pose/IK 模块无变化，正常 BALANCE/TRACKING 这段路径也未改。原生 frame35 已产生接近10mm误差，frame36才冻结，因此冻结不能被称为首个误差的来源；它是持续无法恢复的已定位结构缺口。

## 主代理 CPU 可否证反例

在 candidate `/tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn` 以 `CUDA_VISIBLE_DEVICES='' PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -` 执行，exit0；未写代码文件，`torch.cuda.is_initialized()==False`。

复用 `test_m1_teacher_reference_commit.prepared_teacher(diagnostic=True)`，深拷贝同一教师内部状态两次；保持实际 q、上一已施加目标、载荷和速度相同，将实际 root/COM/四轮共同沿 X 平移 .03m 或 .09m，accepted 世界参考保持原值。调用 `diagnostic_step(...active_wheel=0,lift=False)`，经真实 `m1_action_targets` 解码并比较。

| 场景 | 实际 root 跟踪误差 | executable / reference_valid | freeze | 解码后的16维目标 |
|---|---:|---|---|---|
| 共同平移3cm | .0299999993m | True / 1 | TRACKING(2) | 两场景逐位相同 |
| 共同平移9cm | .0900000036m | True / 1 | TRACKING(2) | 最大差0 |

两场景 accepted root 均未变化，reason=OK。断言全部通过。该合成反例仅证明上述输入改变在此冻结路径不产生纠偏命令，**不是物理反事实，也不证明新增反馈必能跨越**。

本次候选现场 SHA：teacher `f4f329d8e9a06d040534c67e9990f58d73fc3d173871d9c428ee4e774c8d7acb`；pose `396be5ff66cf53a34e88391e79ac7f9eb74114f0636861bd8eb36a778a94c386`；IK `91b456988db689f65c7eb92c5f35e461272b41d89ffe841e4389e710700b3e10`；reference_robot `581a09a3936bc1700e403a2bb16456cfb46ae9d931a8376e08cbd2829ada8e51`。

## 静态负载检查的解释边界

主代理读取当前服务器 IsaacLab `actuator_pd.py`：DCMotor 继承 IdealPDActuator，计算 `Kp*(q_target-q)+Kd*(qd_target-qd)+effort_ff`，再按电机限幅。当前腿 Kp120 / Kd5.5 / effort150；动作入口仅设置腿位置和轮速度，无教师重力/接触力矩前馈。几何 IK 残差≤2mm只证明数学解，不证明有限刚度承重后的实际姿态误差≤10mm。

因此非零承重平衡力矩与非零关节目标偏差相容。121mrad 对应约14.6Nm的比例项，不能据此推断150Nm电机饱和，也不能把该比例项冒充实际电机力矩。旧轨迹缺瞬时 joint_vel / applied_effort / 完整接触切向力与力矩，唯一动力学根因仍 OPEN。

## 原始四行轨迹复核

数据均来自 candidate `teacher_support_ik_flatprep_v2_20261013/stage0_seed101_env{0,1,2,3}_episode0.jsonl`。子代理只读 Python/json 分析各行全序列，主代理另行读取4份原件的 SHA、长度、末帧身份、COM、载荷及关节名称。

| 行 | 控制帧数 | 原始文件 SHA256 |
|---|---:|---|
| env0 | 33 | a75f8e8b00cabb8956596a31fcacb4ff2823fa6d0c3da43af5804717226abca4 |
| env1 | 1000 | d3b217932e3627bcc1dbdb5d1d24c5a25aaf3cf6e3f563145b4e48049c31881c |
| env2 | 1000 | 30b2a39393c6f3f6cac9af419a27a88bff0ddad334f38b4fbaeba7aea9f11f22 |
| env3 | 1000 | 731b6ec7203c07651642642a6e98d6d49a81d1d8a578a54037edb78872e9323e |

env1–3全1000帧的root/joints/Fz/force/wheel_position/teacher_diagnostic、三类targets及teacher/executed action逐帧相等，各自身份正确。探针确实4行批量计算、按row取样；这是同seed同初态的相关重复轨迹，不能把1/4局部完成说成独立随机成功率，也不能由相等推断数据复制。

env0和失败序列input0与output1主要物理数据相同，首次物理分歧在output2、不同控制目标之前：env0 Fz为368.785/358.437/370.062/357.927N，失败序列367.022/394.997/372.404/357.191N；首次目标差异在output3（最大.225mrad）。捕获同选candidate55，rootZ差仅41.664µm。未隔离接触求解器或积分原因，不能从时间顺序直接认定原因。

| 输出帧 | env0输入COM余量mm | env1–3输入COM余量mm | env1–3 prior位置误差mm |
|---|---:|---:|---:|
| 5 | -5.507 | -5.967 | 0 |
| 10 | -5.453 | -6.440 | 6.581 |
| 20 | .176 | -1.897 | 5.459 |
| 30 | 8.309 | 5.157 | 6.781 |
| 33 | 10.181 | 6.823 | 8.569 |
| 36 | 无后续raw | 7.687 | 10.448 |
| 100 | 无后续raw | 4.233 | 19.158 |
| 1000 | 无后续raw | 8.252 | 95.265 |

env0首次COM≥10mm即最后一帧33，输出COM10.745mm、负载89.305–108.038N；局部合取门槛确实通过，但没有长期保持/抬轮证据，也不能反称它已被证明只是瞬时假通过。失败序列全程输入COM最大8.267508mm@frame999，从未到10mm。

子代理按实际关节名称重排，CPU float64、FK Jacobian中心差分ε=1e-6，使用实际root完整四元数旋转raw force。frame1000按FBL/FAR/RBL/RAR：HIP比例项 `120*(target-actual)` 为+13.861/+9.824/−12.593/−11.201Nm，对应JᵀF为−9.819/−7.283/+9.392/+7.942Nm；KNEE比例项+14.577/+13.723/−14.064/−14.013Nm，对应−13.969/−14.580/+13.930/+14.798Nm。相反符号与近似量级支持承重静差假说，不构成完整动力学闭合：ABAD不匹配，raw Fx/Fy全程近零（最大4.09e-5N），缺真实瞬时速度/effort/接触力矩/完整摩擦和分节重力。frame900→1000 root还后漂4.36mm/2s，不称严格静止。该计算没有CUDA初始化。

主代理原件回读程序 exit0；误取不存在的 `preparation_prior_position_error_m` 时打印null，仅是键名不存在，不纳入量化结论；表中的prior使用子代理独立从原始root及prior参考重算的结果。

## 结论与下一步

教师 A 继续 BLOCKED，单腿抬落、10cm跨越及学生训练均未开始。软件结构缺口已通过独立源码审计和实际 CPU 反例复现；物理首误差的唯一因果未证明。

原规格明确使用期望机身变换求几何 IK、不新增物理控制层。若加入教师专用的有界位姿/承重误差补偿，就需要补充设计，明确物理目标、几何解与执行命令的不同语义，不能暗中用补偿后命令冒称原几何残差仍≤2mm。不得放宽准备门槛、重写实际状态、改PD或再次直接开训。保留剩余单机制原生修订预算，未盲用。
