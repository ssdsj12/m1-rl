# M1 Actual Collision Query Initialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在既有8×32参考流程的唯一reset之后、首动作之前实际调用PhysX property query，并用原始状态和事件证明初始化未推进physics或改变控制/RNG。

**Architecture:** opt-in诊断标志默认关闭；同步fastpath只使用已验证CollisionSceneLease。实际PENDING明确记录失败且不pump；现场若需要异步推进，再根据保留证据实现受控等待，不能把同步限制当最终功能的替代。诊断拥有一个临时physics callback，query/watch/path必须在env/app清理前释放。

**Tech Stack:** amp Python3.10，现有IsaacLab45/reference runner，actual USD/Carb/PhysX；CPU测试使用真实USD/lease/query，只有外部SDK/native tensor接口可替身。无SDK/driver/主源码修改。

---

## 范围、路径和前置证据

用户已批准完整encounter规格，不重开审批。上一轮progress：8a3746f＋bc0d5a8，main1565full/0skip、SPEC→QUALITY。fresh bc0d5a8 clean linked worktree；本轮fresh lease/runtime focused171/7.77s/exit0。既有run.py/run.sh尚未改动。

Remote root `/data/hexinkun-m1-acceptance-20260918/encounter-worktree`，adapter `tools/m1_reference_validation`；local staging `C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter/`。

只改 `runtime.py`、`run.py`，新增 `query_initialization_probe.py`、`tests/test_query_initialization_probe.py`。原query/scene/lease/geometry/控制器/阈值/run.sh不动。主代理拥有docs/notes、full与GPU；实现者四文件TDD/scoped commit。输出目录使用/data新唯一目录，不覆写旧run。

全量验证增补：3bcb734后fresh full出现4个test_scale_modes失败，根因其SDK边界替身make_diagnostics仍为旧三参数签名，拒绝新增recorder_events=None；其余1661项通过。允许仅扩展tests/test_scale_modes.py这一文件适配optional参数并断言非probe为None，保留原断言与生产调用，不改控制或验收门槛。该修复需独立RED→GREEN和full重验。

SPEC修正增补：最终poll/diagnostics里的BaseException也必须锁存并继续close、after、failed report，不能从finally提前逃逸。本计划下方Exception示例应按6ed4b42实现的BaseException边界保护理解，CleanupError专属重试规则不变。主代理与SPEC均真实USD/lease复现旧P1并关闭复现owner；新增20项中断测试RED→GREEN。fresh main full在query-init-repair-full为1685passed/168.71s/exit0/0skip；SPEC192focused/19.70s PASS，QUALITY待完成。

最终代码门槛：QUALITY P2“清理前提前发布成功、后续写盘失败残留假成功”由92278b7修复，首次磁盘副本强制failed，内存候选在callback清理/绝对零事件验证后才发布。RED3fail→focused194；QUALITY独立194/22.18s PASS并重放两类持续后置写失败。主代理最终full **1687passed/169.98s/exit0/0skip**，basetemp=query-init-publication-full。五文件代码/测试均已提交，只有本计划文档收尾。真实query门槛未完成：根盘available约531400KiB低于1GiB，用户仅pip缓存迁移授权待返，未启动Kit/GPU/新训练。

## Task 1：opt-in入口与真实recorder观察

- [x] RED：新flag能parse但仅8×32允许、默认false；从runner AST验证调用位于validate_scene之后与RuntimeSink之前且受flag保护。probe未导入时不启动Kit。实际RecorderBridge逻辑不变，新增计数必须在四种recorder dispatch一开始增加，不能调用执行接口来假造事件。

```python
def test_probe_flag_defaults_off_and_rejects_other_budget():
    import runtime
    import pytest
    base = ['--num-envs','8','--steps','32','--output','unused']
    assert getattr(runtime.parse_args(base), 'collision_query_probe', None) is False
    assert runtime.parse_args(base + ['--collision-query-probe']).collision_query_probe is True
    for envs, steps in [('8','1600'), ('1024','32'), ('1024','1600')]:
        with pytest.raises(SystemExit):
            runtime.parse_args(['--num-envs',envs,'--steps',steps,'--output','unused','--collision-query-probe'])
```

