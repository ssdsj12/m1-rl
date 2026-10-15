# 实测抬轮与受限执行统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除命令滞后、小抬升被IK容差吞掉及目标支撑储备不同步的问题，并直接验证10cm跨越和恢复。

**Architecture:** 保留旧命令FK作为受限插值起点；物理请求以实测高度为基准，执行IK对活动腿采用更紧容差。当前及候选载荷统一限制抬升，物理成功只读实际事件，新增独立复算证据。

**Tech Stack:** Python/PyTorch CPU回归；隔离Isaac原生仿真；PowerShell/SSH；现有教师事务与审核器。

**Spec:** docs/superpowers/specs/2026-10-14-m1-measured-execution-reconciliation-design.md

## Global Constraints

- 不启动生产/BC/PPO，不删旧PT、源码快照或证据，不改网络、显示和无关进程。
- 每步关节变化<=2.5*dt（20ms为0.05rad）；IK最多32次；原分支/限位/工作空间/近伸直约束不变。
- 活动腿执行容差0.0001m；支撑腿及非抬腿阶段保持配置容差（默认0.002m）。
- 实际30N安全门槛不变；预测30至45N线性储备，取当前及两种目标几何的最小值。
- 滚动0.05m/s、加速度0.10m/s²，PD/物理/10cm障碍/原恢复要求不变。
- 原生与训练不得并发；测试通过不等于跨越成功。
- 在已有隔离worktree内实施；Git作者未配置时保留diff和SHA，不伪造作者或全局配置。

## Review Focus

- 活动腿索引变化及批量混合阶段：容差不能收紧错误的腿（Task1）。
- 目标超出最高轮高/非有限：不能通过重基准产生有效越界目标（Task2）。
- 当前承载高而目标承载低：进度必须服从较小储备（Task2）。
- IK拒绝或单行reset：不提交尝试进度、不清其他行（Task3）。
- 证据字段被伪造：独立几何复算必须拒绝，不仅比较日志标志（Task3）。

---

### Task 1: 每腿执行IK精度

**Files:** Modify Go2Pvcnn/ame_baseline/m1_teacher_ik.py、m1_teacher_pose.py；Create Go2Pvcnn/tests/test_m1_teacher_execution_reconciliation.py。

**Interfaces:** solve_constrained_ik(q_seed,target_b,branch_q,cfg=None,*,tolerance_m=None)增加可选[B,4]浮点张量；同device/dtype、有限、>0且<=cfg.ik_tolerance_m。None完全保持旧行为。backtrack_feedback_reference仅execution_mode==1的活动腿设置min(cfg.ik_tolerance_m,0.0001)，其余保持cfg；nominal IK不改。

- [ ] 写RED：标准FK目标活动轮+0.0004m，指定该腿0.0001m后iterations>0、关节变化>0、residual<=0.0001；默认路径仍可0次迭代。参数化四腿/float32/64，其他腿误差0.0004m仍可保持。
- [ ] 写RED：非法shape/dtype/device/NaN/0/放宽容差拒绝；mode0和2不启用新精度；不合法分支和无解目标仍失败。
- [ ] CPU运行新测试，确认失败原因是缺失接口或行为而非环境。
- [ ] 实现逐腿active迭代条件及最终valid判定使用同一容差；反馈事务按阶段生成容差，不裁剪q绕过slew。
- [ ] 运行新测试和既有IK/执行目标测试，Expected全部通过；保存完整命令与exit code。保留diff及SHA，满足作者配置时再按授权范围提交。

### Task 2: 实测基准及统一承载储备

**Files:** Modify Go2Pvcnn/ame_baseline/m1_teacher_dynamic_support.py、m1_reference_teacher.py；Extend新测试文件及tests/test_m1_teacher_dynamic_support.py。

