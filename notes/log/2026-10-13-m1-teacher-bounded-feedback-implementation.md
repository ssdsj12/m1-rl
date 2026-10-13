# Teacher有界反馈实施记录

日期：2026-10-13；[T306](../todo/T306-m1-ame-long-train-stability.md) → teacher-to-ppo/teacher-feasibility/support-ik-redesign/physical-tracking/bounded-feedback。

用户已确认直接在现有版本继续修正。执行[四任务计划](../../docs/superpowers/plans/2026-10-13-m1-teacher-bounded-feedback.md)，不再重复确认。Baseline Ref ba79ae9；原runtime4f5a875、最后原生de423a7。生产未改、旧PT保留、BC/PPO/监控不恢复。

## 阶段与状态

- Task1：纯张量有界反馈a3a7635，35CPU通过，独立审查无Critical/Important。
- Task2：双参考IK与事务2e5f214，168CPU通过，独立审查无新增问题。
- Task3：实测速度/effort和schema6已实现6189861，CPU与夹具补测完成，任务独立审查通过。
- Task4：集中修复39a6590及限定复审完成，原生合同通过；准备回放因证据不一致停止，后续scope未跑。见[原生记录](2026-10-13-m1-teacher-bounded-feedback-native.md)。

## 基线检查

本地branch10-13，runtime tracked无既存改动，历史docs/notes和两个watcher保留。沿用用户指定本地mirror与远端隔离candidate，不创建新分支/工作树、不修改依赖。

远端host a21495354824192000872439，candidate /tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn，CUDA_VISIBLE_DEVICES为空，PYTHONPATH=.:tests:rsl_rl，/opt/conda/envs/env_issacsim/bin/python -m pytest tests/test_m1_teacher_ik.py -q：**32 passed in2.00s，exit0**。这是已有IK基线，不是新反馈通过。

## Task1 CPU证据

候选CPU `CUDA_VISIBLE_DEVICES= PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest tests/test_m1_teacher_feedback.py -q`：新增API缺失断言初始RED32errors；实现后32passed；补充inactive大有限输入反例RED1failed/34passed，改为不对inactive行累积后最终**35passed in1.56s/exit0**。纯数学模块新增固定参数、heading误差、逐轴限幅/限速、整行禁止正常windup及安全饱和卸积分；固定积分重算不重复积分。只提交两个所属runtime/tests，未改生产/物理/训练。

该结果不认证实际轮速解码、IK事务、真实支撑或跨越；这些属于Task2–4。独立审查通过，保留一项非阻断防御Minor：手工构造/原地修改proposal时select_integral未单独检查积分边界，正常生成路径已限界；终审再评估。模块SHA1c56c15dbfd898a4a00fce708672ea48e225d39e993172c8fb00d6fff0ef6a17，测试SHA092c1a707f1a810f21ce98558b34c9aa4973467d8b6ccd50faa53cf8cd14a15f；本地与候选一致，CPU导入实际来自candidate，CUDA未初始化。

## Task2 CPU证据

2e5f214仅改pose/Teacher/transaction测试/reference_commit测试四文件。初始RED11failed/51passed，区分真实行为反例与缺新API/schema；原共同X漂移无纠偏、退出未归零即捕获及名义无效但执行有效被接受均由断言复现。完成APPROACH清积分另有RED1failed/3passed/14deselected。最终隔离CPU聚合：`tests/test_m1_teacher_feedback_transaction.py tests/test_m1_teacher_reference_commit.py tests/test_m1_teacher_feedback.py tests/test_m1_teacher_pose.py tests/test_m1_teacher_ik.py tests/test_m1_teacher_phase_progression.py tests/test_m1_teacher_reference_validity.py`，**168passed in20.96s/exit0**。

四文件SHA逐项local==candidate；模块真实导入隔离候选，输出CPU、CUDA未初始化。新v8声明331诊断字段/68整数，保存first/final/committed的不同语义；执行拒绝仍返回原认证hold或不可执行，不以未接受目标当命令。Teacher/pose SHA分别5b920d199e3a4684c2413d3c72f6f97b5ec8957058a0ccf8a6f7f4c9e8dbd8dd、0c55ae1bee8db03f33eaf5f088f36a3ec7ccf41c5e281cb8ffa6580738657ff7。独立规格/质量审查通过，无新增Critical/Important/Minor；没有原生物理结果。

## Task3验证过程（已完成，最终状态见上）

第一轮针对schema/实测effort/保持检查的CPU反例为10failed/21passed；其中旧schema5接受和首次ready即结束为真实行为反例，其余为新增API缺失。随后扩大旧trace/video回归的首轮6failed/175passed（425.81秒）：五项旧fixture仍按旧首次ready端点及三步诊断上限构造，另有frozen dataclass测试赋值错误。正在按新增连续五帧要求调整fixture，保留原物理阈值并补中途失稳重计数。

