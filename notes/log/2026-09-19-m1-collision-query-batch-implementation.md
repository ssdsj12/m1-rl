# M1 非阻塞 collision query batch 实施

2026-09-19；T306.6h.6a.1a.2c。用户已批准 encounter 规格，当前为持续实施，不再等待相同范围审批。

## 范围与当前状态

隔离分支 `codex/m1-encounter-lifecycle`，本包计划 `3d34d82`，基线代码 `c12e0af`。只新增 `collision_query.py` 和对应测试，不改旧 run/runtime、参考源码、SDK、资产或训练入口。此模块将实际 SDK callable/response 接入严格回调协议；不加载 Kit、不 pump、不 step、不阻塞等待。`query_protocol_complete` 不是物理几何、CLEAR 或训练验收通过。

首轮测试在 fixture 内因模块缺失明确失败（1 setup error、非 collection error）；最小 pending collector 后 1 passed。后续实现者报告 constructor/正向快照117 failed→118 passed；坏回调/顺序/异常/metadata/close142 failed→261 passed；clock/deadline等37 failed→308 passed；加17408请求规模等用例后313 passed；timestamp4 RED→最终318 passed（4.99s）。实现提交 `f85c7ea9cfc47e253903d09c938000864422b400`，仅两文件。

主代理独立完整回归 **1338 passed in 145.24s，exit0、0skip**（包含既有1020项），`--basetemp=/data/hexinkun-m1-acceptance-20260918/encounter-query-batch-full`，不覆盖旧证据。bash -n与git diff --check均exit0。独立SPEC PASS，审查者focused318 passed/4.92s及额外交错/时钟/身份/JSON/弱引用probe；随后QUALITY PASS（318 passed/5.02s），另作40轮×12线程竞争，34个事件每轮完整且提前finished失败不被洗掉，query callable回收/关闭迟到回调/严格JSON均通过。本包协议实现完成，不是全G0或实际物理/训练完成。

`diagnostics()` 明确是纯latched-state快照，不读取clock、不改变证据；`poll()`/`finalize()`负责新鲜时钟/期限校验。此项相对计划prototype的小偏差已由主代理接受，并补docstring与测试。callback time只保存合法有限非递减采样或None，不把NaN写入严格JSON。

主代理读代码后提出并实测完成状态的全表重复扫描：128/512/2048请求分别0.01643/.07159/.52667s；17408（1024×17）同步请求27.19021s。实现者以恰好一次合法finished计数取代每callback全表扫描，主代理原脚本重跑17408请求2.33871s COMPLETE。语义仍须每请求已submitted、exact rigid/collider覆盖、真实finished，不能计数提前完成；规模测试逐body检查PENDING直到最后一个。此耗时是CPU协议处理，**不是实际PhysX查询耗时**。

主代理fresh diff确认旧冻结adapter文件均未改变（只排除本阶段八个新增源码/测试）；git diff --check无输出。资源只读：root4.1GiB、/data6.5TiB可用，GPU7仍15754MiB/0%原占位；没有新的GPU实验。

## 下一薄绑定层的只读证据

独立代理对实际 `m1_floating.usda` 的 composed stage 检查：17 body 均为 `translate/orient/scale`，scale 全为单位值；root 无 xform；17 collider 无自己的 xform op。13 Mesh 为 instance proxy，4 Cylinder 非代理；所有层 dirty=False。这是源资产事实，不能代替 live clone 的逐 env 检查。

真实内存 USD 通知验证：body translate/orient 为精确属性 info-only/default 变化；body scale、collider-local transform 必须失效。根外模板 Mesh.points 的通知仅见模板与 prototype 路径，**没有 robot root 路径**；换 reference 会 resync 实例及新旧 prototype。因此不得只按 robot-root 前缀过滤；仅精确 body 的既有 translate/orient value-only 可列入正常运动例外，其他 metadata/order/scale/composition 变化不能忽略。

安装 schema 与实际 prim 分开记录。13 Mesh 未 Apply `PhysxConvexHullCollisionAPI`/`PhysxCollisionAPI`，不存在的 hullVertexLimit/minThickness/contact/rest 属性不能冒称现场有效 64/.001/0。schema fallback 的 contact/rest 为 `-inf`，需要显式 JSON sentinel，不改成零；torsional patch 是摩擦，不混为 hull 几何。实际设置值仍待 Kit 读取。

settings 的显式生命周期接口：`subscribe_to_node_change_events(path, callback)`、`unsubscribe_to_change_events(subscription)`；USD 使用 `Tf.Notice.Register(..., stage)` 与 `listener.Revoke()`。close 必须释放本批订阅及 stage/callback owner，不取消全局 cooking。

主代理新增 CPU 实验只使用新建内存 stage 和局部 `Usd.StageCache()`：未注册 `GetId(stage).ToLongInt()` 为 **-1**（不是 0），Contains=False；Insert 后 Find(id)==stage；只 Erase 自己的局部 cache。`PhysicsSchemaTools.sdfPathToInt` 返回 Python int 且能精确 round-trip。该 import 需要同时在 PYTHONPATH 和 LD_LIBRARY_PATH 加已装 `omni.usd.schema.physx` 及其 bin；前两次缺路径的 ImportError 是诊断加载问题，后一次退出0。没有修改 amp 包或全局 StageCache，没有启动 Kit/GPU。

剩余真实接入：actual stage/path/settings/source 指纹及失效绑定、逐 body tensor link pose（非 COM）的 unit-scale 核验、初始化异步等待不推进 physics 的对照。完整 registry/coordinator/sync/replay/G1/G2/AME/learned/10000 门槛均保留。

关联：[计划](../../docs/superpowers/plans/2026-09-19-m1-collision-query-batch.md)、[query 来源合同](2026-09-19-m1-collision-query-contract.md)、[支持点核](2026-09-19-m1-collision-supports-implementation.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
