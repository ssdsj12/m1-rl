# M1 Encounter Geometry Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现已批准 encounter 规格的不可变身份/方向坐标与再次接近纯几何谓词，作为后续物体关联和生命周期接入的可测试基础；不把此基础包当作控制或物理验收。

**Architecture:** 本包只有NumPy纯函数，不导入Isaac、teacher、sync或verifier，不发动作。独立EncounterKey区分episode与encounter，EncounterFrame保存不可变几何；返回投影视图而不覆盖原world输入。边界严格性、前轴和必需跨越轮的不同索引由CPU向量冻结。

**Tech Stack:** Python3.10 / amp、NumPy、pytest；SSH4090；/data隔离sparse git worktree。

---

## 用户批准、隔离和完整范围

用户2026-09-19明确“按规格实施”，解除具体书面规格e25e805的等待。采用本任务内子代理实施＋规格/质量两级审查，主代理独立复核。源规格正文不变；不再为相同已批准范围索取确认。

远端workspace：`/data/hexinkun-m1-acceptance-20260918/encounter-worktree`，branch `codex/m1-encounter-lifecycle`。以e25e805稀疏检出，adapter以已验收Task3快照逐字节覆盖**此新worktree副本**；原`/home/hexinkun/m1_rl`、Task3、run19不动。仅把已核对的八个scale差异记录为隔离基线，不推广为正式物理通过。

本地编辑暂存：`C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter`；仅apply_patch编辑，再SCP精确文件。下文相对路径以远端workspace为准。

源规格涉及多个子系统，按可独立验证包依序执行。此文件是首包的完整执行计划；后续包须在其代码实施前独立写出同等具体计划，不能用下表代替实施，也不能将首包完成改定义为总目标完成：

| 后续包 | 必需范围 / 规格对应 | 依赖 |
| --- | --- | --- |
| G0-B object geometry/provider | 实际USD所有碰撞形状/逐body pose与完整性清单；静态物体注册表、唯一hit归属、最近前方候选/歧义/large优先阻挡；规格3–5 | 本包 |
| G0-C coordinator | AVAILABLE/CROSSING/DEPARTING/CLEAR、真实有序完成、按物体/面前方历史、重遇seq增长、episode不伪增、原负例历史永久保留；规格4 | A+B |
| G0-D reference/sync integration | 具来源hash的vendor typed hook、G1旧IK/phase0..10前缀、行级缓存新捕获、显式owner释放/新5样本、raw-world/frame跨代连续性；规格6–7 | A–C |
| G0-E evidence/replay | 全env/step原始hit/identity/碰撞包络/动作sidecar、有界分片/流式、合法miss、独立NumPy重建和篡改负例；规格8 | A–D；容量审计 |
| G1 physical | 同一冻结新候选三次8×1600→1024×32→1024×1600，全旧严格门槛与新replay同时通过；规格9 | G0全回归/双审查 |
| G2 route/scenes | 统一方向与轮侧动作、多物体接触、连续真实路线/掉头及隔离场景；8env至少两次encounter，无reset/teleport；规格5/7/9 | 方向动作合同＋路线包 |
| 总目标后续 | 18首次几何负例、AME正常退出、named physical target桥、policy-only小跨越/大绕行、单进程10000实际更新 | 各自物理与学习验收，均未完成 |

## Baseline命令与范围

已有amp包含USD库，裸python不自动暴露pxr。沿用已记录CPU环境，不安装/升级SDK：

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests --basetemp=/data/hexinkun-m1-acceptance-20260918/encounter-baseline-pytest-20260919b
```

预期506通过、0skip。首次漏USD路径的collection error必须记为测试命令错误，不能改成通过或跳过USD测试。每次大测试选全新basetemp，不重用后让pytest清掉既有证据。CPU不占GPU7；此阶段不暂停占位。

## Task A1：纯几何与不可变身份

**Files:**
- Create: `tools/m1_reference_validation/encounter_geometry.py`
- Test: `tools/m1_reference_validation/tests/test_encounter_geometry.py`
- 不改旧runtime/sync/metrics；不在run.py启用此模块。

### API与合同

`EncounterKey(env_id, episode_id, obstacle_id, encounter_seq, geometry_generation)` frozen dataclass，env/episode/generation非负整数、seq正整数，拒绝bool/float ID；obstacle_id是非空绝对prim路径，不接受`.`/`..`/空path段。只表示已有encounter身份，不分配序号或维护历史。

`EncounterFrame(obstacle_id, geometry_generation, center_xy, direction_xy, ground_z, half_length, half_width, required_wheels)` frozen dataclass。center/direction使用不可变tuple；方向单位长度误差≤1e-12，不能为零或静默正交化。半长/半宽>0，全部有限，required_wheels是1..4个唯一0..3整数；顺序为FAR,FBL,RAR,RBL。先验证real数值kind再转float64，拒绝bool/complex/string/object。输入list/array经独立不可变副本储存。

纯函数接口：

```python
def project_points(frame, world_points):  # shape (...,3), 非空，real finite
    points = _points(world_points)
    delta = points[..., :2] - np.asarray(frame.center_xy)
    d = np.asarray(frame.direction_xy)
    left = np.array([-d[1], d[0]])
    out = np.stack((delta @ d, delta @ left, points[..., 2] - frame.ground_z), axis=-1)
    return _finite_output(out)

