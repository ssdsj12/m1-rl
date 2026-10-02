# M1 reference controller 1024 环境就绪性只读审计

日期：2026-09-18。父节点：T306.6h.6a.1。范围：参考控制器的 1024×32 容量检查与 1024×1600 严格验收准备；不涉及 AME 接入、learned policy、绕行或 10000 次更新。

本次仅远程读源码、既有 run14 证据、资源状态及执行 NumPy 字节/精度计算。未修改远程代码、依赖、进程或 GPU 状态，未启动仿真。本地此文档由主代理要求另行生成。主代理并行执行的 run15/run16 不属于本审计的物理证据。

## 结论

当前候选不能直接把参数改成 `--num-envs 1024` 后宣称扩容验收。两个确定的阻碍是：独立 `sync_verdict.py` 仅接受 8×1600；现有 1×1024 长条地形使横杆世界坐标 float32 量化误差超过现有几何门限。32×32 紧凑布局可以避免该精度问题，但还必须实现环境到地形格的确定性一一映射，修改横杆归属解析，并完成同规模真实随机化对照。

CPU、主机 RAM 和现有数据格式的磁盘需求可承受本轮验证。GPU7 可用 8328 MiB 时是否容纳 1024 个普通复制的 M1、扫描器与全身接触诊断，不能由静态数组预算保证。三次同候选 8×1600 严格重复全部通过后，才可进入上述适配及 1024×32 容量门槛；OOM、无进展或正常收尾失败均停止扩大。

## 源码及冻结证据位置

以下路径均为服务器 4090 的真实路径，行号取本次审计时的文件。

- 候选根目录 `CAND=/home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter`。
- 正式根目录 `/home/hexinkun/m1_rl/tools/m1_reference_validation`；本次只读 `git diff --stat -- tools/m1_reference_validation` 输出为空，正式版本仍以父任务记录的 a86cbf5 为准。
- 原参考 `REF=/home/hexinkun/m1/Go2Pvcnn`；IsaacLab `LAB=/home/hexinkun/IsaacLab45/source/isaaclab/isaaclab`。
- SDK utility 根目录 `SDK=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/exts/isaacsim.core.utils/isaacsim/core/utils`。
- 核算输入 `/home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_14_post_cross_sync`，含 50 个 samples NPZ、50 个 sync NPZ、原 report、scene manifest 及 initial randomization。
- 已预读仓库 `AGENTS.md`、`.codex/RULES.md`、`notes/index.md`、`notes/todo.md` 相关顶部、T306 当前分支页及日志索引；详细依据为 `notes/log/2026-09-18-m1-post-cross-sync-implementation.md` 与两个已批准设计 `docs/superpowers/specs/2026-09-18-m1-reference-controller-validation-design.md`、`2026-09-18-m1-post-cross-wheel-sync-design.md`。

## 1. 验收器需要规模及预算明确的分支

`CAND/sync_verdict.py:18` 固定 `N, STEPS = 8, 1600`。限制还贯穿：

- `:92–126`：每块 shape 为 `(T,8,...)`，总步数必须 1600，并整体 concatenate。
- `:174–197`：run_start、report、cleanup、per_env、prepare/IK 次数全部按 8×1600 验证；每个环境的首回合必须 1600 样本、0 reset。
- `:232–367`：独立事件/状态重放以全局 N、STEPS 分配数组。
- `:393–443`：所有环境必须实际接管；尾段固定为 steps 800..1599、799 个相邻差分。
- `:447–472`：最终 `accepted = original_report.passed AND sync_checks_passed`，且必需 baseline。

相对地，原始 `CAND/runtime.py:43–52` 入口和 `:480–538` native finalizer 已支持 `(8,1024)×(32,1600)`。`:521–535` 正确区分 startup 与 strict：32 步只可 `startup_passed`，`passed` 保持 false；1600 步才要求所有环境严格 flags 通过。`metrics.py:352–365` 使用 `passed_envs / self.num_envs`，不存在将分母写死为 8 的问题。无需改原指标门限或正常退出链。

