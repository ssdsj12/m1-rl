# v33 活动轮水平锚点冻结诊断

- 阶段：T306/teacher/actual-crossing/active-horizontal-anchor，OPEN。
- 原始基线：v33，base04133e0工作树，原始归档SHA `f811ccf989893b8c3a9b610f0a12bf932c814cd8ead59bc3f2b528f842b7960c`；当前runtime未修改。
- 输入：stage3_seed101_env1_episode0.jsonl，帧119/120/122/125/129，同帧 preparation_input + execution_body_step + last_applied_q。原始数据不修改。
- 程序：`.superpowers/sdd/2026-10-15-m1-support-height-origin/active_xy_counterfactual.py`；结果同目录 `active_xy_counterfactual_results.jsonl`。服务器 env_issacsim CPU，未启动PhysX或训练。

## 复算与限制

首次诊断脚本错误地给 tolerance_m 标量，接口报错；修正为[1,4]张量。初版使用实测q为seed，产生小解差，不能称精确重放。最终用实际执行器路径的 last_applied_q 为seed，分支符号保持原测量同分支，0.1mm容差/32预算不变，五帧原始解最大q差 <=5.01e-6rad。

只替换最终执行步目标的活动轮XY，Z和三支撑目标不变：完整替换可求解，但最大关节指令差约.082–.092rad，超过原.05rad限制，不可直接部署。替换50%水平差时，五帧IK有效、最大残差<.1mm、最大指令差.03446/.03608/.03639/.03585/.03760rad，均在原限制内。帧119原执行目标相对轮位X=-41.74mm、Z=-11.97mm；半替换X=-20.89mm，Z保持约-11.89mm（容差内）。129原X=-33.20mm，半替换=-16.62mm，Z约+1.2mm。

这证明水平追踪差具有独立可解的修正空间，不证明其为唯一物理失败原因，也不证明跨越。直接跳到实测位置违反速率限制；不得跳过原事务、名义IK、执行器限幅、三轮载荷或独立审计。

## 代码来源与下一步

`m1_reference_teacher._transport_rolling` 只按三支撑轮共同纵向位移运输所有锚点；LIFT保留历史活动轮XY，只有Z使用实测进度。准备阶段活动轮与三支撑差分滚动形成的约4cm水平误差因此继续作为抬轮期间目标。下一设计：在BALANCE→LIFT时以当时活动轮实际XY建立抬轮起点，支撑三轮锚点不动，后续共同滚动运输不变；通过原有有界IK/动作事务衔接，不在每帧追随漂移，也不修改PASS远侧成功证据。需先验证阶段转换/回滚/重试/独立审计合同，再唯一实际10cm实测。旧v33证据保留，不生产训练。
