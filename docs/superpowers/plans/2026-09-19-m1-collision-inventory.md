# M1 Collision Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从真实 USD 建立不漏 instance proxy、明确逐 body 归属的完整机器人碰撞清单，供后续 PhysX query、包络和独立重放绑定。

**Architecture:** G0-B1 是只读 USD 输入适配器，不是离开判定器。输出 JSON-safe 的 `usd_inventory_only` 清单及 authored 几何摘要；不会将 source mesh bounds 宣称为 cooked shape，也不提供 `clear` 或 `geometry_verified=true`。PhysX query/cooked 包含性、动态 body pose 包络、障碍注册与选择仍是 G0-B 的后续必需包。

**Tech Stack:** amp Python3.10 / NumPy / 已有 pxr；CPU-only；现有 `/data` 隔离 worktree。

---

## 已批准范围与来源事实

继续用户已批准的 encounter 规格 §3、4.2、5、8。无需再次征求相同范围授权。A1 的独立规格/质量审查通过后才实施本包；先写测试并看到 RED。

实际 `/home/hexinkun/m1/Go2Pvcnn/assets/m1_panda/m1_floating.usda` 的 `/ZJ_V3_URDF_V1_0` 下是 17 body / 17 enabled collider：13 个 `convexHull` Mesh instance proxy，4 个 Y 轴 Cylinder。遍历整个 pseudoroot 会误收 `/colliders` 模板。13 mesh 共 4,544,118 authored points，不是 cooked hull 顶点数。

SDK property query 的 `aabb_local_min/max` 是 collider-local，官方 graph 用 collider→body 的完整 USD 相对变换处理，不额外叠加 response.local_rot。source mesh 在 cooking 中可能被扩展；因此本包的 authored bounds 仅诊断。后续必须绑定实际 query、完整回调清单、cooked geometry/设置及包含性，不能提前授权 CLEAR。CPU inventory 不加载 Kit/omni/PhysX、不触发 cooking、不动 GPU7 占位。

## 文件边界

- Create `tools/m1_reference_validation/collision_inventory.py`：仅 USD 遍历、归属和静态几何摘要。
- Create `tools/m1_reference_validation/tests/test_collision_inventory.py`：真实 in-memory USD stage 测试，不 mock 遍历/instance proxy。
- 不改 `encounter_geometry.py`、runtime、run、sync、metrics、reference、SDK 或资产。
- local stage：`C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter/`，apply_patch 后 SCP 精确文件到现有 encounter-worktree。

## Task B1：完整 USD collider inventory

### 输入、输出与拒绝语义

公共接口只有：

```python
def collect_collision_inventory(stage, robot_root_path, expected_body_names):
    """Read-only JSON-safe USD inventory; not a verified physical envelope."""
```

`stage` 必须是有效 `Usd.Stage`；root 必须为有效、active、loaded 的绝对 prim path，不可为 `/`、property 或模板 pseudoroot。root 内 active/defined/nonabstract 子树也必须全部 loaded，不能由默认 PrimRange 过滤掉未加载payload后假称完整；只拒绝，不调用stage.Load修改用户状态。`expected_body_names` 是非空 list/tuple、唯一非空字符串；支持测试 1–2 body 和真实 17 body，不硬编码只查 root/四轮。严格要求 robot root 下所有 active rigid body 的名字集合等于声明，名字不得重复，每个声明 body 至少一个启用 collider。enabled=false 或 time-sampled enabled 的 rigid body/collider 明确拒绝，不静默忽略。所有 collider 必须在 root 内找到最近 rigid-body 祖先，不从 root 外借 body。

只支持本资产所需 `Mesh + MeshCollisionAPI.approximation=convexHull` 与 `Cylinder`。其他类型/approximation、缺失/空/非有限 Mesh points、非正/非有限 radius/height、非法 axis 均拒绝。若任何碰撞几何属性或 collider→body 路径的 xform op 有 time samples，拒绝静态绑定；若这段路径存在 resetXformStack，同样拒绝。body 自身的 world pose 不作为静态碰撞变换，未来逐步采集。

