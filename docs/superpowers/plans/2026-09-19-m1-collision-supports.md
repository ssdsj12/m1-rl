# M1 Collision Support Transform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把每个碰撞体的完整保守盒通过完整 collider→body→world 仿射变换展开为八角点，供整机投影及独立重放使用。

**Architecture:** G0-B2a 是纯 NumPy 坐标核，不采集或认证 PhysX query。B1 的 authored bounds 禁止作为现场 query 的回退；本包支持点只有在 B2b 绑定实际 stage/path、所有回调、cooking/settings/geometry generation 后才成为实际碰撞包络输入。所有 body 独立变换，不将 base pose 套给四肢；支持 1024 行批量但不积累时间历史。

**Tech Stack:** amp Python3.10 / NumPy / CPU；现有隔离 worktree，原控制与runtime不变。

---

## 上下文和边界

用户已批准 encounter 规格 §4.2/5/8。A1 f8ce0af、B1 0196f6f 均 SPEC→QUALITY PASS，main913full/0skip。B1清单含17body/17collider，但其 mesh bounds是 authored diagnostic，不能证明cooked shape。B2a解决有限保守盒的完整变换，B2b仍须实际query完整绑定、失效处理、现场非零offset/旋转/scale核验；最后再接障碍registry/coordinator/replay与G1/G2。此次不启动Kit/GPU、不修改SDK/资产，也不新增clear/verified通过标记。

文件仅新增：

- `tools/m1_reference_validation/collision_supports.py`
- `tools/m1_reference_validation/tests/test_collision_supports.py`

local staging：`C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter/`；apply_patch编辑后SCP对应文件到`/data/hexinkun-m1-acceptance-20260918/encounter-worktree`。`encounter_geometry._real_array`作为本adapter内部统一有限实数检查复用，避免复制已测试的mixed-bool/NaN/overflow检查；不改其代码/接口。

## Task B2a：完整八角点与逐body批量变换

### Step 1：先写独立数值测试并观察RED

- [x] 缺production时fixture内部assert产生RED，不制造collection error。加载模块时将adapter路径加入monkeypatch.syspath_prepend，避免影响其他测试。
- [x] 首个fixture两collider、不同body，第一盒min[-1,-2,-3]/max[1,2,3]，collider→body=T(2,0,0)·Rz90·S(2,3,4)。八角点body范围应[-4,-2,-12]..[8,2,12]，不能把两个对角点当完整盒。
- [x] body0再Rz45，body1平移(20,0,0)，独立用itertools.product和显式标量计算/逐点矩阵乘法oracle比较所有点；Rz45 min/max两点漏洞必须使故意错误算法与正确范围不同。

```python
def test_rotation_keeps_all_eight_corners(module):
    bounds = [[[-1., -2., -3.], [1., 2., 3.]]]
    transform = [[[0., -3., 0., 2.], [2., 0., 0., 0.],
                  [0., 0., 4., 0.], [0., 0., 0., 1.]]]
    points = module.make_body_supports(bounds, transform)
    assert points.shape == (1, 8, 3)
    np.testing.assert_array_equal(points.min(axis=1), [[-4., -2., -12.]])
    np.testing.assert_array_equal(points.max(axis=1), [[8., 2., 12.]])
```

RED命令见末尾；预期上述新模块缺失的assert FAIL，无CUDA/Kit导入。

### Step 2：实现最小坐标核

- [x] 实现以下完整接口；docstring明确输出只是条件性几何计算，调用者负责实际query来源及每个collider完整性。矩阵为列向量、有限正det、精确affine末行；保留完整scale。输入不就地改写，输出float64独立数组。计算溢出必须ValueError，不能返回inf。

