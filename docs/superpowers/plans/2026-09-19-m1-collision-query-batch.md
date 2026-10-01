# M1 Collision Query Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对实际 SDK query 调用建立一次性、非阻塞、严格身份与完整性校验的回调批次，不以 query 返回或计数齐全冒充真实 finished。

**Architecture:** G0-B2b1 是 SDK 接口参数化的普通 Python collector，可直接消费真实 response、调用真实 query_prim，但本模块不加载 Kit、不访问 USD/设置、不等待或推进仿真。后续现场绑定层提供 actual stage/path 清单、typed settings 指纹和 geometry generation，监测其失效；初始化诊断核实异步 pump、实际 proxy 回调及正常退出。此包的 complete 只指回调协议完成，不是 geometry_verified/CLEAR。

**Tech Stack:** amp Python3.10 / NumPy / threading.RLock / weakref，已有/data隔离worktree；TDD。

---

## 当前证据与文件边界

用户已批准完整encounter规格，不再询问相同范围授权。上轮为progress：A1/B1/B2a新增实现和1020full/0skip、双审查完成，当前HEAD7706b5a（code c12e0af），本轮fresh git clean且linked worktree确认。无运行中的仿真需要重启。

已安装 `_physx.pyi`：query_prim返回None，mode唯一QUERY_RIGID_BODY_WITH_COLLIDERS，无query cancel handle。rigid有stage_id/path_id/result/type/mass/inertia/center_of_mass/principal_axes；collider有stage_id/path_id/result/aabb_local_min/max/local_pos/rot/volume。callback线程未指定，未缓存query可能需Kit update，不能阻塞Event.wait假完成。只保存普通字段，不保存response、prim、env/view或exception/traceback；callback不查询USD/pump。

仅新增：

- `tools/m1_reference_validation/collision_query.py`
- `tools/m1_reference_validation/tests/test_collision_query.py`

本地adapter staging仍`C:/Users/xk/Documents/project/m1_reference_validation_stage/encounter_lifecycle/adapter/`。apply_patch后SCP到`/data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation/`。不改旧run/runtime/reference/SDK/资产/训练；源码只scoped commit这两文件。

## Task B2b1：严格非阻塞回调批次

### Step 1：明确构造和结果合同，写首个RED

- [x] 测试内loader在production缺失时assert FAIL，而非collection error。每个test执行真实collector逻辑，只替代外部query_prim和SDK response对象；fake镜像上列所有字段，不能mock掉collector。
- [x] 构造器`CollisionQueryBatch(stage_id, requests, *, geometry_generation, settings_fingerprint, timeout_ms=10000, clock=time.monotonic)`。stage_id和path_id为1..2**64-1 Integral（拒bool）；generation为非负Integral。fingerprint是小写64hex。timeout_ms为1..60000 Integral。clock可调用，结果有限非负、非递减。deadline为start+timeout_ms/1000，完成回调时间严格早于deadline；已真实完成的批次不会仅因之后消费晚而过期，但仍须metadata相等。
- [x] requests非空list/tuple，每项严格keys body_path/body_path_id/colliders；colliders非空list/tuple，每项严格keys collider_path/path_id。path使用A1绝对ASCII prim path子集。body路径/ID唯一；collider路径/ID全批唯一；每collider必须等于或在其body路径下；所有ID↔path一一对应，允许同prim同时body/collider。解析后保存独立普通值，不引用传入dict/list。
- [x] `submit(query_prim, query_mode)`一次性调用每body一次，参数使用对应SDK名stage_id/prim_id/query_mode/timeout_ms/finished_fn/rigid_body_fn/collider_fn。query_mode.name必须为QUERY_RIGID_BODY_WITH_COLLIDERS，query_prim可调用。第二次submit不调SDK且锁存失败。外部SDK调用期间不持锁，避免跨线程callback死锁。同步回调或稍后异步回调均支持；submit自身不poll-wait、不update、不sleep。SDK调用抛Exception仅存type/message并永久失败，不重试。
- [x] `poll()`返回PENDING/COMPLETE/FAILED/CLOSED；COMPLETE需所有body都已提交，每body一个VALID rigid、所有声明collider恰好一次VALID、最后一个真实finished。响应顺序可交错，collider可先于rigid。任何重复/未知/跨body/错stage/result/type/坏数值/finished过早或重复/finished之后新响应/clock逆行/超时均永久FAILED，不由后来的好数据洗掉。