每个 collider 保存 collider path、body name/path/index、type、instance_proxy、`collider_to_body_column_matrix`。矩阵为完整 affine 的列向量约定（`np.asarray(GfMatrix).T`），必须有限、末行 `[0,0,0,1]`、线性部分正 determinant；允许非均匀正缩放和旋转，不能只变换 min/max 两点或丢缩放。拒绝奇异/反射及 reset stack。返回矩阵及所有数据为独立 Python list/scalar，不引用 stage/NumPy 可变对象。

质量复核补充：不能只检查GetOrderedXformOps已返回的操作，因为USD会跳过raw xformOpOrder中的missing op。必须按原order逐项核属性存在、USD可解析、静态default有值，blocked/unset/op非法明确ValueError带path；正常完全未声明op仍允许identity，合法!invert! pivot必须保留。此项是完整transform合同的落实，不改变物理几何或阈值。

Mesh 额外保存 `approximation`、`authored_point_count`、`authored_points_dtype`、`authored_points_sha256`、`authored_local_bounds_diagnostic_only`。hash 是 C-contiguous 原 dtype points bytes 的 SHA256，dtype 和 shape（count×3）一起属于记录；不把 float32 悄悄转成 float64 后冒称原始 hash。Cylinder 额外保存 `axis/radius/height`；这里只记录 authored 类型，不推定实际 `/physics/collisionApproximateCylinders` 取值或实际 shape 类型。

顶层固定字段：

```python
{
    'schema': 'm1_collision_inventory_v1',
    'representation_status': 'usd_inventory_only',
    'robot_root_path': str(root.GetPath()),
    'stage_up_axis': str(UsdGeom.GetStageUpAxis(stage)),
    'stage_meters_per_unit': float(UsdGeom.GetStageMetersPerUnit(stage)),
    'body_names': list(expected_body_names),
    'body_paths': [...],  # 与 body_names 相同顺序
    'colliders': [...],   # 依 collider path 排序，稳定顺序但不以槽位冒充ID
}
```

stage unit/up-axis 只如实记录，不因单独 overlay 默认 `.01/Y` 将资产几何擅自重缩放。runtime 的实际 Z/m 单位 guard 保留在未来 live 绑定处。返回值无 `clear/verified/passed` 字段。完整 schema 后续与 run/source hashes 共同冻结；此函数自身不声称匿名测试 stage 已具磁盘来源链。

### Step 1：真实 USD fixture 与 RED

- [x] 创建测试文件，使用函数内 importlib loader，缺少 production 文件时明确 assertion FAIL 而不是 collection error。
- [x] fixture 用 `Usd.Stage.CreateInMemory()`、`UsdGeom.Xform.Define`、`UsdPhysics.RigidBodyAPI.Apply`，创建 `/Robot/B0`、`/Robot/B1`；B0 下 triangle Mesh (`points=[(-1,-2,-3),(1,2,3),(1,-2,3)]`、faceVertexCounts=[3]、indices=[0,1,2])，设置 CollisionAPI / MeshCollisionAPI convexHull；B1 下 Cylinder r=.0959 h=.0465 axisY + CollisionAPI。
- [x] 第一测试断言 schema/status、两 body/两 collider、最近 body mapping、mesh count3/原float32 bytes hash、Cylinder参数、json.dumps成功，stage layer ExportToString 调用前后不变。

```python
def test_inventory_collects_all_shapes_without_mutating_stage(inventory, stage_two_bodies):
    stage = stage_two_bodies
    before = stage.GetRootLayer().ExportToString()
    result = inventory.collect_collision_inventory(stage, '/Robot', ['B0', 'B1'])
    assert result['representation_status'] == 'usd_inventory_only'
    assert result['body_names'] == ['B0', 'B1']
    assert [c['body_index'] for c in result['colliders']] == [0, 1]
    assert len(result['colliders']) == 2
    assert 'clear' not in result and 'geometry_verified' not in result
    assert stage.GetRootLayer().ExportToString() == before
```

