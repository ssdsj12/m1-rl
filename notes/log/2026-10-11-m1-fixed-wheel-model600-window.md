# 固定轮速12腿 PPO：model600 完整窗口

## 后续13:15 UTC：model1100前进通过率进一步下降

9450 stdout/TB1116，cmdline/cwd/env_cfg仍12腿/.30/2048，loss有限。当前run model1100 CPU加载：iter1100/next1101，模型与Adam全有限、12std正有限范围.0171384–.0597787、fixed_wheel_leg_only/.3/12合同保持。SHA `8f36be984b71c130e27eac9499acf06ef40bc5cc7320844c7ff5da6f7773afc3`。

PT.last完整2050回合前进pass_rate.0029268293（6/2050）、2298strict attempts/0success；stage1/streak0，pending1781单列不混入last。对比600的54.09%、800的10.69%，前进通过率继续降到0.293%，固定目标轮速不代表实际机身持续推进。尚无逐帧轨迹，不能确定停滞、偏航、滑蹭或支撑失效何者主导。

301–1116仅796/809/923/974各1次>=2cm预抬诊断，稳定落轮与strict_successes仍全部0；rawdelta587轮非零累计.005036724（归一化量非米）。两次新增稀疏预抬不构成完整技能进展。用户长训优先，未停训、未改奖励/控制器/std、未并发native；后续若安排当前策略逐帧诊断须先安全保存边界与单独GPU时段，不可与22GB训练并发。

## 后续12:16 UTC：首次两次预抬信号与model800

PID9450至892/TB892，12腿/.30/2048合同保持，loss有限/GPU22030MiB。原始TB确认796、809轮各1次>=2cm单轮预抬诊断事件，stdout分别1.0000交叉一致；301–892其余计数0。稳定落轮和strict_successes仍全0；无该事件逐帧视频，不能宣称形成完整跨越。对应rollout碰撞帧1557/1311、最低净空-.0345/-.0349m，聚合量不能归属于这两次预抬所在env/attempt。

当前run model800 CPU核验iter800/next801、模型/Adam有限、12std正有限（.0279362–.0635597）、fixed_wheel_leg_only/.3/12合同完整。SHA b01a6674bd2794683e4897c95e8418a276795dcfc9cbd12ba59bd3aef53abb8b。stage1/streak0，pending1116；last完整2049回合前进pass.1068814/4345attempt/0success，与600的.5408958相比前进通过率下降，不能把pending当完整窗口或把预抬当跨越改善。实际身体进度并非固定轮目标所保证。尚不能由汇总定位失败动作；用户长训优先，未停训、未改奖励/std/生产、未并发native。通知本次新信号后，不重复报告相同两次事件。

2026-10-11 11:12 UTC 只读核验。PID9450/cwd/启动参数/env_cfg/环境变量保持已部署合同：2048env、cuda0、12腿动作、固定轮面目标0.30m/s、keep_std、optimizer恢复。stdout649/TB651，loss有限，GPU22030MiB；未停训、未改生产、未启动native。

当前run `2026-10-11_17-40-08/bb57e7d/model_600.pt` CPU加载成功：iter600/next601，39模型张量和33Adam状态均有限；12个std正有限，约0.03960–0.06322。动作合同version1/fixed_wheel_leg_only/.30及转换来源300 SHA保留。
PT SHA256：`4129351b20b48baae55c87a57332043b9d9dc6175e6dd06249d8a7e6c7777104`。

课程stage1/streak0/pending0；PT.last完整窗口sample_count2054（达到2048后批量越界完成，并非恰好2048），前进pass_rate0.5408958130、strict_attempts6207、strict_successes0。不能把前进通过率当跨越率。

TB原始301–651：>=2cm预抬诊断计数、稳定落轮、strict_successes全部0。prelift_progress_delta有196轮非零，最大0.0001366610231、累计0.001949662420，属于归一化进度而非米；不能因stdout四位0宣称从无任何抬轮增量。近期route_penalty_rate约0.69–0.83，但汇总无法确认具体同轮失败原因。

结论：固定驱动和12维训练仍正常运行，然而350余轮尚未形成严格抬轮跨越，已不是仅最初几轮信号。当前PT没有数值损坏证据；具体支撑/碰撞/净空断链仍需当前策略逐帧诊断，不能套用旧16维模型原因。遵守用户长训优先，不据零计数自动停训、不盲改奖励/std或追加轮数、不并发GPU探针。
