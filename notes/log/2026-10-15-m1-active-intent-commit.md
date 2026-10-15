# v30 抬腿参考独立推进与原子提交

最终原版终态已核实：进程退出0，4recorded/0complete/3locked，stage3成功0，首次env1 frame137锁停。原始审计误报仍保留。原版源码/视频/trace/回执与诊断归档m1-active-intent-v30-original-evidence.tar.gz，双方SHA5ddb16b2ffd98ac773156f625a29794a503f6a3b0bcae499bdbe080fda7bdf34。修正审计41测试通过29.75s、真实env1逐帧独立几何审核0错误，完整回归与同GPU数值后端四路feedback sidecar审核进行中；仅审核纠正，不能将0跨越变为成功。未部署v31/未生产训练。

重要审计更正进行中：native最终episode出现bounded feedback transaction mismatch，独立定位134-136为新accepted回退审核误报。accepted_before已加入当步滚动平移，失败实际应保留retained_physical（134差.35095mm X），记录accepted与retained逐项一致。原runtime/trace未改，原始错误回执保留。新增失败回退7反例RED，修复比较源后40通过1失败：无活动请求时intent篡改.5没有几何差异；本地已加intent==beta规则，待重新GREEN及全回归。不得把本批称为errors空或完整合格。v31航向计划已写，控制实现尚未开始，优先完成证据修正与原始归档。

冻结航向对照完成（20组合、非原生成功）：heading_counterfactual.py保持实际input/pre/名义目标/支撑世界Z/承载/活动目标不变，只在执行支撑水平向量上加入wrap(measured_yaw-command_yaw)的有界旋转，分别cap0/.01/.03/.05rad，经原完整teacher事务/IK/限速/validator。134基线invalid LR残差.1001276mm；.01/.03/.05候选均valid，LR残差.098616/.097156/.097240mm。125原beta.01416，.05候选beta.078125；128原.01123→.03125。活动worldgoal/solved不降。结果表明该通道可在原约束下产生作用，并非物理纠偏或跨越证明；勿把选择的cap当已经验证的最佳参数。全部结果heading-counterfactual.jsonl保留，runtime未更改。

结构性诊断（仅冻结CPU）：在本次真实115/120/125/128帧，保留全部测量、平移、轮目标、支撑Z/load/heave，只给command期望yaw增加.01rad；execution_targets输出support与active body_goal变化严格0。原因是mode1+support_reference路径以measured.quat替代完整command.quat，原设计将姿态交给Z承载通道，但Z通道不提供yaw控制。因此腿部执行链对command航向不敏感，轮速差承担纠偏；不等于已证明它是全部物理偏航原因。下一设计应验证有界航向与承载/平移共存，不能直接恢复原完整姿态XY（历史已证实其roll/pitch项反转移重心），也不能放宽yaw成功标准。heading_channel_diagnosis.py与heading-channel.jsonl保留，无runtime变更。

追加只读执行链排查：同一teacher input的FK(q_measured)与实测轮心body坐标，采样100/110/115/120/125/128/129/133/134主要Z差约-.2mm（活动轮-.22mm），没有cm级坐标错位。actuation采样computed/applied effort逐项一致，未显示力矩裁剪；注意effort采样比teacher input晚.015s，不能将target-input误差直接套PD公式。128四轮命令面速[.075,.025,.075,.025]m/s，而记录实速[.06869,.13155,.07081,.00723]；129右前负速-.14417。该证据只显示跟踪/接触耦合异常，不足认定轮PD或摩擦为唯一原因。原始wheel_force XY为0不能据此声称真实摩擦力矩为0。脚本tracking_diagnosis.py及m1-v30-tracking/yaw.jsonl已保存本地ledger；未修改运行中candidate/PD/门槛。

冻结原因独立CPU复算：使用本次env0已生成episode teacher_config + env1原始input/pre，129帧support_ready/com_ok均true、COMmargin .0393483m，但yaw误差 .159308rad超过 .15；roll .059339/pitch .046175仍在门槛内。128 yaw .148091通过，129开始停止抬腿进度。134左后IK残差 .000100127632m刚越原.0001m（reason6），nominal仍valid；137起右后承载跌破30N触发支撑保护。不能说先抬腿后摔倒，更不能把残差误差单独当物理根因。连续局部修正尚未改变实际抬起结果，下一应检查支撑/偏航/可达性整体耦合，不继续盲叠补丁或放宽门槛。gates.jsonl保留。python388662仍live进行最终审计，不能覆盖candidate或启动新native。

部分现场（非终态）：python388662持续运行，4路stage3 trace生成。env1 frame120 support beta .484375、intent/active fraction均1；125 beta .01416015625但intent1，原始requested .0982700586m、执行goal .0982700288m/solved .0982321501m。证明独立意图通道在native生效，不能证明实际轮抬起：125轮底仅 .0000478029m，Fz[26.50,176.77,106.32,103.69]N，活动轮仍承载。等待同一进程完成并审计，不重复启动或根据部分记录宣布成功。部分快照保存在本次ledger progress-partial.json。

最新现场：完整827CPU通过168.77s，新增扩展34通过23.03s。审查C0/I1/M1；I1物理attempted/accepted独立审计缺口2RED后修复，M1补全四腿×三mode、branch拒绝与全dataclass回滚。首轮3失败为旧共同beta预期2项和旧tiny-slew断言1项，未放宽阈值。5runtime本地/candidateSHA逐项一致，GPU1MiB且无训练/原生/pytest进程后，唯一runner388660于服务器2026-10-14T22:23:37Z启动evidence-first-obstacle-active-intent-v1（服务器时钟保留）。仅隔离10cm实测，非生产训练；目前无成功结论。下文未部署/运行中描述为历史。

Parent T306/teacher/actual-crossing。目标仍真实10cm抬腿跨越并恢复，不以CPU通过或IK合法代替成功。

v29实际125/128帧可行抬升分别被共享beta压掉.143/.176mm。新增真实帧测试先2失败/3通过8.04s；实现后5通过8.04s。实现保留已验证支撑事务，有限搜索独立active参考进度，候选名义IK/实际拼接执行IK/分支/限速/原回调均通过才同时提交physical、command、IK与执行目标；原支撑关节和载荷/高度/heave/反馈历史不变。未改变偏航门槛、轮速、PD或成功标准。

新增execution_intent_fraction区分参考进度与原support beta、执行active fraction；独立审计重建accepted/requested插值，拒绝伪造进度。3个反例先RED，补审核后10通过17.02s。混合环境/float32与64/非crossing/无效行/拒绝回退等扩展共17通过17.39s。极小slew测试允许原.1mm残差内的零关节动作参考微增，但不得声称完整请求完成；这是测试预期修正，不放宽运行门槛。

全相关回归/tmp/m1-v30-full.log正在运行（首轮包含旧版slew断言）；独立审查v30_active_intent_final_review正在进行。候选仍v29源，未启动新native/生产训练。全部历史PT和证据保留。完整结果、审查结论与部署必须以后续现场回执为准。
