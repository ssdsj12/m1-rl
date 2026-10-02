# M1 Live Cooked Collision Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** 在已验证的同stage property-query初始化守卫内读取可用的live cooked convex顶点，并保存与query collider-local盒的交叉证据，供完整碰撞geometry/provider实现使用。
**Architecture:** 默认关闭的cooked诊断扩展；复用当前唯一lease、before/after原始状态和callback清理。collector仅复制SDK getter数据，不请求新cooking、不update/step/reset，不改变控制、阈值或query来源。只有实际可用顶点参与containment，缺失以unavailable保存，绝不伪造。
**Tech Stack:** amp Python3.10、NumPy、现有真实USD/CollisionSceneLease、安装版PhysX cooking只读getter；所有源码改动仅隔离worktree。

---

## 已批准范围和工作区

本包实施已批准encounter规格§5/G0-B与query公开契约的可用live hull交叉核验，不新增控制功能或要求用户重复审批。当前6b1b565 linked worktree clean，上一轮真实8×32/136query/23组bytes/零额外physics/native0完成。完整G0-B/C/D/E、G1三次新8×1600→1024×32→1024×1600、G2真实重遇、AME/named actions/policy/10000保持未完成，不能以此包替代。

Remote root=/data/hexinkun-m1-acceptance-20260918/encounter-worktree，adapter=tools/m1_reference_validation；local staging=C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter。主代理docs/notes、full/GPU；实现者只改下列六个文件：
- Create collision_cooked_evidence.py
- Create tests/test_collision_cooked_evidence.py
- Modify query_initialization_probe.py / tests/test_query_initialization_probe.py
- Modify runtime.py / run.py

原run.sh、lease/query/scene/inventory/supports、controller、SDK/driver/参考目录和dirty主源码不动。既有4参数probe调用的默认行为不变；新增keyword只是显式cooked模式。

## Task 1：纯collector和完整拷贝/身份

- [x] RED：先新module缺失assert和核心数值用例，再实现；不mock collector/lease/query。只有真实SDK getter边界使用可控double。
- [x] 实现函数 `collect_cooked_evidence(artifact, get_count, get_mesh)`，import仅标准库/NumPy与现有纯validation helper，不加载SDK/Torch。
- [x] 完整输入合同、失败和数据隔离按下文逐项测试。

返回JSON安全且deep-detached dict：
```python
{
 "schema": "m1_live_cooked_evidence_v1",
 "representation_status": "cooked_query_crosscheck_diagnostic_only",
 "result": "captured",  # errors非空则failed；不是geometry_verified
 "stage_id": query["stage_id"],
 "geometry_generation": artifact["geometry_generation"],
 "source_fingerprint": artifact["scene"]["source_fingerprint"],
 "settings_fingerprint": query["settings_fingerprint"],
 "getter": "get_nb_convex_mesh_data/get_convex_mesh_data",
 "coordinate_assumption": "raw_getter_vertices_compared_with_query_collider_local",
 "errors": [],
 "records": [],
 "mesh_count": 0, "available_mesh_count": 0, "unavailable_mesh_count": 0,
 "native_cylinder_count": 0, "hull_count": 0, "vertex_count": 0
}
```

仅接受artifact schema/representation=query_source_bound，query status COMPLETE/query_protocol_complete/errors[]，scene source stage_id/query stage_id相同，geometry_generation一致，settings fingerprint一致。source.environments、inventory.colliders组成完整目标清单；env ID与collider path唯一，body清单去重后完整（同body多个合法collider允许），每collider的body_path与query请求一致。query.requests与responses必须恰好覆盖body清单，每条response的request匹配requests，对应rigid VALID/stage/path IDs和真实finished。每collider的query path_id来自该body声明的collider_path映射，必须唯一且VALID/stage相同；missing/duplicate/extra、错stage或错path均在调用任何getter前拒绝。caller提供的是活lease刚finalize的产物，此重复检查不是替代lease真实性。

每个记录包含env_id/body_name/body_path/collider_path、query_path_id、type、query_aabb_local_min/max以及hulls。bounds为finite real shape(2,3)，min<=max。Mesh仅支持原convexHull，其geometry与settings snapshot由lease绑定；Cylinder只记录native_query_only，get_count/get_mesh一律不调用，不将不存在convex hull当错误，更不制造顶点。若Cylinder设置不是明确bool False，则标unsupported并errors记录（当前现场已确认False）。

Mesh执行：
```python
count = get_count(collider_path)  # 使用完整实际instance路径字符串，不转为prototype
# count为non-bool integral >=0，否则该record failed
if count == 0:
    # availability='unavailable'；hulls=[]，不是成功containment或整体geometry证明
    record["availability"] = "unavailable"
    result["unavailable_mesh_count"] += 1
else:
    for hull_index in range(count):
        raw = get_mesh(collider_path, hull_index)
        # 读取num_vertices和vertices，立即完整复制再调用下个getter
        n = raw["num_vertices"]
        raw_vertices = raw["vertices"]
        # n与raw_vertices按下方完整数值合同验证、立即复制并构造hull记录。
```

