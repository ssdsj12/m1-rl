# v25 支撑平移与姿态解耦

状态：v25唯一原生完成并退出0；4×132帧，0跨越/3锁停/1诊断中断，四路审核errors=[]。跨越目标OPEN，无生产训练。
更新：最终独立审查C0/I0/M1，通过隔离验证准入；2026-10-14T20:08:05Z唯一启动runner357190，output=evidence-first-obstacle-translation-decoupled-v1。结果待查，不重复启动。

## v24真实记录的冻结诊断

输入130机身目标Y误差-32.9895mm，但右后支撑轮当前目标相对实测XY为[16.239,-21.194]mm。将原始变换分解为平移与姿态贡献：平移[34.687,40.054]mm，姿态[-18.448,-61.249]mm。姿态项反转了横向支撑目标，而世界Z又由独立高度/承载回路覆盖，形成不一致的耦合。

同帧FK与实测轮心最大分量误差约0.227mm；右后最终关节目标对应轮心偏差[16.228,-21.198,-6.771]mm，已有向下目标，不宜简单归因为IK方向或没有补载。末物理子步computed/applied torque一致不等于全历史无饱和。

上述是同一实测轨迹的几何分解，不是物理反事实成功。原始数据在v24完整归档；诊断脚本和JSON见 .superpowers/sdd/2026-10-15-m1-support-execution-tracking。

## 范围

仅mode1 LIFT/PASS且存在support_reference时，支撑腿使用实测姿态与指令机身位置计算平移目标，使世界XY为wheelXY+measuredBodyXY-commandBodyXY。活动腿保持原实测坐标变换。Z继续由原高度、公共升降、载荷与有界姿态分配负责。

mode0/no-height与mode2 RESTORE保留原行为；保留非有限目标拒绝、所有物理安全、IK限速/回溯、fraction事务、实际跨越和恢复证据要求。未增加增益/修改PD/std/生产训练。

## 验证

- 旧算法XY反例8失败、legacy2通过；独立审核非零姿态LIFT反例1失败。
- 新实现相关84通过；加入全局刚体变换等变性后完整729通过120.40s。
- SSH观察在完成后断开；重连读取完整日志并确认无pytest进程，没有重复运行。
- 三runtime本地与candidate逐SHA一致：
  - execution_targets b4ae900e514f730c6d1517d88d801d4bf86854d3a84a260d9613278c27f3a0b1
  - reference_teacher b9eb8ccdebd917efb4845409abeb8365cff5d527bf613cf22e64f6818ecadf95
  - probe 5463fdd68498aea525aeae4a248d71d44cda89776a66364a35d78f2eebdcb366
- 已派发只读最终审查v25_translation_final_review，尚待结论。
- 原生前核查GPU1MiB，无train/play/probe；尚未启动v25。

设计与计划：docs/superpowers/specs/2026-10-15-m1-support-translation-decoupling-design.md；docs/superpowers/plans/2026-10-15-m1-support-translation-decoupling.md。

## 原生最终

runner357190/python357192已退出，exit0。result FAILED_DIAGNOSTIC，complete_full_denominator=false，recorded4/complete3/counted4/locked3/duplicate identities0；首锁env1/episode0/frame127，physical_failure=false，errors=[]。env1–3轨迹相同，不当作三次独立试验；env0同步中断，不能计为通过。

四路逐回合审核errors=[]，全部student_demonstration_usable=false。实测活动轮底最大0.0000531077m（约0.0531mm），没有有效抬起/经过/恢复成功。视频env1为28帧10fps，末帧已目视核对，未跨越。

新失败链：左后腿IK extension_margin（相对保留的|knee|>=.10rad边界）从frame118约.17444rad，逐帧降到120的.07567、121约.03、122接近0；123开始IKReason.RESIDUAL=6。123–127残差约.1579/.2057/.2469/.2807/.3068mm，高于该执行通道.1mm门槛，迭代32次仍未通过；127累计5次无效锁停。这里不是更改物理关节限位，也不能把扩大残差容差当修复。

frame127的Fz约[69.19,129.67,95.43,115.48]N，未记录碰撞/穿透/支撑丢失；当前不再是v24右后29.53N保护链，但仍未抬起，不能宣称跨越改善。下一冻结检查支撑目标、垂直补偿与左后可达余量的同帧关系，不放宽安全、不盲调增益、不生产训练。

完整归档/tmp/m1-translation-v25-evidence.tar.gz已复制至本地v25ledger目录，双方SHA256=b4353311d339988ea91b9f56687c2f64b745abf5f2548ed9a78d4f5bedbabba6。含完整4路raw/episode/video、runtime/tests、日志与诊断。最终GPU1MiB。归档内notes为归档前版本，本段为追加回执，不修改归档。
