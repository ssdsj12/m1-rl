# M1 Collision Scene Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从真实 USD stage 与 settings 构造可直接提交给已验证 query collector 的精确请求清单、来源指纹和逐 body 姿态绑定，不插入 stage cache、不改场景或用 authored bounds 代替 query。

**Architecture:** 此包是薄的只读 scene snapshot，复用 inventory，直接使用已装 PhysicsSchemaTools 编解码路径与 Usd.StageCache 身份；输出仍标为 `scene_snapshot_only`。紧接的 lease/watch 接入将订阅 USD/settings 变动，实际初始化诊断比较 snapshot、query 与 physics 状态；本包的静态快照不能自行宣称实时有效或 CLEAR。分离静态采集与订阅使可变生命周期不混入可重复的来源采集。

**Tech Stack:** amp Python3.10、NumPy、实际 pxr/PhysxSchema/PhysicsSchemaTools，无 Kit/torch/omni 导入；既有隔离 worktree。

**完成范围与证据：** 静态snapshot及显式native path scope完成，代码c608945；main1452full/146.49s/0skip，SPEC→QUALITY PASS。主代理两次正式scope真实8内存实例136body/136collider/104proxy延后解码、姿态hash不变及只读验证通过。不是live PhysX query、watcher、G1或训练完成。下方初版prototype保留为实施轨迹；最终API强制`path_scope`，以末尾生命周期修正及已提交源码为准，不能复制旧的无scope调用用于runtime。

---

## 依据与文件边界

用户已批准完整 encounter 规格，上一轮是 progress：f85c7ea query 协议 + main1338full/0skip + 双审查；当前干净 HEAD6385a89。保持 SDK/参考/旧控制/全部负结果/GPU占位不动，不重新请求同一范围批准。

仅新增 `tools/m1_reference_validation/collision_scene.py` 和 `tests/test_collision_scene.py`。本地 staging 为 `C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter/`，SCP精确两文件到 `/data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation/`。主代理负责文档与全量，子代理只 focused/两文件 scoped commit。

实查 API：未注册 `StageCache.GetId(stage).ToLongInt()` 是 -1；不允许本包 Insert/Erase/Clear。`PhysicsSchemaTools.sdfPathToInt`→int、`intToSdfPath`可round-trip。settings.get返回真实Python type或missing None；get_as_*会转换，禁止使用。schema fallback来自已注册 `Usd.SchemaRegistry().FindAppliedAPIPrimDefinition(name).GetAttributeFallbackValue(attr)`；缺注册不得猜值。CPU测试通过PXR_PLUGINPATH_NAME指向已装PhysxSchema/resources注册，不更改SDK。root/ancestor/body单位缩放必须现场采集，不把源资产unit scale外推到live clone。

## Task B2b2a：真实 scene snapshot

### 1. 首个 RED

- [x] 测试在函数内assert模块存在（缺失是assert失败，非collection error），用真实Usd.Stage.CreateInMemory、局部Usd.StageCache和真实Cylinder/CollisionAPI/RigidBodyAPI/T-O-S。外部settings仅fake get，禁止mock inventory、USD或path encoder。

```python
def test_unregistered_stage_is_not_silently_inserted():
    import importlib.util
    assert importlib.util.find_spec('collision_scene') is not None
    from collision_scene import collect_collision_scene_snapshot
    from pxr import Usd, UsdGeom, UsdPhysics, Gf
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage, 1.)
    UsdGeom.SetStageUpAxis(stage, 'Z')
    body = UsdGeom.Xform.Define(stage, '/Robot/B')
    body.AddTranslateOp().Set(Gf.Vec3d(0.))
    body.AddOrientOp().Set(Gf.Quatf(1.))
    body.AddScaleOp().Set(Gf.Vec3f(1.))
    UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
    shape = UsdGeom.Cylinder.Define(stage, '/Robot/B/C')
    shape.CreateRadiusAttr(.1); shape.CreateHeightAttr(.05)
    UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
    cache = Usd.StageCache()
    class Settings:
        def get(self, path): return None
    with pytest.raises(ValueError, match='registered'):
        collect_collision_scene_snapshot(stage, ['/Robot'], ['B'], Settings(), stage_cache=cache)
    assert cache.IsEmpty()
```