控制核心自身是通用 N：`post_cross_sync.py:55–86` 按 num_envs 创建 CPU 状态，`sync_bridge.py:94` 传入实际 env.num_envs，`post_cross_sync.py:306–307` 只按逐环境 active mask 替换轮列并转回原动作 device/dtype。`sync_bridge.py:40–79` 对全部环境检查真实轮 joint mapping、JointVelocityAction、scale1/offset0/default velocity0、implicit actuator20/30/0；`run.py:108–114` 检查实际N、16列并创建 `[N,16]` 零策略残差。这些路径没有8-env限定，扩容不需要改变 rad/s、正方向、Ki/τ/feedforward 或控制公式。CPU状态和反复GPU→CPU快照会有随N线性增加的开销，应在容量测量中报告。

建议最小新增独立 scale verifier，保留已验收的 8-env verifier 原文件。原因不仅是隔离改动：`sync_verdict.py:143–145` 与 `sync_bridge.py:26–31` 将该文件自身 SHA256 纳入候选 metadata；直接编辑旧 verifier 会使 run14/15/16 旧证据无法按原 hash 重验。新 verifier 需记录自身 hash，校验冻结 core/bridge/旧 verifier 及新增布局/入口版本。

规模从显式命令/契约给出，并与 run_start、configuration、scene、initial arrays、全部 NPZ 和 report 交叉验证；不能看到少量样本后自动推断 N=8。只允许本阶段 1024×32 和 1024×1600。

32 步分支应验证全部 1024 环境、step0..31 恰好一次、首回合无 reset/结束、每步 4 个子步、32 次原 prepare/IK、finite 状态、所有来源/动作单位/场景归属及正常 native0。此时同步尚未接管，必须验证全 16 列 original/final/actual parity 与独立 gate 状态，但不能要求 phase11、接管、跨杆或 tail800，也不能由 startup 成功标记行为成功。严格分支保留原全部门限、1024 个独立 per_env、完整 1600 样本和逐环境尾段统计。

## 2. 同规模 baseline 是物理前缀对照的必要证据

`CAND/sync_verdict.py:148–161` 对 configuration/provenance/bindings/scene/随机化 JSON 作精确比较，initial NPZ 的 root、joint、mass、material、origin 也逐数组 bitwise 比较。`:213–225` 和 `:393–398` 对各环境首次接管前的全部物理与动作字段进行精确前缀比较。原设计明确禁止假定 1024 的前 8 个随机化样本等于 8-env 的样本。

因此，若沿用“接管前实际物理轨迹逐位一致”验收要求，需要原控制器的 **同为 1024、同布局、同源/资产/seed/实际随机化、同 episode budget** 对照。run12 的 8-env 前缀不能替代。1024×32 对照只覆盖 32 步，不能覆盖 run14 约 245..253 步的接管前窗口；该时刻不能假定对全部 1024 相同。

当前入口仅准 32/1600 两档，所以不新增预算类型的最小路线是完成 1024×32 容量检查后，取得原控制器 1024×1600 baseline，再取得候选 1024×1600。baseline 的完整首回合均速可能失败，这不阻止它作为接管前原行为对照；必须完整公开 baseline 自身报告。

需要明确 baseline 与候选的验收职责。旧 `_completion(baseline)` (`:193`、`:466`) 要求 baseline 所有环境完整首回合 1600 且无 reset，这比前缀用途更强。若原控制器某环境在候选接管时刻之后终止/reset，而其比较前缀连续、未结束且身份一致，尺度专用验收可以只以该有效前缀比较；不能删除该 baseline 的负结果。若结束发生在所需前缀内，则该环境的对照失败。候选仍必须 **1024/1024 全部 exact1600、无 reset/结束且全部严格通过**，不能因 baseline 失败缩短候选分母。

仅在候选内记录每步 original/final 动作可以证明未接管时动作不被修改，但不能替代跨运行真实物理轨迹对照。若不采同规模 baseline，应明确只取得动作一致性/独立重放证据，不宣称物理前缀对照通过。

