# M1 教师到独立 PPO：实施与验证

Parent：[T306](../todo/T306-m1-ame-long-train-stability.md)。[规格](../../docs/superpowers/specs/2026-10-13-m1-teacher-to-ppo-design.md)、[计划](../../docs/superpowers/plans/2026-10-13-m1-teacher-to-ppo.md)。用户选择子代理分工，设计不再待审批。

## 安全边界与基线

- Baseline Ref：`4fdf4e2`（计划）；生产代码基线不因文档提交改变。
- Current Work Ref：`10-12`；普通本地 clone，沿用用户选择，不称 linked worktree。
- Candidate Ref：`4ec1bd6`；软件与原生控制/碰撞合同通过，教师可行性A失败。未部署，BC/撤除/PPO均未开始。
- 当前 host：`a21495354824192000872439`。
- 候选：`/tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn`，复制生产15MB代码；不热改生产。
- 开始时 PID1560 是旧 model1400 的10cm GUI play；05:06UTC按已批准验收边界SIGINT，05:08核实退出/GPU1MiB。最后教师诊断17629亦已退出，未重启play或训练。
- 全部旧PT/日志保留，训练与监控暂停；不改网络/显示/全局SSH/Git。

## 基线验证

在生产只读执行，无字节码/pytest缓存：

```sh
cd /root/quad/m1-rl/.worktrees/contact-recovery/Go2Pvcnn
PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= PYTHONPATH=.:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest -p no:cacheprovider tests/test_m1_collision_budget.py tests/test_m1_learning_curriculum.py tests/test_m1_ame_action_contract.py -q
```

30 passed in 1.93s，exit0：旧实现基线，不是新功能证明。本地 bundled Python缺torch/pytest，使用服务器CPU环境，不安装依赖。

## 任务账本

| 任务 | 状态 | 验证与依赖 |
|---|---|---|
| 1 16维合同/profile/runner | 36a1e7e，规格/质量PASS | 21RED→21GREEN；90相关CPU；原生真实16维动作/观测/物理合同通过 |
| 2 每步2分与0→3课程 | cd050106，规格/质量PASS | 52RED→52GREEN；191相关CPU和48消费者回归；原生十步到20/间歇累计/单行reset/终帧不重复扣通过 |
| 3 教师数学/adapter | 初始+修订30e5781/4ec1bd6，软件两审PASS | 实测支撑门控和刹稳后锚定；两个修订预算已用尽，不代表物理可行 |
| 4 原生教师验收A | 探针最终e99be89，A BLOCKED | run1先失支撑；run2/run3先IK_INVALID后碰撞；最后4完整失败回合0成功，正式固定100集未启动 |
| 5 有界BC | 未开始 | 依赖A真实通过 |
| 6 撤除与独立学生B | 未开始 | mean/sample各90/100 |
| 7 critic校准 | 未开始 | actor与BN逐项不变 |
| 8 显式PPO交接 | 未开始 | 新Adam、来源绑定 |
| 9 生产部署/2048 | 未开始 | 所有门槛通过才启动 |

## 结论

截至最后run3：候选软件实现与诊断仪器完成，但教师尚不能完成第一个10cm跨越，故A阻挡任务5–9。主代理最终独立CPU回归253 passed in 15.62s，exit0；不能将其当作物理成功。生产runtime未改，旧训练/监控保持暂停。以下按时间保留历史过程，最新收尾见文末。

### 只读参考审计（Task3输入）

参考commit `8aeb845f73e39fd1e121758522ef05ee2378150f` 的assets/__init__.py明确轮序FAR/FBL/RAR/RBL，当前kinematics命名序FBL/FAR/RBL/RAR，转换[1,0,3,2]；参考12腿后4轮，当前交错列3/7/11/15。当前腿尺度1.50、轮动作等于轮面m/s，不能抄参考raw轮动作7。前腿负膝分支不能使用当前解析m1_ik的正acos分支，按批准当前姿态DLS实现。

