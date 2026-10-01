# M1 实际 USD scene binding 实施

2026-09-19；T306.6h.6a.1a.2c/G0-B2b2a。用户已批准encounter规格；上一目标轮为progress（f85c7ea、main1338full/0skip、SPEC→QUALITY），不是等待或无进展。本轮fresh HEAD6385a89、linked worktree/非submodule、git clean；方案继续，无重新审批。

## 范围

计划f6a61ad；新增 `collision_scene.py` 与对应测试，读取实际stage/cache/path编码、settings、完整USD inventory、static pose scale/ancestor链、源physics schema属性与fallback。输出只为 `scene_snapshot_only`，不保活USD/native对象、不查询/pump/step、不改SDK/参考/旧控制。实时watcher/lease与8-env初始化现场验证是紧接的必需步骤，不能拿静态snapshot授权CLEAR。

## 接口新增证据

独立只读API核验：Python ISettings无get_item_type；`.get(path)`返回实际Python object，missing=None（`omni/kernel/py/carb/settings/_settings.pyi:81–91`）。get_as_*与is_accessible_as会转换，不能据其false/0判断原值。精确type区分bool/int/float/string；unknown单列。源码typed分支见DictionaryBindingsPython.h:55–73/112–113。

节点订阅回调两参数，tree订阅三参数；unsubscribe必须显式执行。另一线程unsubscribe会等正在执行的callback，因此不得持有callback所需的应用锁去退订。leaf node订阅不涵盖ancestor变化，后续watch需覆盖相关ancestor或已验证的tree范围；多个get组成快照不是原子操作。callback的Item不能保留到通知后。

精确cooking输出为 `physxCookedData:<token>:buffer`；已装token为convexHull/convexDecomposition/triangleMesh/clothConstaint（安装源码原拼写）。不能忽略整个namespace；新增CookedDataAPI的apiSchemas/resync可能混有其他输入变化，不能单靠属性前缀豁免。相关定义：generatedSchema.usda:1652–1657、omni.physx/scripts/utils.py:15–20/861–879。本轮未改cooking策略。

主代理实际CPU核验SchemaRegistry：插件注册必须指向 `omni.usd.schema.physx/plugins/PhysxSchema/resources`，父plugins目录注册0项。前两次未正确注册时报schema插件缺失，随后1项注册成功；当前USD版本方法是 `PrimDefinition.GetAttributeFallbackValue`，不是较新接口GetAttributeDefinition。最终实测 hullVertexLimit64/minThickness0.0010000000474974513/contact与rest=-inf/torsional两字段0。它们是**schema fallback**而不是live有效值；生产记录会显式区分。没有修改安装包或源层。

已装omni.usd `_usd.pyi:454,550–552`确认context的stage ID可用UsdUtils.StageCache.Get().Find查询。薄builder要求actual stage已登记，不自行Insert全局缓存；fixture只使用自己的局部cache。

## 主代理真实资产内存组合验证

纯CPU新建Z-up/meters内存stage，8个 `/World/envs/env_i/Robot` 引用原 `m1_floating.usda`，仅在新内存env祖先设置8m偏移；用已有真实inventory读每个root。

结果：8 roots、136 colliders、每个17body/17collider及13proxy Mesh；world linear unit-rotation最大误差0。inventory总耗时2.28520s；所有已使用层dirty标志前后不变，源文件无写入。没有Kit/physics启动；这不是实际8-env物理运行或G1次数。

## 实施与后续

初版提交0a0be72（source188行/test613行），focused98pass；main独立全量1436 passed in146.72s/exit0/0skip，唯一 `/data/hexinkun-m1-acceptance-20260918/encounter-scene-binding-full`。但独立SPEC拒绝相消反射：ancestor只检查finite affine而最终world determinant>0，两个负det可相消。修复9620fbd，双反射/local determinant overflow/underflow三项真实USD RED DID NOT RAISE→逐ancestor finite-positive determinant→focused101pass，正scale相消保留。

主代理真实8clones snapshot探针进一步触发P1：collect后layer ExportToString/JSON往返再解码proxy path ID，3个独立子进程均SIGSEGV(-11)，faulthandler定位 `intToSdfPath(collider['path_id'])`。即时round-trip测试不足以证明ID长期有效。显式在capture前持有真实Sdf.Path列表的两次对照全部136body/collider decode正确；后续内存姿态设置曾因asset实际Quatd而误用Quatf报Type mismatch（probe错误，已按实际类型修正，不改源资产）。修正后的主代理对照exit0：8root/136body/136collider、source snapshot2.56856s、JSON往返、所有path解码、所有body移动/任意轴80度旋转后snapshot逐项相等，layer/cache只读，全部三个磁盘资产层dirty=False。此时pins只是诊断局部变量，尚不是生产修复。

