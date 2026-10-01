# M1 Collision Scene Lease Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已验证scene snapshot/native path scope/query collector接成订阅先于采集、source/settings改变即不可逆失效、清理顺序明确的单批查询lease。

**Architecture:** 一个小的lifecycle owner持有实际USD通知、Carb settings节点订阅、CollisionPathScope及至多一个CollisionQueryBatch。所有对外API由调用方串行调用；异步settings/query callbacks仅复制字段/锁存失效，外部SDK callable/退订不在应用锁内执行。输出`query_source_bound`仍不代表几何包络、CLEAR或G1通过，下一步8-env现场诊断必须证明query及等待不推进physics。

**Tech Stack:** amp Python3.10，真实pxr Tf/Usd/UsdUtils，既有scene/query模块；仅settings和SDK callable是外部接口，不import carb/omni/torch/Kit，不写USD/settings/cache，不pump/step。

---

## 范围、输入与已完成依据

用户已批准encounter完整规格。上一轮progress：代码c608945、docs fa66e65，main1452full/0skip、真实8内存实例136collider正式scope两次通过、SPEC→QUALITY。fresh fa66e65 clean，已在codex/m1-encounter-lifecycle linked worktree，不另建/重装。不再审计已确定的codec生命周期或静态inventory。

仅新增：`tools/m1_reference_validation/collision_lease.py`、`tests/test_collision_lease.py`。本地：`C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter/`；远程：`/data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation/`。主代理负责文档、full、实际资产与双审；实现者只两文件TDD/scoped commit。原run/runtime/参考/SDK/driver/GPU7占位不动。

实际接口：Tf.Notice.Register(Usd.Notice.ObjectsChanged, callback, stage)，callback(notice,sender)，handle.Revoke；settings.get(path)、subscribe_to_node_change_events(path,cb)，cb(item,event)，unsubscribe_to_change_events(handle)。Item不得保留。leaf不覆盖ancestor replacement，故六个leaf及所有ancestor（含`/`）均精确节点订阅；不使用未知get_item_type或typed转换getter。外部template/prototype的ObjectsChanged不能按robot root过滤。

## Task B2b2b：source-bound lease

- [x] 先RED：函数内assert模块存在，真实USD stage/cache fixture，settings仅模拟真实已知接口；不mock USD notice、scene collector、query collector或path codec。

```python
def test_lease_requires_actual_registered_stage():
    import importlib.util
    from pxr import Usd
    import pytest
    assert importlib.util.find_spec('collision_lease') is not None
    from collision_lease import CollisionSceneLease
    class Settings:
        def __init__(self): self.callbacks = {}
        def get(self, path): return None
        def subscribe_to_node_change_events(self, path, callback):
            token = len(self.callbacks) + 1
            self.callbacks[token] = (path, callback)
            return token
        def unsubscribe_to_change_events(self, token): self.callbacks.pop(token)
    settings = Settings()
    with pytest.raises(ValueError):
        CollisionSceneLease(Usd.Stage.CreateInMemory(), ['/Robot'], ['B'], settings,
                            geometry_generation=0, stage_cache=Usd.StageCache())
    assert settings.callbacks == {}
```

- [x] 最小实现，再以如下完整合同扩展RED→GREEN。此prototype固定API/状态/失效与锁顺序，可为测试清晰度整理helper但不删拒绝条件。