参考m1_curriculum.py:944–960在swing_with_body=True时主要随身体滚行通过；不能把20步计时当实际经过。新计划逐分量dq限.25与参考每腿L2限.25不同；新far buffer.15是轮包络越过远边，不是参考障碍中心+.15。宽.10目标需要轮中心至少越过中心.31915，必须保留可达性检查，不能暗改余量。

adapter目标表用_current_course的centers_top/half_extents/ground_z/valid/ids；landing_*包含填充，只作安全几何。必跨轮mask来自progressive_required_wheels，不能用偏移后轮轨洗掉义务；恢复凭据只读recovered_for_course，不写tracker。Y圆柱最低点用实际wxyz旋转，不固定center_z-radius。源仓库未找到覆盖M1 tasks的根LICENSE，数学独立实现、记录来源，不冒称vendored子项目许可证适用。

子节点teacher-feasibility/mapping CLOSED（只读接口定位）；teacher-feasibility/dynamic-support OPEN：运动学参考.06/.04不证明三轮承重，DLS有限也不证明全腿避碰/10cm通过，必须原生时序验收。

### 教师时间预算审计

当前20s/1000控制步，8目标各要求同侧前后轮，共16次单轮恢复。若将30/10/20/20全部新增为每次最短驻留，16×80×.02=25.6s，必然无法通过。批准计划称这些为调度/ramp参数，并要求实际测量晋级，不应额外引入全部强制驻留；实现须明确每个参数用途，并测试时间到了但物理未达标仍不能晋级。参考sequential balance默认0与taskspace balance30不同，PASS无20步硬等待，不能误合并。

这不是已证明教师可行：平均每轮仅62.5控制步（包含接近/恢复），Task4必须记录每事件耗时、实际推进和reset前receipt；五帧恢复可与RESTORE尾段重叠，但terminal出生状态不能补齐旧receipt。新增子节点teacher-feasibility/time-budget OPEN，禁止暗延长20s/减少目标来通过。

Task1实现仅5个指定文件，新增训练合同v5和学生阶段隔离；profile声明16维/每步2分/(0,3)，实际后端不支持则关闭式拒绝，不能称已可训练。独立规格审查进行中，之后质量审查。配置post-init目前是CPU导入边界替身，非真实Isaac实例。

04:20UTC后Task1两阶段独立审查均PASS，无已证实Critical/Important/Minor；规格审查独立21passed/2.60s且5文件SHA一致，质量审查独立31passed/2.80s涵盖runner原子保存与旧课程恢复。已派Task2实现，生产未改。

Task2提交cd050106仅六个指定文件：52 failed/2.03s（预期缺功能）→52 passed/1.82s；十一组新旧回归191 passed/4.66s；runner/checkpoint/stall-slip消费者48 passed/4.58s。均为候选目录CPU，git diff --check通过。实际profile→manager→gate→backend guard接线及row3的.10m/8+70 authoring通过；真实Isaac和最终wrapper物理奖励仍待Task4。已开始独立规格审查，尚不视为审查完成或可部署。

Task2规格审查PASS：独立52 passed/1.82s及29旧回归/1.96s，六文件SHA一致；主代理另复跑98 passed/3.23s。质量审查继续。04:37UTC服务器身份再核实：旧play1560、父1555及cwd/命令一致，GPU9826MiB；未运行训练或原生候选，candidate资产软链接仍只读指生产m1。

Task2质量审查PASS：源码/消费者调用链与diff检查无Critical/Important；没有重复执行parent的98项，不冒称额外测试。Task3教师数学/adapter实现开始，另派只读原生接口审计；不存在并行实现者或GPU任务。

Task3首批RED：候选CPU17 failed/1.66s，预期独立teacher模块尚不存在。覆盖DLS、负前膝分支、encoder越界、实测门控、远侧余量/receipt、reset与只读adapter。GREEN及原生待验。

Task3实现者自审已取得47 passed/3.94s（42教师+5旧action）。四项新增RED实证并修复：合法leg raw>1误拒、横向墙力误作承重、BALANCE→LIFT的body ramp跳变、LIFT→PASS的lift ramp跳变。现在Fz>30且横力≤Fz，body/lift插值计数跨测量phase连续，无新增hard dwell；NaN实测/零quat/reset身份/course id变化/远world平移覆盖。尚待三文件提交与独立两阶段审查，不称原生可行。