## 3. 现有 1×1024 布局有确定的精度问题

`CAND/runtime.py:240` 将地形设为 1 行、num_envs 列、8×8m tile。`LAB/terrains/terrain_generator.py:176–182` 将整个地形居中，因此 1024 环境的 origin 为 x=0、y=-4092..4092m。

`REF/extension/semantic_course.py:599–658` 用 terrain origin 加固定局部横杆位置；`:878` 调 cuboid spawner。`LAB/sim/spawners/shapes/shapes.py:271` 调 create_prim；`SDK/prims.py:733–734` 将 translation 交给 backend convert。numpy/torch 的 `tensor.py:30/:29` 默认 dtype 均为 float32。run14 manifest 中 y=±28m 的横杆局部 y 已实测为 -0.20000076293945312，符合此量化路径。

对上述确定公式作 NumPy float32 计算，未启动 Isaac：

| 布局 | origin 范围 | 最大局部横杆中心 x/y 误差 | 超过 2e-5m 的环境数 | 最大世界坐标 ULP |
| --- | --- | --- | --- | --- |
| 1×1024、8m | x=0，y=±4092m | 2.3842e-8 / 4.8828125e-5m | 768/1024 | 0.000244140625m |
| 32×32、8m | x/y=±124m | 1.5259e-6 / 3.0518e-6m | 0/1024 | 0.00000762939453125m |

现有 `runtime.py:782–785` 对实际 bar dimensions/local center 使用 `atol=2e-5, rtol=0`，因此 1×1024 的局部中心会被拒绝。建议采用紧凑排布来保持门限，不扩大几何容差。scanner 已有 bbox 与 float32 world bbox 联合边界 (`:392–417`)，这个补偿只处理 scanner 的归属测量，不应被混用成放宽物理净空或实际几何。

## 4. 32×32 不能只改配置行列数

`LAB/terrains/terrain_importer.py:329–347` 的默认逻辑为：terrain_levels 随机抽行；terrain_types=floor(env_id/(num_envs/num_cols))。当前 max_init_terrain_level=0，则改成32列后 **1024 台只占第0行的32个 origin，每点32台**。设置 max_init=None 也只会随机抽行，不能保证每列32次抽样恰好不重复。

必须在 terrain importer 创建 origin 时完成确定性的 env_id↔(row,col) 双射，而不是在 reset 后仅搬机器人。建议选择一个显式固定映射，例如保留默认 terrain_types 的列分组：row=env_id%32、col=env_id//32；同时设置 levels/types 和 terrain.env_origins，并记录全部映射。该建议仅是待实施契约，不是本次已实现。

最小配套检查：

1. `scene.env_origins`、terrain levels/types、robot root 的命名 env_id 与每个 tile 唯一一致；恰好 1024 个不同 origin，最小间距仍8m。相关原检查在 `runtime.py:719–747`。
2. `own_bar_indices` (`runtime.py:251–263`) 当前硬要求 row0 且 col=env_id，需按同一显式双射解析 `row/col/slot0`；missing/duplicate/extra filter 仍拒绝。
3. 不按路径字典序猜 env_id。现有 body/sensor row 检查、实际 filter path 顺序审计、own filter index、scanner bbox 均保留；路径形如 col_100 使字典序与数序不同，必须使用名称映射。
4. 1024 个 tile 各保留同一根 `(0.85,-0.20)`、`(.06,.16,.06)` bar。参考 zero-count arrays 在 `m1_pvcnn_small_obstacle_env_cfg.py:956–963`；rows>9 经 `extension/semantic_curriculum.py:97–128` clamp，仍为0；`semantic_course.py:522–535` 的 mandatory slot0 仍单独生成一根。因此增加行数本身不会增加随机障碍，但实际输出仍须核验。
5. `InteractiveScene` 先普通复制 Xform 再建立 terrain/assets (`LAB/scene/interactive_scene.py:143–179,718–736`)；`scene.env_origins` 优先返回 terrain origins (`:363–368`)。布局适配应在 terrain 构造阶段完成，使初始 reset、机器人、bar、scanner 使用同一原点来源，不能只改 `_default_env_origins`。
6. 保留 `replicate_physics=False`、filter_collisions 与 owner 正常释放。`clone_evidence.py:8–120` 验证声明的 USD group 图，并明确记录 `dynamic_collision_filtering_verified=False` 和 `bar_own_environment_isolation_verified=False`。没有异环境接触机会不能证明引擎动态过滤。验收应如实区分声明图检查、实际间距、扫描归属、运行中的 foreign-bar 力零记录。