执行末尾 focused 命令，预期缺模块的 assertion RED，无 Isaac/GPU 导入。

### Step 2：最小遍历与实现

- [x] 按下面算法实现单一入口及小型私有检查 helper；完整失败条件以上节为准，helper 只读属性，禁止 `.Apply/.Set` 出现在 production。

```python
import hashlib
import math
import numpy as np
from pxr import Sdf, Usd, UsdGeom, UsdPhysics


def _static(attr):
    if not attr or attr.GetNumTimeSamples() or attr.Get() is None:
        raise ValueError(f'missing or time-varying static attribute: {attr}')
    return attr.Get()


def _nearest_body(prim, declared_paths, root_path):
    cursor = prim
    while cursor and cursor.GetPath().HasPrefix(root_path):
        if cursor.HasAPI(UsdPhysics.RigidBodyAPI):
            if str(cursor.GetPath()) not in declared_paths:
                raise ValueError(f'undeclared body: {cursor.GetPath()}')
            return cursor
        cursor = cursor.GetParent()
    raise ValueError(f'collider has no own rigid body: {prim.GetPath()}')


def _relative_matrix(prim, body, cache):
    cursor = prim
    while cursor != body:
        xform = UsdGeom.Xformable(cursor)
        if xform:
            if xform.GetResetXformStack():
                raise ValueError(f'resetXformStack: {cursor.GetPath()}')
            order = xform.GetXformOpOrderAttr()
            if order and order.GetNumTimeSamples():
                raise ValueError(f'time-sampled xformOpOrder: {cursor.GetPath()}')
            raw_order = list(order.Get() or [])
            for token in raw_order:
                token = str(token)
                inverse = token.startswith('!invert!')
                attribute_name = token[len('!invert!'):] if inverse else token
                attribute = cursor.GetAttribute(attribute_name)
                _static(attribute)
                try:
                    op = UsdGeom.XformOp(attribute, inverse)
                    if not op or str(op.GetOpName()) != token:
                        raise ValueError('xform op did not preserve declared identity')
                except Exception as error:
                    raise ValueError(f'invalid xform op {token}: {cursor.GetPath()}') from error
        cursor = cursor.GetParent()
    matrix, resets = cache.ComputeRelativeTransform(prim, body)
    column = np.asarray(matrix, dtype=np.float64).T.copy()
    if (resets or not np.isfinite(column).all()
            or not np.array_equal(column[3], [0., 0., 0., 1.])):
        raise ValueError(f'invalid collider affine: {prim.GetPath()}')
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        determinant = np.linalg.det(column[:3, :3])
    if not np.isfinite(determinant) or determinant <= 0:
        raise ValueError(f'singular or reflected collider affine: {prim.GetPath()}')
    return column.tolist()


def _shape(prim):
    if prim.IsA(UsdGeom.Mesh):
        if not prim.HasAPI(UsdPhysics.MeshCollisionAPI):
            raise ValueError(f'missing mesh collision API: {prim.GetPath()}')
        approximation = str(_static(UsdPhysics.MeshCollisionAPI(prim).GetApproximationAttr()))
        if approximation != 'convexHull':
            raise ValueError(f'unsupported approximation: {prim.GetPath()} {approximation}')
        points = np.asarray(_static(UsdGeom.Mesh(prim).GetPointsAttr()))
        if (points.ndim != 2 or points.shape[1] != 3 or len(points) == 0
                or points.dtype.kind not in 'iuf' or not np.isfinite(points).all()):
            raise ValueError(f'invalid authored points: {prim.GetPath()}')
        return {
            'approximation': approximation,
            'authored_point_count': len(points),
            'authored_points_dtype': points.dtype.str,
            'authored_points_sha256': hashlib.sha256(np.ascontiguousarray(points).tobytes()).hexdigest(),
            'authored_local_bounds_diagnostic_only': [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
        }
    if prim.IsA(UsdGeom.Cylinder):
        shape = UsdGeom.Cylinder(prim)
        axis = str(_static(shape.GetAxisAttr()))
        radius = float(_static(shape.GetRadiusAttr()))
        height = float(_static(shape.GetHeightAttr()))
        if axis not in ('X', 'Y', 'Z') or not all(math.isfinite(v) and v > 0 for v in (radius, height)):
            raise ValueError(f'invalid cylinder: {prim.GetPath()}')
        return {'axis': axis, 'radius': radius, 'height': height}
    raise ValueError(f'unsupported collider type: {prim.GetPath()} {prim.GetTypeName()}')


def collect_collision_inventory(stage, robot_root_path, expected_body_names):
    if not isinstance(stage, Usd.Stage) or not stage:
        raise ValueError('stage must be a valid Usd.Stage')
    if not isinstance(robot_root_path, str) or not Sdf.Path.IsValidPathString(robot_root_path):
        raise ValueError('robot_root_path must be a valid absolute prim path')
    path = Sdf.Path(robot_root_path)
    if not path.IsAbsolutePath() or not path.IsPrimPath() or path == Sdf.Path.absoluteRootPath:
        raise ValueError('robot_root_path must not be relative, property, or pseudoroot')
    root = stage.GetPrimAtPath(path)
    if not root or not root.IsActive() or not root.IsLoaded():
        raise ValueError(f'missing/disabled/unloaded robot root: {path}')
    if (not isinstance(expected_body_names, (list, tuple)) or not expected_body_names
            or any(not isinstance(n, str) or not n for n in expected_body_names)
            or len(set(expected_body_names)) != len(expected_body_names)):
        raise ValueError('expected_body_names must be unique nonempty strings')
    names = tuple(expected_body_names)
    predicate = Usd.TraverseInstanceProxies(Usd.PrimIsActive & Usd.PrimIsDefined & ~Usd.PrimIsAbstract)
    prims = list(Usd.PrimRange(root, predicate))
    for prim in prims:
        if not prim.IsLoaded():
            raise ValueError(f'unloaded robot descendant: {prim.GetPath()}')
    bodies = [p for p in prims if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    by_name = {p.GetName(): p for p in bodies}
    if len(by_name) != len(bodies) or set(by_name) != set(names):
        raise ValueError('actual rigid bodies do not exactly match expected_body_names')
    for body in bodies:
        if _static(UsdPhysics.RigidBodyAPI(body).GetRigidBodyEnabledAttr()) is not True:
            raise ValueError(f'disabled rigid body: {body.GetPath()}')
    body_paths = [str(by_name[name].GetPath()) for name in names]
    declared = set(body_paths)
    records = []
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    for prim in prims:
        if not prim.HasAPI(UsdPhysics.CollisionAPI):
            continue
        if _static(UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr()) is not True:
            raise ValueError(f'disabled collider: {prim.GetPath()}')
        body = _nearest_body(prim, declared, path)
        record = {
            'collider_path': str(prim.GetPath()), 'body_name': body.GetName(),
            'body_path': str(body.GetPath()), 'body_index': names.index(body.GetName()),
            'type': prim.GetTypeName(), 'instance_proxy': prim.IsInstanceProxy(),
            'collider_to_body_column_matrix': _relative_matrix(prim, body, cache),
        }
        record.update(_shape(prim))
        records.append(record)
    if {r['body_path'] for r in records} != declared:
        raise ValueError('one or more declared bodies have no enabled collider')
    units = float(UsdGeom.GetStageMetersPerUnit(stage))
    if not math.isfinite(units) or units <= 0:
        raise ValueError('invalid stage metersPerUnit')
    return {
        'schema': 'm1_collision_inventory_v1',
        'representation_status': 'usd_inventory_only',
        'robot_root_path': str(path),
        'stage_up_axis': str(UsdGeom.GetStageUpAxis(stage)),
        'stage_meters_per_unit': units,
        'body_names': list(names), 'body_paths': body_paths,
        'colliders': sorted(records, key=lambda r: r['collider_path']),
    }
```