- [x] GREEN，仅添加以下入口；保留其余CLI含kit_args原值。`run.main`里初始化一个仅probe模式非None的`recorder_events`字典并传入make_diagnostic_cfgs；release_runtime_owners清该局部引用。

```python
# runtime.parse_args, before parse_args:
parser.add_argument('--collision-query-probe', action='store_true')
# after parsing:
if args.collision_query_probe and (args.num_envs != 8 or args.steps != 32):
    parser.error('collision query probe requires --num-envs 8 --steps 32')

# runtime, constant:
RECORDER_EVENT_NAMES = ('pre_step', 'post_step', 'pre_reset', 'post_reset')

# run.main, after parse and alongside owner locals:
recorder_events = {name: 0 for name in RECORDER_EVENT_NAMES} if args.collision_query_probe else None
# existing make_diagnostic_cfgs call adds recorder_events=recorder_events.
# after validate_scene (and any scale report), before RuntimeSink:
if args.collision_query_probe:
    from query_initialization_probe import probe
    probe(env.unwrapped, output, counters, recorder_events)
```

make_diagnostic_cfgs只改签名，不重写原函数其余内容：

```diff
-def make_diagnostic_cfgs(filter_expressions, sink_holder, decimation=4):
+def make_diagnostic_cfgs(filter_expressions, sink_holder, decimation=4, recorder_events=None):
```

四个method新增实际行如下：

```python
def record_pre_step(self):
    if recorder_events is not None: recorder_events['pre_step'] += 1
    return bridge.pre_step(self._env)
def record_post_step(self):
    if recorder_events is not None: recorder_events['post_step'] += 1
    return bridge.post_step(self._env)
def record_pre_reset(self, env_ids):
    if recorder_events is not None: recorder_events['pre_reset'] += 1
    return None, None
def record_post_reset(self, env_ids):
    if recorder_events is not None: recorder_events['post_reset'] += 1
    return bridge.post_reset(env_ids)
```

## Task 2：同步probe协议、原始状态证据和错误清理

- [x] 先RED新模块missing assert，再用真实USD/CollisionSceneLease fixture和实际CollisionQueryBatch测试下面协议。可复用test_collision_lease的真实USD scene/settings/nativequery response fixtures，但不fake lease或querycollector。

对外helper：`execute_query_probe(lease_factory, query_prim, query_mode, capture, write_state, write_report)`。capture返回非空str→numeric ndarray字典，立即完整clone；拒绝object/复数/非有限/空dict，比较key/dtype/shape及原始bytes完全相同（不使用宽容差或仅np.allclose）。write_state(label, arrays)持久化before/after原始NPZ；write_report(report)保存detached JSON。

固定流程：before capture/持久化→factory构造lease→保存source snapshot→submit一次→要求返回COMPLETE→finalize→finally先保存latched query诊断/close，再capture/保存after→严格比较→写最终report→若任一error则raise RuntimeError。PENDING错误清晰写“pending; no pump attempted”；任何错误不能调用app.update/sim.step/reset/pause。不可fallback sourcebbox或当作PASS返回。before自身失败也须尽力写failed report，但无需无意义factory/after。

清理合同：构造抛CollisionLeaseCleanupError时取error.cleanup_owner；该owner的构造cleanup已尝试一次，finally允许再close一次。正常构造后close首次抛CleanupError时允许仅一次额外close重试，仍把初次cleanup error作为诊断失败保留；持续失败明确pending和错误，不无限重试。不得保存异常对象/traceback/native view在report；例外对象只在处理期间存在，finally后清owner/异常引用。最终report不能删除失败history以让重试变PASS。write_state/report异常亦不得跳过owner清理或返回成功。

report schema=`m1_collision_query_initialization_v1`，`representation_status='initialization_diagnostic_only'`；字段至少result=`complete_unchanged`/`failed`、errors(字符串列表)、query_state、source_snapshot、artifact(仅真实lease.finalize成功时)、query_diagnostics_before_close、cleanup_diagnostics、before/after数组shape/dtype/sha256、changed_fields、pump_count=0。不能含geometry_verified/CLEAR/pass/G1声明。

实现骨架（每个分支须在测试中落到上述实行为）：

