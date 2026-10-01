# M1 AME 生命周期接入准备审计（2026-09-18）

## 结论与边界

T306.6i 仍未验收。可以把接入限定为 **M1 入口启动配置、资源所有权释放、外层真实完成审计，以及 mixed-terrain 复制/碰撞回归**，不需要修改 PPO 更新循环、奖励、动作或 fresh 计数。当前 AME fresh 10000 的正确终点仍是 `model_9999.pt / iter=9999 / next_iter=10000`。

reference adapter 的三次 8×1600 通过只证明该参考场景/控制器及其正常退出；不能证明 AME 学会跨越、大绕行，不能证明 AME mixed terrain 的普通复制路径、8-env 训练退出、1024 容量或 10000 更新稳定性。

本次只读远端，唯一写入是本地本文；未启动 Isaac、训练、评测或 GPU 任务，未发 signal、安装、修改远端源码/notes。CPU 只做了一次 `amp/bin/python -B` 模块来源取证，没有实例化 runner/env；输出 `cuda_initialized=False`。未运行测试。本审计按委派任务覆盖 AGENTS 的 subagent override，不另启 skill/委派。

## 取证基线

- 已读远端 `AGENTS.md`、`.codex/RULES.md`、`notes/index.md`、todo/dashboard 和 T306 当前 `.6i`、相关 log index 条目、AI00/AI03、floating AME/AMP/1024 日志、owner-cleanup/launcher-cleanup/GDB-frames/normal-clone/exit-owner 日志及最新 wheel-reward 120-update 完成记录。
- 远端根目录记为 **R=`/home/hexinkun/m1_rl`**；下文 `Go2Pvcnn/...:行号`、`tools/...:行号` 均相对 R。SDK 根目录记为 **L=`/home/hexinkun/IsaacLab45/source/isaaclab/isaaclab`**。
- 审计期间仓库 HEAD 已到 `5553e84e90b2b59e09d35b80205c9ff8ba3c524d`，工作区本来有大量 M1 修改；不是干净提交验收。独立 scale 工作并行进行，本文不审其实现。
- AME 主入口 SHA256 `541462c844a330af99b13353b38d0fe8491adda1071e6ec3ff26e2fa8198b233`；AMP 入口 `f89d70199e5b01077ae43dd38a2153dc9c6d63efa7d8bd76fc91cc6fffea05e9`。
- headless launcher SHA256 `d9d2fc33f35ff0cdd6382e8e5cd90f8d81e89a893bbd0719594b16e03894cefd`；AME runner `c49c77e2aa704e0bf66405e86159ee1146c3bb881408310477c861686c88655c`；AMP runner `b525c3ed46ff6cdce84a6b7bf66f5772636c2a766333d551768cd7f727eb2fc3`；基础 runner `88ba77e249e3f1f2d6b3e5868c1b681b2cde4e5c6ff0bbcdb9f020dd4e7884e3`。

## 1. 实际运行来源：当前是 m1_rl，不是 amp 仓库副本

`Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py:15` 和 AMP 入口 `:16` 插入当前文件对应的 `Go2Pvcnn` 与 `Go2Pvcnn/rsl_rl`；headless `:14` 也显式提供这两条 R 下路径。安装的 `site-packages/__editable___rsl_rl_2_0_2_finder.py:9` 映射同样是 `/home/hexinkun/m1_rl/Go2Pvcnn/rsl_rl/rsl_rl`。

实际 CPU import 同时打印 `__file__` 和函数 `__code__.co_filename`，确认如下类都来自 R：

| 类型 | 本次观测路径 |
| --- | --- |
| `OnPolicyRunner.learn` | `Go2Pvcnn/rsl_rl/rsl_rl/runners/on_policy_runner.py` |
| `PPO.update` | `Go2Pvcnn/rsl_rl/rsl_rl/algorithms/ppo.py` |
| `ParallelismAMPPPO.update` | `Go2Pvcnn/rsl_rl/rsl_rl/algorithms/parallelism_amp_ppo.py` |
| `AmeOnPolicyRunner.save` | `Go2Pvcnn/ame_baseline/ame_runner.py` |
| `AmeAmpOnPolicyRunner.save` | `Go2Pvcnn/ame_baseline/ame_amp_runner.py` |