```python
def test_query_return_without_finished_is_not_complete(module):
    query = module.CollisionQueryBatch(41, [{
        'body_path': '/Robot/B0', 'body_path_id': 101,
        'colliders': [{'collider_path': '/Robot/B0/C', 'path_id': 201}],
    }], geometry_generation=0, settings_fingerprint='a'*64, clock=lambda: 2.)
    calls = []
    query.submit(lambda **kwargs: calls.append(kwargs), SimpleNamespace(name='QUERY_RIGID_BODY_WITH_COLLIDERS'))
    assert len(calls) == 1
    assert query.poll() == 'PENDING'
    with pytest.raises(ValueError, match='complete'):
        query.finalize(geometry_generation=0, settings_fingerprint='a'*64)
```

pending时尝试finalize只是拒绝，没有失败callback则仍允许后续真实完成；不将尚未完成当作终止或重新提交理由。

### Step 2：最小实现骨架（内部可整理，完整校验合同不变）

- [x] 使用下列完整算法，首RED后逐边界测试扩充验证。字段副本仅Python dict/list/int/float/str；用A1 `_integer/_real_scalar/_real_array/_obstacle_id`复用已测试的数值拒绝规则，不改A1。

```python
import copy
import math
import re
import threading
import time
import weakref
from encounter_geometry import _integer, _real_array, _real_scalar, _obstacle_id


def _id(value, name):
    value = _integer(value, name, 1)
    if value > 2**64-1:
        raise ValueError(f'{name} exceeds uint64')
    return value


def _fingerprint(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('settings_fingerprint must be lowercase SHA256')
    return value


def _requests(values):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError('requests must be a nonempty list or tuple')
    result, by_id, by_path, bodies, colliders = [], {}, {}, set(), set()
    def bind(path, path_id):
        if (path in by_path and by_path[path] != path_id) or (path_id in by_id and by_id[path_id] != path):
            raise ValueError('path and path_id must be one-to-one')
        by_path[path], by_id[path_id] = path_id, path
    for value in values:
        if not isinstance(value, dict) or set(value) != {'body_path', 'body_path_id', 'colliders'}:
            raise ValueError('request fields must be body_path/body_path_id/colliders')
        path, path_id = _obstacle_id(value['body_path']), _id(value['body_path_id'], 'body_path_id')
        if path in bodies:
            raise ValueError('duplicate body_path')
        bind(path, path_id)
        bodies.add(path)
        children = value['colliders']
        if not isinstance(children, (list, tuple)) or not children:
            raise ValueError('colliders must be nonempty list or tuple')
        copied = []
        for child in children:
            if not isinstance(child, dict) or set(child) != {'collider_path', 'path_id'}:
                raise ValueError('collider fields must be collider_path/path_id')
            cp, ci = _obstacle_id(child['collider_path']), _id(child['path_id'], 'path_id')
            if cp in colliders or not (cp == path or cp.startswith(path+'/')):
                raise ValueError('collider must be unique and within its declared body')
            bind(cp, ci)
            colliders.add(cp)
            copied.append({'collider_path': cp, 'path_id': ci})
        result.append({'body_path': path, 'body_path_id': path_id, 'colliders': copied})
    return result


class CollisionQueryBatch:
    def __init__(self, stage_id, requests, *, geometry_generation, settings_fingerprint,
                 timeout_ms=10000, clock=time.monotonic):
        self._stage_id = _id(stage_id, 'stage_id')
        self._requests = _requests(requests)
        self._generation = _integer(geometry_generation, 'geometry_generation')
        self._settings = _fingerprint(settings_fingerprint)
        self._timeout_ms = _integer(timeout_ms, 'timeout_ms', 1)
        if self._timeout_ms > 60000 or not callable(clock):
            raise ValueError('timeout_ms must be <=60000 and clock must be callable')
        self._clock = clock
        self._last_time = _real_scalar(clock(), 'clock')
        if self._last_time < 0:
            raise ValueError('clock must be nonnegative')
        self._deadline = self._last_time + self._timeout_ms/1000.
        if not math.isfinite(self._deadline) or self._deadline <= self._last_time:
            raise ValueError('deadline must be finite and distinguishably after start')
        self._lock = threading.RLock()
        self._closed = self._submission_started = False
        self._errors, self._events = [], []
        self._finished_count = 0
        self._state = {r['body_path']: {'submitted': False, 'rigid': None, 'colliders': {},
                       'finished': False, 'request': r} for r in self._requests}

    def _now(self):
        now = _real_scalar(self._clock(), 'clock')
        if now < self._last_time:
            raise ValueError('clock moved backwards')
        self._last_time = now
        return now

    def _complete(self):
        return self._finished_count == len(self._state)

    def _error(self, token, kind, error):
        message = f'{token}: {kind}: {type(error).__name__}: {error}'
        self._errors.append(message)
        self._events.append({'request_token': str(token), 'kind': kind,
                             'thread_id': threading.get_ident(), 'error': message})

    def _response(self, token, kind, response=None):
        with self._lock:
            if self._closed:
                return
            try:
                now = self._now()
                if now >= self._deadline:
                    raise ValueError('query deadline expired')
                state = self._state[token]
                if not state['submitted'] or state['finished']:
                    raise ValueError('response before submission or after finished')
                request = state['request']
                if kind == 'finished':
                    expected = {c['path_id'] for c in request['colliders']}
                    if state['rigid'] is None or set(state['colliders']) != expected:
                        raise ValueError('finished without exact rigid/collider coverage')
                    state['finished'] = True
                    self._finished_count += 1
                else:
                    if response.result.name != 'VALID':
                        raise ValueError(f'query result {response.result.name}')
                    stage_id, path_id = _id(response.stage_id, 'response.stage_id'), _id(response.path_id, 'response.path_id')
                    if stage_id != self._stage_id:
                        raise ValueError('response stage_id differs')
                    data = {'stage_id': stage_id, 'path_id': path_id, 'result': 'VALID'}
                    if kind == 'rigid':
                        if state['rigid'] is not None or path_id != request['body_path_id'] or response.type.name != 'RIGID_DYNAMIC':
                            raise ValueError('duplicate/wrong rigid body response')
                        data.update(type='RIGID_DYNAMIC', mass=_real_scalar(response.mass, 'mass'))
                        for name, size in [('inertia',3), ('center_of_mass',3), ('principal_axes',4)]:
                            data[name] = _real_array(getattr(response,name), name, (size,)).tolist()
                        state['rigid'] = data
                    else:
                        expected = {c['path_id'] for c in request['colliders']}
                        if path_id not in expected or path_id in state['colliders']:
                            raise ValueError('unknown/cross-body/duplicate collider response')
                        lo = _real_array(response.aabb_local_min, 'aabb_local_min', (3,))
                        hi = _real_array(response.aabb_local_max, 'aabb_local_max', (3,))
                        if (lo > hi).any():
                            raise ValueError('collider AABB min exceeds max')
                        data.update(aabb_local_min=lo.tolist(), aabb_local_max=hi.tolist(),
                                    local_pos=_real_array(response.local_pos, 'local_pos', (3,)).tolist(),
                                    local_rot=_real_array(response.local_rot, 'local_rot', (4,)).tolist(),
                                    volume=_real_scalar(response.volume, 'volume'))
                        state['colliders'][path_id] = data
                self._events.append({'request_token': token, 'kind': kind, 'time': now,
                                     'thread_id': threading.get_ident()})
            except Exception as error:
                self._error(token, kind, error)

    def _callbacks(self, token):
        reference = weakref.ref(self)
        def callback(kind):
            def receive(response=None):
                batch = reference()
                if batch is not None:
                    batch._response(token, kind, response)
            return receive
        return callback('rigid'), callback('collider'), callback('finished')

    def submit(self, query_prim, query_mode):
        with self._lock:
            if self._closed or self._submission_started or not callable(query_prim) or getattr(query_mode,'name',None) != 'QUERY_RIGID_BODY_WITH_COLLIDERS':
                error = ValueError('submit requires an open unsubmitted batch and valid query interface/mode')
                self._error('batch', 'submit', error)
                raise error
            self._submission_started = True
        for request in self._requests:
            token = request['body_path']
            with self._lock:
                if self.poll() != 'PENDING':
                    break
                self._state[token]['submitted'] = True
            rigid, collider, finished = self._callbacks(token)
            try:
                query_prim(stage_id=self._stage_id, prim_id=request['body_path_id'], query_mode=query_mode,
                           timeout_ms=self._timeout_ms, rigid_body_fn=rigid, collider_fn=collider, finished_fn=finished)
            except Exception as error:
                with self._lock:
                    self._error(token, 'query_prim', error)

    def poll(self):
        with self._lock:
            if self._closed:
                return 'CLOSED'
            if not self._errors:
                try:
                    now = self._now()
                    if not self._complete() and now >= self._deadline:
                        raise ValueError('query deadline expired')
                except Exception as error:
                    self._error('batch', 'poll', error)
            return 'FAILED' if self._errors else ('COMPLETE' if self._complete() else 'PENDING')

    def diagnostics(self):
        with self._lock:
            result = copy.deepcopy({'status': self.poll(), 'stage_id': self._stage_id,
                'geometry_generation': self._generation, 'settings_fingerprint': self._settings,
                'requests': self._requests, 'responses': self._state,
                'callback_events': self._events, 'errors': self._errors})
            for state in result['responses'].values():
                state['colliders'] = [state['colliders'][c['path_id']] for c in state['request']['colliders']
                                      if c['path_id'] in state['colliders']]
            return result

    def finalize(self, *, geometry_generation, settings_fingerprint):
        with self._lock:
            try:
                if (_integer(geometry_generation,'geometry_generation') != self._generation
                        or _fingerprint(settings_fingerprint) != self._settings):
                    raise ValueError('query geometry generation/settings changed')
            except Exception as error:
                self._error('batch', 'finalize_binding', error)
                raise ValueError('query binding changed or invalid') from error
            if self.poll() != 'COMPLETE':
                raise ValueError('query batch is not complete and valid')
            return {'schema': 'm1_collision_query_batch_v1', 'representation_status': 'query_protocol_complete',
                    **self.diagnostics()}

    def close(self):
        with self._lock:
            self._closed = True
```

