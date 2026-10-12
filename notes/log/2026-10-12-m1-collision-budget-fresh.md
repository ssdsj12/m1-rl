# M1 碰撞累计预算与从零训练

最新状态优先：2026-10-12 16:26UTC已部署并fresh开训，PID12788/run2026-10-13_00-26-49/bb57e7d，0–5轮优化有限；model0完整CPU验收通过。下方“候选/暂停/待验收”为保留的过程记录。

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

## 原生最终验收与部署

第二次12469完成200步满预算后，诊断断言错误地假设其他滚动行始终不碰撞，因此要求env1仍为.7而失败；实际env1自行碰撞累计到2.9，未reset。保留该失败证据。修正探针为比较reset前快照与reset后未结束行真实total，不改生产/检测/阈值。

第三次12630完整通过并退出：`/tmp/m1-collision-budget-native-v3.jsonl`320行（319控制步×4env=1276环境帧），唯一COMPLETE；SHA `fa6dd761ae2493eb38d14a43697e6982018ab617fc49521944ad3395abe957ed`。实际200收费步，float32输出积分20.000000298（计账float64准确封顶20）；前199无reset，第200只env0 reset、failure_termination0；其他行非零累计保留。下步env0total0，原始碰撞进入strict共257环境帧，碰撞帧final reward组成已验证。flat100步前进.571–.583m/0reset；stage0/1/2/3/4配置均经过；单行纯timeout无-20；90度姿态失败离散项-20（总reward-20.04725）。没有PPO学习或跨越成功证明。

16:26:43UTC GPU1MiB且全部probe退出后，备份7runtime到`/tmp/m1-collision-budget-production-before-20261012T162643Z/manifest.json`，逐SHA核实部署。新fresh进程12788由kernel flock入口启动；回执`/tmp/m1-collision-budget-fresh-deploy.json`、log`/tmp/m1-ppo-collision-budget-fresh-20261012.log`。已要求fixedABAD/2048/cuda0/flat-first/max10000/save100，清除旧checkpoint/optimizer加载变量；首轮优化/PT审计待下方追加，当前不能只凭进程宣称训练验收完成。

## Fresh 实际更新与首个模型验收

新run `2026-10-13_00-26-49/bb57e7d`（服务器UTC+8命名）实际0–5轮更新；4/5轮value .0584/.0478、surrogate均-.0010，GPU23074MiB。PID12788现场cmdline/cwd/environ核实2048/cuda0/max10000，无resume/checkpoint/CHECKPOINT/M1_LOAD_OPTIMIZER；fixedABAD1/轮速.30不变。

`model_0.pt` SHA `6057f34c8c55bf0d1aae0831da1eac408d658a606adf86916b9873f49ed51f29`；CPU39模型张量和33Adam状态全部有限、step20，8个正std .04961965–.05028835，stage0/streak0/iter0 next1，训练合同v4/动作v2/85policy88critic完整，无action_conversion/reward_conversion。审计`/tmp/m1-collision-budget-model0-audit.json`同时逐项核实7个已部署runtime SHA。不是旧模型续训。新模型已按碰撞预算合同保存，但stage0没有障碍，尚不能据此证明跨越学习效果。

TensorBoard旧10838身份核实后停止，仅替换其6006服务；新PID12992的`/data/logdir`独立核实为本run。6007和local16006转发未动、local未重验。每小时监控m1-ppo已更新为新PID/run/合同与预算指标，禁止旧暂停提示误重启；无实质变化保持安静。GitHub发布回执另见后续追加，不把本地提交当上传成功。

## 收尾回执

普通push后独立ls-remote确认`10-12=6ede420e3cedf65a7026286e1bbd10fa1d515123`，含实现1a2619a/README/实际fresh验收记录。README/notes/spec/plan/测试/探针12文件同步服务器tar-diff无差异；同步时本log SHA为`73ef24389f103b7450c3b55b419cd75bb2c7b44522c081266154974039f4e2e2`（此收尾段追加前）。最终stdout至12轮，11/12轮value .0290/.0281、surrogate -.0010/-.0012有限。预存诊断notes和旧watcher保留，未stage；所有旧PT保留。没有证明跨越能力已改善。