```python
def copy_state(value):
    if not isinstance(value, dict) or not value or any(not isinstance(k,str) for k in value):
        raise ValueError('state must be nonempty named arrays')
    result = {}
    for key, item in value.items():
        array = np.array(item, copy=True)
        if array.dtype.kind not in 'biuf' or not np.all(np.isfinite(array)):
            raise ValueError('invalid state array: ' + key)
        result[key] = array
    return result

def state_metadata(state):
    return {key: {'dtype': array.dtype.str, 'shape': list(array.shape),
                  'sha256': hashlib.sha256(array.tobytes(order='C')).hexdigest()}
            for key, array in state.items()}

def changed_fields(before, after):
    return sorted(key for key in before.keys() | after.keys()
        if key not in before or key not in after
        or before[key].dtype != after[key].dtype
        or before[key].shape != after[key].shape
        or before[key].tobytes(order='C') != after[key].tobytes(order='C'))

def execute_query_probe(lease_factory, query_prim, query_mode, capture, write_state, write_report):
    report = {'schema':'m1_collision_query_initialization_v1',
              'representation_status':'initialization_diagnostic_only',
              'result':'failed', 'errors':[], 'query_state':None,
              'source_snapshot':None, 'artifact':None,
              'query_diagnostics_before_close':None, 'cleanup_diagnostics':None,
              'before':None, 'after':None, 'changed_fields':[], 'pump_count':0}
    owner, before = None, None
    before_written, cleanup_limit = False, 2
    def note(label, error):
        report['errors'].append(label + ': ' + type(error).__name__ + ': ' + str(error))
    try:
        before = copy_state(capture())
        report['before'] = state_metadata(before)
        write_state('before', copy_state(before))
        before_written = True
        owner = lease_factory()
        report['source_snapshot'] = owner.snapshot()
        report['query_state'] = owner.submit(query_prim, query_mode)
        if report['query_state'] != 'COMPLETE':
            reason = 'pending; no pump attempted' if report['query_state'] == 'PENDING' else 'query not complete'
            raise RuntimeError(reason)
        report['artifact'] = owner.finalize()
    except Exception as error:
        if isinstance(error, CollisionLeaseCleanupError):
            owner, cleanup_limit = error.cleanup_owner, 1
        note('query initialization', error)
    finally:
        if owner is not None:
            if report['artifact'] is not None:
                try:
                    if owner.poll() != 'COMPLETE':
                        report['errors'].append('source/query invalidated after finalize')
                except Exception as error:
                    note('final source guard', error)
            try:
                report['query_diagnostics_before_close'] = owner.diagnostics()
            except Exception as error:
                note('diagnostics before close', error)
            for attempt in range(cleanup_limit):
                try:
                    owner.close()
                    break
                except CollisionLeaseCleanupError as error:
                    note('cleanup', error)
                    owner = error.cleanup_owner
                except Exception as error:
                    note('cleanup', error)
                    break
            try:
                report['cleanup_diagnostics'] = owner.diagnostics()
                if report['cleanup_diagnostics']['pending_unsubscriptions']:
                    report['errors'].append('cleanup still has pending subscriptions')
            except Exception as error:
                note('cleanup diagnostics', error)
            owner = None
        if before_written:
            try:
                after = copy_state(capture())
                report['after'] = state_metadata(after)
                write_state('after', copy_state(after))
                report['changed_fields'] = changed_fields(before, after)
                if report['changed_fields']:
                    report['errors'].append('initialization changed state: ' + ','.join(report['changed_fields']))
            except Exception as error:
                note('after state', error)
    if not report['errors']:
        report['result'] = 'complete_unchanged'
    write_report(copy.deepcopy(report))
    if report['errors']:
        raise RuntimeError('collision query initialization failed: ' + '; '.join(report['errors']))
    return copy.deepcopy(report)
```

- [x] tests明确覆盖：complete unchanged保存原始array且source/query只读；PENDING/FAILED/missing/duplicate/timeout/SDK异常均failed且scope关闭；构造失败含cleanup_owner；close一次失败重试成功仍failed/两次失败无第三次；write before失败不创建lease、write after/report失败清理已完成；after采样异常；capture与SDK导致任一time/index/pose/vel/joint/episode/RNG/counters变化皆拒绝；dtype/shape/keys/-0bit变化；返回artifact/diagnostics与保存states互不alias；import不加载Kit/torch/omni/carb。