上述边界保护必须由测试冻结：deadline加法finite且>start；每个submit调用前poll deadline（expired则FAILED且不调用SDK）；响应按manifest顺序输出list，json.dumps/loads保持语义一致。诊断成功和失败events保留，错误不清空。关闭后迟到回调无作用且不读clock；外部generation/settings值检查不等价于实际watcher，本包不能报现场完成。

实施时明确的小调整：生产版 `diagnostics()` 只复制已经锁存的状态，不采样时钟，也不因读取证据改变状态；新鲜期限/时钟结论必须调用 `poll()` 或 `finalize()`。此选择由主代理接受，并用docstring及独立测试冻结。事件time保存通过有限/非递减校验的采样（包括合法时钟下的超时样本）；非法时钟或已FAILED后忽略的回调time为None，保证严格JSON。

### Step 3：协议负例RED→GREEN

- [x] 同步完整、异步交错、collider先于rigid和多body、多collider正例；通过json.dumps(...,allow_nan=False)与loads往返检查detached普通数据。
- [x] 仅return、仅数据无finished、finished过早、重复rigid/collider/finished、finished后response、unknown token/path、cross-body、错stage、nonVALID result、wrong rigid type、缺字段、NaNInf/bool/shape/invertedbox均拒绝，failed后好数据也不能成功。
- [x] constructor所有id/path/hash/timeout/clock/manifest失败；uint64大ID不转浮点；body与collider同prim合法；ID/path互相冲突拒绝。
- [x] fake clock手动推进，不靠sleep：deadline前可完整，exactdeadline和之后失败；已及时完成后晚消费允许；clock倒退/nonfinite、deadline溢出或加法不可分辨、过期submit不调用SDK均拒绝。无重试、无sleep/pump/importSDK。
- [x] query_prim抛错及已同步finished后再抛错均锁存FAILED；二次submit不调用SDK；pending finalize不会把未完成变为终止；generation/settings变更即使恢复旧值仍失败。
- [x] 完成检查不能在每次callback/poll扫描全部请求。仅在已submitted、rigid/全部collider齐全且第一次真实finished时递增完成数；每个body完成后poll仍须PENDING直到最后一个。以17408body（1024×17）CPU协议用例覆盖规模，不用机器耗时作flaky测试门槛。主代理在中间版本测得全表扫描27.19021s，修改后以相同脚本重测；这只是协议处理性能，不是PhysX实际query耗时。
- [x] 真thread+Barrier/Event的有界线程测试：外部query callable同步等待worker callback能完成，证明submit未持锁；多个body并发callback结果和events完整，thread IDs为int。testsjoin带短deadline防死锁，无任意长sleep。
- [x] 保留callback后weakref+gc证明不保活batch；close幂等、迟到callback不读已失效clock、不恢复成功；callback返回后SDK response弱引用可释放；输入manifest和返回diagnostics/finalize数据修改不改变内部状态。