Run below focused command. Expected missing-module assert RED, then implement only behavior tested and extend through following cases.

### 2. 只读采集实现

- [x] 以下代码固定输入与来源合同；可按TDD最小增量整理内部结构，不改变拒绝条件。实际生产只保存普通JSON数据，不保留stage/cache/settings/prim。body世界位姿不进入静态指纹，正常平移/旋转不会让同一几何snapshot hash每步变化；静态body scale/order及ancestor完整矩阵进入指纹。

```python
import hashlib
import json
import math
import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics, UsdUtils, PhysicsSchemaTools, PhysxSchema
from collision_inventory import collect_collision_inventory, _validate_xform_order
from collision_query import _identifier, _manifest
from encounter_geometry import _obstacle_id

SETTING_PATHS = (
    '/physics/collisionApproximateCylinders', '/physics/cooking/ujitsoCollisionCooking',
    '/persistent/physics/useLocalMeshCache', '/physics/saveCookedData',
    '/physics/updateToUsd', '/physics/suppressReadback',
)
_SCHEMAS = (
    ('PhysxConvexHullCollisionAPI', PhysxSchema.PhysxConvexHullCollisionAPI),
    ('PhysxCollisionAPI', PhysxSchema.PhysxCollisionAPI),
)

def _scalar(value):
    if value is None: return {'type':'missing', 'value':None}
    kind = {bool:'bool', int:'int', float:'float', str:'string'}.get(type(value))
    if kind is None: raise ValueError('unsupported scalar type')
    if type(value) is float:
        if math.isnan(value): raise ValueError('NaN source/settings value')
        if math.isinf(value): value = {'nonfinite': 'positive_infinity' if value > 0 else 'negative_infinity'}
    return {'type':kind, 'value':value}

def _sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def _path_id(path):
    path_id = _identifier(PhysicsSchemaTools.sdfPathToInt(path), 'path_id')
    if str(PhysicsSchemaTools.intToSdfPath(path_id)) != path:
        raise ValueError('path codec must round-trip exactly')
    return path_id

def _matrix(xform):
    result = np.asarray(xform, dtype=np.float64).T
    if result.shape != (4,4) or not np.isfinite(result).all() or not np.array_equal(result[3], [0.,0.,0.,1.]):
        raise ValueError('body/ancestor transform must be finite affine')
    return result

def _pose_binding(stage, path, cache):
    prim = stage.GetPrimAtPath(path)
    xform = UsdGeom.Xformable(prim)
    _validate_xform_order(xform, path)
    order = list(xform.GetXformOpOrderAttr().Get() or ())
    if order != ['xformOp:translate','xformOp:orient','xformOp:scale']:
        raise ValueError('body pose binding requires exact translate/orient/scale order')
    scale = np.asarray(prim.GetAttribute('xformOp:scale').Get(), dtype=np.float64)
    if scale.shape != (3,) or not np.array_equal(scale, np.ones(3)):
        raise ValueError('body scale must be exactly unit for tensor link pose binding')
    world = _matrix(cache.GetLocalToWorldTransform(prim))
    linear = world[:3,:3]
    if not np.allclose(linear.T @ linear, np.eye(3), rtol=0, atol=1e-12) or np.linalg.det(linear) <= 0:
        raise ValueError('body world linear transform must be a proper unit-scale rotation')
    ancestors = []
    parent = prim.GetParent()
    while parent and not parent.IsPseudoRoot():
        if parent.HasAPI(UsdPhysics.RigidBodyAPI):
            raise ValueError('nested rigid-body ancestors are unsupported in static pose binding')
        parent_xform = UsdGeom.Xformable(parent)
        if parent_xform:
            _validate_xform_order(parent_xform, str(parent.GetPath()))
            ancestors.append({'path':str(parent.GetPath()),
                              'local_column_matrix':_matrix(parent_xform.GetLocalTransformation()).tolist(),
                              'xform_op_order':list(parent_xform.GetXformOpOrderAttr().Get() or ())})
        parent = parent.GetParent()
    return {'body_path':path, 'body_path_id':_path_id(path), 'xform_op_order':order,
            'scale':scale.tolist(), 'ancestors':ancestors}

def _topology(prim):
    records = {}
    if not prim.IsA(UsdGeom.Mesh): return records
    mesh = UsdGeom.Mesh(prim)
    for name, attr in [('faceVertexCounts',mesh.GetFaceVertexCountsAttr()), ('faceVertexIndices',mesh.GetFaceVertexIndicesAttr())]:
        if attr.GetNumTimeSamples(): raise ValueError('animated collision topology is unsupported')
        value = attr.Get()
        if value is None:
            records[name] = {'present':False}
        else:
            array = np.asarray(value)
            if array.ndim != 1 or array.dtype.kind not in 'iu': raise ValueError('topology must be integer vector')
            records[name] = {'present':True, 'dtype':array.dtype.str, 'count':int(array.size),
                             'sha256':hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()}
    attr = mesh.GetOrientationAttr()
    records['orientation'] = _scalar(attr.Get())
    return records

def _physics_source(prim):
    fields = {}
    registry = Usd.SchemaRegistry()
    for schema_name, schema_type in _SCHEMAS:
        definition = registry.FindAppliedAPIPrimDefinition(schema_name)
        if definition is None: raise ValueError('PhysxSchema definitions must be registered')
        for name in schema_type.GetSchemaAttributeNames():
            attr = prim.GetAttribute(name)
            if attr and attr.GetNumTimeSamples(): raise ValueError('animated cooking/contact input unsupported')
            fields[name] = {'exists':bool(attr), 'authored':bool(attr and attr.HasAuthoredValueOpinion()),
                            'composed':_scalar(attr.Get() if attr else None),
                            'schema_fallback':_scalar(definition.GetAttributeFallbackValue(name)),
                            'runtime_effective':'not_observed'}
    return {'applied_schemas':list(prim.GetAppliedSchemas()), 'attributes':fields,
            'topology':_topology(prim)}

def collect_collision_scene_snapshot(stage, robot_roots, body_names, settings, *, stage_cache=None):
    if not isinstance(stage, Usd.Stage): raise ValueError('stage must be a Usd.Stage')
    if not isinstance(robot_roots,(list,tuple)) or not robot_roots: raise ValueError('robot_roots must be nonempty')
    roots = [str(_obstacle_id(path)) for path in robot_roots]
    if len(set(roots)) != len(roots) or any(a != b and b.startswith(a+'/') for a in roots for b in roots):
        raise ValueError('robot roots must be unique and disjoint')
    if UsdGeom.GetStageMetersPerUnit(stage) != 1. or str(UsdGeom.GetStageUpAxis(stage)) != 'Z':
        raise ValueError('live scene must use meters and Z-up')
    stage_cache = UsdUtils.StageCache.Get() if stage_cache is None else stage_cache
    if not isinstance(stage_cache, Usd.StageCache) or not stage_cache.Contains(stage):
        raise ValueError('stage must already be registered in the supplied stage cache')
    stage_id = _identifier(stage_cache.GetId(stage).ToLongInt(), 'stage_id')
    if stage_cache.Find(stage_cache.GetId(stage)) != stage: raise ValueError('stage cache identity mismatch')
    settings_records = {path:_scalar(settings.get(path)) for path in SETTING_PATHS}
    environments, requests = [], []
    xforms = UsdGeom.XformCache(Usd.TimeCode.Default())
    for env_id, root in enumerate(roots):
        inventory = collect_collision_inventory(stage, root, body_names)
        bodies = [_pose_binding(stage, path, xforms) for path in inventory['body_paths']]
        colliders = []
        for record in inventory['colliders']:
            prim = stage.GetPrimAtPath(record['collider_path'])
            colliders.append({'path':record['collider_path'], 'path_id':_path_id(record['collider_path']),
                              'physics_source':_physics_source(prim)})
        by_path = {record['path']:record['path_id'] for record in colliders}
        for body in bodies:
            requests.append({'body_path':body['body_path'], 'body_path_id':body['body_path_id'],
                             'colliders':[{'collider_path':c['collider_path'], 'path_id':by_path[c['collider_path']]}
                               for c in inventory['colliders'] if c['body_path']==body['body_path']]})
        environments.append({'env_id':env_id, 'robot_root_path':root, 'inventory':inventory,
                             'body_bindings':bodies, 'collider_bindings':colliders})
    requests = _manifest(requests)
    source = {'stage_id':stage_id, 'stage_root_layer':stage.GetRootLayer().identifier,
              'stage_meters_per_unit':1., 'stage_up_axis':'Z', 'environments':environments}
    return {'schema':'m1_collision_scene_snapshot_v1', 'representation_status':'scene_snapshot_only',
            'source':source, 'source_fingerprint':_sha(source), 'settings':settings_records,
            'settings_fingerprint':_sha(settings_records), 'requests':requests}
```

