# M1 碰撞累计预算与从零训练

- Purpose/Stage：T306/pure-ppo-learning/fixed-abad/collision-budget；用户批准每秒最多5、累计20重置、不追加termination20，并明确改好后直接从零开训。
- Baseline Ref：afe7202（设计），生产固定ABAD实现399cf7b；Candidate Ref：当前10-12工作树。
- [规格](../../docs/superpowers/specs/2026-10-12-m1-collision-five-fresh-design.md) / [计划](../../docs/superpowers/plans/2026-10-12-m1-collision-budget-fresh.md)。用户继续指定当前镜像内逐项执行，不重复启动审批。
- 当前训练仍暂停，生产未改。2026-10-12 UTC现场无训练/回放进程，GPU1MiB后启动隔离candidate原生12181；本进程是探针，不是新训练。

## 设计与输入输出

几何碰撞与腿/机身接触障碍取max，不重复叠加；实际每步费=剩余20预算与5*signal*dt的较小值。脱离碰撞不清累计，reset仅清对应行。manager termination每个common_step_counter最多更新一次，reward读同一快照；自动reset保留旧终止帧快照直到下一控制步。预算结束帧不再扣failure20（含同帧其他失败）；预算前其他物理失败仍扣20，纯超时不扣20。其他费用不退还，回合总奖励不等于固定-20。

训练合同固定ABAD版本4，记录collision_budget配置，拒绝旧版本精确续训。8HIP/KNEE、ABAD0、轮面.30、2048、root.62/PD/std、其他奖励、地形、成功门槛保持。碰撞容错不等于把碰撞经过认作严格跨越。

## CPU验证

- 先12反例RED（缺实现），再12GREEN；新合同反例额外RED，接线后109相关CPU通过（/tmp/m1-budget-green.log）。涵盖200*20ms满预算、间歇保留/单行reset、最后分数截断、重复调用幂等、非有限信号、终止快照/超时/其他失败和checkpoint拒绝。
- 初次相关测试1个checkpoint失败因为系统rsl_rl覆盖仓库版本；使用与训练相同的PYTHONPATH=$PWD:$PWD/rsl_rl后109全部通过，不改测试绕过。
- 裸pytest --maxfail=1在test_m1_sdf_probe.py收集阶段缺pxr，/tmp/m1-budget-full.log；不能称全库通过。
- 原生/独立审查/部署/fresh首轮验收尚未完成，不宣称可学习跨越。

## 后续

原生真实碰撞费用、累计重置、不重复termination、reset行隔离与物理失败保护通过；独立审查重要项闭环；探针退出GPU释放后，备份部署并启动唯一fresh run。新Adam/stage0/no PT与真实更新必须现场确认。旧PT/日志一律保留。

## 审查与补强（部署前）

独立审查2项Important：旧strict碰撞读取已删除reward名，及native只校验raw manager reward未校验wrapper最终值。两项先以新增反例RED复现，再将原始合并signal保留在终止快照、透传strict碰撞门控；探针断言同实际碰撞输入和最终reward=raw-正基础奖励（碰撞无bonus）。补强后161相关CPU通过，/tmp/m1-budget-review-green.log。

首原生12181已退出，320条左右阶段记录但无COMPLETE：累计20/无额外20部分通过，最后180度倒置没有触发现有bad_orientation（它用abs(projected_gravity.z)），故不能称通过。保留原证据。仅诊断夹具改为90度侧倾，生产判据未改；该历史倒置盲区归为T306/termination/inverted-orientation OPEN，不扩大本次修改。新12469验证完整生产接线及最终奖励。

审查minor的原生单行累计保留已按计划补充：env1非零.7状态哨兵不参与真实扣分证据，env0预算reset时必须保持env1.7。CPU core重复同step已测试；adapter生命周期由真实manager探针覆盖。部署/fresh能力及学习效果审查者未判定，仍由主任务现场验收，不作为已通过。