```python
import copy
import threading
import time
import weakref
from pxr import Tf, Usd, UsdGeom, UsdUtils
from collision_scene import CollisionPathScope, SETTING_PATHS, collect_collision_scene_snapshot, _scalar, _sha
from collision_query import CollisionQueryBatch
from encounter_geometry import _integer


def _watch_paths():
    paths = {'/'}
    for path in SETTING_PATHS:
        parts = path.strip('/').split('/')
        paths.update('/' + '/'.join(parts[:i]) for i in range(1, len(parts) + 1))
    return tuple(sorted(paths))


WATCH_PATHS = _watch_paths()


class CollisionLeaseCleanupError(RuntimeError):
    """Cleanup could not finish; retry cleanup_owner.close() explicitly."""
    def __init__(self, cleanup_owner, errors):
        self.cleanup_owner = cleanup_owner
        super().__init__('collision scene lease cleanup failed; retry error.cleanup_owner.close(): '
                         + '; '.join(errors))


def _usd_callback(reference):
    def receive(notice, sender):
        lease = reference()
        if lease is not None:
            lease._on_usd(notice)
    return receive


def _setting_callback(reference, path):
    def receive(item, event):
        lease = reference()
        if lease is not None:
            lease._fail('settings_notice', path=path)
    return receive


class CollisionSceneLease:
    def __init__(self, stage, robot_roots, body_names, settings, *, geometry_generation,
                 stage_cache=None, timeout_ms=10000, clock=time.monotonic):
        self._generation = _integer(geometry_generation, 'geometry_generation')
        self._timeout = _integer(timeout_ms, 'timeout_ms', 1)
        if self._timeout > 60000 or not callable(clock):
            raise ValueError('invalid timeout_ms or clock')
        if not isinstance(stage, Usd.Stage):
            raise ValueError('stage must be a Usd.Stage')
        for name in ('get', 'subscribe_to_node_change_events', 'unsubscribe_to_change_events'):
            if not callable(getattr(settings, name, None)):
                raise ValueError('settings must supply ' + name)
        self._lock = threading.RLock()
        self._state, self._failure = 'CAPTURING', None
        self._stage, self._settings, self._clock = stage, settings, clock
        self._cache = UsdUtils.StageCache.Get() if stage_cache is None else stage_cache
        self._scope = CollisionPathScope(stage)
        self._listener, self._subscriptions = None, []
        self._usd_receiver = None
        self._snapshot, self._batch = None, None
        self._closed_query_diagnostics = None
        self._motion_paths = frozenset()
        self._submitted = False
        self._cleanup_errors = []
        reference = weakref.ref(self)
        try:
            self._usd_receiver = _usd_callback(reference)
            self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._usd_receiver, stage)
            for path in WATCH_PATHS:
                token = settings.subscribe_to_node_change_events(path, _setting_callback(reference, path))
                if token is None:
                    raise ValueError('settings subscription returned no handle')
                self._subscriptions.append(token)
            snapshot = collect_collision_scene_snapshot(stage, robot_roots, body_names, settings,
                         stage_cache=self._cache, path_scope=self._scope)
            with self._lock:
                if self._state == 'FAILED':
                    raise ValueError('source changed during capture')
                self._snapshot = snapshot
                self._motion_paths = frozenset(
                    request['body_path'] + '.' + name
                    for request in snapshot['requests']
                    for name in ('xformOp:translate', 'xformOp:orient'))
                self._state = 'READY'
        except BaseException:
            self.close()
            raise

    def _fail(self, reason, **details):
        with self._lock:
            if self._state in ('CLOSED', 'FAILED'):
                return
            self._failure = {'reason': reason, **details}
            self._state = 'FAILED'
            batch = self._batch
        if batch is not None:
            batch.close()

    def _on_usd(self, notice):
        with self._lock:
            if self._state in ('CLOSED', 'FAILED'):
                return
            capturing, motion_paths = self._state == 'CAPTURING', self._motion_paths
        try:
            resynced = notice.GetResyncedPaths()
            if resynced:
                self._fail('usd_resync', path=str(resynced[0]), count=len(resynced))
                return
            for path in notice.GetChangedInfoOnlyPaths():
                fields = sorted(str(field) for field in notice.GetChangedFields(path))
                if capturing or str(path) not in motion_paths or fields != ['default']:
                    self._fail('usd_change', path=str(path), fields=fields)
                    return
        except Exception as error:
            self._fail('usd_notice_error', error_type=type(error).__name__, message=str(error))

    def _refresh(self):
        with self._lock:
            if self._state in ('CLOSED', 'FAILED'):
                return
        try:
            stage_id = self._snapshot['source']['stage_id']
            if (not self._cache.Contains(self._stage)
                    or self._cache.GetId(self._stage).ToLongInt() != stage_id
                    or self._cache.Find(self._cache.GetId(self._stage)) != self._stage):
                raise ValueError('stage cache identity changed')
            if (self._stage.GetRootLayer().identifier != self._snapshot['source']['stage_root_layer']
                    or UsdGeom.GetStageMetersPerUnit(self._stage) != 1.
                    or str(UsdGeom.GetStageUpAxis(self._stage)) != 'Z'):
                raise ValueError('stage metadata changed')
            current = {path: _scalar(self._settings.get(path)) for path in SETTING_PATHS}
            if _sha(current) != self._snapshot['settings_fingerprint']:
                raise ValueError('settings fingerprint changed')
        except Exception as error:
            self._fail('source_refresh_error', error_type=type(error).__name__, message=str(error))

    def poll(self):
        self._refresh()
        with self._lock:
            state, batch = self._state, self._batch
        if state in ('FAILED', 'CLOSED') or batch is None:
            return state
        query_state = batch.poll()
        if query_state in ('FAILED', 'CLOSED'):
            self._fail('query_failed')
        with self._lock:
            return self._state if self._state in ('FAILED', 'CLOSED') else query_state

    def snapshot(self):
        if self.poll() in ('FAILED', 'CLOSED'):
            raise ValueError('collision scene lease is not valid')
        with self._lock:
            if self._state in ('FAILED', 'CLOSED'):
                raise ValueError('collision scene lease changed')
            return copy.deepcopy(self._snapshot)

    def submit(self, query_prim, query_mode):
        if self.poll() != 'READY' or self._submitted:
            raise ValueError('query may be submitted exactly once on a ready lease')
        self._submitted = True
        try:
            batch = CollisionQueryBatch(self._snapshot['source']['stage_id'], self._snapshot['requests'],
                      geometry_generation=self._generation,
                      settings_fingerprint=self._snapshot['settings_fingerprint'],
                      timeout_ms=self._timeout, clock=self._clock)
            with self._lock:
                self._batch = batch
                if self._state == 'FAILED':
                    batch.close()
                    raise ValueError('source changed before query submission')
                self._state = 'PENDING'
            batch.submit(query_prim, query_mode)
        except Exception as error:
            self._fail('query_submission_error', error_type=type(error).__name__, message=str(error))
            raise
        return self.poll()

    def finalize(self):
        if self.poll() != 'COMPLETE':
            raise ValueError('source-bound query is not complete and valid')
        try:
            query = self._batch.finalize(geometry_generation=self._generation,
                                        settings_fingerprint=self._snapshot['settings_fingerprint'])
        except Exception as error:
            self._fail('query_finalization_error', error_type=type(error).__name__, message=str(error))
            raise
        if self.poll() != 'COMPLETE':
            raise ValueError('source changed while finalizing query')
        with self._lock:
            if self._state in ('FAILED', 'CLOSED'):
                raise ValueError('source changed while finalizing query')
            return {'schema': 'm1_collision_query_lease_v1', 'representation_status': 'query_source_bound',
                    'geometry_generation': self._generation, 'scene': copy.deepcopy(self._snapshot), 'query': query}

    def diagnostics(self):
        with self._lock:
            return {'state': self._state, 'failure': copy.deepcopy(self._failure),
                    'cleanup_errors': list(self._cleanup_errors),
                    'pending_unsubscriptions': len(self._subscriptions) + int(self._listener is not None),
                    'query': copy.deepcopy(self._closed_query_diagnostics) if self._batch is None else self._batch.diagnostics()}

    def close(self):
        with self._lock:
            self._state = 'CLOSED'
            batch, listener = self._batch, self._listener
            subscriptions, settings = list(self._subscriptions), self._settings
        if batch is not None:
            batch.close()
            with self._lock:
                self._closed_query_diagnostics = batch.diagnostics()
                self._batch = None
        errors, pending = [], []
        if listener is not None:
            try:
                listener.Revoke()
                self._listener = None
                self._usd_receiver = None
            except Exception as error:
                errors.append('USD unsubscribe: ' + type(error).__name__ + ': ' + str(error))
        for token in subscriptions:
            try:
                settings.unsubscribe_to_change_events(token)
            except Exception as error:
                pending.append(token)
                errors.append('settings unsubscribe: ' + type(error).__name__ + ': ' + str(error))
        with self._lock:
            self._subscriptions = pending
            self._cleanup_errors.extend(errors)
            self._scope.close()
            self._stage = self._cache = self._clock = None
            self._motion_paths = frozenset()
            if not pending:
                self._settings = None
        if errors:
            raise CollisionLeaseCleanupError(self, errors)

    def __enter__(self):
        if self.poll() in ('FAILED', 'CLOSED'):
            raise ValueError('collision scene lease is not valid')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
```