### Step 4：主代理核验、双审查与记录

- [x] 实现者focusedGREEN、自审、scoped commit，只两文件；main独立核数据/生命周期边界与真实完整旧回归，独立SPEC后QUALITY，发现问题先RED修复再复审。
- [x] focused命令如下，完整回归仅main使用全新`--basetemp=/data/hexinkun-m1-acceptance-20260918/encounter-query-batch-full`；如修复后需另全量用唯一后缀，不覆盖旧证据。
- [x] notes/todo/T306/log同步；目标保持active，此包不计G1/G2/10000通过，不动GPU7占位。后续立即接薄USD/SDK snapshot/watch与单独8-env初始化现场诊断，不退回重复已完成的A1/B1/B2a审计。

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree/tools/m1_reference_validation
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest tests/test_collision_query.py -q --tb=short -p no:cacheprovider
```

## 自审

- [x] 批次绑定身份和complete条件明确；真实SDK接口已读，fake仅隔离外部调度，不能成为物理来源证明。
- [x] 无阻塞等待/隐含physics step/取消全局cooking；弱回调和显式close不持有USD/env/native响应，SDK无取消handle事实保留。
- [x] 未添加checkpoint重启/旧state reset/阈值变化。后续实际stage/settings变化watcher与proxy/无额外步现场验收明确未被本包代替。
- [x] 继续已批准规格范围，使用现有隔离分支、TDD、SPEC→QUALITY，不重复征求执行选择。