主代理另外发现缺feedback_context的有效事务可能被旧成功fixture跳过校验，已严格拒绝，并以真实CPU事务替代旧合成成功fixture。固定输入缓存只复用纯数学重算，逐帧实际receipt和验收始终独立检查。独立CPU/GPU数学审计保留微小物理单位舍入容差；真实请求/解码/四次apply仍逐位一致。

唯一14文件最终聚合为**451passed/1failed in1001.40s，exit1**。唯一故障是旧episode_reset测试夹具缺现有wrapper的`_m1_required_gate`，断言前即AttributeError；未修改wrapper，仅给夹具补required_gate/stall_window哨兵并断言准确done行。补测`test_m1_teacher_episode_reset.py test_m1_teacher_feedback_evidence.py`为**11passed in8.50s，exit0**；不声称重新跑过452项全绿。六任务文件本地/候选SHA一致，CPU导入隔离candidate、CUDA未初始化，Teacher/pose/feedback哈希保持Task1/2版本。独立审查未完成前不原生。SSH空闲断开时远端CPU仍运行，未并发重跑。

## 整体审查与一次集中修复

整体审查Critical0/Important1：单行reset后的全batch初始化可能提前缓存同行下一帧Teacher输出，下一次decide清空诊断context后，Teacher同帧缓存不重新触发事务observer，合法输出因而缺证据。修复必须按row/episode/frame绑定context，同时让新帧无事务明确为None；不能取消清空并沿用过期证据。

此波同时处理两个小项：手工修改的feedback proposal边界检查，以及准备保持计数器的同行reset强断言。继承的abort完整输入及attempt/time认证限制不扩展修改，abort持续排除BC。修复后只做限定复审，不开启新一轮全分支审查。PD、物理、Teacher控制增益和成功门槛不因此变动。

集中修复39a6590共四文件。真实RED6failed/1passed（2.12s），最终定向GREEN57passed（9.26s），既有生命周期/abort定向12passed/148deselected（25.48s）。主代理独立读取服务器保存日志，并核对五runtime SHA；不把这些定向结果写成重跑全部聚合。三行真实Teacher的异步/同批多行reset、同帧缓存、新帧无事务、旧episode隔离均覆盖。限定复审关闭I1/M1/M2，无新增C/I/M；继承M3仍保留。

## 边界

后续证据接口预查（只读，未启动Isaac）：当前服务器IsaacLab的`articulation_data.py`提供joint_vel（PhysX速度读取）和computed_torque/applied_torque（执行器未裁剪/裁剪后命令）。`articulation.py:1869–1901`复制执行器输出；后者不是额外关节力矩传感器，也不能把Implicit轮估计当实测。Task3需在原pre-reset采样点clone，注明最后物理子步命令与控制步末速度的时序。全部6个现有IsaacLab source目录存在；原生将使用每命令PYTHONPATH，不改全局安装/网络。

只Teacher位置补偿，名义/虚拟/实测分离；PD/物理/判据不变。一次单机制原生修订已使用，证据失败即停止后续scope，未另行重跑。内部SDD账本按任务记录精确commit与审查，不把旧准备1个局部端点或新6帧局部保持当教师学会。

## 执行裁定归档（按作出顺序）

1. 沿用用户指定10-13本地镜像和远端隔离candidate，不新建工作树：用于接续当前版本，保留无关dirty；若判断错误，代价是可回退的局部提交整理，不涉及生产。
2. 允许新增固定积分的纯重算helper：避免两遍事务重复积分；若接口判断错误，代价为小范围helper重构，不改变控制参数。
3. 原生输出改为candidate内部新目录，修正计划原有/tmp外部示例：遵守既有validate_paths边界；代价仅输出路径调整，Isaac导入仅每命令设置，不改全局环境。
4. Task3仅扩展旧episode_reset测试fixture，加入当前wrapper已存在的required_gate/stall_window哨兵与准确done断言：否则测试在断言前崩溃；代价是单个测试夹具修订，不改变生产reset行为。聚合与补测分开报告，不冒称全套重跑。

## Git refs（最终实施）

- Baseline Ref：ba79ae9。
- Candidate Ref：39a6590；分支10-13。
- Last Verified：任务/整体修复/限定复审完成，CPU计数见正文，原生合同通过。flat-preparation证据复核失败，不是Teacher A通过；后续及BC/PPO未运行。
- Key Files：计划Task1–3列出的runtime/tests与本日志。