状态细节：query COMPLETE由batch.poll返回，内部状态保留PENDING表示已提交；diagnostics是latched观察，不刷新clock/settings，不把未poll过的状态冒称当前。失败首因锁存后不可恢复，即使值改回原样；close不清failure/history，重复close只重试失败退订，其余handle不重复操作。constructor失败必须撤已有所有handle，即使一个退订失败也尝试其余并保留错误。调用方串行调用API与close，callbacks可跨线程；不宣称USD多线程写安全。native callback无stage读取、SDK query/pump或Item持有。

close后不能仅清lease._clock却保留batch._clock：关闭batch后保存普通JSON diagnostics并放开batch引用；SDK closures只weakref batch，关闭或回收后均不能复活。源码既有query模块不改。清理失败的subscription owner只保留供retry，除此不保活旧runtime对象。

真实USD RED补充：`Tf.Notice.Register`不保活临时Python closure；21项通知测试实际出现`Tried to call an expired python callback`。lease必须显式持有USD receiver，receiver内部仍仅weakref lease。成功Revoke后释放receiver；Revoke失败时与listener一起保留供重试，不靠全局引用或SDK补丁修复。

finalize RED补充：batch.finalize内clock错误使内部batch失败时，外层diagnostics原先仍PENDING；必须立即锁存query_finalization_error并保留内部query证据，不等待下次poll修正状态。真实stage生命周期测试区分Boost无效wrapper与native存活：只对stage接受None或bool(stage)==False，独立无lease私有cache对照已证实该包装器行为；其余Python对象仍要求weakref为None。

