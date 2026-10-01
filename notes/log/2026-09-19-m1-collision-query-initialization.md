# M1 实际碰撞查询初始化诊断

2026-09-19；T306.6h.6a.1a.2c/G0-B2b2c。前一目标轮为progress：lease代码8a3746f、文档bc0d5a8、main1565full/零跳过与SPEC→QUALITY通过。当前fresh linked worktree为codex/m1-encounter-lifecycle/bc0d5a8 clean；完整目标保持，不重复旧基础审计或既有授权。

## 实施初期范围与前置验证（历史，最终状态见下文）

拟在隔离adapter runtime.parse_args增加仅8×32允许的collision-query-probe标志，默认false；run.py在唯一wrapper reset和validate_scene之后、RuntimeSink和first action之前执行独立probe。同步query完成才继续原32步；PENDING或来源失效明确记录并结束本次诊断，不偷偷step/reset/pump或自动重启。若实际需要异步pump，按现场证据继续受控pump实现，不以本次同步限制替代最终能力要求。

计划已scoped提交9a57924，主代理自审无占位符/合同冲突；fresh实现代理收到完整四文件合同，正在TDD。公开API为copy_state/state_metadata/changed_fields、execute_query_probe、capture_live_state和probe；错误报告/原始NPZ/cleanup-owner重试/自有callback释放均为显式门槛，不能以旧CPU结果替代实际query。

Fresh CPU baseline：collision_lease＋runtime_contract **171 passed in7.77s/exit0**，basetemp=/data/hexinkun-m1-acceptance-20260918/query-init-baseline-full。本次尚未启动Kit/GPU。

实现首批TDD已RED：43 failed、61 passed/7.64s，失败落在新增module/helpers/flag/recorder接线缺失；实现者正在补齐，不能把RED或后续focused单独当验收。主代理复核run.sh仅启动一个native child并wait真实退出，没有自动重启；旧8×32 run11留存128 sensor updates、32 prepare/IK、0reset，可供新诊断完成后的预算/原始样本比较。该旧run不是本候选的新物理证据。

## 无额外步数守卫接口核对（只读）

切点run.py validate_scene之后/RuntimeSink之前。env.sim.current_time/current_time_step_index为仿真事件计数；另读取env._sim_step_counter/common_step_counter/episode_length_buf及prepare/IK计数。现有diagnostic sensor.physical_update_count只在accumulator.armed时增加，本切点未armed，因此不足以证明没有physics事件；需单独注册自有physics callback并finally移除。

不得只比较robot.data缓存：App.update若触发physics但未调用scene.update，_sim_timestamp可能不变，data getter可返回旧值。需从root_physx_view读取并clone原始root/link transforms、root/link velocities、DOF position/velocity；native transforms是LINK pose/xyzw，native velocities按IsaacLab定义为COM velocity，证据命名不能混淆。读取Python、NumPy、Torch CPU和本任务GPU7 RNG，不调用get_rng_state_all去初始化其它GPU。

实际source getter/cache/查询接口与完整采样合同由本轮计划固定；callback来源守卫沿已完成lease，不再改其豁免或将source bounds当query结果。

独立只读接口审查完成，主代理另实读SDK query入口、raw getter和physics callback source。env.sim.add/remove_physics_callback按自有name持有/释放receiver，不clear_all；stage ID只用现有UsdUtils cache GetId/Find，不用会Insert的sim_utils helper。App.update源码直接调用_app.update，而正常sim.step(render=True)也使用它，所以不能当无physics的默认pump。raw root/link velocity在当前IsaacLab被明确当COM velocity；pose为LINK/xyzw。本轮guard保留这些命名。根盘第二次检查仍约1.9GiB，未新增SDK/log/cache改动。

## 资源与安全

本轮fresh full：3bcb734四文件实现后，**4 failed、1661 passed/168.65s**，basetemp=query-init-implementation-full。四处全部是旧test_scale_modes边界替身不接recorder_events新optional参数，而非Isaac物理失败；实现者获准仅补该test fixture参数并断言非probe为None，保留原断言，另做RED→GREEN/full。独立SPEC审查进行中，尚未QUALITY或现场。