count0是可用性信息，报告不虚构错误；record availability=available/unavailable/native_query_only/failed。get_count/get_mesh的普通Exception记字符串errors、当前record failed，继续其它物体，以保留可用证据；KeyboardInterrupt/SystemExit必须向上传播，让现有helper锁存失败并执行close/after，不将用户中断吞成成功。

每hull读取dict必需num_vertices、vertices；SDK其余已文档字段不必伪造或用于本顶点包含判据。num_vertices为non-bool integral>=1，len/shape必须精确(n,3)。支持native carb.Float3(x,y,z)或numeric三元组/ndarray；提取后先检查dtype.kind i/u/f、finite，再独立float64复制，不能用float()接受string/bool/object/complex。原float3分量经float64表示是精确提升，保存`vertices_dtype="<f8"`及全部普通Pythonfloat三元组；不保存native对象、view、exception/traceback。忽略num_polygons/indices不等于验证mesh拓扑，本包只验证凸体全部顶点对query box的包含。

hull记录：
```python
lo, hi = np.asarray(query_min), np.asarray(query_max)
lower = np.maximum(lo - vertices, 0.0)
upper = np.maximum(vertices - hi, 0.0)
# np.errstate处理浮点溢出，任何非finite差值拒绝；不放宽atol
record = {
 "hull_index": i, "num_vertices": n, "vertices_dtype": "<f8",
 "vertices": vertices.tolist(),
 "vertices_aabb_min": vertices.min(0).tolist(),
 "vertices_aabb_max": vertices.max(0).tolist(),
 "max_lower_violation_m": lower.max(0).tolist(),
 "max_upper_violation_m": upper.max(0).tolist(),
 "all_vertices_in_query_aabb": bool(np.all(lower == 0) and np.all(upper == 0))
}
```
任何available hull不包含则保留raw vertices/数值，在errors追加collider_path/hull_index/违反值，result=failed；不移动box、不加容差、不改source或者SDK。不乘response.local_rot，不把getter返回值先旋转/缩放到“能通过”的坐标。

需测试：真实USD/lease/query产物构造一Mesh和native Cylinder；getters调用精确实例path/index；两hull/reused storage立即复制；boundary exact包含、1ULP出界失败且raw保留；float3、非finite/负数/bool/string/complex/object/malformedshape/count mismatch/普通getter exception、0available、Cylinder不调用、unexpected Cylinder mode；输入artifact/getter storage不变，返回值无alias，JSON roundtrip值相同。身份错/重复/extra与结果状态不对时0getter调用。不要从collector自身计算expected。

核心测试数值固定：
```python
vertices = np.array([[-1.,0,0],[1.,0,0],[0,-1.,0],[0,1.,0],[0,0,-1.],[0,0,1.]])
# query [-1,-1,-1]..[1,1,1]，包含；将vertices[1,0]改nextafter(1,inf)需保留并failed
# 准备0count的Mesh时unavailable_mesh_count==1且vertex_count==0；不能当available pass。
```

## Task 2：在既有守卫和清理内接线

- [x] RED：new flag/default/budget、reallease Inspector执行时序、SDK边界接线；旧非cooked测试原断言不删。
- [x] runtime新增默认false flag，只有显式query-probe的8×32允许：
```python
parser.add_argument("--collision-cooked-probe", action="store_true")
# 在既有query budget校验后：
if args.collision_cooked_probe and not args.collision_query_probe:
    parser.error("collision cooked probe requires --collision-query-probe")
```
- [x] run.py保持一个lazy probe调用位置，在原四positional参数后传 `capture_cooked=args.collision_cooked_probe`。若旧外部SDK替身签名确需增加optional参数，必须报告范围，由主代理核对，不能删原断言或改生产默认逻辑迁就替身。
- [x] probe增加keyword-only `capture_cooked=False`；为false时不import cooked module/get_physx_cooking_interface，也不增加report字段。true时在已启动SDK内lazy构造collector闭包；传给execute_query_probe，并在probe退出时无native getter/interface永久引用。接口属于SDK借用对象，不调用全局release：
```python
def inspect_cooked(artifact):
    from omni.physx import get_physx_cooking_interface
    from collision_cooked_evidence import collect_cooked_evidence
    cooking = get_physx_cooking_interface()
    return collect_cooked_evidence(artifact, cooking.get_nb_convex_mesh_data,
                                  cooking.get_convex_mesh_data)
```
- [x] execute_query_probe新增keyword-only `cooked_inspector=None`。不改_new_report默认字段；query COMPLETE/finalize之后、既有finally/poll/close/after之前调用，产物先deepdetach：
```python
report["artifact"] = _detached_json(owner.finalize())
if cooked_inspector is not None:
    report["cooked_evidence"] = _detached_json(cooked_inspector(_detached_json(report["artifact"])))
    evidence = report["cooked_evidence"]
    if evidence["schema"] != "m1_live_cooked_evidence_v1" or evidence["result"] != "captured" or evidence["errors"]:
        raise RuntimeError("live cooked evidence failed: " + str(evidence.get("errors")))
```
owner真实finalpoll必须在读取cooked之后生效，检测其过程改变来源；原23raw state检查覆盖所有getter。BaseException继续原字符串锁存、close重试上限/after/保守首次failed发布/callback cleanup不变。不能增加第二lease、callback、query提交或sim步骤，不能将坏inspection覆盖成成功。

