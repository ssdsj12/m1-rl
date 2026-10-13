# M1 教师支撑姿态与 IK 重设计：分支与方案调查

关联：[T306](../todo/T306-m1-ame-long-train-stability.md) → teacher-to-ppo/teacher-feasibility/support-ik-redesign；阻挡student-withdrawal/ppo-handoff。前置证据：[三次教师原生失败](2026-10-13-m1-teacher-to-ppo-implementation.md)。

## 授权与状态

2026-10-13用户要求今天工作放`10-13`，并允许重新设计支撑姿态和IK。新分支从`cc34c102768b5e960ea49878548a38e3e9263c34`建立，保留`10-12`历史，不改写提交。已有dirty notes/watchers/PT保持，不stage整目录。当前是新设计调查，不是旧候选第三次自动调参；没有修改runtime或启动GPU/BC/PPO。

- Baseline Ref：`cc34c10`，前一教师代码`4ec1bd6`。
- Current Work Ref：`10-13`，本地普通clone。
- Last Feature / Verified Ref：仍为旧候选证据中的`4ec1bd6`/253CPU与FAILED_DIAGNOSTIC；不因文档分支变更称新功能已验证。
- Key Files：`Go2Pvcnn/ame_baseline/m1_reference_teacher.py`、`m1_teacher_adapter.py`、`Go2Pvcnn/scripts/probe_m1_teacher.py`及各自测试；当前未改。

## 调查事实与边界

run3四个10cm回合仍未进入LIFT，先IK_INVALID58/59，再unsafe87；无receipt。run2冻结实测重算已发现前左目标需求长度.544484m超过.54m。不能把run2数值直接套到run3，后者尚缺被拒绝解的完整残差/限位/分支原因。

当前源码`body_shift_error`把anchor-actual与shift表达在锁定heading坐标，后续`target_body`由当前完整root姿态旋转到body坐标后直接减该error。这两个坐标基一般不相同；应显式经过world或同一完整旋转变换，而不是混用分量。当前还会在IK有效性判断前增加body_age，IK_INVALID回退保持实测关节时插值依旧继续。这些是源码已确认的机制风险，不是已经完成物理反事实验证的唯一原因。

新设计保持原资产/质量/重力/PD/关节限位、初始rootZ .62、10cm的8目标+70填充、20s课程和既定完整成功条件。教师可在物理允许范围主动改变姿态，不瞬移/外力扶持；其目标高度不是改资产初始高度。学生仍16维，最终完全撤除教师；碰撞2/控制步累计20不变。旧训练和自动监控继续暂停，旧PT全部保留。

## 已确认的架构选择

1. **推荐：显式机身目标姿态 + 支撑约束 + 可达性受限IK。** 刹稳并建立测量参考；用统一world→desired-body完整刚体变换计算四轮目标，保持独立的机身倾角/高度参考，防止把不断倾斜的实测姿态当作期望姿态。基于实际质量加权COM和接触几何选支撑姿态；COM投影只作候选准备条件，不替代真实三轮载荷/动态安全。IK同时检查所有支撑腿与摆动腿的工作空间、原限位、膝分支和距伸直奇异点的余量，逐步缩小请求姿态增量直至有效，不放宽2mm残差或截断目标冒充成功。推进取决于实测达成和有效解，失败冻结参考/进度并提供完整原因；无法安全维持则本次示范无效并停止，不把失败标签给学生。
2. **备选：有限姿态库 + 局部IK。** 先验证若干可达支撑姿态后插值，较易检查，但容易只适配少数初态、落轮位置与课程场景。
3. **不建议作为本轮：新增动力学WBC/MPC。** 涉及另一控制系统和力矩约束，扩大范围；当前用户未批准重新引入，仍排除。

推荐方案先验证单轮准备/抬落，再同侧前后与相邻障碍衔接，最后原20s完整10cm固定验收集。小样本局部成功不等于95/100教师验收，所有阶段保持原判据；完整教师未达标不推进BC。日志新增实际COM/支撑几何、期望与实测机身姿态、每腿目标体坐标/可达性余量/残差/限位与分支拒绝原因、参考步长及冻结原因，绑定同env/episode/输入输出帧。

## Brainstorming 工作清单

- [x] 复核仓库状态、源码与最新失败证据。
- [x] 核实用户新分支和重设计方向，保持已批准任务约束。
- [x] 提出可选架构与推荐方向；本次为算法/验收选择，暂不需要视觉布局工具。
- [x] 用户确认推荐架构，允许教师主动降低、前后及侧移机身。
- [x] 按确认方案写[正式规格](../../docs/superpowers/specs/2026-10-13-m1-support-ik-redesign-design.md)，明确坐标、支撑、IK接口和有界失败处理。
- [x] 规格自审：明确预测COM近似、候选搜索上限、执行目标连续性及诊断退出不改环境reset。
- [x] 用户审阅并确认书面规格及本版新增数值边界。
- [x] writing-plans形成[实施计划](../../docs/superpowers/plans/2026-10-13-m1-support-ik-redesign.md)，完成范围/接口/反例覆盖自审。
- [ ] 用户审阅实施计划，随后按已指定子代理方式实现/规格/质量审查。

## 本次验证

只读git核查：本地及远端原先均无`10-13`；`git switch -c 10-13`成功，git-dir/common-dir均`.git`，未冒称新worktree。新runtime测试未运行、生产未修改。发布回执以实际独立远端ref核查为准。

## 用户确认后：书面规格

用户回复“确认，允许”，本轮完成书面设计，不重复询问架构许可。文档基线`58a564b`。首版提出机身前后±4cm/侧移±6cm/降低最多8cm、实测COM投影10mm余量、近伸直膝角.10rad及执行腿目标2.5rad/s连续性约束；这些是待审与待物理验证的教师参数，不是已取得效果。全部四腿联合可达性与原2mm残差保持，无解冻结，连续5步无解锁定示范失败。

按brainstorming流程先由用户审阅已保存规格，再写子代理实施计划。没有改runtime/生产，没有GPU或学生训练；既有失败教师验收仍阻断BC。原有dirty notes/watchers不混入本次文档提交。仅检查文档diff、相对链接和范围，不把文档检查称作运行测试。

## 书面规格确认后：执行计划

用户再次回复“确认”，本轮将书面规格标为已批准，并形成六项计划：真实测量/执行目标、受约束IK、机身参考、状态提交、诊断证据、分级原生验收。沿用已指定子代理方式，每项先RED/GREEN后规格与质量审查；主代理独占GPU调度。计划明确当前host/candidate/Python和实际apply目标来源，未读取或修改全局配置。

Baseline Ref：`cb6fde98452efd8fb076eddbd1c8f4fc654ee971`（已独立确认远端10-13）。本轮仅计划/规格状态/README变更；Key Files为`docs/superpowers/plans/2026-10-13-m1-support-ik-redesign.md`与对应spec。Last Feature/Verified Ref不变。文档检查为相对链接、占位符、diff及规格覆盖，不是CPU控制测试。按writing-plans要求等待计划审阅，不重复询问执行方式；原生A未通过仍不允许学生训练。