启动前资源复查：根盘available=515920KiB（约504MiB），低于1GiB预设门槛，暂停真实Kit/GPU启动。只读定位本人~/.cache为23GiB，其中pip23GiB；未删除/移动。/data仍充足；原占位身份不变。资源恢复或获得精确缓存处理授权前，不强行启动。

Fresh根分区约1.9GiB，/data约6.5TiB；输出/临时证据放/data，启动前须再查余量。GPU7 UUID=GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e，仅原占位PID351307/hexinkun/启动Sep18 23:05:13/python sleep.py，约15GiB使用、8.3GiB空闲。未停止占位或其它进程。既往8×32显存约4.9GiB，可在占位保留情况下尝试；仍需正式启动前fresh核验。无新安装、SDK/driver/参考资产写入或主工作区源码改动。

## 最终代码验证（CPU完成，真实query未执行）

最终代码92278b779eb6afa566af94257000d0e36de794f3；主代理fresh full **1687 passed in169.98s、exit0、0skip**，basetemp=/data/hexinkun-m1-acceptance-20260918/query-init-publication-full。SPEC修复复审PASS；QUALITY最终194/22.18s PASS并独立复现两类late persistent writer failure，磁盘均保守failed而非假成功，订阅释放。当前无开放代码review缺口，实际PhysX query/无额外physics gate仍未验收。

最终module337行、test873行，本地/remote哈希一致：query_initialization_probe.py=e82b130ac9b40ec454589354a2ed24e9fc2746163605c338ee63f783007742e6；test_query_initialization_probe.py=35063dfde6bed50062c7575532091ba33e0f670ee4ed1c51880fea4ade1157ab。原run.sh/SDK/driver/正式主源码/参考/训练模型均未改，本包代码只在隔离linked worktree。

最终资源核验available531400KiB（约519MiB），/data约6.4TiB；GPU7 UUID不变、15754MiB used/8328MiB free/util0，原占位351307未动。没有本轮Kit/仿真/训练进程。已询问用户能否把且仅把pip下载缓存迁/data并保留原路径链接，未收到授权，因此未执行迁移/删除。下一步不是再做基础审计：待授权或根盘空间恢复后fresh核验，按已批准命令单次8×32 --collision-query-probe并跟到实际native/wrapper退出，继续actual bounds/后续encounter实现。完整目标保持ACTIVE，本轮progress；该资源阻碍首次出现，尚不满足三轮BLOCKED条件。

## 全量与SPEC/QUALITY反馈历史

P1修复6ed4b42已完成：新增20个KeyboardInterrupt/SystemExit边界用例RED20fail，GREEN192/19.07s；原CleanupError仅一次额外retry保持。独立SPEC复审192/19.70s PASS，另四次真实USD/lease query/final-poll中断均close1、after/failed report、subscriptions/nativepaths0/stageNone。主代理fresh full **1685 passed in168.71s、exit0、0skip**，唯一basetemp=query-init-repair-full。主代理核对五文件本地/remote SHA256全一致；QUALITY进行中。完整现场query门槛还未执行。

6ed4b42阶段源码SHA256：query_initialization_probe.py=59a465246ee5c644a1ae4744d5c3d0e97b8170f060929b2f26d16c8c17c2d476，test_query_initialization_probe.py=2fe9fc34de3f23d442633ad3379c2a478be5d32de977d2207867e298c048f352。

QUALITY首审192/19.16s，但FAIL/P2：首次write_report在callback移除/最终绝对physicscount检查前已落盘complete_unchanged；后续final与failure报告两次写入若都OSError，磁盘仍留过早成功。独立reviewer用setup_probe真USD/lease/query复现普通late persistent writer failure，也复现remove_event导致实际count1而磁盘仍0。已委派原实现者改保守初次发布、增加这两个RED/GREEN，不以full曾通过掩盖新发现；当前6ed4b42尚不准进入现场。