def canonical_points(frame, world_points):
    points = _points(world_points)
    if (frame.center_xy == (.85, -.2) and frame.direction_xy == (1., 0.)
            and frame.ground_z == 0.):
        return np.array(world_points, copy=True)  # 验证后保留原dtype/位模式
    out = project_points(frame, points)
    out[..., :2] += np.array([.85, -.2])
    return _finite_output(out)

def projected_extent(frame, support_points_world):
    points = _points(support_points_world)
    if points.ndim != 2:
        raise ValueError('support points must have shape (K,3)')
    longitudinal = project_points(frame, points)[:, 0]
    return float(longitudinal.min()), float(longitudinal.max())

def departed(frame, extent):
    low, high = _extent(extent)
    return low > frame.half_length + .005

def in_front(frame, extent):
    low, high = _extent(extent)
    return high < -frame.half_length - .005

def approach_kinematics(frame, previous_root, current_root, heading_xy, wheel_positions):
    previous = _point(previous_root)
    current = _point(current_root)
    wheels = _wheels(wheel_positions)  # 必须 (4,3)
    heading = _heading(heading_xy)     # 必须有限 (2,) 非零，不改其方向
    root_s = project_points(frame, np.stack((previous, current)))[:, 0]
    local = project_points(frame, wheels)
    front = local[[0, 1], 0]         # 两前轮，不是required_wheels
    corridor = local[list(frame.required_wheels), 1]
    heading_dot = float(heading @ np.asarray(frame.direction_xy))
    if not np.isfinite(heading_dot):
        raise ValueError('non-finite heading projection')
    return {
        'moving_toward': bool(root_s[1] > root_s[0]),
        'heading_toward': bool(heading_dot > 0.),
        'front_in_window': bool(np.all(front >= -.45 - 1e-12)
            and np.all(front <= -frame.half_length - .0959 + 1e-12)),
        'required_corridor': bool(np.all(np.abs(corridor)
            <= frame.half_width + .0959 + 1e-12)),
    }
```

上述内部检查函数的完整行为：`_points`以np.asarray先检查dtype.kind属于i/u/f、最后轴3、至少一个元素，再复制float64并拒绝任何非有限值；`_point`进一步要求(3,)；`_wheels`要求(4,3)；`_heading`要求real finite(2,)且至少一个分量非零，不用平方范数导致溢出；`_extent`要求real finite(2,)且low≤high；`_finite_output`拒绝任何非有限输出后返回独立数组。投影运算用局部np.errstate(over='ignore',invalid='ignore')再显式拒绝，不改变全局NumPy状态。构造参数标量也先拒绝bool/complex/string/object，验证 finite/shape/domain，不能仅`float(value)`接受字符串。内部helper只为验证，不实现隐含控制。

`projected_extent`只是对**调用者传入的真实形状support点**求投影；不宣称输入已覆盖机器人。G0-B必须验证完整碰撞shape清单/pose，曲面需解析support或准确且声明的保守包络；不能用轮中心/稀疏圆周点冒充全碰撞体。本包不接runtime，所以它不可能单独授权CLEAR。`approach_kinematics`只是四个几何条件，不携带完成/离开/前方历史或hit资格，调用者coordinator必须补齐这些条件；不提供一个误称“允许开始”的总bool。

- [x] **Step 1：先写fixture与最小RED测试，不写production文件。**

测试在函数内用importlib加载目标，先assert文件存在以使缺失功能是明确assert失败而非import collection错误。下列为核心用例，按API加入参数化反例：

```python
def test_g1_canonical_preserves_bits_and_does_not_alias(geometry):
    frame = geometry.EncounterFrame('/World/bar', 0, (.85,-.2), (1.,0.), 0., .03,.08,(0,2))
    raw = np.array([[.1,.1,.57],[-0.,0.,.3]], dtype=np.float32)
    result = geometry.canonical_points(frame, raw)
    assert result.dtype == raw.dtype
    assert result.tobytes() == raw.tobytes()
    assert not np.shares_memory(result, raw)

