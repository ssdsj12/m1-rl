# 1024 baseline18：首次跨越几何与源函数回放

2026-09-18；T306.6h.6a.1a.1。阶段：reference 控制器的全量首次跨越诊断，**不是学习策略验收，也不是修复通过**。

## 目的、输入与验证方式

解释 [baseline18 行为分组](2026-09-18-m1-scale-baseline-behavior.md) 中 18 个首次有序跨越缺失环境。输入为完整 `20260918_gpu7_1024x1600_18_scale_baseline` 的原始 NPZ/initial_randomization，以及绑定的原始 `m1_curriculum.py`、`m1_rsl_rl_wrapper.py`。全部 CPU 只读，不修改配置、样本、验收器、参考源码或 SDK，不启动 Isaac。

两项独立调查分别检查 FAR 高度、RAR 横向；主代理复核初始条件、几何分解，并独立执行两份源函数回放。使用 SSH stdin 调用 `/home/hexinkun/miniconda3/envs/amp/bin/python -`，设置 `CUDA_VISIBLE_DEVICES=''`、Torch 单线程。两份回放退出 0，`torch.cuda.is_initialized()` 均为 False。

源函数回放步骤：

1. 从实际绑定源码 AST 提取 `build_stabilized_task_space_wheel_actions`，不导入 Isaac，不改函数。
2. 用保存的 wxyz 四元数构造旋转矩阵，将轮位置转换到 body frame；action t 使用 sample t−1 状态，phase/Jacobian 使用 sample t 的 prepare 记录。
3. 用首次 phase0 的 s0−2 样本恢复最后 inactive prepare 的 nominal wheel/body height 缓存，再执行原 wrapper 的高度补偿。
4. 使用实际配置：lift .22/rear .20、action scale .8、damping .05、max joint step .25、lateral .06、longitudinal .04、balance 30、lift ramp 10、restore 20、restore offset .12；swing_with_body、support stabilize、balance、active swing XZ only 均开启；lateral recovery gain/max 均为 0。
5. 比较回放的全部 12 列 IK 与已保存 IK。FAR 回放通过只读 return trace 提取函数局部 `target_pos`，转换到 world；它是**与动作数值吻合的源函数重建值，不是原运行直接保存的 target**。

固定几何门槛不变：x∈[.82,.88]、y∈[−.3759,−.0241]、wheel-center z≥.1609 m、force≤1 N，并要求已有 prelift。有 6 个 FAR 高度缺失、17 个 RAR 横向缺失，并集 18；不能只验收剩余 1006。

## 初始随机化：有关联，但不能把质量当作单一原因

去除 env origin 后，1024 个初始 root state 完全相同，root z=.6200000048；joint position 相同、joint velocity 为零。只有 BASE_LINK mass 随环境变化，范围 19.250087738..23.24382782 kg；material properties 也有随机化。startup 配置为 static/dynamic friction [.3,1.2]、restitution [0,.15]、64 buckets，base mass additive [−1,3]；reset pose/velocity 无随机扰动，joint scale=1、external force=0、push disabled。

18 个失败环境的质量均值 23.020993 kg，其余 1006 为 21.193013 kg；mass 与 FAR window max-z 的 Pearson r=−.794246，与 RAR window max-y 的 r=−.881991。**这是同一批样本中的关联，未做隔离动力学因果实验。**

反例：失败 env471=23.20337677 kg，成功 env467=23.20344925 kg，差仅 .0000725 kg；最重 env877=23.24382782 kg 也成功。此前三次 8-env 的相同随机化中也包含超过 23 kg 的成功样本。因此不能关闭/缩窄 mass randomization 来宣称修复。material shape axis 尚未独立映射到各碰撞形状，不按行号臆断轮子摩擦。

## FAR：世界坐标抬升目标随机身状态下降

9 个环境 × 14 控制步（120、138..150）的主代理回放，12 列 IK 最大绝对差 **6.854534149e−7**；四元数导出的重力与记录差 **5.960464478e−8**。下表各环境 x 窗口内 applied FAR action 与记录 IK 完全相同，bar force 均为 0。

| 环境 | 实测最高 z (m) | 重建目标最高 world-z (m) | 原高度门槛 |
| --- | ---: | ---: | --- |
| 471 | .158028 | .158220 | 失败 |
| 563 | .159397 | .158933 | 失败 |
| 768 | .155101 | .155283 | 失败 |
| 824 | .157637 | .157752 | 失败 |
| 972 | .152884 | .151830 | 失败 |
| 990 | .149522 | .149169 | 失败 |
| 467，对照 | .193205 | .194827 | 通过 |
| 877，对照 | .196979 | .198385 | 通过 |
| 388，近边界对照 | .161603 | .161481 | 通过 |

6 个失败者经过 x 窗口时仍为 phase1、lift scale=1；不是提前切到落腿恢复，也不是没有经过 x 窗口。原函数对 active FAR 的 body-XZ 目标随 body frame 变换到 world 后同样偏低。

数据流：wrapper 730–741 在 inactive 更新 nominal；742–760 计算 `clamp(nominal_root_z-current_root_z, ±.1)` 并从 nominal body-z 减去；curriculum 823 初始化目标，898–943 加 FAR 抬升，969–983 加 body shift，1067–1102 执行 active swing XZ IK/ABAD=0。support-only merge 不会覆盖 active FAR 的该路径。