`_validate_xform_order`会拒绝body/ancestor动画、缺省/非法op和reset栈；当前M1支持域就是静态T/O/S+单位body/world scale，其他布局明确拒绝而非静默漏掉scale。当前实际M1的17body为root下同级；如果任何body有RigidBodyAPI祖先（包括robot root之外）明确拒绝nested结构，否则父body运动会错误进入子body的静态ancestor hash。collider→body非均匀scale仍由已有inventory与support内核支持。非body祖先局部矩阵允许任意proper affine，只要body实际world rigid部分unit；局部互相抵消的scale保留在来源矩阵中。对attribute记录不得Apply schema、Set attr、Save层或构造shadow默认值代替实际schema fallback。

### 3. 扩展 RED→GREEN 与自审

- [x] 注册stage正例：局部cache.Insert仅在fixture中，builder不改cache；真路径codec round-trip每body/collider，传入完成query collector可全清单完成；snapshot仍无geometry_verified/CLEAR/passed。
- [x] 多root/不同body顺序/同prim是body和collider的真实USD正例；重复/重叠root、非法路径、错误body集合、禁用/孤立collider等沿原inventory拒绝；设置mixed bool/int/float/string/None保真、不使用typed getters；NaN及list/dict拒绝，Infinity显式sentinel可JSON round-trip。
- [x] 真实非proxy Cylinder及root外模板instance proxy Mesh：完整body/path/points/topology hashes；代理源points变更使source hash改变，返回对象修改不影响后续采集；不保存Usd.Prim/Stage/native/np对象。
- [x] body平移和旋转改变不改source/settings hash；body scale、ancestor scale/order、collider local offset/scale、hull参数/contact offset/API presence/拓扑/points变化被记录或明确拒绝。不存在属性与schemafallback清晰分离，`-inf`不是0。
- [x] 验证层dirty标志、各层ExportToString、settings原值、局部cache.Size/IDs前后不变；调用两次相同值/hash；属性按默认采集且动画拒绝；父ancestor无xform/嵌套xform/非法变换等边界。
- [x] 模块无torch/omni/carb/Kit导入，不调用query/pump/step。主代理会用真实M1资产在新内存Z/m stage引用验证17body/17collider（不更改原source）；还须独立审查和全量。此证据不能替代8-env实际query/失效watcher。