## Task 3：实际scene/native/RNG绑定

- [x] 实现`capture_live_state(env, counters, physics_events, recorder_events, expected_stage, cache)`，SDK依赖只在调用时import。每次确认omni.usd当前stage与expected_stage、env.scene.stage均相等；cache.Contains/GetId/Find只读校验，与env.scene.stage_id一致，不调用会Insert的sim_utils.get_current_stage_id。状态读取如下，不读取robot.data公共state缓存作为物理见证。

```python
robot = env.scene['robot']
view = robot.root_physx_view
sensor = env.scene['diagnostic_bar_contacts']
# Every native getter is immediately copied by snapshot_array with its exact shape.
raw = {
 'root_link_pose_xyzw': (view.get_root_transforms, (8,7)),
 'body_link_pose_xyzw': (view.get_link_transforms, (8,17,7)),
 'root_com_velocity': (view.get_root_velocities, (8,6)),
 'body_com_velocity': (view.get_link_velocities, (8,17,6)),
 'joint_pos': (view.get_dof_positions, (8,16)),
 'joint_vel': (view.get_dof_velocities, (8,16)),
}
state = {name: snapshot_array(getter(), name, shape) for name,(getter,shape) in raw.items()}
state.update({
 'episode_length': snapshot_array(env.episode_length_buf, 'episode_length', (8,)),
 'sim_time': np.array([env.sim.current_time], dtype=np.float64),
 'sim_step_index': np.array([env.sim.current_time_step_index], dtype=np.int64),
 'env_step_counts': np.array([env._sim_step_counter, env.common_step_counter], dtype=np.int64),
 'stage_ids': np.array([cache.GetId(expected_stage).ToLongInt(), env.scene.stage_id], dtype=np.int64),
 'prepare_ik_counts': np.array([counters['prepare_calls'], counters['ik_calls']], dtype=np.int64),
 'recorder_counts': np.array([recorder_events[name] for name in RECORDER_EVENT_NAMES], dtype=np.int64),
 'physics_event_count': np.array([physics_events['count']], dtype=np.int64),
 'physics_dt_sum': np.array([physics_events['dt_sum']], dtype=np.float64),
 'sensor_update_count': np.array([sensor.physical_update_count], dtype=np.int64),
 'sensor_armed': np.array([sensor.accumulator.armed], dtype=np.bool_),
 'articulation_data_timestamp': np.array([robot.data._sim_timestamp], dtype=np.float64),
})
if not torch.cuda.is_initialized():
    raise RuntimeError('CUDA must already be initialized')
encode = lambda value: np.frombuffer(json.dumps(value, allow_nan=False, separators=(',',':')).encode(), dtype=np.uint8).copy()
numpy_state = np.random.get_state()
state['rng_python'] = encode(random.getstate())
state['rng_numpy_keys'] = np.array(numpy_state[1], copy=True)
state['rng_numpy_meta'] = encode([numpy_state[0], int(numpy_state[2]), int(numpy_state[3]), float(numpy_state[4])])
state['rng_torch_cpu'] = snapshot_array(torch.get_rng_state(), 'torch_cpu_rng')
state['rng_torch_cuda7'] = snapshot_array(torch.cuda.get_rng_state(7), 'torch_cuda7_rng')
return copy_state(state)
```

严格校验n=8、17个unique body_names集合=runtime.CONTACT_BODY_NAMES、16joints和实际root view prim_paths按env0..7对应Robot根（已知/可验证的完整路径，不猜测）。lease roots用明确`/World/envs/env_i/Robot`，body_names用实际robot.body_names顺序并在report附该顺序。generation=0，timeout_ms=10000。记录LINK pose xyzw与COM velocity语义，不能误称LINK velocity。只监测默认Python/NumPy/Torch CPU/CUDA7 generators，不称所有自定义generator。

probe实际绑定（使用前述capture_live_state/execute_query_probe，并把辅助import置于需要时）：

