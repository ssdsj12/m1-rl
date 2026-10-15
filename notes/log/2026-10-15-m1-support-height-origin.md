# v33 支撑高度捕获原点

v33实测终态：exit0但FAILED_DIAGNOSTIC，4记录/3完整失败/3锁定/0成功，未完成全分母。原始视频/trace/log已归档，双方SHA f811ccf989893b8c3a9b610f0a12bf932c814cd8ead59bc3f2b528f842b7960c。当前无原生运行、不生产训练。新冻结线索：进入LIFT119活动轮完整目标X比实测后退39.22mm、Z低1.02mm；129仍后退33.21mm、Z仅高1.21mm。完整目标不等于限速后实际动作；尚未证明因果。下一核对阶段切换锚点/接触中水平追踪与倾斜载荷的耦合，不盲改PD或放宽安全。

## 最新运行中实测（未终态）

PID421416现场确认仍运行，四路trace到139帧。env1–3在119进入LIFT，原点.535581827正确捕获并保持；127–129执行fraction/intent=1，但活动轮底仍约.00005m，没有真实抬离或跨越。130首次reason5，root.531820，相比v32同帧.52440下沉减小，但倾斜仍增加。当前trace三支撑Fz180.59/134.07/33.32N；准备输入为上一测量177.43/144.18/41.02N，不混为同一时刻。当前姿态三轮预测最小33.455N，而所选姿态对实测支撑三角预测28.9646N触发30N保护，combined reserve0；不能据此称实际三轮全失载。139锁定，审计进程仍活，不将部分记录当完整终态。下步等终态归档后定位姿态/支撑参考耦合，不放宽门槛、不并发原生、不启动训练。

承接v32：实际未跨越，原始归档双方SHA2e094f42f358d4a2caa118215f573709924b256fd429026427558408c57aa3cb。冻结rootZ扰动发现支撑目标随机身下沉缩短；本次仅修坐标参考，不提高增益或安全阈值。

规格/计划位于docs/superpowers/specs/2026-10-15-m1-support-height-origin-design.md及plans同名。直接执行授权有效。现已完成可选execution_targets support_capture_root_z[B]：三支撑有效高度=stored+measuredZ-origin，活动腿不改变，旧调用legacy。23测试RED→182相关GREEN12.93s，覆盖4active/2dtype/LIFT与RESTORE/零跳变/混合行/非法参数。更大950回归正在/tmp/m1-v33-geometry-full.log。

低层完整950回归已终止通过190.64s。教师capture/commit/rollback/RESTORE和独立证据审计现已接入本地及CPUoverlay：5事务测试RED→GREEN3.36s，5证据测试RED→GREEN3.91s；捕获原点与高度配对提交，RESTORE几何先转换存储坐标，独立审计重建delta并绑定历史，fingerprint v33。

第一轮集成960回归36失败/924通过152.55s：34项旧冻结/手工夹具缺少配对原点，2项合成heading测试替换测量位置后未同步原点。只对测试显式作零delta坐标转换，不修改原始fixture、不放宽生产历史校验；这是当前单步约束验证，不声称还原旧版完整历史。补充最终encode拒绝不提交、单行reset、完成恢复清理及共享生产器遗漏origin也被独立审计拒绝的测试。相关重验/tmp/m1-v33-integration-targeted.log进行中。

bare pytest仍13项收集错误（与v32一致）：ame_baseline/test_ame_amp_checkpoint；rsl_rl/test_parallelism_amp_checkpoint/discriminator/dual_value/gae/ppo_alignment/update；test_hybrid_distillation_schedule；test_m1_online_teacher_schedule；test_m1_sdf_probe；test_mpc_body_leg_collision_headless；test_mpc_policy_eval_metrics；test_viewer_reset。缺rsl_rl相关模块/pxr/Go2Pvcnn及overlay的mpc_policy_eval文件，不称全项目通过，不为此修改环境。

最新：191针对性通过70.98s，最终962相关回归通过197.16s。独立审查Critical0/Important0；非零delta与强制beta回退、最终恢复交接的组合回归覆盖建议非阻断，记录延后。部署四文件SHA逐项匹配，tarSHA aa49b0311ccf3241b56d5b415fc442c1ecc6835f270899faa9def6ccde7adb12。v32原始归档保留且SHA复核，无并发/GPU1MiB后启动唯一runner421414，remote2026-10-15T00:09:03Z，prefix evidence-first-obstacle-height-origin-v1。尚无实际跨越结果，不能称成功；不重复启动、不覆盖运行中candidate、生产训练未动。后续跟踪原始trace/video/result/exit，目标仍OPEN。
