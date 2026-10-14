# Teacher 准备目标停滞：实测支撑几何只读调查

日期：2026-10-14 UTC。用户要求持续验证至真实抬腿跨越成功。

## 范围和状态

- Stage：Teacher 支撑准备；Todo：T306/teacher-to-ppo/teacher-feasibility/support-ik-redesign/physical-tracking/bounded-feedback/actual-support-geometry-gap。
- Baseline / Current Work Ref：`b4b5f03756fa44af099ea80526ca230bb4f708a3`；控制 runtime 仍为 `39a6590`，未改源码或部署。
- 原始证据：[v4 完整原生记录](2026-10-14-m1-feedback-backend-native.md)。本轮仅读取既有记录、当前实现与已批准规格，CPU 冻结几何计算，不是新的物理反事实回放，也不是原 CUDA 事务的重新认证。
- 服务器 `a21495354824192000872439` 现场未见 train/play/probe，GPU0 为 1MiB/0%。未开训、未启动 native、未修改生产或旧轨迹。

## 新确认的选择机制

`choose_support_pose` 使用捕获时的四轮 world 锚点筛选预测 COM，再按到上一 accepted 姿态的归一化位移最小选择。候选125就是上一 accepted；它一旦预测合格，位移代价为0。`ReferenceTeacher` 在 BALANCE 每步重选并覆盖 goal，但实测 COM 仅作为进入 LIFT 的门槛，不进入候选支撑几何。

v4 env1/episode0 中：

- 第5帧原候选55的侧移目标为约 -30mm。
- 第31帧 accepted 只走到 -26.2604mm；第32帧开始选择候选125，原 -30mm 目标被中间 accepted 替代。
- 第32–1000帧共969帧，candidate_index 全为125，accepted XYZ 只有一个唯一值，freeze_reason 全为 PREPARATION；实测准备始终未达。
- 第180帧实际 COM 余量0.587622mm，预测旧锚点余量10.725421mm；因此不是反馈完全未执行，也不是这次抬腿后摔倒。该段尚未抬腿。

上述行为符合已批准的“旧锚点预测筛选 + 最小参考位移”规则，当前没有据此证明实现违背规格；它暴露的是该启发式允许实际准备长期不达的设计缺口。实测轮位移的完整动力学起因仍未隔离。

## 冻结几何比较

过程：通过 SSH 的 Python stdin，设置 `CUDA_VISIBLE_DEVICES=`，导入现有 pose/IK 纯数学模块。读取 env1 record 的 preparation_input、feedback_context 和诊断。按捕获 heading 生成原125网格并添加原 accepted，保持原固定 wheel anchors 作为 IK 目标，使用当前实测 body COM 偏移经候选姿态旋转预测 COM；分别对原锚点三角形及本帧实测轮心三角形计算余量。保留原 .62-.08 高度下界、2mm/32次 IK/膝分支，比较两种几何均>=10mm时到上一参考最近的候选。仅研究筛选，不执行动作、不更新任何控制状态。

CPU float32 数值不是原生 CUDA 的逐位复核；frame32的 level 候选姿态也不等同当时仍有微小倾角的 accepted。它是明确的替代筛选几何实验，不能冒充实际移动后的载荷、COM或轮位姿。

| 输入帧 | 原保持姿态：旧锚点预测 mm | 原保持姿态：实测三角形预测 mm | 双几何最近候选 | 该候选实测三角形预测 mm | 最大IK残差 mm |
|---|---:|---:|---:|---:|---:|
| 32 | 10.8861 | 1.2389 | 30 | 14.7923 | 1.9888 |
| 49 | 10.8682 | -0.2100 | 30 | 13.2500 | 1.9203 |
| 180 | 10.7254 | -1.9701 | 30 | 10.9168 | 1.7606 |
| 426 | 10.8169 | 2.7221 | 30 | 15.2542 | 1.2300 |
| 1000 | 11.0653 | 7.3032 | 55 | 10.6342 | 1.9800 |

候选30相对捕获参考约X=-20mm/Y=-30mm/Z不变，候选55为X=0/Y=-30mm/Z不变，均来自已有网格，不新增包络或增益。五帧双几何可行候选数分别24/24/22/27/32。仅保留原候选55不一定足够：第180帧对实测三角形的预测仅1.308878mm，仍不足10mm。

原 record 路径：`/tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn/m1-feedback-flat-v4/stage0_seed101_env1_episode0.json`；读取前后 SHA 均为 `8fe70fd1f964353158c566eb36295278467186b7dd4a42699f97367e02692942`。

## 决策边界和待验证

建议的单机制新修订是候选筛选额外考虑当前实测支撑三角形，同时保留原固定 world IK 锚点、原包络、位移代价、反馈增益和真实 ready 门槛。不通过重新捕获锚点吸收滑移，不降低10mm，不扩大20s，不加力矩控制。

备选仅锁存原网格目标较小，但上述冻结结果表明不能解决全部几何不足；重新设计力矩/接触控制范围更大，目前不建议直接切换。

这是新设计选择，不是已验证的物理修复：实测三角形可能继续移动，COM偏移会随关节变化，候选可能抖动/不可达，且X修正依赖有界轮速通道。必须先确认修订规格，再做负例/审查及串行合同→准备→抬落→10cm；不能因CPU候选可行跳过准备或开始BC/PPO。Teacher A仍BLOCKED。

Key Files：`Go2Pvcnn/ame_baseline/m1_teacher_pose.py`、`Go2Pvcnn/ame_baseline/m1_reference_teacher.py`、原支撑/IK与有界反馈规格。最后独立审查结论另行追加，不预写通过。

## 独立只读审查

`feedback_scoped_review` 完成，未写文件或运行GPU/native。确认该行为符合原规格而非实现偏差；建议新筛选对全部126候选一致应用，独立传入同帧实测轮位，不回写锚点；保留候选计数/代价/平局规则及无可行候选的原拒绝边界。必须校验测量身份/有限性/非退化性，并分别记录两种预测余量、更新合同及fingerprint。不能要求当前COM已合格才搜索，也不能把目标候选的10mm条件强加给尚未到达的插值中间帧。名义CPU IK可行不证明补偿command IK、CUDA执行slew或实际物理可行。此审查支持下一设计讨论，不是实施或验收批准。
