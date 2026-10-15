# 活动腿抬轮执行坐标诊断

## 范围与用户目标

用户明确要求实际抬起跨障，不以独立卸载或静态支撑为目标。本轮按确认只读诊断现有实际10cm记录；未运行新物理/训练，未修改runtime、PD、保护或生产。
节点：T306/teacher-feasibility/actual-crossing/lift-load-redistribution/active-leg-command-frame（新子节点，由本次证据触发）。Baseline/Current Work04133e0+既有未提交v14候选；Last Verified不升级为跨越成功。

## 方法和输入

输入为[动态支撑实测](2026-10-14-m1-dynamic-support-implementation.md)冻结四路JSONL。CPU float64重算：接受关节角分别放入command机身位姿和同帧measured机身位姿，比较正运动学轮心；再用实测关节核对实测轮心，并按joint_names核对接受/实际下发目标。只选LIFT且未failure_locked的73+62+62+62=259采样，不把三个同批中断当独立失败。

脚本/输出在本计划.superpowers/sdd/2026-10-14-m1-dynamic-support-measured-lift的diagnose_lift_execution.py和lift-execution-audit.json。服务器只读脚本/tmp/m1-diagnose-lift-execution.py；在候选Go2Pvcnn用CUDA_VISIBLE_DEVICES=''、OMP/MKL1、PYTHONPATH=.:rsl_rl和env_issacsim python执行。记录含源JSONL SHA，未修改源记录。

## 结果

259/259样本：接受关节角放到实际机身位姿下的目标轮心，比当前实测轮心更低。动作接口下发误差0；实测关节FK与实测轮心最大误差0.2511mm，远小于厘米级目标偏差。所录每控制步最后物理子步computed/applied effort差0；不代表全部子步无裁剪，也不证明力矩充足。

env0 frame165（全部为轮心Z，不是轮底）：
- 期望轮心117.146mm；在command机身位姿下，接受关节FK为118.382mm，IK残差约1.34mm，说明求解器满足了它收到的几何目标。
- 同一组接受角放到实际机身位姿：轮心82.315mm。
- 同帧实测轮心97.108mm；因此当前接受角在冻结实际机身下指向更低14.793mm，而非向上。
- command根高614.224mm，actual594.099mm；高度与姿态差共同使上述FK轮心下降36.067mm，不把它全算成根高差。
- 实际关节与目标尚有差值；地面约束/动力学参与其中，不能解释成“命令正确只是电机追不上”。

## 代码机制和对照

m1_teacher_pose.py::feedback_command以physical.root+feedback修正构建虚拟command body，但world wheels不变；world_to_goal_body对全部四腿统一使用此command body求IK。支撑腿需要借这种反向几何纠偏托机身，活动腿却也被一起按尚未达到的机身位姿求解。于是world wheel目标数值上抬高，不保证在实际机身上产生抬起动作。v14的实测领先限制在轮不动后又冻结参考；仅继续加参考高度/力矩不是已验证修复。

冻结几何反事实：只把活动腿目标变换改用measured body，其余三个支撑腿body目标保持原值。env0 frame165 IK valid，活动腿预测轮心116.493mm，目标117.146mm；env1–3 frame180预测115.492mm，目标116.550mm，IK valid。此对照只证明坐标分配能改变目标方向，不是动态安全或跨越成功。
重要限制：直接反事实解相对上次下发最大跳变0.33385/0.37080rad，超过原每步0.05rad上限，禁止直接应用；必须连续衔接并保留回溯/编码/动作限速/真实碰撞/经过/恢复检查。

## 结论与下一步

已定位具体控制分配问题，不再以“先完成卸载”作为额外前置目标。建议仅slowrolling LIFT/PASS将活动腿实际位姿抬轮与支撑腿机身纠偏分配分开；以实测轮轨目标求活动腿IK，保留连续性及失败保护。不能直接把全部腿切成measured body，否则会改变支撑纠偏；不能直接套用大跳变反事实解。
本轮是诊断，不是已修复。需将该坐标分配修订及渐进衔接写成小范围设计/反例后再修改，直接在障碍场景验证，不加独立卸载试验、不盲改PD/奖励/重启PPO。已有多轮控制修正未实现跨越，本次先明确此架构边界而非再叠加参数。

