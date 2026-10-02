# Encounter全碰撞输入：实际USD只读核验

2026-09-19，T306.6h.6a.1a.2c后续G0-B provider依赖。Baseline=e25e805规格/260c8e4冻结adapter；无碰撞实现变更。

## 方法与输入

子代理用amp已有pxr CPU打开原reference `assets/m1_panda/m1_floating.usda`，遍历instance proxies及rigid-body祖先，检查类型、enabled、局部变换。主代理独立运行同一真实asset的type/count/points/binding断言。PYTHONDONTWRITEBYTECODE=1、CUDA_VISIBLE_DEVICES为空、TMPDIR为/data任务临时目录；未启动Isaac/Torch/GPU、未改USD或写大文件。

## 已核事实

- 必须以机器人root `/ZJ_V3_URDF_V1_0` 为遍历边界并遍历instance proxies。主代理第一次从整个stage扫描得到34个collider，包含`/colliders`模板定义；这不是机器人实际34个形状。限定root并检查rigid-body祖先后，准确为17个刚体各一个enabled collider。
- 13个mesh均convexHull、instance proxy：BASE_LINK 1,735,086 authored points；四组ABAD各75,150、HIP各344,766、KNEE各282,342。总4,544,118。这个数不是去重顶点数，也不是PhysX cooked hull顶点数。
- 四个wheel_collision为非proxy Cylinder，Y轴，radius=.0959、height=.0465。Y圆柱局部方向u的解析support为 `.0959*sqrt(u_x²+u_z²)+.02325*abs(u_y)`，不需要也不能用稀疏圆周点假称精确极值。
- 子审计所有collider→所属body的变换为identity（scale1、无shear、det1、沿途无resetXformStack）。非root body自身不能忽略：FAR_FOOT_LINK相对asset平移约(.32950001955,-.20740000904,-.53979998827)。后续实际运行必须逐body绑定实际pose，而不是全部套root pose。
- 独立overlay显示的stage fallback仍为.01/Y，不能据此缩放当前已经验证的米制spawned scene；live stage单位/Z轴仍需按原guard核对。

## 实施约束与未证范围

G0-B需要保存17-body完整形状/绑定清单以及逐步pose，丢proxy、误扫模板、仅轮/root都应失败。4.5M authored points不能在1024env×1600每步简单展开；离线静态几何表示需完整、可审计，动态包络使用有限内存算法。mesh authored convex hull与真实PhysX cooked shape的完全一致性本次未验证，不能把原始点集极值直接宣称已证实际完整碰撞包络。后续需明确并验证安全的形状表示/保守性，不放宽clearance，也不改原碰撞体。

本次是geometry首包实施期间的后续输入核验；geometry纯函数不负责真实USD采集，尚未接runtime。shape导出/离线重建、coordinator、reference/sync、G1/G2与学习验收仍未完成。

## 已安装PhysX接口及保守性审计

独立只读审计＋主代理实读SDK pyi、graph节点和自带tests，没有调用query/cooking或开启Kit。SDK根为amp/site-packages/isaacsim/extsPhysics，106.5.7：

- `omni.physx/omni/physx/bindings/_physx.pyi:1121`的`query_prim`提供body/collider/finished回调；`:3154` response包括aabb_local_min/max、local_pos/rot、path_id/stage_id/result。
- `omni.physx.graph/omni/physxgraph/ogn/nodes/propertyquery/OgnPhysXPropertyQueryRigidBody.py:87–98`根据path_id取collider，使用`ComputeRelativeTransform(collider,body)`和完整`Gf.BBox3d`变换query local box；不再额外乘response local_rot。双重叠加会错。
- `omni.physx.tests/omni/physxtests/tests/PhysxPropertyQueryInterface.py:306–335`的fixture声明local box不含scale；`:370–404`有多个子collider的offset；`:438–446`分别测simulation前/运行中查询。本轮是源码核验，未执行这些SDK测试。
- `_physx.pyi:2042`的request_convex_collision_representation可返回完整小型convex vertices，demo示范启动simulation前同步取出，但仍须Kit/PhysX插件；不是amp＋pxr纯CPU已能直接调用。旧get_convex_mesh_data要求simulation正在运行。

source AABB不能直接当safe CLEAR包络：cooking的顶点限制可能扩展输入形状，某些plane shifting产生远离原始点的顶点；不应假设source凸包等同实际cooked形状。[PhysX官方几何说明](https://nvidia-omniverse.github.io/PhysX/physx/5.4.1/docs/Geometry.html)

contact/rest offset是独立的接触生成语义，不能冒称已包含在vertices里，也不能无依据改本规格.005clearance。[官方接触说明](https://nvidia-omniverse.github.io/PhysX/physx/5.4.1/docs/AdvancedCollisionDetection.html)

下一步采用明确分层：B1只读USD完整shape/body清单，固定`usd_inventory_only`；B2绑定实际query、cooked包含性/来源及缩放，完整八角保守盒或解析support配逐body pose。未经live核验不允许提供可授权CLEAR结果。Cylinder也需记录实际`/physics/collisionApproximateCylinders`；USD类型不能证明最终为原生圆柱。query timeout、漏/重复/unknown collider、错误stage/path/单位、动态geometry均应拒绝。

关联：[实施计划](../../docs/superpowers/plans/2026-09-19-m1-encounter-geometry.md)、[实施记录](2026-09-19-m1-encounter-geometry-implementation.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