因此“当前算法可能实际来自 `/home/hexinkun/amp/Go2Pvcnn`”不能再作为现状结论。此取证不改写历史进程的 provenance；下一次真实训练仍应持久化实际来源，避免以后 editable 或 `PYTHONPATH` 漂移。

## 2. 计数合同和完成证据

基础 runner `on_policy_runner.py:120` 初始化迭代为 0；`:199` 取 `start_iter`；`:200` 计算 `start_iter + num_learning_iterations`；`:201` 使用半开 `range`。实际更新在 `:307`，更新成功后 `:330` 赋当前迭代，`:343` 保存最终模型。此循环没有 `simulation_app.is_running()` 门槛、提前 `break` 或按 checkpoint 截断的分支。

`ame_runner.py:64` 保存 `next_iter=current_learning_iteration+1`，`:99` 至 `:106` 验证并恢复下一次迭代；`:18` 至 `:37` 原子保存并 fsync。因此 fresh 10000 必须仍为 `0..9999` 共 10000 次，最后 `iter=9999,next_iter=10000`，不需要改 runner 计数。默认每更新 40 env steps（`ame_train_cfg.py:8`），若 1024 env 完整训练则共 `409600000` env steps。

当前证据缺口：

- AME 入口 `:149` 返回后，在 `:150` 打印 `Training Complete`，但 `env.close/app.close` 尚在 `:157` 至 `:160`。AMP `:174` 至 `:185` 相同。
- `Go2Pvcnn/scripts/run_m1_validation.sh:5` 至 `:12` 只收子进程返回码及任意 `Training Complete` / probe / eval 标志；没有独立的 post-cleanup 证明、run-ID/PID 绑定、exact 更新序列、最终 checkpoint/TB 检验，也未分别持久化原始 native code 和审计 verdict。
- `env.close()` 若异常，顺序 finally 会跳过 `simulation_app.close()`；cleanup 异常也可能覆盖原异常。已有完成标志仍留在日志。
- 历史 `run_logs/m1ame_floating_1024x120.log:87` 明确 `Replicate physics: True`；`:4935` 有完成标志，`:4937` 有 validation 0。notes 的 exact120/1000、finite checkpoint/TB 是有效的历史过程/工件证据，但不是本次待迁移 `fast_shutdown=False + replicate_physics=False` 的正常关闭证明。

AME-AMP 必须单列：`ame_amp_runner.py:83` 的 legacy warm-start 从 0 起；完整 AMP 恢复 `:99` 直接读 `iter`，保存 `:110` 至 `:122` 无 `next_iter`，也不是 AME 的原子保存。AMP 入口 `:164` 总会加载 checkpoint，不能称为 AME fresh。其差异本轮只登记，不修复，不阻塞对 AME fresh 的计数结论，也不宣称 AMP 恢复已对齐。

## 3. 当前启动与遗留早退/挂起条件

1. 两训练入口均 `AppLauncher(args)`（AME `:81`，AMP `:88`）；SDK `simulation_app.py:79` 的 `fast_shutdown` 默认 True，`:321` 传给 `/app/fastShutdown`。它不是正常 Python 析构/扩展 shutdown 的证明。reference 在 `tools/m1_reference_validation/run.py:68` 显式 False。
2. M1 配置继承 `ame_env_cfg.py:66` 至 `:69` 的 `replicate_physics=True`，M1 `__post_init__` 没覆盖；AMP 又继承 M1（`m1_ame_amp_env_cfg.py:19`）。改为 False 必须在场景创建之前且仅在 M1 接入边界，不改所有 Go2 任务的默认配置。
3. headless `:30`、`:46` 默认仍是 `cuda:4`。后续用户要求物理 GPU7，必须显式配置并验证 `DEVICE=cuda:7`，保持 `:21` 的 `unset CUDA_VISIBLE_DEVICES`，同时核实解释器和 UUID。fresh 必须没有继承 `CHECKPOINT`，否则 headless `:54` 自动追加 resume。保持 `:61` 的单次 exec，不接回 supervisor。
4. launcher 的 Vulkan preflight `:24` 至 `:28`、CLI 参数/缺 checkpoint、浮动根断言、导入、创建环境、PPO/update/checkpoint 错误均可以阻止或中断训练。AME 入口 `:152` 捕获 `BaseException` 后重抛；`AppLauncher` 构造本身在 try 之前，部分启动失败不受其 finally 保护。
5. SDK `L/app/app_launcher.py:154` 至 `:159` 安装 SIGTERM/SIGABRT/SIGSEGV 的 bound-method handler；`:975` 至 `:978` 直接 `self._app.close()`。它可能从训练中间进入关闭，缺少入口的完成审计；本轮没有发送任何信号。
6. 实际 SDK `L/sim/simulation_context.py:611` 至 `:614` 传播 callback 异常；`:617` 至 `:621` 在动画录制完成时 shutdown。暂停时 `:624` 的循环会等待继续。其 STOP callback 当前实现 `:943` 至 `:946` 是持续 render 等待 play，不能照注释或旧版本断言“STOP 一定立即退出”。
7. `simulation_app.py:569` 等待 replicator，`:597` 等待 stage loading；正常 close 本身可以停留。源码不能保证 10000 无早退/挂起，也不能据此把所有历史中断归因为同一 native 析构缺陷。

