# v31 有界支撑偏航修正（已部署隔离实测，未取得跨越成功）

## 当前运行优先

**最终：404090/404092均已退出，exit=0；result.json=FAILED_DIAGNOSTIC，recorded4/complete0/locked3/stage3_success0，首次stop为env1/frame139/support_lost，errors=[]。以下仍运行描述为历史。** 原始证据、视频、源码归档 `/tmp/m1-support-heading-v31-original-evidence.tar.gz`，本地/服务器SHA256一致：`3e77947bd4954314777a1af35e685c1e641a56658875e5c986df55fe66c5efb0`。生产训练未启动。

### 本次续查：目标、IK、实际执行的区别

- 同帧FK与测量的body坐标误差约0.2mm量级；目标关节与实测关节存在更大差异，例如134帧右前膝约.1367rad；采样effort与输入时刻相差.015s，不能视为同瞬时因果。已检查样本computed_effort=applied_effort，无执行器裁剪证据。
- 135帧左后膝目标.10000002rad，实测.103646；136帧实测.099091，138帧.091510。目标贴近伸直边界与支撑fraction约1%同时出现。保留原.1rad边界，不放宽。
- CPU冻结几何试验：保持height/heave输入，command rootZ降低10mm，支撑body_goal仅变化1.1e-16m。此通道设计将高度调节交给heave；不能简单称整个高度控制无效。
- 同125帧，将三个支撑目标沿世界Z提高2mm（假设几何，非物理运动）得到全部原.1mm残差内解，max关节步.034246rad（原全目标需.103923）。130/135帧则需要更大几何调整，已不能直接满足原单步.05rad限制。禁止把这些假设解直接下发或声称跨越成功。
- 完整_teacher._step_row CPU冻结试验，只把heave参考降低10mm且保留原.02m/s限速：125帧fraction .5625→.8125；130帧.0151367→.0166016，仍贴边，说明事后限速补偿改善有限。
- 另一CPU假设仅在同承载评分候选间优先膝余量：名义支撑姿态选低40–60mm，但120/125帧实际execution_fraction和heave几乎未变。说明仅改候选名义姿态排序不足；下一步需追踪参考限速/反馈到实际执行目标的一致性，而非再堆一个排序补丁。
- 上述只读脚本及JSONL在v31 ledger保存；未改runtime/PD/力矩/阈值。未将CPU假设当成完整反事实物理回放。最终跨越目标仍OPEN。

最新续查：四份 episode JSON 已生成，均 `verification.errors=[]`、success=false；env0为diagnostic_interrupted，env1–3为diagnostic_failure且failure_locked/unsafe=true。每条144帧；尚未生成最终result/exit，404092仍在运行。源码确认finish_episode之后还会重审中断记录及verify_suite全部记录，因此不能把轨迹停止增长当进程卡死，也不能覆盖候选或重复启动。

同env1实际失败链：第130帧支撑execution_fraction降至.0151367，而活动intent_fraction仍为1；第135帧分别.0102539/1，目标轮Fz11.138N但轮底仅.00005587m，尚未抬离。第136帧yaw=.155382触发freeze4；第139帧右后Fz29.3503N低于原30N门槛，reason5，随后锁定。相较v30偏航冻结129推迟到136、失支撑137推迟到139，只是延后失败，不是跨越成功。仍需区分支撑IK步长受限、实际姿态和承载变化的因果，不凭这些值直接增益加码。

env1视频共30帧，已解码查看0/12/19/23/28/29六帧，能看到10cm场景、接近及机身偏转，未看到完整跨越；视频索引不冒充遥测帧编号。截图位于本地v31 ledger/video_inspect.png，原MP4未改。当前只新增只读证据工具和文档，生产/控制参数未改，未启动训练。

审查修复后完整相关913 passed/189.10s，四runtime本地/CPU/候选逐SHA一致，原v30归档SHA再次核实，无其他train/play/probe/pytest/re-audit、GPU1MiB后，唯一runner404090已启动 `evidence-first-obstacle-support-heading-v1`。服务器记录启动时间2026-10-14T23:07:39Z（保留服务器原时钟，不修改）。同4环境/实际10cm/slow-rolling/load-feedback/最多1000诊断控制步，带视频；不等于已成功，禁止重复启动。

部署文件SHA：heading `d2007f9488065f93e1bee9f3e4aaf5f32eb537213941aef4e87d25570deac50b`；targets `c53454624a28c9ae6cdb21215fe30c45e1f7ee34b58809238f9094fbcf12c251`；teacher `3110a8654ffabb18c5194d4657c9e71a54876660398e735bce6d7ed02ed4d609`；probe `3eac8bc4524f9076a3c8f3e0bc3e5e5cf11e4449a620d6094ae92c445359f62c`。

以下“未部署/回归中”为历史过程记录。生产训练未启动。

## 最新审查修复