```python
def probe(env, output, counters, recorder_events):
    from omni.physx import get_physx_property_query_interface
    from omni.physx.bindings._physx import PhysxPropertyQueryMode
    from pxr import UsdUtils, UsdPhysics
    import carb.settings, omni.usd
    from collision_lease import CollisionSceneLease
    from runtime import CONTACT_BODY_NAMES, write_json
    output = Path(output)
    if env.num_envs != 8:
        raise ValueError('query diagnostic is 8-env only')
    robot = env.scene['robot']
    names = list(robot.body_names)
    roots = [f'/World/envs/env_{i}/Robot' for i in range(8)]
    stage = omni.usd.get_context().get_stage()
    cache = UsdUtils.StageCache.Get()
    if len(names) != 17 or len(set(names)) != 17 or set(names) != set(CONTACT_BODY_NAMES):
        raise ValueError('actual body names mismatch')
    if len(robot.joint_names) != 16 or len(set(robot.joint_names)) != 16:
        raise ValueError('actual joint names mismatch')
    articulation_paths = list(robot.root_physx_view.prim_paths)
    if len(articulation_paths) != 8 or len(set(articulation_paths)) != 8:
        raise ValueError('actual articulation path count mismatch')
    for root, path in zip(roots, articulation_paths):
        if not (path == root or path.startswith(root + '/')):
            raise ValueError('actual articulation environment order mismatch')
        if not stage.GetPrimAtPath(path).HasAPI(UsdPhysics.ArticulationRootAPI):
            raise ValueError('actual articulation root is not declared')
    physics_events = {'count':0, 'dt_sum':0.0}
    report = None
    def write_report(value):
        nonlocal report
        report = copy.deepcopy(value)
        report['body_names'] = names
        report['articulation_paths'] = articulation_paths
        report['physics_callback_removed'] = False
        write_json(output / 'collision_query_initialization.json', report)
    def write_state(label, arrays):
        path = output / ('collision_query_guard_' + label + '.npz')
        if path.exists():
            raise ValueError('refusing to overwrite probe evidence')
        np.savez_compressed(path, **arrays)
    def on_step(dt):
        physics_events['count'] += 1
        physics_events['dt_sum'] += float(dt)
    name = 'm1_collision_query_probe_' + str(id(physics_events))
    if env.sim.physics_callback_exists(name):
        raise RuntimeError('probe callback already exists')
    cleanup_error = None
    try:
        env.sim.add_physics_callback(name, on_step)
        if not env.sim.physics_callback_exists(name):
            raise RuntimeError('probe callback registration failed')
        execute_query_probe(
            lambda: CollisionSceneLease(stage, roots, names, carb.settings.get_settings(),
                geometry_generation=0, stage_cache=cache, timeout_ms=10000),
            get_physx_property_query_interface().query_prim,
            PhysxPropertyQueryMode.QUERY_RIGID_BODY_WITH_COLLIDERS,
            lambda: capture_live_state(env, counters, physics_events, recorder_events, stage, cache),
            write_state, write_report)
    except BaseException as error:
        if report is None:
            report = {'schema':'m1_collision_query_initialization_v1',
                      'representation_status':'initialization_diagnostic_only',
                      'result':'failed', 'errors':[], 'pump_count':0}
        report['result'] = 'failed'
        report['errors'].append('probe: ' + type(error).__name__ + ': ' + str(error))
        raise
    finally:
        try:
            if env.sim.physics_callback_exists(name):
                env.sim.remove_physics_callback(name)
            if env.sim.physics_callback_exists(name):
                raise RuntimeError('probe callback not removed')
        except Exception as error:
            cleanup_error = type(error).__name__ + ': ' + str(error)
        if report is None:
            report = {'schema':'m1_collision_query_initialization_v1',
                      'representation_status':'initialization_diagnostic_only',
                      'result':'failed', 'errors':['probe failed before query report'], 'pump_count':0}
        report['physics_callback_removed'] = cleanup_error is None
        report['physics_event_count'] = physics_events['count']
        report['physics_dt_sum'] = physics_events['dt_sum']
        if physics_events['count'] != 0:
            report['result'] = 'failed'
            report['errors'].append('physics event occurred during initialization')
        if cleanup_error is not None:
            report['result'] = 'failed'
            report['errors'].append('physics callback cleanup: ' + cleanup_error)
        write_json(output / 'collision_query_initialization.json', report)
        print('M1_COLLISION_QUERY_INIT_' + ('COMPLETE' if report['result'] == 'complete_unchanged' else 'FAILED'),
              json.dumps({'result':report['result'], 'errors':report['errors']}, allow_nan=False), flush=True)
        if cleanup_error is not None:
            raise RuntimeError(cleanup_error)
        if report['result'] != 'complete_unchanged':
            raise RuntimeError('collision query probe failed: ' + '; '.join(report['errors']))
```