SPEC P2补充：正常公开构造失败且close又遇退订错误时，不能只把残项放在未返回的self上。清理错误公开为`CollisionLeaseCleanupError(RuntimeError)`，强持有`cleanup_owner`，保留原始构造异常链；调用方可从异常取owner并显式close重试残项，之后放开异常/owner。测试必须使用正常构造器而非仅`__new__`预留owner，不增加全局引用或无限重试。已有close/context的RuntimeError兼容性与清理顺序不变；实际runtime接入也须处理此错误载荷。

## 扩展测试（每组先看到正确RED）

- [x] 真实注册stage/Cylinder/T-O-S，正常READY→submit→PENDING→COMPLETE→finalize→close；fake SDK完整rigid/collider/finished字段沿现有query合同，缺/重/迟到/错误/timeout依旧失败；exact once submit，closed禁止snapshot/finalize/submit；query_source_bound没有geometry_verified/CLEAR/passed。使用真实collector，不仅验证fake被调用。
- [x] 实际Usd.Notice：已绑定body translate/orient仅default变更继续有效；timeSamples/order/scale/metadata/default之外字段、新属性resync、祖先矩阵、collider参数、外部template points/prototype/reference替换、stage meter/upAxis都不可逆FAILED。同一notice夹正常motion+非法变更仍失败。未知stage路径变化保守失效，不按robot-root过滤；当前包不豁免cooked输出，首次实际query若写cache应记录失效，下一现场诊断决定是否需要独立预热后全新capture，不能暗中放行。
- [x] settings六leaf＋全部ancestor精确订阅，missing→creation、set/delete/ancestor replace、bool→int（值同1）/NaN/unknown值、改变再恢复均失败；未相关的其他leaf且其祖先未直接变更不误发fake回调。通过get触发同步设置通知验证capture期间变动被拒绝且资源清理；无通知但当前值变更时poll fingerprint守卫也捕获。callback不访问/保留item，query/settings外部调用均不在应用锁内（用线程同步事件而非sleep竞态测）。
- [x] 实际cache Erase（fixture自己的stage）/reinsert新ID在poll失效；default cache自有stage fixture只清自己的ID。多env/真实instance proxy manifest与scope延后解码/churn保持可用；不全局pin，不泄漏stage/native引用。watch路径回调经weakref不保活lease；close后的迟到callback无效，不读clock或notice。
- [x] 订阅中途抛错/返回None/采集失败逐一测试已获得handle撤销；unsubscribe一项失败时仍撤其余、query先close、scope最终释放，diag留history/pending，第二次close只重试残项；异常context不吞原异常。跨线程callback和unsubscribe等待不得死锁（子进程timeout30s）。API无并行close支持，测试不伪装成保证。
- [x] 返回snapshot/finalize/diagnostics都是独立JSON副本；caller修改不影响下一次结果。含实际query caller的weakref清理，close释放stage/settings/clock/scope own路径；close失败保留待重试settings owner有明确诊断，不隐瞒。源层文本/dirty/cache/settings值前后不改；import无Kit/omni/carb/torch。