第一次修正后的完整相关回归911 passed/189.31s。独立审查 C0/I1/M1：I1为float32 ±π环绕时独立double审计误拒，真实Torch确认，端到端几何反例1RED/1控制通过；仅审计角度比较改为 `max(2e-7,16*dtype_epsilon)`，控制器和其他几何/残差安全门槛未变。64项针对性测试通过10.19s，最终完整回归 `/tmp/m1-v31-final-reviewed-full.log` 运行中。

M1为“非零roll/pitch+yaw混合行”的直接组合不变量测试补强，未发现运行时缺陷，暂缓；已有独立yaw、倾斜、混合行和非有限拒绝覆盖，实际行为仍须native验证。审查未判断的真实成功/CUDA/部署均仍OPEN；不把13项收集错误当通过、不把历史脏改动当已审查。

审查后候选包本地/远端 SHA256 `0a1cd62a68f8040693a82b5111aa3008fbb2b0bb41f1e4d9b7ecf6f656b5a2a1`，仅上传 `/tmp/m1-v31-reviewed-runtime.tar.gz`，未解压、未native。probe新SHA `3eac8bc4524f9076a3c8f3e0bc3e5e5cf11e4449a620d6094ae92c445359f62c`。

用户最新授权直接运行，继续限定教师修正和隔离实际 10cm 跨越测试；不启动生产训练。

## v30 收尾

修正独立审计的失败回滚绑定后，847 项相关 CPU 回归通过（181.23s）。原始四条各 142 帧轨迹经原生产 CUDA 后端反馈事务 sidecar 复核，均无反馈错误。原始结果、原始审计错误和视频未改写；原生跨越仍为零。

原始归档双方 SHA256：`5ddb16b2ffd98ac773156f625a29794a503f6a3b0bcae499bdbe080fda7bdf34`。

## 本轮变化

只在 mode1 且有支撑高度输入时恢复有界偏航通道：测量 yaw 减命令 yaw，经 wrap 后限幅 ±0.05rad，仅旋转剩余三轮的支撑 XY；保留世界 Z 和活动轮目标。原 IK、关节变化限制、分支和验证器未放宽。±0.05 为待物理验证的试验限幅，不是已优化参数。

新增 `execution_heading_delta` 与 v31 指纹，独立审计自行从四元数重建角度和目标；不调用生产 heading helper。近似单位四元数审计漏归一化已被测试复现并修正（1 RED、6 controls pass）。

## 已有验证与待办

- 48 项几何测试先 RED，最小实现后连同原执行目标测试 81 passed。
- 三项审计篡改测试先 RED；集成修正后 113 passed。
- 旧 v29 第134帧由拒绝变为可执行，改为验证原 .1mm 残差和 .05rad 单步限制，不保留过时的“必须失败”断言。
- 原 v30 SHA 校验后提取 115/120/125/128/134 五帧，全部满足原执行界限；这不是物理运动证据。
- 新增非零偏航全局坐标等变性及四元数归一化验证；最新几何/审计组合 81 passed in 11.26s。
- 完整相关回归 `/tmp/m1-v31-full.log` 正在运行，尚无全套通过结论。
- 裸 `pytest` 在 CPU overlay 收集阶段失败（13 errors, 9.28s）：`tests/ame_baseline/test_ame_amp_checkpoint.py`；`tests/rsl_rl/test_parallelism_amp_{checkpoint,discriminator,dual_value,gae,ppo_alignment,update}.py`；`tests/test_hybrid_distillation_schedule.py`、`test_m1_online_teacher_schedule.py`、`test_m1_sdf_probe.py`、`test_mpc_body_leg_collision_headless.py`、`test_mpc_policy_eval_metrics.py`、`test_viewer_reset.py`。原因包括解析到 site-packages 的 rsl_rl 缺项目模块、pxr/Go2Pvcnn 缺失、overlay 无 mpc_policy_eval.py。不是全项目通过，也没有据此修改无关依赖或运行环境。完整原始日志 `/tmp/m1-v31-bare-pytest.log`。
- 尚需最终独立审查、受限候选部署、同场景实际 10cm 跨越与落轮恢复实测。

### 完整回归后续

初次完整相关回归907 passed/4 failed（186.91s）。三个旧 active_progress 测试固定要求 v27 支撑步长，现改为与同版本关闭活动腿精化的支撑解作精确比较，继续核对支撑关节、历史、解码和独立审计。旧 seed137 原本拒绝，现只获得 active_fraction .65625 的合法局部步，不是完整抬腿；验证原残差/限速/独立审计，旧132/133/134仍要求完整活动步。专项 active_progress16通过，seed18通过。修正后完整回归正在 `/tmp/m1-v31-full-corrected.log` 运行，审查和实际部署仍未开始。

代码仅本地和 `/tmp/m1-v30-audit-fixed` CPU overlay 改动。正式候选 `/tmp/m1-teacher-student-candidate-20261014/Go2Pvcnn` 仍为原 v30；生产目录、PT、显示和网络未改。
