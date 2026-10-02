# PhysX collision query 来源与现场核验合同

2026-09-19；T306.6h.6a.1a.2c，G0-B2前置只读审计。基线f8ce0af/e9f0669；没有新增query实现或GPU实验。B1 inventory与B2实际geometry来源严格区分。

## 证据和适用边界

已安装amp `omni.physx 106.5.7`，SDK根`.../site-packages/isaacsim/extsPhysics`。主代理实读 `_physx.pyi:2005–2042`，旧`get_convex_mesh_data(meshPath,convexIndex)` / `get_nb_convex_mesh_data(meshPath)`明确仅simulation running时使用。返回num_vertices/num_polygons/vertices/polygons/indices；polygon含plane/num_vertices/index_base。不含stage ID、scale或shape ID，因此不得独自充当完整绑定。

官方旧示例加载physics后提取cooked vertices，再使用源collider LocalToWorld转换，支持collider-local顶点约定。[NVIDIA示例](https://forums.developer.nvidia.com/t/how-to-access-collision-shape/274440) 新request API是独立geometry请求，不因成功就证明它属于当前已附着shape；安装demo主代理已读，调用在simulation前仍需Kit/PhysX插件。[官方迁移说明](https://forums.developer.nvidia.com/t/warning-omni-physx-plugin-deprecated-function-please-use-iphysxcooking-requestconvexcollisionrepresentation-interface-instead/296302)

property query的stage_id/path_id/result/finished与collider-local box、完整USD相对变换是可依赖的SDK公开契约。无需把取得native.so内部C++指针证明变成新验收门槛。也不能将source authored bounds替代此实际query。具体已装坐标/scale用例见[前次接口核验](2026-09-19-m1-encounter-collision-inputs.md)。

Cylinder实际可为native或convex近似，必须记录collisionApproximateCylinders。未找到可按path读取native cylinder参数的Pythongetter；全场numCylinderShapes不足以唯一身份绑定。未来优先使用实际query保守bounds；不能用未核margin的USD radius/height替代。旧convex接口在Cylinder近似模式下是否提供结果是现场事项，不以它缺失自动冒称shape失败或制造vertices。

## 后续B2最小现场条件

1. 同一实际simulation stage、完整17collider/body manifest、来源/cooking/settings指纹；全部query callback成功且finished到达。不能用dict覆盖重复path回调或忽略missing/unknown。
2. collider-local bounds→完整collider-to-body affine→逐body world pose；核非零offset、旋转/非均匀scale。不得双乘response.local_pose，不能只变两个min/max角。
3. 可得live cooked hull时验证所有有限vertices处于query box内；作为交叉证据，不单独替代stage/path绑定。Cylinder不伪造顶点。
4. stage reload或geometry/settings改变使快照失效。缺输入、超时、单位/绑定不一致明确拒绝，不能把failedquery回退成sourcebbox后授权CLEAR。
5. 独立重放保存静态query记录、transform/source/settings与逐body pose，重建保守包络而非信任运行时clear声明。盒保守性可以导致更晚离开，不得以加容差消除真实失败。

本次只读安装源码和官方文档，没有运行query/cooking/Kit，不能宣称现场B2通过；剩余现场问题是回调完整性、实际stage/scale绑定和Cylinder模式，而非必须获得SDK内部源码。完整G0/G1/G2及学习目标保持。

## B2实施前追加接口核对

B1已在0196f6f完成main913full/0skip和双审查。B2a坐标核计划`2b67905`开始TDD，完整八角点及逐body世界变换单独实现，不借用SDK脚本的包络结果。

主代理完整读`omni.physx/scripts/propertyQueryRigidBody.py`：其`Result.get_bbox()`仅Transform两个min/max角，不足一般旋转；`QueryManager`保留prim/self且缺少精确回调清单检查，因此只能参考API，不能直接继承其bbox/完成判据。官方graph使用`Gf.BBox3d(...).ComputeAlignedRange()`的完整变换方法仍适用；不修改SDK。

主代理实读`_physx.pyi:3298–3357`：rigid response也有`stage_id/path_id/type/result`，必须与提交的body请求严格绑定，不能只靠回调closure认body。`PhysxPropertyQueryInterface.py:105–110`等待collision tasks并调用`next_update_async`，:225–230 timeout测试也需要给update机会；因此不能假设主线程`Event.wait`就能完成未缓存query。现场绑定层先支持真实finished的同步fastpath；异步query必须有经过实测不推进physics的受控pump，记录sim时间/index、raw root/joint/RNG与prepare/IK计数前后不变。不能透明加sim.step/reset，不能以protocol CPU fake证明真实query完成。具体初始化位置、暂停/恢复对生命周期影响与instance proxy回调路径仍须现场测试。

独立有界审计补充：query_prim返回None，没有request/cancel handle；未承诺callback线程。后续collector需锁保护、每请求独立不可变token、复制普通Python字段并记录thread ID，错误锁存交外层抛出，不保存native response/env/view/traceback或在callback内调用USD/pump。每body恰好1个VALID rigid、每声明collider恰好1个VALID response、恰好1个真实finished，任何重复/未知/跨body/缺失/超时均永久失败。已close的迟到回调不得恢复成功；不取消全局cooking任务冒充取消自身query。

实际设置至少记录存在性与带类型原值：`/physics/collisionApproximateCylinders`、`/physics/cooking/ujitsoCollisionCooking`、`/persistent/physics/useLocalMeshCache`、`/physics/saveCookedData`、`/physics/updateToUsd`、`/physics/suppressReadback`。SDK `_DEFAULT` 常量是路径不是实际bool，unknown不能转成false。`Tf.Notice.Register(Usd.Notice.ObjectsChanged, callback, stage)`及GetResyncedPaths/GetChangedInfoOnlyPaths可监测几何输入变动，listener.Revoke显式清理；实例template/source也要覆盖，不仅root字符串。body自身运动与静态collider变换分开，cooked-data写回与实际geometry输入改变需要显式区分并保留记录。stage/context/settings变动使快照失效，不能用notice监测冒称能证明native内部未变。

实际接入点：run.py创建env115→wrapper唯一显式reset121→validate_scene124→sink/随机化保存128→首teacher动作139。优先验证reset后且首动作前的query；若需异步pump，比较reset前query和reset后paused-pump两个初始化位置，严格以sim时间/index、raw root/joint、RNG及prepare/IK/recorder计数不变证明；不得假定其中任何一个已经保持parity。本次仍只读，未进行query/Kit/物理试验。

关联：[B1实施](2026-09-19-m1-collision-inventory-implementation.md)、[规格](../../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