Task3已提交0cb211e，仅三指定文件；parent逐SHA对齐候选后独立复跑teacher/action/contract/newcollision/newcurriculum：120 passed/5.54s，exit0。teacher SHA9ead38e8235c4b0368e234d8e187e72f1505a32b5e80e584876dc8cca3dcff07，adapter6500dffa0226eb7a5041d2ca37a719f968ac0b7d6612f45722f4cfd5b279dc4f。只读规格审查开始。flat轮面.30、有目标cruise1.0/PASS.8属于教师动作参考并进参数hash，不改任务command/20s或电机20rad/s限位；实际身体速度待原生测量。

Task3独立规格PASS/47 passed3.78s；质量审查发现1Important（CPU最小反例）：RESTORE四稳定帧→NaN观测返回invalid但stable仍4→下一正常帧即完成。已退回原实现者要求RED/GREEN修复连续性和跳步边界，再由原质量审查者复核；不能忽略问题进入Task4。未改生产/未native。

Task4只读接线发现：EncounterCrossingTracker的episode_complete恒False，wrapper在done行更新前清tracker，因此完整课程必须在非done帧将recovered_for_course与固定required mask逐ID配对（8目标×同侧前后=16）。probe可hook原_reset_idx前保存终止物理和旧episode证据、hook原update后读取receipt，无需改变生产成功判据。显式单行env.reset(env_ids=...)会更新scene/physics forward及obs history，不能只调用_reset_idx后沿用旧obs。stage0空required mask不能被真空all当成跨越成功。

Task4视频只读审计：四行flat-first同stage/column会共享tile origin，env_spacing不会使画面分开。候选probe须按显式env_ids使用robot.set_visibility只切UsdGeom渲染可见性（不改physics/pose/collision），逐行拍摄后finally恢复；不得将叠影当独立四行证据。建议每5控制步10FPS视频、50Hz完整轨迹，另补reset前末帧并记录真实时间映射；原生先检查非黑/单机器人/Fabric可见性再正式计样。AppLauncher先于Isaac导入，candidate代码路径优先、实际16action与1621/1624obs核验；旧1589/1592探针不可沿用。

Task3修复1d7294d：4RED→51 passed/4.10s；所有invalid输出清恢复计数，跳步断连续，同步重复幂等，目标释放延迟到最终动作有效后。原质量审查者独立7passed及原最小反例复测PASS，候选与本地SHA一致，无新Critical/Important。Task4已分派独立实现者，先CPU验收探针再GPU串行。

05:06UTC再次核实旧play1560的cmdline/cwd为旧model1400演示后，仅对该PID发送SIGINT，为原生验收释放GPU；未更改显示/网络或启动训练。释放状态另行核实，不能把信号发送当已退出。

05:08:22UTC：PID1560已不存在，nvidia compute列表空，GPU1MiB，旧play退出确认。主代理对修复后五组CPU独立回归124 passed/5.17s；无原生教师验收结果，禁止将软件通过描述为跨越能力。

Task4探针da9d389仅两个指定文件：首轮27RED/0.21s，补充空物理字段与flat第一实测位置3RED后，最终34探针+119关联=153 passed/8.00s。四模式smoke/contract/teacher/acceptance：默认小探针，teacher短诊断不会A PASS，acceptance固定200回合（两stage各100）。视频实际文件hash/解码/完整时间轴、reset前snapshot、课程16义务和flat至少70%命令位移均检查。CPU/probe阶段审查不等于原生合同或教师通过。

Task4规格审查PASS/独立34passed4.07s；质量审查发现两Important并退回同实现者：圆轮XY投影与整体最低点组合会把明确分离前缘误报穿透（实证轮心[-.13,0,.19]/box顶[0,0,.1]，clears_box=True），应只记录同一实际采样点的内部穿透；validate_paths只校验脚本未绑定实际业务模块导入，可能哈希候选却执行生产，须绑定candidate并校验实际module来源。均为探针证据问题，不改生产判据。未native。