def test_strict_exit_and_front_equalities(geometry):
    frame = geometry.EncounterFrame('/World/bar',0,(.85,-.2),(1.,0.),0.,.03,.08,(0,2))
    b = frame.half_length + .005
    assert not geometry.departed(frame, (b,b+.1))
    assert geometry.departed(frame, (np.nextafter(b,np.inf),b+.1))
    assert not geometry.in_front(frame, (-b-.1,-b))
    assert geometry.in_front(frame, (-b-.1,np.nextafter(-b,-np.inf)))

def test_front_axle_is_not_required_crossing_pair(geometry):
    frame = geometry.EncounterFrame('/World/bar',0,(0.,0.),(1.,0.),0.,.03,.08,(0,2))
    wheels = np.array([[-.30,0,.1],[-.30,.40,.1],[-.60,0,.1],[-.60,.40,.1]])
    actual = geometry.approach_kinematics(frame,[-.35,0,.55],[-.34,0,.55],[1.,0.],wheels)
    assert all(actual.values())  # RAR在front窗口后不应导致front不通过；FBL在走廊外不影响required
    wheels[1,0] = -.1249
    assert not geometry.approach_kinematics(frame,[-.35,0,.55],[-.34,0,.55],[1.,0.],wheels)['front_in_window']
```

还需精确断言：+90° `(center=(10,20),d=(0,1),ground=2,p=(9.94,19.6,2.57))`与反向`d=(-1,0),p=(10.4,19.94,2.57)`都映射canonical(.45,-.14,.57)，rtol0/atol1e-12；所有输入调用前后byte/dtype/writeable不变。全support示例min(s)=.030则未离开，改最落后support至.036才离开，即使root1.30/两轮1.01不能提前CLEAR。

- [x] **Step 2：运行RED并保存实际失败原因。**

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tests/test_encounter_geometry.py -q -p no:cacheprovider
```

预期明确缺失encounter_geometry.py的assert FAIL，无Isaac/CUDA导入。

- [x] **Step 3：实现上述两个dataclass和六个纯函数及严格输入验证。** 只创建指定production文件。逐组加测试→RED→实现→GREEN；不从新模块导入旧controller构造expected，不在测试结束后反向补造RED。
- [x] **Step 4：补齐边界RED/GREEN。** ID错误类型/负值/seq0；mutable构造输入隔离；非法prim path；空/重复required；方向0/非unit；尺寸≤0；每种shape/NaN/±Inf/bool/string/complex/object；有限极值相减溢出；extent反转；front两个端点包含、-.1255拒绝；corridor .1759+.5e-12允许/+.2e-11拒绝；停止/远离/heading垂直/反向分别false；不同frame调用不能修改旧frame或world样本。
- [x] **Step 5：运行focused＋全部原506回归、bash -n，独立SPEC审查通过后再QUALITY审查。** 主代理fresh323 focused、829 full（506+323）、0skip，bash-n和旧文件diff-rq通过；SPEC修正mixed Integral后PASS，QUALITY PASS，仅冗余复制minor不阻塞。见实施日志。
- [x] **Step 6：仅在隔离branch提交两个新文件，记录hash、测试命令/退出码、旧文件逐字节未变、notes。** A1=1cb83bc，mixed Integral fix=f8ce0af；未接runtime、未新物理验收。

```bash
git -C /data/hexinkun-m1-acceptance-20260918/encounter-worktree add tools/m1_reference_validation/encounter_geometry.py tools/m1_reference_validation/tests/test_encounter_geometry.py
git -C /data/hexinkun-m1-acceptance-20260918/encounter-worktree diff --cached --check
git -C /data/hexinkun-m1-acceptance-20260918/encounter-worktree commit -m 'feat: add immutable M1 encounter geometry primitives'
```

## 自审与后续

- [x] 规格覆盖按上方包矩阵明确；本包只落实§3身份/§4.2与§5的纯几何，不偷换成完整provider/coordinator/验收。
- [x] 前轴0/1与必需轮0/2分开；严格离开不使用scanner容差或减atol；G1恒等不修改旧IK env-origin-y。
- [x] helper、签名、dtype和失败语义已定义；fixture以独立数值expected验证。
- [x] 新工作区/已有USD库/全新临时目录明确；无GPU运行、无新安装、无旧日志删除。
- [ ] 完成A1后，继续G0-B provider/碰撞清单的具体计划与实现，再C/D/E；持续目标不在A1结束时标完成。