所有扩展用真实USD fixture，外部settings fake只需要get，刻意令get_as_bool等抛出以证明没误用。必须先看到对应缺失行为RED再实现，不以stack import error代替功能RED。

### 4. 验证与交付

- [x] 实现者focused、自审、scoped两文件提交。main独立复核、真实资产CPU采集、full（唯一basetemp）、SPEC→QUALITY；问题RED修复并复审。
- [x] 同步notes/todo/T306/index/per-test log。本包完成只代表静态绑定；下一步紧接watch/lease与8-env现场初始化诊断，不回头重复已有A1/B1/B2a/B2b1审计或把此静态快照用于无失效监控的CLEAR授权。

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp PXR_PLUGINPATH_NAME=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx/plugins/PhysxSchema/resources PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310:/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin:/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tests/test_collision_scene.py -q --tb=short -p no:cacheprovider
```

Main full将tests/test_collision_scene.py替换成tests，并附`--basetemp=/data/hexinkun-m1-acceptance-20260918/encounter-scene-binding-full`（尚未使用）。不能复用并删除旧fixture证据。

## 自审

### 实际资产触发的生命周期修正（2026-09-19）

主代理在真实8实例/136 collider的只读探针中，collect后进行layer文本/JSON往返再解码proxy path ID，3个独立子进程均在 `intToSdfPath` SIGSEGV(-11)。同脚本仅在采集前保留真实 `Sdf.Path` 列表后，2次所有body/collider解码通过。独立审查读取已装库，确认 `sdfPathToInt` 返回内部编码但不增加path引用；它不是持久字符串hash。因此本包原“仅JSON快照可直接提交”的隐含生命周期假设不成立。不得靠全局永久缓存或不保存proxy ID掩盖。

- [x] 新增显式 `CollisionPathScope(stage)`，仅负责持有本stage及已编码的真实Sdf.Path；`close()`幂等释放自己的引用，context manager退出调用close；不Insert/Erase cache、不改USD，不碰SDK。
- [x] `collect_collision_scene_snapshot(..., *, stage_cache=None, path_scope=None)` 必须接收同一stage的未关闭scope；无scope、错误类型、其他stage、已close均明确ValueError，不返回潜在悬空的请求清单。JSON输出仍完全脱离native对象，native生命周期由调用者的scope显式管理。query/回调未结束前必须保留scope；先关闭本批query再close scope，磁盘JSON的整数仅是当次进程证据、不能跨scope/进程复用。
- [x] 先加入真实USD instance-proxy回归（含JSON/layer序列化和临时路径分配、延后解码），子进程隔离native崩溃并断言returncode=0；首次缺scope API明确RED。正常/异常context退出、closed/wrongstage拒绝、无全局保活均测；原101项按显式scope fixture迁移，不用fake路径编码器。
- [x] 最小代码结构：scope构造验证Usd.Stage；保存`_stage`和私有`_paths={}`；`_encode(stage,path)`检查open和同stage，先存`Sdf.Path(path)`再调用实际codec并当场round-trip；`close()`清自己的字典和stage引用。builder先检查scope，body/collider编码统一经scope。不得改变source数据/几何判据或允许反射。
- [x] 实现者focused后，主代理重跑原真实8clone探针（按asset实际Quatd类型设置内存fixture姿态，原Quatf probe错误单独保留），全量使用新唯一basetemp `encounter-scene-binding-pins-full`；SPEC→QUALITY重新审查。旧1436full只代表修复前，不作为此修复通过证据。

此修正是本包native路径生命周期错误的必要修复，不改用户验收规格或运行SDK；watcher/lease与真实query仍是下一必需包，不能凭scope保活授权CLEAR。

- [x] 本包将实际stage/path/schema/settings接到已验证协议manifest，不引入新的控制/阈值/默认GPU假设。
- [x] USD/cache/settings均只读，真实设置类型、缺失与fallback分离，source bounds保留diagnostic_only来源。
- [x] 静态snapshot与实时有效性严格分开，watcher/真实query/无额外physics-step/G1/G2/learned/10000均不由本包替代。
- [x] 输入签名、测试命令与生产代码一致；沿用现有隔离分支，已有书面规格批准，不重复暂停问执行方式。