Task4修复232e648：13新增RED→47GREEN，再补真实go2_pvcnn.sensor namespace反例1RED；最终49探针+119相关=168 passed/9.79s。穿透仅同一圆柱采样点XY内部且Z低于顶面；有限采样没见证不能宣称精确无碰撞。实际候选业务模块在导入前绑路径/校验origin，运行初末记录actual文件SHA。原质量审查者复核中；native仍NOT_RUN。

Task4原质量审查者复审PASS：49 passed/5.73s，原几何反例witness=False，污染PYTHONPATH实际导入候选，正常namespace/rsl_rl/teacher profile通过。未发现新增Critical/Important。现放行原实施者为唯一GPU操作者，重核空闲后串行smoke；启动和原生成绩另记，尚不等于A通过。

05:35:04UTC实施者再次确认GPU1MiB/无训练或play后启动唯一smoke PID7373，输出`/tmp/m1-teacher-student-candidate-20261013/Go2Pvcnn/teacher_probe_smoke_20261013_053505`，stdout同路径加`.stdout.log`。启动参数显式unset两fixed变量、候选代码和四Isaac路径、headless/enable_cameras。05:36首次RTX shader编译，05:37真实4env创建/dt.005/step.02；此时尚未合同通过或教师运行。

首smoke退出（05:38:47进程不存在/GPU1MiB）。contract.json真实验证16actions/命名映射/processed targets、policy1621/critic1624（85/88+1536）、PD/轮圆柱/摩擦等；主代理已独立读取该回执。后续stage3坐标断言8项均差2m：探针混用spawn origin与authoring tile origin，不是障碍被移动。946f1f3修复只probe/tests，1RED后169CPU通过；改用terrain.terrain_origins[level,type]且新增USD世界中心↔grounded记录↔course顶面三方核对，不改expected/地形。定向复审中，失败文件保留；尚无warmup图、teacher或A结果。

946f1f3独立定向review PASS/1passed。第二smoke PID8589（05:43:21UTC启动）目录`teacher_probe_smoke_20261013_054420`正常exit0/GPU1MiB，contract/实际stage0与3几何/100控制步通过：elapsed1.999999955s，四行各advance.571159m，无done/碰撞。A明确NOT_RUN。证据下载本地`C:/Users/xk/Documents/project/.native-probe-artifacts/teacher_probe_smoke_20261013_054420`，主代理独立读取json并view_image两图：可见图清晰，隐藏图有时域残影，不能据此称每行视频干净。probe拟关闭DLSS抗锯齿/帧生成（仅当前进程render选项）后重验；生产物理不变。红色地板因候选缺`assets/teacher_object/...mdl`，生产同级亦无assets；仅视觉材质缺失，几何/摩擦/语义raycast合同已验证，不以安装或网络修改绕过。

f5fae36渲染小修：新增1RED→51探针+119关联170passed/9.88s，独立质量定向1passed0.34s并核对实际Isaac schema/render实现PASS。仅probe进程Off/DLSSG=False、3次无physics render并前后仿真时间断言，保存visible/hidden/restored；完整视频文件验收不被warmup替代。放行下一唯一contract模式，仍无teacher/BC/PPO运行。

原生contract PID9783正常exit0/GPU1MiB，目录`teacher_probe_contract_20261013_055200`（实际约05:50UTC启动）。主代理独立读取回执和view图：本体ghost已消除，hidden仍有地面阴影缓存，阴影不作为接触证据。真实env0十步每步2、总2..20，最后仅env0done，live reset_total=[0,10,0,0]；env1隔步2/0累计保留2,2,..10,10。末帧raw=-2.129310608，去正项.034561228后final=-2.163871765，failure_termination0；纯timeout failure0/final.034390513；90°物理失败项-20/final-20.047056198且等于完整manager组合。flat100步和地形合同重复通过。证据本地`.native-probe-artifacts/teacher_probe_contract_20261013_055200`。这不是教师成功。