`nearest_declared_body` 从 collider prim 开始（支持 collider 同 prim 也是 rigid body），逐 GetParent 向上，只在 robot root 范围内；遇最近 rigid body 未声明则拒绝，不能跳过它绑定更上层。`static_attr` 检查 attr.GetNumTimeSamples()==0 和 attr.Get()；local xform 检查从 collider 到 body 的不含 body 本身链上所有 `UsdGeom.Xformable.GetOrderedXformOps()` 的 `.GetAttr()`。所有错误用带 path/字段说明的 ValueError，不吞掉缺形状后继续。

### Step 3：proxy / completeness / transform 边界 RED→GREEN

- [x] instance proxy fixture：在 root 外 `/Templates/Shape` 定义 Xform+mesh，仅 `/Robot/B0/collisions` 内部引用该 Xform 且 SetInstanceable(True)；断言只收 `/Robot/B0/collisions/mesh` 这一个实际 instance proxy，不收 template。真实bodyB1仍一个Cylinder。
- [x] 额外 body、缺 body、重复 leaf name、某body无collider、root外 orphan collider（将无body shape放入Robot）均拒绝。root外其他模板不是 orphan，应排除。
- [x] disabled或time-sampled enabled的rigid body/collider、root仍loaded但内部payload unloaded、unsupported Cube、Mesh approximation none/convexDecomposition、empty/nonfinite points、Cylinder axis invalid/r/h<=0/nonfinite，分别先RED再最小实现。主代理已实际复现三项遗漏；它们落实静态/完整合同，不改变物理门槛。
- [x] xform 用 collider local `translate(2,0,0)`＋rotateZ90＋scale(2,3,4) 的已知顺序；独立 Gf.Transform 逐点与返回 column_matrix 对照，非对角旋转中只变 min/max 两点必须能被用例区分；body自身 translate(100,200,300)不应混入 collider_to_body。
- [x] resetXformStack、time-sampled point/radius/xform、singular/reflected scale 拒绝；有限静态非均匀正缩放通过。原值不改，返回 list 修改不影响 stage；每次 collect 结果独立。
- [x] raw order missing op、blocked op default、op未赋default、unknown opcode，均先RED后明确ValueError；保留无op identity，并验证合法pivot !invert! 的独立预期坐标。不能接受USD warning后静默回退identity。
- [x] 缺 root、relative/property/pseudoroot、invalid stage、empty/duplicate/nonstring expected body names，均 ValueError。