独立审查直接读取已装libphysicsSchemaTools.so确认sdfPathToInt仅返回SdfPath内部裸编码，不增加引用。无stage极简A/B：保留原path 5/5正确，del path或直接编码str各5/5错解为后续新分配路径。ID1281曾变成/Other_Root_2_3061；不是稳定hash。没有改SDK。3×5000临时Sdf.Path与短清理调度可触发节点复用，native故障探针均禁core。

当时SPEC为FAIL，不能把1436测试冒称本包验收。计划增必要生命周期修正：`CollisionPathScope(stage)`显式保活当次Sdf.Path与stage，builder要求同stage/open scope，JSON仍脱离native；query关闭后再释放scope，禁止全局永久缓存或跨scope/进程复用整数。

修复提交 **c608945e98b63a5faee8906fc4de315c2ab5a030**（两文件source238/test791行）。12个新API/context用例先RED，再GREEN；迁移原101项；临时去掉_encode字典pin但保留API时，真实33proxy延后解码回归再次RED（child断言），恢复后GREEN。补close释放真实Sdf.Path弱引用、独立scope互不影响；最终focused114 passed/3.33s，全部subprocess timeout30s。

主代理正式scope版本真实8clones探针连续两次独立进程exit0：136body/136collider/104proxy，无额外局部pins；layer序列化＋JSON往返＋3×5000临时path分配后延后decode全正确；全部body平移/实际Quatd任意轴80度旋转后完整snapshot相同；layer/cache只读；关闭scope后builder拒绝。采集耗时2.57158s/2.56322s。可重跑脚本保存在 `/data/hexinkun-m1-acceptance-20260918/collision-scene-binding-probes/verify_actual_scene_scope.py`；settings为明确的空fake mapping，不伪装live Carb。

主代理新全量 **1452 passed in146.49s，exit0、0skip**，唯一 `/data/hexinkun-m1-acceptance-20260918/encounter-scene-binding-pins-full`。SPEC复审PASS：独立114focused3.28s；额外14个body/proxy ID经4×6000 churn全部正确，close一scope不影响另一scope，层文本/dirty/cache不变。原生A/B scope保活3/3正确，旧borrowed编码2/3错解；P1和P2均关闭。随后 **QUALITY PASS**：独立114focused3.37s/exit0、diff--check通过，无新P1/P2/P3。新建review agent被thread limit拒绝，复用未参与本模块实现的encounter_geometry_test_vectors作独立质量审查，未以实现者自审替代。本包完成仅限静态绑定与串行显式路径生命周期。

可重跑真实资产probe SHA256 `2a595e39458b3ba6f90d3c6593ca5f04340f66e6a8b0f9d3c55caf5ee7ee271c`；提交源码SHA256 `fbf43625c41bd63dcdd0e6a47859a170166b7927d9e1f50b3f43a526c557626e`。主工作区仍m1_rl/e25e805，仅任务notes/docs更新；source实现只在隔离worktree，不改用户已有dirty代码。

完整coordinator/sync/replay/G1/G2/AME正常退出与named target/policy-only/10000目标均未缩小或标完成；GPU7占位未动。

## 紧接接入边界（不是已实现能力）

失效watch必须先订阅再采集，覆盖真实stage的root外prototype/template通知，以及六个settings leaf和它们的ancestor变化。正常motion仅能精确豁免已绑定body的既有translate/orient value-only通知；scale/order/metadata/resync/外部source/cooking-input变化失效，不能按robot-root前缀过滤，不能忽略整个cooked namespace。多个settings.get非原子，捕获期间通知要拒绝该候选；改变再恢复也不能洗掉失效。

lease统一拥有显式path scope和watch订阅，query关闭/迟到回调变no-op后才释放path scope；unsubscribe不能持有callback所需锁。当前scope只保证调用方串行使用/关闭，不等于异步线程安全或geometry有效。原run.py现场入口仍是原wrapper唯一reset后、validate_scene后、RuntimeSink/first action前；若初始化query需要Kit update，必须记录前后sim时间/index/root/joints/RNG/prepare/IK/recorder无变化，不能默加physics step。正常cleanup先撤本批query/watch/path引用再env/app关闭，不给解释器遗留新的native owner。

本轮readonly资源：root4.4GiB可用、/data6.5TiB；GPU7 UUID46a1bc7e…15754MiB/0%，hexinkun占位PID351307/start Sep18 23:05:13仍在；无新GPU训练/仿真。旧冻结Task3 adapter除本阶段十个新增源码/测试外diff为空，run.sh bash-n与git diff--check通过。

关联：[计划](../../docs/superpowers/plans/2026-09-19-m1-collision-scene-binding.md)、[上轮query协议](2026-09-19-m1-collision-query-batch-implementation.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