已放行初始默认教师唯一串行短诊断（两stage各4行/400控制步上限，8s），需逐env完整轨迹/视频，不当100回合A；尚未修改教师配置，最多两次后续修订预算未消耗。BC/PPO继续禁止，先看首次真实失败链。

初始教师诊断run1（PID10196，05:53:12UTC启动）已正常结束，进程不存在/compute为空/GPU1MiB。证据下载`.native-probe-artifacts/teacher_probe_diagnostic_20261013_run1`；两stage各4行×400控制步/8s，8视频SHA与回执匹配。flat无invalid/unsafe/自然done，但8s未达到20s完整验收，不能报flat100%或A通过。result为FAILED_DIAGNOSTIC，8条诊断、0完整回合、0重复，不是正式100回合成功率。

主代理逐帧独立读取stage3 env0：frame36仅一帧BALANCE；37进入LIFT，Fz=[0,190.507,123.735,43.744]；38首次support_lost，Fz=[0,234.391,149.799,26.555]（右后低于30N），左前轮底.006225735m，root vx.281504m/s；39教师读取上一物理帧后才reason3/SUPPORT_LOST返回invalid。env1–3对应37/38。所有stage3行全程无collision/penetration/receipt。可证先失去有效三轮支撑、后fallback，不能把fallback后的动作归为首因，也不能归咎碰撞惩罚。body-shift ramp仍初期且仍有前进速度是待验证调度假设，不是已证明唯一因果。

历史run1保存实际joints/root/forces但未保存执行action/processed targets，不能把关节实测冒充动作。已要求同probe实施者追加有时间戳的原始动作/目标与terminal对齐测试，只修改诊断仪器，不伪造补写旧证据；教师原实现者同时只读分析最小修订。教师物理修订预算仍两次未使用，禁止自动重启验收/BC/PPO。

仪器49dda58：10新增RED→61probe+119关联=180passed12.91s，两个文件已提交；原quality复审中。新增动作前episode/frame/time与teacher action，实际term.process_actions恰一次后冻结executed action/processed targets及命名顺序，terminal仍取旧行冻结证据。历史run1未补写动作。主代理查看视频frame35/40（10fps不能称拍到38瞬间），可见第一次抬轮前后姿态变化；接触力结论来自50Hz记录而非画面猜测。

教师修订1/最多2已放行原实现者：仅BALANCE→LIFT增加完整transported机身偏移XY误差≤.01m、root线速度norm≤.05m/s、原tilt/rate≤.15/.20门控；三轮承重30N不变。新增两参数纳入hash，不加30帧硬等待、不改ramp/fallback/physics/20s/成功标准。输入证据frame36实际vx.2816、vz-.0883，完整偏移尚差约44/60mm；root投影在支撑三角外约29mm只是几何proxy，不冒称实际COM。假设为支撑转移未建立即卸载，实际修订效果须原生证实；不能把同帧有载等同已稳定。

49dda58独立quality PASS：10passed1.78s+无pending原处理路径检查，实际wrapper先clamp再env.step，记录真实term输入/processed_actions，不重算目标或增加physics。教师修订1已提交30e57814747f4541aac5306eb16b04426655517a，仅teacher/tests；14RED→最终teacher/action/probe133passed13.51s，diffcheck通过。v3-native1-balance-readiness指纹，配置两新增阈值；规格/质量复审后方可原生run2，目前GPU仍停止。

修订1独立spec PASS/72passed5.75s；quality PASS/27passed及24例非零yaw/四轮平移/边界组合独立通过。06:14:49UTC原生实施者核GPU1MiB/无训练playprobe后启动唯一run2 PID13595，输出`teacher_probe_diagnostic_20261013_run2`，同run1两stage各4行/400步。显式unset fixed变量，teacher/tests/probe SHA本地候选一致；只新教师门控与已审查动作证据仪器变化，未改生产。结果待验，不预宣称修复失载。

