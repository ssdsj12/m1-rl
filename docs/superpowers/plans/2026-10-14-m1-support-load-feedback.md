# M1 Support Load Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。沿用本线程inline及最终独立审查，用户授权连续实施，无逐项许可。

**Goal:** 闭环修正三条支撑腿执行目标，直接验证10cm抬轮跨越与跨后恢复。

**Architecture:** 纯张量载荷分配/零和有界偏置模块→现有IK事务→真实力反馈。物理轨迹与执行补偿分离，失败回滚，审核独立复算。

**Tech Stack:** PyTorch CPU TDD、隔离Isaac GPU原生、PowerShell/SSH。

**Spec:** docs/superpowers/specs/2026-10-14-m1-support-load-feedback-design.md

## 约束与Review Focus

保留全部历史dirty工作和证据。无生产训练/自动push/删除。实际30N保护、碰撞/穿透/经过/恢复不变，世界Z补偿不混bodyZ；仅LIFT/PASS及RESTORE连续退出。关注活动腿不受补偿、dt只一次、回溯偏置与真实选中执行一致、测量无效不能误推进、目标总量不可使用四轮总量、RESTORE不能跳变。Git作者未配置则保存源码快照不伪造作者。

## Task 1: 有界载荷反馈纯函数

Files: 新Go2Pvcnn/ame_baseline/m1_teacher_load_feedback.py及tests/test_m1_teacher_load_feedback.py。

Interface: propose_load_feedback(raw_fz[B,4], fractions[B,3], active_wheel long[B], previous[B,4], dt[B], valid bool[B]) -> LoadProposal(target_fz[B,4], offset[B,4], velocity[B,4], valid[B])。无效行保留previous/速度0/validfalse；参数类型和dt非法抛ValueError。previous要求有限/零和/活动腿0/幅度合法。几何比例非负且和正。

- [ ] RED：用importlib发现模块缺失断言失败，再覆盖4活动轮/2精度、[12,179,159,35]弱RR向下、总和保持、目标>=45N、总支撑<135拒绝、NaN/invalid单行冻结、饱和边界/错误dt/状态。
- [ ] GREEN：载荷与速度均欧氏投影boxed simplex。求lambda使sum(clamp(v-lambda,lo,hi))=sum_target，80次二分；float32/64守恒误差分别1e-5/1e-10。支持载荷投影lo45/hiS、速度lo=max(-.01,(-.015-b)/dt)/hi=min(.01,(.015-b)/dt)，目标sum0。velocity=-.0002*(target-raw)。offset=b+dt*velocity。
- [ ] Run CPU pytest tests/test_m1_teacher_load_feedback.py，Expected全通过并保存输出/exit。检查数据独立，不引入GPU。

## Task 2: IK与教师事务接入

Files: 修改m1_teacher_execution_targets.py、m1_teacher_pose.py、m1_reference_teacher.py；新tests/test_m1_teacher_load_feedback_transaction.py。

- [ ] RED构造倾斜root、worldZ偏置，独立旋转应与body目标一致；不同active/mode/回溯beta不串行；IK拒绝状态不提交；单行reset/RESTORE退出连续。
- [ ] execution_targets增加可选support_offset_w_z[B,4]，加R_measured^T*[0,0,b]到body_goal后做旧命令FK插值。默认None保持legacy。仅support mask。
- [ ] backtrack_feedback_reference增加previous/proposed support offset；每beta取old+beta*(new-old)，执行目标记录selected offset；启用支撑修正时对应三腿tol=min(cfg,.0001)，活动腿保持v18。保持原slew和encoded检查。
- [ ] 教师scratch调用Task1；仅完整事务成功后提交选中偏置，失败保持旧状态；无效proposal冻结抬升。RESTORE以相同速度/幅度/零和约束将偏置向0退出，未退出不完成恢复。完成/reset清本行，换腿不继承。
- [ ] 配套CPU回归含v18现有全部相关测试，Expected新旧约束通过，保存非预期失败定位。

## Task 3: 独立证据与原生

Files: 修改scripts/probe_m1_teacher.py、新tests/test_m1_teacher_load_feedback_evidence.py、notes/log/2026-10-14-m1-support-load-feedback.md。

- [ ] RED伪改rawFz/target/previous/proposed/selected偏置/修正body目标，审核必须拒绝；新增指纹与配置参数、同帧id、实际输出轨迹。
- [ ] 审核独立标量投影及旋转/FK，不调用目标构造器，复算目标守恒/速度幅度/零和/回溯、每腿tol与下发q。记载子步采样范围，不冒充完整扭矩连续记录。
- [ ] 跑全部相关CPU及裸pytest；如pxr/历史重名既有限制仍在，保留且如实报告。git diff --check、源码快照/SHA、最终独立审查；Important/Critical一次RED/GREEN修复。
- [ ] 只部署/tmp隔离候选；独立核实SHA、GPU空闲和无训练/native；flock唯一新目录启动4env seed101 first-obstacle slow-rolling10cm。持续读取同PID，不因超时重启。
- [ ] 完整视频/JSONL/审核/exit/GPU终态归档SHA。只有实际跨越及恢复完整事件可判成功，否则定位首次失败，不开训练。更新index/T306与账本。

## 自审

Task1输出供Task2原子事务消费，Task3独立复算同接口；世界/机身坐标与阶段不同路径分别有反例。参数和停止边界按已批准规格，不以CPU通过替代物理目标。
