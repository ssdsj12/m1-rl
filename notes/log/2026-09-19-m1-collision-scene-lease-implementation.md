# M1 collision source watch/query lease 实施

2026-09-19；T306.6h.6a.1a.2c/G0-B2b2b。上一目标轮为progress（c608945＋fa66e65、main1452full/0skip和双审），不是等待。fresh linked worktree codex/m1-encounter-lifecycle/fa66e65 clean；主工作区用户dirty变更继续保留，user已批准完整encounter规格，不重复相同审批。

## 范围与状态

计划685280a，新增 `collision_lease.py`/对应tests；订阅先于capture，真实stage/settings变动锁存失效，持有CollisionPathScope和至多一个CollisionQueryBatch。只用amp CPU，未启动Kit/仿真/训练/GPU；SDK/driver/旧adapter/参考/占位不变。输出source-bound不是geometry_verified/CLEAR，实际8-env query无额外physics-step诊断仍为后续必需门槛。

本轮当前完成：代码8a3746f，主代理1565full/152.72s/exit0/0skip，最终实际Carb/M1 CPU集成PASS，SPEC→QUALITY PASS。构造清理P2已关闭；本轮为progress，不是等待/阻塞。下面保留各次RED、拒绝和修复过程；不再重复旧基础审计，直接进入8-env实际query初始化诊断。

Fresh baseline：原scene/query focused432 passed in8.34s/exit0/0skip。实现者首次模块assert RED（1failed/.19s）→最小stage拒绝GREEN（1passed/.24s）；完整扩展实施中。Main full将使用唯一 `/data/hexinkun-m1-acceptance-20260918/encounter-scene-lease-full`，尚未运行，不以旧1452结果冒称新实现通过。

计划prototype已补一项引用释放：既有CollisionQueryBatch.close不清clock，故lease.close必须先关闭batch、保存普通JSON query diagnostics、释放batch引用，再退订与scope关闭。只清lease._clock不足以释放实际clock owner；不改已验收query源码。

## 独立实际Carb订阅CPU证据

独立只读审查者在新的amp CPU进程仅加载 `carb.dictionary.plugin` 和 `carb.settings.plugin`，无Kit/Sim，kit_loaded=false，exit0。初始化为 `carb.get_framework().load_plugins(loaded_file_wildcards=[...], search_paths=[.../omni/kernel/plugins])`；kernel Python路径为 `/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/omni/kernel/py`，共享库路径为同site-packages的omni及amp/lib。没有安装或改包。

仅在本进程自有 `/m1CollisionLeaseProbe/e9035fed26c943638c65903b40a0a6ab` 树设置root/A/leaf/later，四个node订阅（later起初不存在）。真实结果：leaf改变或重复设置同值只向leaf发送CHANGED，不通知ancestor；missing leaf可以预订阅，创建时CREATED→CHANGED。set(A,dict)为整棵替换，A和旧leaf先DESTROYED，A/新节点随后CREATED，leaf再CHANGED；destroy(A)通知A及存在leaf。删后重建原订阅仍有效；dict→scalar通知子leafDESTROYED、A CHANGED；删除自有root通知所有相关节点。回调在对应调用返回前记录。

callback签名确为(Item,ChangeEventType)。probe中bool(item)引发12条getAsBoolInternal incompatible item type5，说明它是值转换、不能用作指针有效性；lease callback不会读取、转换或保存Item。结束显式退订4handles，随后自有树再次set/delete回调0。只改该隔离进程内自有settings，未保存或修改真实配置，不能冒称live Isaac通过。

## 实施中的真实USD发现（保留负例）

基础query/source组35 passed in0.54s；通知组出现21项真实USD失败并伴随`Tried to call an expired python callback`。根因是Tf.Notice.Register不强持有临时Python closure。lease显式持有receiver，receiver内部仍weakref lease；成功Revoke后释放，失败与listener一起保留供重试。此修复后83 passed in0.92s、无expired callback warning；计划同步，不改SDK。

主代理实际8个M1内存实例＋真实Carb集成首轮exit1：第一个BASE_LINK.xformOp:translate Set触发usd_resync，并非持续default motion。独立小probe确认：引用资产的composed属性在匿名root layer还没有local spec，首次Set产生resync＋default，第二次Set只有default。此失效符合既定严格合同，不能为了探针通过豁免resync。探针改为显式保留“首次local opinion拒绝”负例，再于capture前在自有匿名层物化同值pose opinions，检验已存在属性的持续default motion。实际runtime初始化仍须观察是否已完成该结构稳定阶段；CPU准备不代替现场验证，也不修改原资产或生产逻辑。

主代理探针脚本：`/data/hexinkun-m1-acceptance-20260918/collision-scene-binding-probes/verify_actual_scene_lease.py`。新过程只加载dictionary/settings插件；对/physics相关setting的set/destroy仅在该无Kit、无persistence的新CPU进程内，不影响正在运行的实例或磁盘配置。

第2轮实际CPU集成PASS/exit0，45.606605s：8个内存M1实例136body/136collider借用ID在3×5000 path churn后全部正确解码；全部body已存在local pose default修改保持READY、snapshot不变，其他无关settings叶变化不失效。真实collector接synthetic外部SDK完整字段后COMPLETE，finalize为query_source_bound。实际Carb samevalue、ABA、missing-create、ancestor replace分别锁存settings_notice；实际USD scale ABA锁存usd_change；首次local pose opinion仍作为usd_resync负例。各case close均pending_unsubscriptions=0，late query回调无作用，capture/query不改source/cache/settings，磁盘资产不dirty。该结果明确actual_physx_query=false、kit_loaded=false，不是G1行为通过；待最终代码commit后再跑独立full/核心集成并双审。

