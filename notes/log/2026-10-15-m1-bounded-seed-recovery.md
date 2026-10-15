# v29 有界姿态IK初值恢复

## 最终实测与后续定位

runner381178/python381180已退出，exit0/GPU1MiB；总结果FAILED_DIAGNOSTIC、4记录/3完整/3锁定、stage3成功0，首个锁定env1第138帧；不是跨越成功。归档`/tmp/m1-seed-recovery-v29-evidence.tar.gz`已下载本地v29证据目录，双方SHA `8daa0750038ad941a6535eab807fcaa30a13a5fccddaff64aaeaef005bde484c`。

原133帧IK拒绝已消除，但134帧LR执行残差.100272839mm仍超过原.1mm门槛。真实轮底约.05mm，没有有效离地。第129帧支撑/COM仍合格，yaw误差.158689rad超过.15门槛，使抬腿冻结；不等于抬起后摔倒。差速纠偏已工作，实际轮速未跟踪；接触缓存XY全0，无法据此认定偏航力矩原因。

另确认整体物理参考beta把可行抬升请求压小：125/128帧损失.143/.176mm。CPU完整请求对照通过名义IK和执行门槛，但不能证明动态成功。后续v30独立抬腿参考/原子提交正在本地CPU回归与独立审查，尚未部署；见设计`docs/superpowers/specs/2026-10-15-m1-active-intent-commit-design.md`。禁止自动重启v29或生产训练。

Parent T306/teacher/actual-crossing。用户直接执行授权，目标仍实际10cm抬腿经过并恢复；不生产训练。

v28真实133/134帧因LR膝略低于.10guard，使候选和名义IK双重拒绝。仅修selector不足，统一pose入口的有界初值恢复可使完整事务valid；137仍执行残差.111552mm>.1mm拒绝。详见[v28](2026-10-15-m1-active-execution-progress.md)。

实现：新m1_teacher_seed_recovery仅在有限/硬件限位内/同非零分支/膝幅值正、实际tensor deficit在(0,.01]时把求解初始knee放到既有guard。原始测量、其余关节不动；基础IK不动；所有输出约束/事务限速/编码残差/实际支撑门槛不动。pose5个调用入口使用wrapper；fingerprintv29。不是把越界实测当安全，也不是直接裁剪动作。

验证：14单元RED→GREEN；真实v28四帧中的133/134先RED，再整条事务与独立编码审核GREEN，18通过7.22s。旧失败帧feedback_context=None，用新重放observer采集实际反事实context，未改审核规则/原始证据。完整806通过142.79s，日志保存v29证据目录。

独立审查C0/I0/M2。保留minor：132未自动断言完整基线等价/137未断言特定拒绝原因；.01浮点边界可能保守拒绝而未测试相邻值。无epsilon放宽。不可用单元通过证明动态成功。

v28退出exit0/GPU1MiB并归档双方SHA9e28c06b56c8bc77a376f8211967d2dd97b0802f76ea707d46faacbc856a850d后，候选3runtime本地远端SHA匹配：seed43a5fc3b、posea6d5e68f、teacher087c4cbc。启动唯一flock隔离evidence-first-obstacle-seed-recovery-v1，启动回执见ledger。无生产训练/删除/无关改动，实际成功仍OPEN。