run2结束，06:20:40UTC PID13595不存在/GPU1MiB；SSH teardown为Ncat remoteclosed/exit1，原生日志已完整MILESTONE_A及result，无traceback，不能称SSH exit0。teacher fingerprint `1fa43d977b79af687d5b049d798660aa3ae1ea262a1822d5186af4e02eda0cc4`；全部证据本地`.native-probe-artifacts/teacher_probe_diagnostic_20261013_run2`。stage0四行400步无invalid/unsafe；stage3 env0自然失败122步，env1–3自然失败106步，未排除或重试，result FAILED_DIAGNOSTIC/4完整失败回合/0成功/完整100回合未跑。

run2 env0第一invalid为frame50 IK_INVALID，仍在BALANCE/body_age15/lift_age0，四轮有载且尚无碰撞/失支撑；frame77才首次collision+support_lost，78才锁存COLLISION。不能以95帧锁存后的末态误称碰撞是首因。frame45–49实际执行轮速目标全0，前左合法膝目标逐步趋近伸直（frame49 -.12441rad）；frame50 fallback为动作前实测HIP .33106/KNEE -.26108。母线完整动作/目标/时间对齐verifier errors=[]；主代理独立读45–51帧。下一步只读检查FK与实测的一致性、目标可达性/分支/残差，不先增加IK迭代或松容差。教师仅完成修订1，尚有1次有证据修订预算。

另只读顺序风险：实际箱间距1.1m，当前rear远侧门槛c+.31915；下一同道贴地front近Y轴不接触下箱需x_front<c+.95410，因此front-rear跨度需<.63495m。run1前期实际跨度.67082–.69841m若保持则存在后续顺序冲突；此为条件性投影推导，不是run1/run2真实碰撞，也不是全局不可达。约13.8s PASS+1.6s恢复的20s预算估算依赖实际速度/位置假设，不当严格时间下界。未修改目标/时间/余量绕过。

run2 CPU首因审计：旧sample.joints未记录raw robot名字，不能直接用contract动作序。依源码reason5 fallback=动作前实测q，28个命名processed_targets与前一帧raw joints唯一逐值匹配一致，恢复planner→raw索引[1,5,9,0,4,8,3,7,11,2,6,10]；明确是交叉恢复而非原始名字证据。由此FK与实测四轮最大欧氏误差约.246mm，排除厘米级FK错配。frame50输入49/anchor35/body_age15重构前左target_body=[.273555,.245801,-.530020]m，去ABAD后两杆需求.5444836m超过.26+.28=.54m约4.484mm；32次DLS残差4.33664mm，256次4.33657mm且近零膝分支不稳，不是靠增加迭代能解决。当前pitch-.10147rad及anchor高度补偿14.17mm共同进入目标构造。此为冻结实测的CPU几何分析，不是完整物理反事实回放。

仪器e99be89只probe/tests，7RED→68probe+140关联208passed15.62s；独立quality PASS/7passed1.75s，核IsaacLab robot.joint_names与joint_pos来自同一PhysX view。新增实际raw名字和数值快照、episode绑定，不覆盖原action序，terminal仍reset前；未补造旧run1/2证据。

最后教师修订2/2放行：APPROACH capture后BALANCE prep保持live nominal+零轮速；实测全四轮原承重条件、speed≤.05/tilt≤.15/rate≤.20才只锁一次anchor/yaw/support_origin/lift_start并开始原30步ramp。prep不IK/不增body_age/不计时放行，后续修订1LIFT门控不变；不改姿态目标公式、FK、PD、IK容差/迭代、成功、20s或16义务。run1 nominal+停轮后frame70可达speed.04418/tilt.01058/rate.01717且四轮有载只是可用状态证据，不证明新调度必然解决。备选姿态参考修正在冻结观测可达但属于另一机制，本轮不混改。修订2审查后仅最后原生验证；失败则A阻断，不自动追加参数轮次/BC/PPO。

