# v28 active execution progress:设计与真实反例

Parent:T306/teacher/actual-crossing/active-execution-floor。基线04133e09加保留的v27候选改动，尚无v28runtime实现/部署/新原生/训练。

v27冻结诊断：166实测LR膝.09988598rad略越.10guard导致所有候选拒绝；只修初始化可恢复候选但不是跨越解。150完整LR目标超几何伸展9.929mm，共同fraction.01123047将活动轮指令压在实测轮心之下。共同支撑Z+15mm的冻结目标可解，但超过单步关节限速；完整事务+.4mm只提交约.0051mm，否定单独加heave目标即可解决。

选定窄结构修正：先保留有效支撑事务，再只对当前抬轮独立搜索合法执行步长；支持三腿、零和载荷/公共高度历史与标量fraction不变，最终全腿编码/限速/实际承载门槛保留。不是所有支撑腿独立推进。数值seed越界修正不混入本次。

规格[active execution](../../docs/superpowers/specs/2026-10-15-m1-active-execution-progress-design.md)；[计划](../../docs/superpowers/plans/2026-10-15-m1-active-execution-progress.md)。用户直接执行授权覆盖重复审批，主代理inline/最终独立review。

已执行：精确v27帧122/137/150配置+动态输入/prestate导出fixture并保留traceSHA；pytest3项5.26s均在activefraction>supportfraction断言RED，非收集错误。证据.superpowers/sdd/2026-10-15-m1-active-execution-progress/red-3.log。下一补全保持支撑/安全/证据负例并最小实现。

v27原生368881最近仍live，四路episodeJSON已生成、最终suite审计未结束；不重复启动或修改运行源码。真实跨越/恢复OPEN，不把CPU反例或合法IK当成功。

## 后续实现与终态更新

## v28原生初步诊断（最终审核未结束）

最终更新：376680已退出/exit0/GPU6MiB，result FAILED_DIAGNOSTIC，4recorded/3complete/3locked/0success，首次env1frame137锁停，physical_failurefalse/errors[]。完整runtime/probe/tests/视频JSONL/log/exit/冻结诊断归档/tmp/m1-active-progress-v28-evidence.tar.gz，远端SHA9e28c06b56c8bc77a376f8211967d2dd97b0802f76ea707d46faacbc856a850d，已复制本地v28证据目录。无实际跨越恢复成功。以下运行中表述为历史。

后续完整事务冻结诊断：exact-config结果与先前selector JSON逐字节相同。只投影choose_support_pose初值仍失败，因为backtrack_feedback_reference内名义IK也使用越界实测seed。仅CPU反事实统一pose solver初值（未改运行源码）后，133/134完整事务valid，4腿执行残差分别最大.094914/.098940mm，活动fraction1，所有原门槛保留；137仍被左后执行残差.111552mm>.1mm拒绝。132合法输入结果不变。不能把投影当物理恢复/保证成功，不能删除137负例或放宽残差。保存本地seed-transaction.json/seed-all-transaction.json及脚本；对应远端/tmp/m1-v28-seed-transaction.json、/tmp/m1-v28-seed-all-transaction.json。下一设计有界合法求解初值恢复，且输出独立重验，不修改测量与安全事实。原生376680仍审核live，候选源码冻结。

376680现场live，实际10cm合同8目标/70填充。第120–132帧mode LIFT的active_fraction=1，support fraction降至.008789，说明活动执行解耦生效但仍未有效离地。122同帧实测活动轮心Z .0972071、执行目标Z .0977057（仅高.499mm），实际轮底仍贴地；不能把轮心变化1.26mm当轮底离地。

133开始candidate_index=-1/reason5。冻结CPU逐帧重放132有效、133/134/137无效与原始记录一致：133仍8候选满足非IK几何/载荷条件，但全部左后NEAR_STRAIGHT(reason4)，实测LR膝.0975438、上次命令.100000024；仅求解初值投到原.10边界（改.0024562rad）可得候选0，残差1.878mm属于名义2mm门槛，不等于执行.1mm/限速/动态验收。137初值偏差增至.008487rad。当前动作/支撑目标仍未解决实际抬起，不能称成功。

首轮冻结诊断沿用v27相同TeacherConfig，v28 env0 record生成后已另启动exact-config重跑。证据/tmp/m1-v28-selector.json及/tmp/m1-v28-selector-exact-config.json。原生正在逐episode审核，未退出/最终suite尚未确认；不修改candidate或重复启动。下一只读初值边界恢复诊断，保留原输出/支撑安全门槛。

最新v28：完整788CPU通过133.91s（原5失败均旧callback次数断言，保留support搜索预算并新增active阶段验证后修正；未放宽runtime门槛）。额外完整heave/load/height/feedback诊断与支撑解码目标精确保留的16测试通过9.23s。最终独立review C0/I0/M3，callback与history覆盖项已处理，非零混合batch及更多篡改组合仍为测试覆盖minor，不是实测成功。

五个运行文件本地/候选远端SHA逐项一致；v27完整归档保留。GPU1MiB、无旧native/训练后，以既有flock启动唯一v28第一障碍10cm诊断，runner376678，证据前缀evidence-first-obstacle-active-progress-v1；远端记录UTC2026-10-14T21:35:42Z，仅照录不修改时钟。尚待原生结果/视频和完整审核，不能称跨越成功；没有生产训练。

v28最小实现已在本地及独立/tmp/m1-v28-cpu验证，非原生candidate部署。3真实帧活动步长改善，同CPU基线支撑关节与heave提交精确不变，单步关节限速保持；3伪造activefraction审核RED→GREEN。合计6通过8.91s。全负例/完整回归/独立review尚未完成，不能宣称可部署或跨越成功。

v27已终态：进程退出/exit0/GPU1MiB，4recorded/3complete/3locked/0success，env1frame170。原生源码、全部原始视频/JSONL、结果/log/exit、tests与冻结诊断归档/tmp/m1-ik-tangent-v27-evidence.tar.gz，SHA0af096343c19b033dcaf23b99a56395b644c00494781b752a9705f9a5666d2fe。本地归档同名位于v27证据目录，核验输出为准。未新原生/生产训练。