从控制步 120 到 142 的目标 world-z 变化，可按恒等式分解为 `Δroot_z + R2_z·Δbody_target + ΔR_z·body_target1`：

| 环境 | 总变化 mm | root-z mm | body-target mm | 姿态旋转 mm |
| --- | ---: | ---: | ---: | ---: |
| 471 | −41.233 | −9.843 | −9.659 | −21.731 |
| 990 | −52.974 | −13.467 | −13.197 | −26.309 |
| 467，对照 | −10.383 | −2.082 | −2.058 | −6.243 |

这证明目标坐标与机身下沉/姿态存在耦合，不证明支撑腿补偿全局符号错误。支撑腿向下伸可能是正确的抬机身动作，**不能将所有腿的高度补偿统一翻号**。还不能从现有记录独立确定机身下沉的力矩/摩擦原因。

## RAR：横向越界包含 root 平移和姿态旋转

对 17 个失败者，取各自真实 x 窗口内 y 最大的样本，归一化 wxyz 四元数，使用 RzRyRx 约定精确分解 world-y 为 root-y、body-y、roll 项、含 pitch 耦合的 yaw 项。主代理重建误差 0；相对 sample0 的分量均值分别为 **−180.894852、+6.623250、+48.674685、−49.618356 mm**。这是运动学恒等分解，不是动力学因果贡献率。

因此不能解释成“RAR 腿自身统一向外多摆约 180 mm”。大部分横移在 RAR 抬腿前的机身运动中已累积；但不同近边界案例不能都归因于 root-y。

同一 RAR x=.85 m 的插值对照：

| 对照 | root-y 差 mm | body-y 差 mm | roll 项差 mm | yaw 项差 mm | 最终轮 world-y 差 mm |
| --- | ---: | ---: | ---: | ---: | ---: |
| 失败471 − 成功467 | −55.482 | +.755 | +12.641 | +14.390 | −27.697 |
| 失败140 − 成功689 | +2.012 | +1.589 | −.665 | −8.018 | −5.082 |

第二对中失败者 root 更靠内，但 yaw 相关项使轮子更靠外，说明简单统一 lateral 偏置不能由这批证据直接推出。

主代理再对 `(env,step,nominal_sample)`=(471,200,94)、(467,197,94)、(140,199,94)、(689,201,95) 执行原函数 CPU 回放。均为 phase7，12 列 IK 最大误差分别 **2.980232239e−7、3.725290298e−8、2.086162567e−7、5.960464478e−8**，prepared action 与 IK 完全相同。active RAR ABAD target=0，XZ-only 求解不消费 RAR y target；不能把函数内算出的 y 目标描述成已启用的横向闭环。

支撑腿 ABAD tracking error 在成功与失败环境中都存在；仅凭该误差不能认定失败因果。当前记录缺少实际关节力矩/限幅、接触力方向及作用点、完整子步速度与碰撞形状映射，尚不足把漂移唯一归因到某个 wheel gain 或摩擦系数。

## 结果、边界与后续

- **诊断取得新证据，行为修复仍未完成。** 前轮是 active swing 的 world 目标高度不足链；后轮是包括 root/yaw 在内的横向轨迹问题。跨后同步或完成锁存都不能补回这 18 个首次跨越事件。
- 本轮不实施新控制律、不增加 lift/gain、不收窄随机化、不放宽 z/y/force 阈值，不改 full-1024 分母，不启动新仿真。
- [phase 重入修复 A/B](2026-09-18-m1-scale-wave-reentry-diagnosis.md) 仍等待用户选择；brainstorming 设计确认门槛未通过，不把自动持续任务当作该选择。A 仅解决完成后同障碍重复激活，首次几何问题另立设计与单变量验证，不能混改。
- 下一物理候选必须保留原负例与初始条件，先 CPU 回归/审查，再按 8-env→1024-env 门槛；不能用当前诊断或原参考控制器成绩代替 policy-only 跨越、大绕行、单进程 10000 更新。

23:32:35 新鲜资源核验：GPU7 UUID=GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e，只有原 reservation PID351307（hexinkun、23:05:13 启动、python sleep.py）占 15744 MiB；其 cwd/exe/script hash 与恢复记录一致。占位使用 m1 runtime 不是任务训练 runtime；本轮 CPU 回放使用 amp。未终止进程。

## Git 与来源

Baseline Ref：完整 run18 / frozen scale Task3；Candidate Ref：无新候选、run19 负例原样保留。repo HEAD=5553e84e90b2b59e09d35b80205c9ff8ba3c524d，formal reference=646f486。

外部参考 `m1_curriculum.py` SHA256=6e630a8f7be6e31d4fbebeec87d1736ab8ac1e764532fca7026ad0c51ecacb5b，`m1_rsl_rl_wrapper.py`=d6c7056d422a83efb028e1053d8ce496879e14b25410d6cf14a789734c82100a；未修改。Key evidence：run18 `initial_randomization.npz`、首段 `samples*.npz`、source bindings；key functions/数据边界如上。

任务状态见 [T306](../todo/T306-m1-ame-long-train-stability.md)。