最后教师修订2提交4ec1bd634cf34e5b63334f581db317b4ddeaab39，仅teacher/tests；15RED→155相关passed13.76s，新fingerprint `268f08f985eb9bc86e69464e3520b781f62a26b147cfa341e907fa2327c33f13`。无新phase/参数，捕获时清旧anchor，prep不IK/不推进ramp，测量达标后锁一次再原ramp；候选CPU同步，独立复审中。不得将155测试当教师通过，第三次原生后不再自动教师调参。

修订2独立spec PASS/87passed5.26s；quality PASS/47passed和跨目标旧anchor/延迟捕获/混合batch单行reset独立反例。06:35:36UTC唯一原生run3启动PID17629，原实施者preflight无相关进程/GPU1MiB，四文件SHA核实，输出`teacher_probe_diagnostic_20261013_run3`。同400步短诊断与既有合同，第三次为最后教师修订预算；只若本配置真正可行才做固定完整集，不能将短测当95/100。

## 最后原生run3与停止结论

run3结果为FAILED_DIAGNOSTIC：8条诊断记录、4个自然结束的10cm失败回合、0成功、0重复；平地4行各400步/8s无invalid或unsafe，但未跑完整20s，不能报平地100%或正式100回合成绩。输出已完整下载至`C:/Users/xk/Documents/project/.native-probe-artifacts/teacher_probe_diagnostic_20261013_run3`，主代理独立读取所有verification（errors=[]）及逐个校验8视频SHA一致。全部行保留，未筛掉失败或重试。

- env0：frame36进入BALANCE准备，40实测speed约.04775m/s，41的body_age首次1；根据源码+时序可重建锚定采用input40，但prepared/anchor未单列原始字段，不冒称日志直接记录了锚点。
- frame58首次IK_INVALID，动作前input为episode0/frame57/time11.3899997454，body_age18/lift_age0。输入四轮Fz=[65.4863,138.7226,82.7707,84.6389]N，输出后四轮仍有载，碰撞/费用/支撑丢失均false；尚未LIFT。此时轮目标全0，不能归因持续前进轮命令。
- frame87才首次碰撞与失支撑，Fz=[120.3582,104.9692,22.9903,0]N，预算首次2；88读取87后锁存COLLISION，不能把锁存尾态当首次原因。108预算达到20自然reset；env1–3首次IK_INVALID59、首次unsafe87、预算20终止129。所有行没有经过/恢复receipt，也未进入LIFT。
- 新raw_joint_names与实际joint_pos同源，planner→raw为[1,5,9,0,4,8,3,7,11,2,6,10]，与run2按fallback交叉恢复一致；不回填旧文件。run2前左目标超两杆长度4.484mm是已做CPU几何审计，不能把该数值未经重算直接套给run3。
- 最后诊断PID17629已退出；06:40:32UTC实施者核compute空/GPU1MiB。无新GPU任务，无BC/PPO、无学生PT、无生产runtime部署。

最终候选八组CPU复核：teacher_contract/student_collision/student_curriculum/reference_teacher/teacher_probe_contract及旧collision_budget/learning_curriculum/ame_action_contract，`253 passed in 15.62s`，exit0。两次教师修订已用尽，按已批准失败边界和subagent-driven-development阻断规则停止推进；下一步需重新审阅支撑姿态/可达性控制设计，不能暗改物理、放宽成功、延长回合或继续用失败标签预训练。

独立只读质量审查确认8组JSON/JSONL一致、帧连续/20ms、teacher_action=executed_action、旧terminal一致、teacher源码SHA正确；frame58的hold-current fallback按raw名字重排与input57实测q最大误差约7e-9rad。A阻断结论成立，但run3未记录被拒绝IK解的残差/限位/分支/目标体坐标，因此不得认定唯一IK根因或随后碰撞的唯一控制原因。PNG key01..06对应40/55/60/85/90/108，不含58/87瞬间，50Hz时序用于先后判定。主代理06:43:55UTC独立现场确认17629不存在、compute空/GPU1MiB，无训练或play（pgrep仅返回本次查询shell）。

发布范围为候选代码与失败证据，不是生产部署或学会。README/规格/计划/本账本归本次提交；已有dirty任务索引/历史notes保持工作区内容，不把旧watcher/PT混入提交。
