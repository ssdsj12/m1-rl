# 原地/打滑双惩罚规格记录

## 最新实施与切换（2026-10-12 09:25 UTC）

### 09:29 UTC 部署回执

#### 实际训练更新核验

PID6598现场cwd/cmdline/environ核实2048/cuda0/9799/resume/keep_std/M1_LOAD_OPTIMIZER1/save100/.30。
新run `2026-10-12_17-28-55/bb57e7d` stdout201–202，value .0035/.00081004、surrogate .0052/-.00237612，均有限。
TB202 stage0/新stall和slip率及积分全0（按合同保留stage0旧feet_slide）；GPU23116MiB。
TB6768已替换且只停止核实的旧5041，指向17-28-55；local16006未改/未验证。
6runtime部署SHA与manifest再次逐项核验；首个新PT保存点尚未到达，初始化200非新训练结果。
发布10-12待本轮普通push及独立ref回执，不宣称先前e45a007已含本实现。

- 实现78e6e6a，审查补强6d90e80：183相关CPU通过。独立审查1项Important已反例RED/GREEN修复：原生COMPLETE必须包含非零成熟窗和终止帧场景；无遗留Critical/Important。
- 首次原生6258退出，保留旧日志但不能单独放行；补强6438原生通过并退出/GPU1MiB。4env空地150步0reset/前进.860–.881m/tilt.01108，1.5cm间隙不reset；碰撞仅env0终止/reward-20.20258。新项5阶段隔离、140非零stall样本、历史有力当前无力免罚、1次指定env0 timeout切mixed且保留旧stage/旧force/次步新窗口，rate误差2.98e-8。非策略成功或学习证明。
- 回执 `/tmp/m1-stall-slip-resume-deploy.json`；6runtime备份 `/tmp/m1-stall-slip-production-before-20261012T092849Z/manifest.json`，候选/本地/生产SHA核验。没有热改4885。
- 新PID6598已启动，log `/tmp/m1-ppo-stall-slip-model200-20261012.log`；201+9799到exclusive10000/2048/cuda0/save100/M1_LOAD_OPTIMIZER1/keep_std。首个实际更新待核验，不把启动当训练完成。
- 独立初始化 `logs/rsl_rl/m1_cross_large_complex_ame/stall-slip-initialization/model_200_stall_slip.pt` SHA `792fbd76684db07fac1f9bfa0041ce35e8a3fc7c72497ec6c62d75d6e0d527b7`；逐张量确认模型/Adam和param_groups/课程与原200相同，仅新增reward_contract/m1_reward_conversion。全部旧PT保留。
- 数值边界：两项上限.75/秒，20秒新增费用≤14及gamma.99增量比较不证明整体回报最优。接触滑速是重力平面最低圆盘点近似，不是精确PhysX接触对。预步stall费用有一控制步测量滞后，避免新生行污染。

- 用户已确认书面数值及model200：旧run没有249保存点，200为stage0/streak1，last完整2048/pass1.0；不偷跳stage1。
- Candidate 78e6e6a（核5c2664a）：新增原地/替换当前承重滑移、RewardManager单次dt积分、逐行reset、奖励合同迁移。182相关CPU通过；新31测试包含RED/GREEN及课程/Adam非有限拒绝。
- source200 SHA `098616326b726de0494f2a6376766a67073a01b2d00751ce8ec98f027b12a67f`，39有限模型/33Adam/12正std；显式转换在/tmp/m1-stall-slip-model200.pt，源文件不变。
- 当前旧训练4885已核实cwd/cmdline后SIGINT退出，GPU1MiB；最新完整600 CPU合同/权重/Adam/课程核验，SHA `ff098d40767594b0b4a706d2791f9fa819aec5f9b8f4eafb5136221184f47dd4`。所有PT和日志保留。
- 独立全分支审查与候选原生验证进行中；生产未改、没有长训运行，禁止自动重启旧PID或候选。
- 原生候选/tmp/m1-learning-tests-only-20261012，日志/tmp/m1-stall-slip-native-20261012.log；无训练/native并发。

## 以下为设计时历史

- Purpose/Stage：T306/pure-ppo-learning 的 reward/stall-slip 子节点，关联timeout-without-crossing诊断。
- Baseline Ref：e45a007；Candidate Ref：本设计提交（无runtime代码）；Key Files：m1_required_crossing.py、m1_ame_rewards.py、m1_ame_env_cfg.py、ame_env_wrapper.py。
- 用户已确认双惩罚方向；[规格](../../docs/superpowers/specs/2026-10-12-m1-stall-slip-design.md)明确2秒/5cm、当前承重打滑和有界费用。
- Procedure：只读现有feet_slide接线与rolling residual，确认已有-0.1项且使用history接触最大值；当前改为替换而非重复叠加。
- Input：参考机器人v2/85与88state/12腿/固定轮.30/stage1–3；不引入动作控制。
- Result：建议原地上限.50/秒、打滑.25/秒、滑速容差.03m/s，dt积分；这些细化数值等待书面审阅。
- Verification：文档公式、单位、reset/terminal、阶段隔离、激励风险与验证范围自检；尚无新CPU或原生实现测试。
- Conclusion：设计方向确认不等于已部署；未改生产、未停止/重启训练；保留已有未提交监控notes和两个未跟踪watcher。
- Follow-up：审阅规格后writing-plans/TDD；安全GPU边界验证，显式同谱系奖励合同迁移而非从零训练。