布局差异应单独命名、哈希并写 manifest；8-env 重复继续使用已冻结布局，1024 baseline/candidate 必须使用相同布局实现。保留原摩擦/质量随机化，不能为匹配8env而关闭随机化。

## 5. 接触诊断确实是二次方

`CAND/runtime.py:604–611` 强制诊断 contact tensor 为 `[N,17,N,3]`，每个 physics substep 计算全部 filter 的 norm 并拆 own/foreign。源码 `REF/go2_pvcnn/sensor/semantic_contacter/semantic_global_contact_sensor.py:135–156,198–207` 为每个 body 使用全部 N 根 bar filter，并保存/复制全矩阵。

| 1024 时数组 | 大小 |
| --- | --- |
| 全身17-body contact force matrix `[1024,17,1024,3]` float32 | 213,909,504 B = 204 MiB |
| 全身 force norm `[1024,17,1024]` float32 | 71,303,168 B = 68 MiB |
| 原参考4-wheel sensor force matrix `[1024,4,1024,3]` float32 | 50,331,648 B = 48 MiB |

一个全身矩阵不是全部峰值：PhysX 返回值与 sensor buffer、vector_norm 和 index_select 临时量，以及原4轮 sensor 同时存在。仅按这些已见数组的并存估计就可达到约640 MiB，尚未计入底层 contact view、PhysX 容量、机器人、扫描器、渲染/SDK、分配器缓存。17-body contact view 对应 17,825,792 个 sensor/filter 组合，初始化与计算成本也呈二次方。

32 步容量检查只证明短时容量/启动/收尾，不能外推1600步运行时间。现有全部 force 矩阵不落盘：每子步压缩为 own `[N,17]`、foreign `[N]`，步末只记录峰值/计数。无需为了磁盘原因删减全环境接触覆盖。没有容量实测前，不建议更换接触传感器算法或将 foreign 检查抽样；那会引入独立的接触验收契约变更。

`clone_evidence.py:95–107` 还对约1024个 env/bar 查约1025个 collection query，属于另一处 CPU 二次方启动开销；RAM 足够不代表初始化会很快。

## 6. NPZ、CPU 内存和磁盘精确预算

计算方法：读取 run14 第一块全部实际 array 的 shape/dtype/nbytes；只把确有 env 轴的字段从8扩至1024，保留 `step`、`elapsed_seconds`、`ik_joint_ids`、`full_jacobian_shape` 不随N扩展。再按50块计算。未把压缩比当作保证。

| 数据 | 每32步1024-env数组字节 | 全1600步数组字节 |
| --- | --- | --- |
| samples | 29,463,040 | 1,473,152,000 |
| sync | 15,565,056 | 778,252,800 |
| 候选 samples+sync | 45,028,096 | 2,251,404,800 |
| 原控制器 baseline samples + 候选 samples+sync | — | 3,724,556,800 ≈3.47 GiB |

run14 实际 samples 压缩文件合计5,979,108B、ZIP未压缩含NPY头11,923,200B；sync 压缩2,298,884B、ZIP未压缩6,259,200B；整目录8,827,437B。1024×32若 baseline+candidate 都取样，则数组约74.49MB。metadata、JSON、ZIP头、日志以及可能的 crash/core dump 另计。