其中 `simulation_app.py` 的完整路径是 `/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/exts/isaacsim.simulation_app/isaacsim/simulation_app/simulation_app.py`。

## 4. app.close 前的真实 owner 与释放顺序

AME 当前不存在 reference 的 `RuntimeSink`/recorder-holder。应从真实保留链起步，避免机械复制一个没有所有权语义的 sink 清单：

| 保留者 | 源码证据 | 迁移时的边界 |
| --- | --- | --- |
| 入口 `runner → runner.env → wrapped_env.env → env` | AME 入口 `:122,:135`；基础 runner `:32`；wrapper `ame_env_wrapper.py:15` | 结束采集后不再调用它们，清理所有入口/辅助函数引用；仅 `env.close()` 不等于所有对象已不可达 |
| writer 与算法/rollout tensors | runner `:117,:155`，训练入口 `:135` | 先 flush/close writer，确保最后 TB 事件落盘；释放 runner/alg/storage。基础 runner 没有 writer.close/finally cleanup |
| 入口 `policy_obs, critic_obs, extras`，learn 异常 frame 的 `actions,obs,infos,locals` | AME `:123` 至 `:124`；runner `:169,:221,:224,:333` | 释放 tensor、字典和 frame；普通 tensor 不等于已证实 PhysX owner，但不能留下完整 env/observer 引用链 |
| cfg/observer/holder 闭包 | reference `run.py:41` 至 `:52`，runtime recorder bridge `:354` | 当前 AME cfg 多为静态函数，不能声称全是 runtime retainer；未来接入显式 observer 后必须关闭回调、清空 holder 与捕获 env 的 cfg/term，再 drop refs |
| AppLauncher 两个 timeline subscriptions 和 signal bound method | `L/app/app_launcher.py:140` 至 `:159` | plugins 还在时 unsubscribe；只恢复仍由本 launcher 持有的原 handler，随后释放 launcher refs；SDK fatal handler 与 faulthandler 的顺序需要专门覆盖 |
| 异常及 traceback frame | AME `:152` 至 `:160`；reference GDB-frames 日志 | 现在 finally 执行时原异常仍活跃，traceback 可保留 learn/env/native views；不要把异常对象或带 traceback 的对象存进候选报告 |

SDK 已提供有顺序的 `env.close`：`L/envs/manager_based_rl_env.py:309` 先删除 command/reward/termination/curriculum managers，再调用 `L/envs/manager_based_env.py:499`，后者删除 action/observation/event/recorder/scene 并清 callbacks、clear instance。应使用这条路径，不能另猜私有 PhysX 接口释放。随后 `SimulationApp.close():616` shutdown，`:617` 卸载插件，故 owner/循环 GC 必须在这之前完成。

推荐正常顺序：最后训练工件/CPU 摘要 → writer flush/close → env.close → detach observer/owned launcher subscriptions → 清空 caller 与 cleanup helper 中的 runtime owner 容器/闭包 → `gc.collect()`（app 仍存活）→ app.close → post-cleanup 标志 → 外层收到真实 native exit 后裁决。每步失败继续尝试其余必要清理，同时总体非零且不生成成功证明；失败信息只保留字符串/CPU 元数据。

