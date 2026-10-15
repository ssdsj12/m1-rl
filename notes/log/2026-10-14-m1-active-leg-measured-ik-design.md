# 活动腿IK修正规格与参数核查

最新：[已实施及实际10cm回执](2026-10-14-m1-active-leg-measured-ik-implementation.md)，374CPU通过、1支撑锁停3中断/零跨越，原生exit0/GPU释放；下文为设计阶段记录。

用户批准修正并实测，允许核查其他参数。承接[执行坐标诊断](2026-10-14-m1-active-leg-command-frame.md)，不是重开卸载试验。采用brainstorming将细化写入[规格](../../docs/superpowers/specs/2026-10-14-m1-active-leg-measured-ik-design.md)，书面审阅前未修改runtime/原生/训练。

Baseline/Current Work04133e0+v14未提交候选。节点T306/teacher-feasibility/actual-crossing/lift-load-redistribution/active-leg-command-frame。

## 本次只读参数核查

输入冻结evidence-first-obstacle-dynamic-support-v1四JSONL与contract.json，使用CPU普通Python遍历186×4帧；按applied_target_joint_names映射，不假设USD原始顺序。contract为当次真实原生初始化断言后输出，非最新运行进程证明。

- 744帧control_dt全部0.02，substeps全部4，decimation4，process次数1，action_matches_request全部true。
- env0最大下发关节增量0.0480462313rad；其余0.0476105809，均小于0.05。
- 最大归一化executed action0.196310342；动作尺度为腿1.50rad、轮1/radius；已有逐名目标往返/下发一致证据，不是动作饱和。
- 实际采样腿速度最大3.61888576rad/s；最后子步腿力矩最大16.79509735Nm，computed/applied一致。不能外推全部物理子步没有限幅或力矩一定充足。
- 原生合同腿DCMotor120/5.5/150/20；轮Implicit0/30/200/20；physicsdt0.005×4=0.02。未发现误配，不修改。
- 前后关节符号/几何的实测FK误差此前<=0.2511mm，未发现能解释厘米级反向目标的映射错误，不声称全面物理模型精确。
- 已知physics回调时钟量化与配置dt差异仍需正式恢复证据处理；本轮没有改阈值或声称此问题已解决。

## 选择与边界

推荐已获方向批准的分腿坐标分配；不采用全部腿measured IK（取消支撑纠偏）或增大PD/目标（掩盖错基准）。活动腿按同帧实测body，支撑腿维持command body；最后真实下发目标FK起步有界回溯，保留原0.05rad/步、落腿连续交接及事务回滚，防止0.334rad直接跳变。
文档自审已完成，无TODO/新卸载前置/生产改动。用户随后已确认规格；[四任务实施计划](../../docs/superpowers/plans/2026-10-14-m1-active-leg-measured-ik.md)已写并自审，覆盖分腿目标/连续事务、teacher交接、证据复算、参数审查及直接10cm。按writing-plans技能待计划审阅，执行方法保持inline＋最终独立审查。本轮尚未修复或新实测。未提交：沿用此前Git身份缺失约束，不改全局身份。

