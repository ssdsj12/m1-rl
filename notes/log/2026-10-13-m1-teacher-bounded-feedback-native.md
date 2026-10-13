# Teacher 有界反馈：v3原生证据

日期：2026-10-13；分支10-13；[规格](../../docs/superpowers/specs/2026-10-13-m1-teacher-bounded-feedback-design.md)、[实施记录](2026-10-13-m1-teacher-bounded-feedback-implementation.md)。这是已有局部准备结果上的一次单机制修订，不是从头训练。BC/PPO/旧watcher保持暂停，生产未改，旧PT/轨迹保留。

## 放行状态

当前软件Ref39a6590：Task1/2/3独立任务审查、整体修复及限定复审已完成。35及168项任务CPU通过；最终14文件聚合451通过/1旧fixture错误，补齐测试哨兵后11项定向补测通过，最终修复57项及12项定向通过。原生合同通过，但准备回放因反馈事务证据不一致停止，Teacher A BLOCKED。以下按时间保留来源和执行过程，不能把软件测试或局部准备当完整跨越。

## 候选隔离与来源

host `root@a21495354824192000872439`，candidate `/tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn`，Python `/opt/conda/envs/env_issacsim/bin/python`。生产`/root/quad/m1-rl/.worktrees/contact-recovery`未写入。本次不安装依赖、不改全局PYTHONPATH/SSH/网络/显示。

主代理独立读取候选五runtime SHA，逐项与本地/任务报告一致：

| 文件（Go2Pvcnn下） | SHA256 |
|---|---|
| ame_baseline/m1_teacher_feedback.py | 1c56c15dbfd898a4a00fce708672ea48e225d39e993172c8fb00d6fff0ef6a17 |
| ame_baseline/m1_teacher_pose.py | 0c55ae1bee8db03f33eaf5f088f36a3ec7ccf41c5e281cb8ffa6580738657ff7 |
| ame_baseline/m1_reference_teacher.py | 5b920d199e3a4684c2413d3c72f6f97b5ec8957058a0ccf8a6f7f4c9e8dbd8dd |
| ame_baseline/m1_teacher_adapter.py | f6e068c7a02983d90b4c7aa6e42c13d5b7491178cbbb9e4806c37d797ce6364e |
| scripts/probe_m1_teacher.py | f218225c91899d81b7ef103d2b088eb8cded4fa5afb72aa8a4bd3cb5b8e721dd |

五文件候选冻结备份`/tmp/m1-feedback-v3-candidate-sources-6189861.tar.gz`，SHA`af28605e1c826b37e090ec4f09b5a31b2d3734a2255ebbd962d1e25456806512`。CPU实际导入candidate的331字段/68整数/schema6/Teacher fingerprint38d3ff681b152894ca0cbadf30a31bf27bdbd1178014cf712ee6709ce997d5e1已核实；原生还要核对自己的import回执。

## 执行边界

最终修复候选Ref39a6590：feedback SHA`676cf5dd250061585fa8d5ad1862a2fbf9d7ed1465a54ef32ec22c5e4a1fd08e`，probe SHA`85ea5cfaeaf01a7e57611a27fcf6d7866f8665dc23ffb875fe87974341ace307`；其余三runtime保持上表。新的独立备份`/tmp/m1-feedback-v3-candidate-sources-39a6590.tar.gz` SHA`e02d704a096d4b8206f896473922f566e3dbaf7e8b6bce199869b46140cf99b9`，旧备份保留。14:56:34UTC现场没有train/play/probe/pytest，GPU0为1MiB/0%；启动前仍需复核。

原生输出必须位于candidate且不存在，分别`m1-feedback-contract-v3`和`m1-feedback-flat-v3`。使用每命令PYTHONPATH包含candidate、rsl_rl及已有`/root/quad/isaac/IsaacLab/source/`六模块根，不改全局安装。单进程flock保护；仍须逐次核实训练/play/probe退出和GPU释放。

按计划先contract，再flat-preparation四支撑准备；首次双ready还需连续5个额外真实控制帧。首次关键失败即停止后续wheel/obstacle/transitions/course/正式200回合，不自动变更增益/PD/判据重试。局部准备不是跨越能力，相关并排行不是独立随机成功率。实际joint_vel与explicit actuator computed/applied effort只做诊断，后两者不是外部力矩传感器；最后子步命令与控制步末速度时序分开。

## 结果

限定复审关闭I1/M1/M2，无新增Critical/Important/Minor；M3继承的abort审计限制保留且不可BC。15:08:31UTC再次核实无train/play/probe/pytest、GPU1MiB后，启动`run-native-v3.sh contract`。contract：RUNNING；flat-preparation及后续：NOT_RUN。