```python
"""Finite conservative-box transforms; not a PhysX query or a CLEAR authority."""
import numpy as np
from encounter_geometry import _real_array


_CORNERS = np.array([(x, y, z) for x in (0, 1) for y in (0, 1)
                     for z in (0, 1)], dtype=np.int64)


def _affines(value, name, shape):
    matrices = _real_array(value, name, shape)
    if not np.all(matrices[..., 3, :] == (0., 0., 0., 1.)):
        raise ValueError(f'{name} must have affine final row [0,0,0,1]')
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        determinants = np.linalg.det(matrices[..., :3, :3])
    if not np.isfinite(determinants).all() or np.any(determinants <= 0):
        raise ValueError(f'{name} must have finite positive linear determinants')
    return matrices


def _names(value, name, unique):
    if (not isinstance(value, (list, tuple)) or not value
            or any(not isinstance(item, str) or not item for item in value)):
        raise ValueError(f'{name} must be a nonempty list/tuple of nonempty names')
    if unique and len(set(value)) != len(value):
        raise ValueError(f'{name} must contain unique names')
    return tuple(value)


def make_body_supports(collider_local_bounds, collider_to_body):
    """Return (C,8,3) body-local corners of supplied (not certified) query boxes."""
    bounds = _real_array(collider_local_bounds, 'collider_local_bounds')
    if bounds.ndim != 3 or bounds.shape[1:] != (2, 3) or bounds.shape[0] == 0:
        raise ValueError('collider_local_bounds must have nonempty shape (C,2,3)')
    if np.any(bounds[:, 0] > bounds[:, 1]):
        raise ValueError('collider_local_bounds min must be <= max on every axis')
    transforms = _affines(collider_to_body, 'collider_to_body', (len(bounds), 4, 4))
    corners = bounds[:, _CORNERS, np.arange(3)]
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        result = (np.einsum('cij,ckj->cki', transforms[:, :3, :3], corners)
                  + transforms[:, None, :3, 3])
    if not np.isfinite(result).all():
        raise ValueError('collider_to_body support transform must remain finite')
    return result


def world_support_points(body_supports, collider_body_names, body_names,
                         pose_body_names, body_to_world):
    """Return (N,C,8,3) points using each collider's own body's world matrix.

    Every declared body must be represented; the caller must also bind every
    collider/query and the actual pose names/paths/env/generation. This pure
    function cannot establish provenance, collision coverage or permission.
    """
    bodies = _names(body_names, 'body_names', True)
    pose_names = _names(pose_body_names, 'pose_body_names', True)
    collider_names = _names(collider_body_names, 'collider_body_names', False)
    if pose_names != bodies:
        raise ValueError('pose_body_names must exactly match body_names in order')
    if set(collider_names) != set(bodies):
        raise ValueError('collider_body_names must cover exactly all declared bodies')
    points = _real_array(body_supports, 'body_supports', (len(collider_names), 8, 3))
    raw_poses = _real_array(body_to_world, 'body_to_world')
    if raw_poses.ndim != 4 or raw_poses.shape[1:] != (len(bodies), 4, 4) or len(raw_poses) == 0:
        raise ValueError('body_to_world must have nonempty shape (N,B,4,4)')
    poses = _affines(raw_poses, 'body_to_world', raw_poses.shape)
    indices = [bodies.index(name) for name in collider_names]
    selected = poses[:, indices]
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        result = (np.einsum('ncij,ckj->ncki', selected[:, :, :3, :3], points)
                  + selected[:, :, None, :3, 3])
    if not np.isfinite(result).all():
        raise ValueError('body_to_world support transform must remain finite')
    return result
```

内部helper按已有项目风格可整理，但不可弱化校验/增大容差/归一化数据。退化盒(min=max)作为保守盒数学输入允许，实际shape合法性归现场query绑定；不凭空膨胀盒。shape中仅N=1024那一维扩展，禁止构造(N,C,B,...)叉积。不存在root-only快捷方式。

### Step 3：失败边界与完整body映射测试

- [x] parameterized RED→GREEN：bounds空/错shape/min>max/NaN/Inf/字符串/object/complex/bool和mixedbool；matrix错count/shape/nonaffine/reflection/singular/非有限以及运算overflow。
- [x] 多collider映射同body允许；乱序collider按name映射；漏body、未知body、重复body、pose names缺/多/错序、空/非字符串名称明确ValueError。输入/输出数组互不alias，返回值修改不污染下次结果。
- [x] N=1和1024、C=B=17；每body有不同translation/rotation，后肢远于root的负例证明不能用base-only离开。1024输出shape=(1024,17,8,3)，float64 nbytes=3,342,336；不保存逐步历史。
- [x] seeded随机正仿射与逐点4x4 oracle至少32组；单独90°和45°旋转、非均匀scale、非零offset、两级变换，Rz45两角点不足的反例。
- [x] A1 `projected_extent`接完整flatten点云，所有支持点对任意选定单位方向均在min/max内；整机后部卡在h+.005时departed=false，严格跨过才true。只证明条件性数学，不自造query证据。
- [x] source/SDK/runtime导入guard、无副作用、bash-n及所有旧CPU回归保持。新测试不得增加对GPU/torch/omni的依赖。

### Step 4：主代理验证、SPEC→QUALITY与 scoped commit

- [x] 实现者报告RED/GREEN、self-review、只add上述两文件的git SHA；不提交主代理并行docs。
- [x] main独立数值/focused/all-tests验证，SPEC后QUALITY顺序审查，真实问题补RED后复审；唯一新全量basetemp=/data/hexinkun-m1-acceptance-20260918/encounter-supports-full。
- [x] notes/todo/T306/log同步证据；只把B2a标为数学核完成，B2b现场query和完整G0/G1/G2/AME/learned/10000保持未完成。

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tests/test_collision_supports.py -q --tb=short -p no:cacheprovider
```

## 自审

执行结果：源码3a1d25f/c12e0af，仅新增上述两文件。主代理1020full/0skip（140.58s）；SPEC107focused0.54s、QUALITY107focused0.50s均PASS。实际USD17collider136角点与Gf独立数学对照maxerror0，但状态明确authored_bounds_math_only。B2a完成，不关闭B2b实际query/geometry失效/现场无额外physics-step等待门槛，也不关闭G0/G1/G2及训练总目标。

- [x] 只覆盖完整规格的有限geometry子组件，不声称整机现场来源/离开已验证。
- [x] 所有接口/shape/name语义及源代码路径一致；八角点、全body、完整affine、错误类型、内存上界明确。
- [x] 实际query完整性/geometry失效/pose命名、独立raw重放及物理验证明确属于后续B2b和C/D/E，并未省略。
- [x] 已有隔离worktree及批准范围内自动继续，不重复请求用户选择执行方式；使用subagent-driven-development与TDD。