**Interfaces:** measured_lift_step增加keyword measured_floor=False，旧调用不变。True时仅reserve>0且当前安全允许推进才用min(max(accepted_z,measured_z),max_z)作为物理请求基准；新增高度仍用原rate*dt*reserve/lead/ceiling约束，reserve==0保持accepted_z。在教师中只对rolling LIFT/PASS启用，wheel_progress==False仍不提交。若measured_z>max_z或既有accepted_z>max_z，不生成向上新目标，并记录ceiling，不把压低动作称抬升。next_z是请求，不是实际进度。

record_tripod_choice保存两种目标预测的valid与min_load张量；在同帧测量及所选候选下计算min(current,anchor,measured)预测储备，任意无效则0。真实载荷与趋势储备继续在measured_lift_step内取min。

- [ ] 写RED：旧命令低于实测13mm且reserve>0时，请求基准不再低于实测；reserve0完全不增加；命令领先时仍受lead；到达/超过ceiling不新增；遗留False路径不变。
- [ ] 写RED：47.43/45.76/36.75N得到0.45储备而不是1；任一30N/NaN/invalid为0；批量中其他行不受影响。
- [ ] 实现上面两个接口并接入同一帧教师事务，保留世界XY目标和旧命令插值起点。实际成功/经过条件不改，拒绝时不提交参考。
- [ ] 从v17原始证据生成含source SHA的冻结输入113及有效LIFT帧夹具。验证每一步实际输出仍满足原slew，原始输入不伪造；命令追赶未改变实测轮高时成功仍false。多步静态输入只标记为数值追赶实验。
- [ ] CPU运行新测试及dynamic/tripod/feedback相关套件，Expected全部通过；保存结果及未满足条件，不把数值追赶当物理成功。

### Task 3: 证据闭环、独立审查、实际10cm验证

**Files:** Modify Go2Pvcnn/ame_baseline/m1_reference_teacher.py、scripts/probe_m1_teacher.py；Extend执行/动态/反馈证据测试；Create notes/log/2026-10-14-m1-measured-execution-reconciliation.md。

**Interfaces:** 新指纹support-ik-transaction-v18-measured-execution-reconciliation。诊断新增每腿execution_tolerance_m、活动轮执行起点/目标/求解后世界Z、current/anchor/measured预测储备及其min。保存物理请求、实际轮高、命令追赶差与实际相对捕获轮高增量；不得用命令增量命名为实际抬升。

- [ ] 写RED：冻结记录伪改活动腿容差、求解轮高、目标储备、实际进度时独立审核拒绝；reset/换腿/失败/单行事务拒绝不能遗留进度或污染其他行。
- [ ] 审核器从原始q/root/FK及预测几何复算，不调用新目标构造器来证明自身；编码后的真正下发q也满足各腿容差及原限幅。
- [ ] 跑全部相关CPU回归，记录测试数与exit0；裸pytest既有pxr/归档重名限制如仍存在如实报告，不称全库通过。
- [ ] 生成新源码快照、diff和审查包；按既定Native方式调用一次独立最终审查。Critical/Important做反例RED/GREEN修复及完整相关回归，保留审查裁定。
- [ ] 只读核实远端GPU和进程无训练/原生并发。只部署到/tmp隔离候选目录，逐文件SHA一致；使用新唯一证据目录，不覆盖v17。
- [ ] 运行现有first-obstacle/slow-rolling/10cm/4env/seed101原生配置。保留所有视频、逐帧状态、命令、载荷、碰撞和退出码，读取完整result及实际进程终态。
- [ ] 如完整跨越及恢复成立，再审核完整分母与逐轮事件；否则定位首次实际失败并报告未完成。更新notes/index及T306，不自动启动训练、不自动发布。

## 自审与交付

Task1的容差接口由Task3独立审核消费；Task2的三种载荷预测由Task3复算。所有Review Focus已有测试归属。先确认计划，随后连续实施，不在任务间重复索要继续许可。已有隔离worktree和历史证据保留，新的计划账本与证据单独存放。