factory/getters须接到前面明确API；不允许假query。需在report最后记录callback移除状态与零physics事件；若删除失败或出现事件，即使query成功也必须把report改成failed并抛错。不要clear_all_callbacks。临时receiver不持env/view；SDKquery callable/lease/闭包在返回前清除，原runner正常owner-release仍执行。stage/name等尚未注册callback前的预检查失败，由既有run.py candidate_report/traceback记录（此时没有query初始化成功报告）；不可因缺probe报告推断通过。写入report失败不能随后被finally改成complete。

- [x] CPU tests对外部native getters用可复用storage替身确认每次立即clone，不允许前后共享内存导致假相等；实际USD cache只读；实际default Python/NumPy/Torch CPU RNG不因capture改变，CUDA7 getter边界替身且拒绝未初始化，不调用get_rng_state_all。实际physics callbacks需GPU现场证明；CPU external simulation-context替身验证只删自己名字且所有异常路径都有删除、删除失败报告failed。recorder四methods分别真实dispatch行为测试计数/None模式不变。

## Task 4：验证与唯一现场尝试

- [x] 实现者focused/scoped commit；主代理独立full、SPEC→QUALITY，无未修缺口再启动。初full=query-init-implementation-full，修复后最终full=query-init-publication-full（1687/169.98s/0skip）。未启probe的旧controller路径保持原行为，旧source/SDK/driver不改。
- [x] 资源fresh检查：管理员实际扩容500GiB后root944G/约498G可用，/data约6.4T。GPU7独立核验仅原placeholder351307/15744MiB、free8328MiB，无训练并发。占位全程保留，输出/data新唯一目录，TMPDIR为/data私有temp，core dump disabled；未装包/删缓存。
- [x] 同一隔离run.sh仅启动一次 `--num-envs 8 --steps 32 --collision-query-probe`：query-init-live-20260919-1618，PID3669456，exec session33380持续跟至terminal0；native/wrapper0与POST_CLEANUP对应，无重启。source/artifact及原始before/after证据完整。
- [x] 主代理独立验证＋独立现场审查PASS：136queries/408callbacks、23组raw bytes/metadata SHA完全同、零额外physics、callbackremoved/leaseclosed、完整8×32/128substeps/32prepare/IK/0reset，native/wrapper0。本初始化门槛通过，不是geometry/G1/G2/PPO10000。todo/T306/logindex与本轮现场日志对齐，不重复静态基础审计。
- [ ] 继续实际bounds/cooked cross-check及provider/registry/coordinator：已有实际query离线坐标诊断，不以source bbox回退或该中间门槛替代完整目标。

现场补充：code/baseline=b16168b，module/test SHA与上轮已审查版本一致；管理员扩容解除此前约0.5GiB资源阻碍，不再等待pip迁移。全部104mesh的query box不同于authored diagnostic bounds（max6.334mm）；32Y-axis native cylinder查询盒与声明尺寸差8.31e-9m，若错误追加query.local_rot会造成72.65mm轴错位。全部八角点/逐body native pose矩阵与直接quat复算差3.55e-15m；未取得live cooked vertices，不声明geometry_verified/CLEAR。详见[现场日志](../../../notes/log/2026-09-19-m1-collision-query-live.md)。

## 自审与技能边界

- [x] 本计划是已批准query公开契约的现场实现，无控制/奖励/阈值新设计；不重开审批。
- [x] 同步尝试是诊断步骤，实际PENDING后仍必须完成可行的无额外步数初始化；不重定义完整目标。
- [x] raw getters＋独立physics事件弥补lazy缓存/未armed传感器假相等，记录器只是计数不触发动作。
- [x] 所有输出是诊断证据，成功不直接授权CLEAR；旧参考prefix保持，原生正常退出仍由外部finalizer判定。