测试需通过既有Execution真实USD/lease/queryfixture验证顺序finalize→inspector→poll→close→after；inspector变更artifactcopy不改变原artifact；inspector异常/写盘失败/改变source/改变capture/KeyboardInterrupt均failed且owner关闭/guardafter存在。true/false SDKgetter调用和导入行为；原4参数调用完全保持、metadata中无cooked字段。AST接线保证scope位置未挪。

## Task 3：主代理验证、独立审查和唯一现场

- [x] focused RED→GREEN，scoped六文件commit；主代理full回归、bash-n、SPEC→QUALITY（只在SPEC PASS后QUALITY），无未修Important才启动。
- [x] root空间/GPU7身份fresh核验；默认保留原15GiB占位，唯一新/data目录，TMPDIR/data/coreoff。单次命令：
```bash
bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 \
  --collision-query-probe --collision-cooked-probe \
  --output /data/hexinkun-m1-acceptance-20260918/cooked-live-UNIQUE
```
UNIQUE由主代理现场时间生成且检查不存在，不是让实现者猜路径。跟踪同一handle到真实terminal，无观察timeout重启。
- [ ] 从真实report/23NPZ重新核验原初始化+32步/128substeps/native/wrapper0与POST_CLEANUP；遍历每个可用hull原始vertices独立重算包含，不信自报bool，核counts和身份。不可用明确记录，不当作geometry完成；若矛盾则根据证据定位坐标/scale，不修改阈值。
- [x] 更新主notes/todo/T306/logindex/每次证据log及本计划；主源码/SDK不改。通过时继续source-bound支持点/provider/registry/coordinator，完整目标保持。

CPU baseline/focused/full环境复用已记录amp USD/Physx schema路径与CUDA_VISIBLE_DEVICES空；每个pytest basetemp是/data新唯一目录，不复用让pytest删除旧证据。本次baseline=cooked-evidence-baseline。主代理自审：六文件边界、非cooked默认兼容、现有lease/guard全面复用；缺失getter不是伪顶点，未把精确float顶点比较改为物理容差；与已批准可得live hull合同一致。

主代理baseline实测：test_query_initialization_probe.py **122 passed in17.56s/exit0**；不是把上轮联合194误写成此单文件数量。API独立审计完成：安装106.5.7旧getter只标simulation-running；官方旧示例以source mesh LocalToWorld转换，支持mesh-local但没有验证instanceproxy/scale。本次如实采集这些实际路径，不新增内部PxShape指针证明要求。弃用警告记录而不自动替换request API；不调用官方示例中的force_load/release。

例行CPU命令（从adapter目录；使用已配置USD/Physx库环境，不装包）：
```bash
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp PXR_PLUGINPATH_NAME=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx/plugins/PhysxSchema/resources PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310:/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin:/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests/test_collision_cooked_evidence.py tests/test_query_initialization_probe.py --basetemp=/data/hexinkun-m1-acceptance-20260918/cooked-evidence-focused
```

focused首轮须RED，写实现后用新的basetemp后缀再GREEN。主代理full把两个测试文件参数换为tests并使用cooked-evidence-main-full新目录。执行方式沿用户持续实施授权，使用子代理实施而非重复询问；主代理自审已完成范围/签名/精确错误路径检查。

2026-09-19 CPU门槛：06f3526六文件完成，focused216passed，main full1781passed/177.59s/0skip。SPEC发现负向subtraction overflow先clip掩盖-inf，c02bde0仅两文件TDD修复，四例RED2failed2passed→focused220passed/28.02s；主代理修后full1785passed/178.11s/exit0/0skip、bash-n/diff-check通过。SPEC复核PASS后QUALITY PASS；独立现场verifier主代理17self-tests通过。暂无真实cooked现场结果。17:02fresh root497G可用、GPU7仅原占位351307/15744MiB，8328MiB free，保持占位启动唯一8×32。

2026-09-19现场后续：唯一cooked-live-20260919-1703已terminal，native PID3824745，启动b0d4270。104hulls/3664vertices全部获取，无unavailable；32native Cylinder。23raw前后bytes/46metadata、136query/408callbacks来源、0额外physics/pump与关闭有效。40hulls比raw query边界外溢1float32 ULP，max7.450580596923828e-9m；主代理与独立struct逐步舍入均复现624/624 query边界=实际hull extrema的float32 center±extent。严格判据failed保留，normal cleanup/native1/wrapper2、0budgetsteps，故上方32/128/exit0验收项不能勾选。没有改box或容差、没有重启。新T306.6h.6a.1a.2c.1接续保守geometry数学与provider；完整G1/G2/AME/policy/10000不缩小。详见[现场负例](../../../notes/log/2026-09-19-m1-live-cooked-evidence.md)。