不能只向 helper 传 `cleanup(env, runner, sink)` 然后在 caller `del`：调用参数栈仍可能持有对象。reference `runtime.py:460` 至 `:465` 已用可消费 dict 清 helper 和 caller 的引用。异常路径还需让持有 runtime locals 的工作函数/except scope 先退出，再清理已结束的 traceback frame；必须保留错误文本与非零语义，不能以吞异常换退出成功。

path-stat cache 是独立的 traceback 保留来源：历史 GDB 把残留 frame 关联到缓存 OSError 的 importlib 路径。reference 默认 kit args 在 `runtime.py:51` 禁用启动缓存，`:84` 至 `:108` 同时核实实际设置、有效配置与 hook；单独 cache-off 曾仍 native134，不能称其独立修好了问题。AME 当前没有该设置/检查，若移植已验证启动组合，应一起做来源/有效性验证，不能只复制 `replicate_physics=False`。不调用私有 reset-cache API。

AMP 额外 owners（仅兼容性清单）：`tracking/env.py:32` 至 `:39` 的 reward-compute 闭包捕获 self；`tracking/managers/parallelism_reference_manager.py:199` 持 env，`:317` 至 `:332` 包装 env.reset，`:865` 至 `:870` 又由 env 保存 manager，形成环；`tracking/amp_env.py:99` 至 `:102` 保存 AMP manager/历史 buffers。入口还留 `base_env`。它们需要释放/GC。另一方面，虽然 AMP 入口调用 `attach_trajectory_manager_if_enabled`，当前 `trajectory_manager_factory.py:11` 白名单不含 `m1_cross_large_complex_ame_amp`，`:153` 立即返回；不能把 `_trajectory_manager` 当作此路径已实际创建的 owner。

## 5. replicateFalse 必须在 mixed terrain 上重新验收

`L/scene/interactive_scene.py:145` 至 `:171` 的 False 分支先独立复制 xform，随后按对象创建；True 分支 `:181` 至 `:204` 使用 physics replication/env IDs。False + collision filtering 在 `:209` 调显式 `filter_collisions`，实际 cloner 调用在 `:298` 至 `:304`。这是场景构建和碰撞过滤实现变化，不能只当一个退出开关。

AME 的 terrain 来自 `tracking/cross_large_complex_ppo_env_cfg.py:114` 至 `:123` 的 `SemanticCourseTerrainImporter` 和 mixed terrain/layout，不是 reference 的单横杆。reference 普通复制日志也明确只证明碰撞组声明图，没有证明每 collider/instance-proxy 或有接触机会时的动态过滤。后续至少需要：

- 比对 M1 17 刚体/16 关节、浮动根、actuator、material、有效 origin、robot/terrain/obstacle prim 和 scanner mesh 绑定；确认没有错误复制共享地形、缺 obstacle 或 collision group 目标。
- 对实际 mixed terrain 验证机器人与本地地形/障碍仍会碰撞，跨 env 过滤符合期望；全局 terrain 的 collision 归属应以实际场景图为准，不能沿用 reference 的 bar 组数量。
- 单独记录 scanner 的全局 mesh 可见性与 PhysX 过滤差异。AI03 已说明 2.5m probe 会扫描到隔壁障碍，8m 只对 bounded probe 已验证；不要为迁移关闭自动改 training spacing/reward/curriculum。
- 8-env 正常结束不证明 1024 普通复制的峰值显存、初始化耗时或吞吐。历史 1024 AME 约 13.5GB 的观测来自旧复制路径；GPU7 当前可用容量必须按实际资源再次评估，不能外推 reference 8-env 的占用。

## 6. 小而可测试的建议接口

建议新增 M1 专用 lifecycle helper，由两个 M1 训练入口和后续 policy evaluator 复用；不导入 reference 控制器/runtime，不改基础 runner loop。

1. `run_training_phase(args, owners) -> CPUTrainingResult`：保留现有 create→learn 调用和动作/奖励；向可消费 `owners` 注册 env/wrapper/runner/observer；成功后只返回 requested updates、完成迭代、checkpoint 路径/元信息、run-ID/PID 等 CPU 数据。异常先格式化为不含 locals 的文本，释放已退出工作 frame，结果明确失败。
2. `cleanup_training(owners, launcher_state) -> CPUCleanupResult`：明确 writer、env、observer 和 launcher ownership，逐步 attempt，清 caller/helper refs，在 app 活着时 GC；处理部分初始化、重复调用与各步骤异常。post-cleanup 标志只有全部所需清理成功后生成。不要返回/缓存 exception、bound callback 或 GPU 对象。
3. 外层 `finalize_training(..., native_exit_code)`：使用一次子进程，分别保存 native code 与 verdict；绑定新建 run-ID/PID/output，核实唯一启动、exact `0..9999` 顺序、最终 `iter/next_iter`、checkpoint/TB finite，以及 cleanup 标志。缺任何关键证据均拒绝完成，不能复用任意旧 `Training Complete` 标志。policy-only 跨越/绕行评测继续是独立行为验收。

