# 2026-10-14 跨越优先与0.3秒恢复设计

- Stage/Todo：T306/teacher-to-ppo/teacher-feasibility/crossing-recovery-outcome；双几何准备筛选的关联子任务，不是已验证控制修复。
- Baseline Ref：4a48652feab8c95f9d4021cce4205f81fd193f63；Candidate Ref：本次文档提交；Teacher runtime39a6590/verifier de46186未改。
- 目的：落实用户“过程可稍微倾斜，跨完恢复原状态即可”。先确认1秒，后缩短并最终确认0.3秒；1秒要求已撤销。
- 输入：已批准双几何规格、当前TeacherConfig及BALANCE/LIFT/PASS/RESTORE源码、用户新服务器root@a21506654554025984756592。
- 方法：只读核对恢复容差、5帧局部记录、跟踪/承重门控；写[新规格](../../docs/superpowers/specs/2026-10-14-m1-crossing-recovery-outcome-design.md)，不执行控制或仿真。
- 关键发现：恢复倾角.15rad/角速度.20rad/s/腿角误差.15rad/高度误差.08m；静止条件用于准备而非全程。LIFT/PASS仍有跟踪/支撑约束，未证实过严倾角是卡住主因。
- 拟定结果：整机完成评估范围后在前进中形成0.3秒窗口，不给每腿加等待；恢复指标沿用，拟定净前进>=1cm及当前四轮向上力>10N等细节待书面审阅。15个20ms区间不等于15个时间戳。
- 结论：目标及0.3秒已确认；书面细化待审阅，未实现/测试物理效果/改生产、训练、奖励、PD。新服务器未连接，不继承旧主机进程事实。
- 文档验证：提交前核对新增相对链接、文档diff及仅暂存本轮；历史dirty/watchers/PT保留，无runtime测试结果。
- Key Files：新规格、本日志、双几何规格补充链接、notes索引/T306及ai-17/human-17设计状态。
- Next Step：审阅书面细化后编写计划，Teacher A/BC/PPO保持未通过。
