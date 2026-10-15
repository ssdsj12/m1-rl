# 滚动抬轮与机身跟踪耦合定位

日期2026-10-14；T306/teacher-feasibility/actual-crossing/rolling-lift-tracking-freeze。用户要求继续修实际过障。本轮只读复算上一轮原生记录，尚未修改runtime、门槛、PD、生产或启动native/训练。

Baseline04133e0+未提交slowrolling；输入为[上一轮归档](2026-10-14-m1-slow-rolling-crossing.md)，archive SHA c0122ea2d8909c5bc27425032e4c89f95ba2b1bc0edadea02939eff10307115c。teacher SHA ac4abb7afa8a21de9a6bc078936d521293f33f35fdd6a62abeb48e584dffbb2a。Last Feature/Verified不更新为物理成功。

## 方法与结果

逐行读取stage3_seed101_env0..3_episode0.jsonl，按env/frame对齐teacher输入root/接受参考、实测支撑载荷、COM余量、输入姿态、实际关节目标和最后物理子步computed/applied effort。仅统计未锁定LIFT帧；不把静态门控复算当新策略物理反事实。

|环境|未锁定LIFT帧|TRACKING冻结帧|冻结但三轮承重/COM>=10mm/相对角度<=0.15rad帧|最大相对角误差rad|computed/applied effort最大差|
|---|---:|---:|---:|---:|---:|
|0|65|60|51|0.040385|0|
|1|54|48|3|0.055495|0|
|2|54|48|3|0.055495|0|
|3|54|48|3|0.055495|0|

三轮承重采用同帧输入各Fz>30N且横向力范数<=Fz。env0首个符合其他上述条件的冻结frame113，env1–3 frame131。computed/applied torque相同只说明记录的最后子步无裁剪，不说明力矩足以完成抬升或所有亚步无裁剪。

env0 frame112→113位置误差9.821→10.535mm、lift_age固定5；env1 frame130→131误差9.205→10.617mm、lift_age固定6。目标轮轮底仍近地面且有载荷。相对姿态误差小于原0.15rad，所以已确认1cm位置项足以触发冻结，不能归因摔倒或碰撞。

## 代码机制

`m1_reference_teacher.py::_tracked`将root位置norm<=1cm与相对角度<=.15合成一个bool。该bool同时控制body_age、lift_age，且false时将wheels_goal整体回退accepted.wheels_w。因此机身欠跟踪不仅触发机身PI纠偏，也停止新的抬轮参考推进。抬轮动作已被执行，实际卸载不足、body下沉的动力学成因尚未完全隔离。

此前批准的[跨后恢复规格](../../docs/superpowers/specs/2026-10-14-m1-crossing-recovery-outcome-design.md)明确不自行删除_tracked；若其阻挡实际过障需依据实测另行决定。因此本轮不静默放大门槛。

## 候选修订与待决定

推荐仅将slowrolling LIFT/PASS的进度解耦：1cm继续约束机身参考推进和驱动纠偏；抬轮进度单独依据同帧三轮承重、COM余量、姿态、无碰撞及合法IK/关节连续性。准备起抬及跨后恢复检查保持。距离保护、失败锁定和事务回滚不变，仍直接10cm障碍验证。

不推荐直接把1cm整体放大，也不推荐当前就改变PD/力矩参数。推荐方案属于控制门控修订，需要用户确认；尚未编写实现/新验收常量，不承诺能够跨越。后续必须包含root未tracked但支撑安全、支撑不安全、IK拒绝回滚、真实轮底未清障不得PASS等反例，以及同场景实际视频。禁止以51/3帧的静态可用性证明新的运动会安全或成功。