上述是建议接口而非已实现/已测代码。若无需新 observer，保持空注册集合；不为了生命周期额外引入全量 rollout sink，也不重启之前失效的 profile-hook 路线。

## 7. 后续验证门槛（本次均未执行）

| 门槛 | 必须覆盖的内容 |
| --- | --- |
| CPU | fake app/writer/env 的严格顺序；弱引用/循环引用能在 app.close 前释放；正常、初始化失败、learn/save/writer/env/detach/close/报告写入错误；异常 frame/holder/参数栈保留反例；native0但缺计数/cleanup、native非0、重复/跳跃迭代、错 PID/run-ID、非有限工件均拒绝；保持原 runner 计数测试 |
| AME 8 env | amp/物理 GPU7/fresh/单进程，正常关闭配置生效、模块来源落盘；至少短训练包含真实 PPO update、最终 save/writer flush/env close/app close/native0，mixed-terrain 实体/碰撞/扫描回归通过；参考8×1600结果不代替此门槛 |
| AME 1024 env | 先容量与短训练关卡，测初始化/峰值显存/训练更新/退出；对普通复制下的 mixed scene 作规模检查。随后才按主任务行为门槛决定长训练；不能因 CPU/8env green 直接宣称10000保障 |
| 最终目标 | 新的单一进程完整 fresh10000、exact0..9999/next_iter10000、native0与独立 audit green；再用 policy-only 固定场景证明跨越和大绕行，不能用 teacher/reference 代替 |

## 可复核命令（只读，不启动训练）

远端没有 `rg`，本次使用 `grep/nl/sed`。以下在 `ssh 4090` 后执行；模块来源检查只 import Python/torch 模块、不创建 env、不初始化 CUDA：

```bash
cd /home/hexinkun/m1_rl
nl -ba Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py
nl -ba Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_amp.py
nl -ba Go2Pvcnn/scripts/run_m1_validation.sh
nl -ba Go2Pvcnn/rsl_rl/rsl_rl/runners/on_policy_runner.py | sed -n '115,125p;195,207p;292,345p;430,454p'
nl -ba Go2Pvcnn/ame_baseline/ame_runner.py | sed -n '45,107p'
nl -ba Go2Pvcnn/ame_baseline/ame_amp_runner.py | sed -n '78,122p'
grep -n MAPPING /home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/__editable___rsl_rl_2_0_2_finder.py
grep -nE 'Replicate physics|Training Complete|VALIDATION_EXIT' run_logs/m1ame_floating_1024x120.log
PYTHONDONTWRITEBYTECODE=1 /home/hexinkun/miniconda3/envs/amp/bin/python -B - <<'PY'
import sys, importlib
sys.path[:0] = ['/home/hexinkun/m1_rl/Go2Pvcnn/rsl_rl', '/home/hexinkun/m1_rl/Go2Pvcnn']
targets = [
    ('rsl_rl.runners.on_policy_runner', 'OnPolicyRunner', 'learn'),
    ('rsl_rl.algorithms.ppo', 'PPO', 'update'),
    ('rsl_rl.algorithms.parallelism_amp_ppo', 'ParallelismAMPPPO', 'update'),
    ('ame_baseline.ame_runner', 'AmeOnPolicyRunner', 'save'),
    ('ame_baseline.ame_amp_runner', 'AmeAmpOnPolicyRunner', 'save'),
]
for name, cls, fn in targets:
    module = importlib.import_module(name)
    print(name, module.__file__, getattr(getattr(module, cls), fn).__code__.co_filename)
import torch
print('cuda_initialized=', torch.cuda.is_initialized())
PY
```

本地交付只更新本文，root notes/todo/log 未改；由主代理决定将哪些确认发现纳入 T306.6i 后续计划。未开展参考到策略的桥接或大绕行学习架构设计。