旧fixture修复f82da92：仅test_scale_modes.make_diagnostics接optional recorder_events并assert None，RED4failed/10passed→focused172passed18.49s。生产路径不为mock回退，原controller/cleanup断言不动。

SPEC首审FAIL/P1，独立focused158/18.02s不能覆盖中断窗口。主代理再用真实USD/CollisionSceneLease/query及外部Settings.get在final source poll注入KeyboardInterrupt，复现order仅capture,before,factory,query；reports0、before only、pending_unsubscriptions12/nativepaths2。原因是helper的finally前置diag/poll只except Exception，BaseException跳出finally绕过close；query入口中断另会close但丢after/report。两次复现均手动关闭所有owner、恢复settings getter，不遗留订阅。已委派原实现者补对应RED/GREEN，不接受当前实现进入GPU。joint_names只要求16unique校验，合同未要求输出名单，因此未采纳该潜在额外项。

精确资源问题已通过非阻塞问题呈给用户：是否允许迁移/home/hexinkun/.cache/pip到/data并保留原路径软链接。只读du显示http-v2约19GiB、wheels4.4GiB，未发现本人pip/conda install/create/update进程；没有授权前不迁移或删缓存。该问题阻止现场启动，但本轮CPU修复/审查仍有实质进展，目标不标BLOCKED/COMPLETE。

## 资源授权复核：第2个连续目标轮

上一目标轮为progress（完成92278b7＋1687full与双审），并首次确认root不足/迁移权限待返。本次自动续行不是用户同意迁移。fresh remote HEAD=b16168b121963bad2637789dba2be0c10cfc9bfc、worktree clean；rootavailable530612KiB（约518MiB），/data6894435612KiB；GPU7仍原UUID、15754MiBused/8328MiBfree/util0，占位351307身份/启动时刻不变。没有新query run活跃handle可等待，不属于verified wait；代码已通过的CPU门槛不重复跑。

本次只能确认同一启动资源/权限阻碍仍存在，不能把状态复述或本条记录当实质实现进展；当前连续计数2，完整目标保持ACTIVE，未达到三轮BLOCKED门槛。未移动/删除pip缓存、未启Kit/GPU/训练，未改源码/SDK/阈值。下一动作仍是用户授权精确迁移或根盘空间恢复后的fresh启动检查，不以未授权缓存操作或强行启动绕过限制。

## 资源授权复核：第3轮，目标BLOCKED

上一轮属于无实现进展的同条件复核，非verified wait。本次自动续行仍不是用户迁移授权；fresh rootavailable533224KiB（约521MiB）、/data6894435612KiB，HEAD=b16168b121963bad2637789dba2be0c10cfc9bfc且worktree clean。GPU7computeapps仅351307/python/15744MiB，ownerhexinkun、启动Sep18 23:05:13均不变；pip原路径仍真实目录/home/hexinkun/.cache/pip。没有本轮真实query/训练handle可等待，也未出现根盘恢复。

同一根盘不足+缓存迁移未授权阻碍已连续3个目标轮，满足严格blocked门槛：原实现轮完成CPU进展但首次被现场资源阻断，之后两次续行确认相同条件。CPU门槛与review已完成；下一既定动作依赖真实query，不能把重复测试/状态记录当推进，也不以未经授权搬缓存或低空间强启来绕过门槛。调用update_goal(status=blocked)，完整目标不是完成或缩小；待用户批准精确迁移或外部空间恢复再恢复，恢复后的blocked审计重新计数。未动占位、SDK/驱动、源码、模型、历史日志或缓存。

## 未验收目标（完整范围保持）

此诊断不是几何包络/CLEAR/G1，不是policy-only跨越或绕行。三次新8×1600→1024×32→1024×1600、G2真实再次遇障、AME生命周期/命名actions、单进程10000actual updates全部仍保留。

关联：[计划](../../docs/superpowers/plans/2026-09-19-m1-collision-query-initialization.md)、[前置lease](2026-09-19-m1-collision-scene-lease-implementation.md)、[query合同](2026-09-19-m1-collision-query-contract.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