### Step 4：实际 USD CPU 核验、复核与提交

- [x] focused 全过后，主代理/独立 reviewer 用真实 `/ZJ_V3_URDF_V1_0` 和实际 17 body names 运行 collector，assert 17 body / 17 collider / 13 proxy Mesh /4 Cylinder / 总points4,544,118；每个relative变换identity。该检查仍不是 PhysX geometry 已验证。
- [x] 独立 SPEC→QUALITY 审查；修复先RED再GREEN，主代理独立focused＋所有旧测试回归（新basetemp，数据在/data）。确认只新增两个文件，旧参考/资产hash不变。
- [x] 仅 scoped add 两文件＋commit，记录 git SHA、命令/退出码、证据状态、notes/todo/log。不得在本包结束关闭 G0-B 或总goal。

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tests/test_collision_inventory.py -q --tb=short -p no:cacheprovider
```

## 自审和后续接口

- [x] 本包只实现 G0-B 的完整 USD shape/body输入，不自报实际包络验证，不改变已批准clearance/控制。
- [x] source mesh/cooked 区别、instance proxy、模板排除、逐body而非root、column affine/scale、Cylinder近似配置均明确。
- [x] 每种字段、type/shape/disabled/static失败与真实USD测试路径已定义；无新安装、大磁盘副本或GPU占位变更。
- [ ] 后续G0-B2：实际query/cooked绑定和完整性、经核验的保守盒+逐body pose有限内存包络；之后障碍registry/hit唯一关联/候选选择。C/D/E及新三次8×1600→1024×32→1024×1600/G2/AME/policy/10000完整门槛均继续，不将inventory当验收。