Runtime 与 bridge 每32步 flush (`runtime.py:927–942`, `sync_bridge.py:132–147`)，存储内存为 O(32N)。原 full Jacobian `[N,17,6,22]` 虽每步 CPU 深拷贝 (`runtime.py:885`)，只将它的 shape 写NPZ (`:920`)，没有把约9.2MB/step完整Jacobian乘1600写盘；这是“两个run可能20GB+”直觉估算不成立的主要边界之一。

旧 verifier `_chunks` 保存所有块再 concatenate (`sync_verdict.py:95–126`)，`evaluate` 同时加载 candidate samples、baseline samples、sync (`:462–464`)；三组主数组约3.47GiB，拼接临时副本、float64事件重放和掩码还有额外峰值，应按数GiB余量计。主机RAM不构成当前阻碍；可在最小版本保留批量读取并测 RSS，或另行按块重放，但不能改变逐env证据覆盖。

`_npz` 的每归档256MiB未压缩上限 (`sync_verdict.py:82–83`) 足够当前1024时28.10MiB samples/14.84MiB sync chunk，**不需要放宽**。形状/field/dtype/step连续性验证仍需保留。

## 7. 资源快照与容量判断

2026-09-18 20:15:17 CST 只读快照：

- 物理GPU7 UUID `GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e`，total24564MiB、used15754MiB、free8328MiB、utilization0%。
- 保留进程 PID2795762，用户hexinkun，`python sleep.py`，GPU15744MiB；未停止或发送信号。
- 主机128逻辑CPU；load average7.09/7.34/6.82。RAM约1.0TiB，available892GiB，swap0。
- 根盘与目标目录在同一volume；稍后精确 `df -B1` 可用43,084,832,768B，约40.13GiB。没有删除既有数据。

上述磁盘余量可覆盖约3.47GiB未压缩主数组及合理日志余量；运行前仍需重新检查，预留至少数倍预计写入和其他任务增长空间。GPU保留状态不允许直接认定可容纳1024：run14报告 `cuda_peak_allocated_bytes=36,599,808` 只是PyTorch allocator统计，不能代表Isaac/PhysX总显存。容量run应同时记录外部nvidia-smi的进程/设备峰值以及PyTorch峰值，并记录启动阶段、逐32步耗时、sensor采样/NPZ时间和native退出。

根据已有授权，若主代理选择调整本人占位，应由主代理重新核验PID/用户/脚本并执行、在无计算任务后恢复；本审计没有做该操作，也不建议凭静态预算先停止占位。其他用户任务不在操作范围。

## 8. 建议的有限后续顺序

1. 等待同一候选三次8×1600严格报告、native0和独立sync verdict全部通过，冻结其代码/参数/资产hash。
2. 仅准备1024布局适配及独立尺度验收器；CPU检验1024个唯一origin、row/col/filter映射、32与1600预算语义、全分母与缺证据拒绝、baseline前缀边界。原controller/core、物理门限、动作单位和native finalizer保持冻结。
3. 重新预检GPU7、CPU/RAM/磁盘，明确容量阶段的时间和峰值记录。在同一1024布局上运行批准的32步容量检查；正常收尾、native0、全部1024采样/隔离/来源/同步startup checks通过才继续。
4. 若保持物理prefix合同，取得同规模原controller baseline，再运行候选1024×1600。candidate必须1024/1024同标准通过，tail800逐环境799差分；baseline和candidate的真实随机化/场景/动作前缀都比对，不从8env推断。
5. 任一环境失败、证据缺失、进程不完整或退出异常时，保留全部1024分母和首个违约阶段；停止升级。该阶段成功仍只是固定约45mm露出窄杆的controller-assisted并行扩容，不构成policy-only越障、AME接入、大绕行或10000更新完成。

待核验项：1024普通复制的实际native内存/初始化时间、1024×32正常退出、实际紧凑场景归属/隔离、同规模随机化和物理前缀精确可重复性，以及1024×1600真实严格行为。以上均未在本只读审计中执行或声称通过。