## 冻结代码与主代理独立验证

实现者scoped代码提交 `b5307f4102396365345480c022372be8f4c1d1e9`，仅新增source263行/tests931行。最终fresh focused111 passed in4.11s、staged diff --check通过；主代理读完两文件并确认commit范围，该版本源码SHA256 `c0e10d693c79b018ad50e423bfa083857d0ea1616a8a7f300a9268aab231a7c2`。主代理独立focused111 passed in4.21s，full1563 passed in153.36s/exit0/0skip，唯一encounter-scene-lease-full。此版本仍被SPEC的真实构造清理P2拒绝，不以测试通过取代合同审查。

冻结代码上的主代理第3轮实际Carb/M1 probe再次PASS/exit0（46.123444s），全部边界与第2轮一致；脚本SHA256 `10f07f74b2ce56bf0dfc7bf5866a0f2ac15291673aa7bd2d8b5b9f50670552e0`。两次CPU通过仍明确没有真实PhysX query或GPU。

新增TDD证据：清理6项RED→补齐全面退订、保留/重试残项与释放path/settings/clock。finalize内部clock错误1failed/110passed→111passed，外层即时锁存query_finalization_error而非等后续poll。独立无lease的Usd.Stage/privatecache对照证明：native已销毁后Boost包装器可能仍由weakref返回invalid null stage，故stage用None或boolFalse判native已释放；settings/clock/query/path等仍严格weakref None，不放宽生产释放责任。跨线程测试用Event并带30s子进程超时，无sleep竞态。

## SPEC P2：构造清理失败无公开重试owner

独立SPEC 111focused/4.28s/exit0，其余合同无阻塞，但正常`CollisionSceneLease(...)` capture失败且token2退订失败时，构造不返回owner。弱回调不能保活lease；异常释放/GC后settings.callbacks仍有token2('/persistent')且lease weakref已失效。旧测试用__new__先持owner，绕过了公开API。主代理已检查source对应except/close和测试确认问题，SPEC FAIL/P2有效。

批准范围内修复：公开`CollisionLeaseCleanupError(RuntimeError)`强持有`.cleanup_owner`，原构造错误链不丢；调用方从异常取得owner后显式close仅重试残项，不加全局保活/无限重试。原实现者进行普通构造RED→GREEN，完成后复跑新focused/full及SPEC→QUALITY。实际runtime接入须处理该异常载荷，不能忽略构造失败残项。此处是资源清理协议修复，不声称是此前Isaac长训原生退出的根因。

## P2修复后独立验证

修复提交 `8a3746f100b575241aefeb9d38347bc8f01c464f`，仅原两文件。普通公开构造和direct close两项回归先2failed/111deselected，再113focused/4.29s。源码SHA256 `19179f50a2b03b2c75bc74900f946eea08305ea6d5e916e5855a0edd03d4b8f3`，test SHA256 `264667a3d1e49982944ae46dff71ce9039cf1af1b090b9c6305c5d496365a322`。

主代理新鲜最终full：**1565 passed in152.72s/exit0/0skip**，新唯一目录 `/data/hexinkun-m1-acceptance-20260918/encounter-scene-lease-cleanup-full`，没有覆盖旧1563证据。最终代码实际Carb＋8个M1资产CPU probe再次PASS/exit0/46.494456s，仍明确synthetic外部query callbacks、actual_physx_query=false、kit_loaded=false。

SPEC复审PASS：独立113focused/4.41s/exit0；普通构造取cleanup_owner、保留ValueError、handles1..11后只重试token2、pending1→0、再close无重复、history保留；释放异常链和owner后owner/settings/clock均回收、native stage无效。无其它合同缺口。随后独立QUALITY PASS：完整读276行source/986行tests及plan，113focused/4.01s/exit0/0skip；无P1/P2/P3，锁顺序/weakref/native cleanup正常，diff check clean。双审均未修改文件或使用GPU。

主工作区仍m1_rl/e25e805；最终plan文档已scoped提交bc0d5a8，隔离工作区clean。GPU进程只见本人原占位351307/物理GPU7/15744MiB，未启动Kit/仿真/训练，未动占位、原参考、SDK/driver或其它任务。计划在local/main/isolated三处SHA256一致：ed73da43ea5f0d9708fc9737dadd9897cf42f132c6e8954502864b5e0e31dfe1。

下一项具体边界：既有run在wrapper唯一reset、validate_scene完成之后，RuntimeSink/first action之前，做隔离8-env真实stage/cache/Carb/PhysX query初始化诊断；验证同一body/path完整响应、无额外physics step/reset、sim time/index/root/joint/RNG/prepare/IK/recorder未被等待推进。不得再用CPU source-bound替代query现场结果。若现场query触发cooked/source resync，要保留失败证据并决定稳定初始化后的新capture，不能暗中豁免。正常/异常释放顺序为query→watch/settings→scope→env/app；constructor清理异常需从cleanup_owner重试残项。此工作未执行；不要求用户重复相同授权。

## 剩余完整验收目标（未完成）

完整coordinator/owner/replay/G1三次8×1600→1024×32→1024×1600/G2实际再次遇障/AME正常生命周期及named targets/policy-only小跨大绕/单进程10000实际updates均保留，未由本CPU包代替。首次几何18env负例不因source lease通过而自动关闭。

关联：[计划](../../docs/superpowers/plans/2026-09-19-m1-collision-scene-lease.md)、[前置scene scope](2026-09-19-m1-collision-scene-binding-implementation.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