contract已exit0，`result.json native_contract=true`：空地100步/1.999999955s、四行advance均0.571159363m；`collision_result.json passed=true/errors=[]`。录像warmup记录nonblack/isolated_robot及physics_time_unchanged均true。原生import回执核对feedback/pose/teacher/adapter均来自candidate且SHA与冻结源一致。材质MDL缺失有渲染警告，但合同完成；不因此更改资源或渲染配置。

contract进程退出且GPU回到1MiB后启动flat-preparation。它的结果尚未取得，不能据合同成功称Teacher有跨越能力。

### flat-preparation已停止：证据不一致，不是物理摔倒

原生进程exit0仅表示诊断程序完成，`result.json`实际为`FAILED_DIAGNOSTIC`，在env0/episode0/output frame49/control49触发`evidence_invalid`：`bounded feedback transaction evidence mismatch`，`physical_failure=false`。其余行按上限仅多收5帧，到54停止；没有第二次原生或调参。wheel1–3准备、全部single-wheel/obstacle/transitions/course/正式200回合均NOT_RUN。Teacher A继续BLOCKED，BC/PPO未开始。

只读CPU复算保存样本的`preparation_observed`（CUDA未初始化），env0真实input/output连续ready帧为44–49，首次ready加5帧达到局部保持要求。该六帧input/output重心余量12.3846–13.1702mm，跟踪位置误差6.7017–8.3793mm；末帧Fz为104.15/100.58/103.56/98.51N。env0共49帧没有碰撞、失载、termination或action_matches_request失败；腿部applied effort最大绝对值9.1291Nm，未观察到computed→applied裁剪。这是实际执行器命令，不是外部力矩传感器。

env1–3为相关重复轨迹，各54帧无ready，末帧COM余量约5.9176mm，跟踪误差8.3669mm，均无碰撞/失载/动作receipt不匹配；最大腿effort8.2745Nm、无裁剪。被证据错误提前打断，不能称20s物理超时，也不能把1/4写成独立随机跨越率。尚未进入抬腿。

`m1-feedback-flat-v3-summary.json`和`m1-feedback-flat-v3-physical.json`保存只读汇总。原生退出后再次核实GPU1MiB、无train/play/probe。仅允许冻结数据上的CPU根因定位，不放宽容差或重跑，完整验收仍不成立。

关键文件SHA256：result `6f8320df2071221d45ad86e5268ec3f646b145df64cd84cb8d1650c5dd0dbf87`；env0 JSONL `483fff7a3168d5833eb16f2f7fd183e61911fafb8dd3a729faec15737340c323`；env0视频 `e9e4665230e086e2362f87aed3cddc4208e56f615fa393d9605d711e71251da7`；physical汇总`302db96c4e705147a5247bcbea47201b4ebcecb65c40739e5b90d58be46cb244`。四个短视频、result和physical汇总已复制到本地`C:/Users/xk/Documents/project/.native-probe-artifacts/m1-feedback-v3-20261013/`，上述本地三个文件SHA与服务器一致；完整trace留在隔离candidate，不写入Git。视频未凭视觉判为成功。

### 冻结数据CPU定位（不修改验证器）

env0最早在output frame4/input3出现差异，而不是49帧才发生：`accepted_q_5`原生-0.6091251373291016、CPU重算-0.6091486215591431，绝对差2.3484230041503906e-5rad；`math.isclose(rel_tol=2e-5,abs_tol=2e-5)`取max门限2e-5，故拒绝。peer首差异也是frame4，`ik_extension_margin_rad_0`原生0.510185718536377、CPU0.5101754665374756，差1.02519989e-5，略大于相对门限1.02037144e-5（该字段abs门限2e-7）。结束episode时批量复核到此差异，因而49才触发停止。

首个差异帧CPU/native均passes1、first/final beta0；真实request=executed、decoded=processed=applied及四子步receipt逐位一致，不是实际动作回执矛盾或reset context缺失。所能确认的是同源float32的CPU重算未落入原生值的既定容差；不能据此断言全部浮点差异都无害或直接放宽全部阈值。原证据SHA前后不变，CPU检查CUDA未初始化。原生验收结果仍保留FAILED_DIAGNOSTIC，新的numerical-replay验证问题OPEN，本轮未修复/未重跑。

这不是单个孤立采样：原验证器离线重跑env0为41/49帧事务不一致，其他各47/54。上述具体数值和逐位执行核对是各行第一处差异的定位，不代表已穷尽所有后续字段。主代理独立读取`.task3-native-evidence-diagnosis.json`确认count、first exception、执行链和CUDAfalse/artifacts_unchanged，不把整批记录改判为合格。