## 验证、提交与后续

- [x] 实现者focused、自审、只两文件scoped提交；主代理独立focused/full/实际asset source+notice probe；SPEC→QUALITY，缺口TDD修复后复审。不用旧1452结果替代新代码验证。
- [x] 更新todo/T306/index与本轮log，并明确本包仍非实际PhysX query或完整G0。下一项为8-env初始化现场诊断，再registry/coordinator/sync/replay/G1/G2/AME/policy/10000，保持原门槛；这些后续工作未在本复选项内宣称完成。不重复向用户申请相同授权。

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp PXR_PLUGINPATH_NAME=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx/plugins/PhysxSchema/resources PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310:/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin:/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extsPhysics/omni.usd.schema.physx/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tests/test_collision_lease.py -q --tb=short -p no:cacheprovider
```

Main full替换测试目标为tests，唯一 `--basetemp=/data/hexinkun-m1-acceptance-20260918/encounter-scene-lease-full`；保留旧fixture。Main首次fresh baseline可只跑已完成scene/query两个focused（432项），完整1452基线已有上一轮明确commit且本轮diffclean。

## 主代理自审

- [x] 是批准规格内geometry generation失效的必需接入，不调控制/奖励/阈值，不要求新范围选择。
- [x] API/输入/输出与新测试名称明确，源USD/真实query协议不mock，外部Carb/SDK callable边界才替身。
- [x] callbacks可异步而API串行；退订不持callback锁，path scope明确先queryclose后释放，无永久全局保活。
- [x] 实際Kit query/pump/GPU物理验收不在CPU结果中冒称通过；source-bound只是后续物理来源验证前置。

## 实施证据（2026-09-19）

- 首版b5307f4：111focused，主代理1563full/153.36s/exit0/0skip；SPEC发现构造失败退订残项没有公开retry owner，故此版未接受。
- 修复8a3746f：正常构造/直接close两个新RED→113focused；公开CollisionLeaseCleanupError携cleanup_owner，原异常链不丢。最终主代理1565full/152.72s/exit0/0skip，新basetemp为encounter-scene-lease-cleanup-full。
- SPEC复审PASS：独立113focused/4.41s及正常构造cleanup retry/GC探针通过；随后独立QUALITY PASS，113focused/4.01s/0skip，无P1/P2/P3问题，完整审查276行source/986行tests及plan。
- 最终代码actual M1八个内存实例136body/136collider＋actual fresh-process Carb，CPU probe PASS/46.494456s/exit0。query使用真实collector但外部SDK callbacks是synthetic，不是实际PhysX或G1。
- 保留首次本地pose opinion触发usd_resync的负例；已有local opinions后normal motion有效。首次实际runtime不得靠放宽resync绕过初始化边界，必须诊断实际source稳定/physics时间与步数。
- 下一步为8-env实际query初始化诊断，再完整registry/coordinator/sync/replay/G1/G2/AME/policy/10000；旧runtime/SDK/driver/主源码/占位未改。记录见notes/log/2026-09-19-m1-collision-scene-lease-implementation.md。
