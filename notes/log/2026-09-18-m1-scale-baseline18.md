# 1024×1600 reference baseline run18

Task：T306.6h.6a.1a / Task4。已完整结束，baseline公共证据门槛通过；原行为仅615/1024通过，不是strict全量验收成功。

## 最终结果（22:51复核）

- 单一PID132238完成exact1024×1600；50个32步sample chunks、6400实际sensorupdates、prepare/IK各1600。正常envclose→launcher owners detached→runtime refs released→appclose→POST_CLEANUP，实际native0。进程已不存在，GPU7回到4MiB且无compute PID。
- 外层wrapper3来自行为负例，非提前进程退出：originalpassed=false，615/1024通过，53个env有reset/termination，timeout0；measurement_issues=[]、finalization_errors=[]。原report及per-env负结果保留，未改写或缩小分母。
- failed gate次数（同env可多项）：wheelmean spread397、tilt54、height_last54、no_termination53、root_progress46、height_recovery_mean30、RAR overbar/passed/touchdown各17、FAR对应各6。
- 主agent只读ampCPU独立公共校验exit0：冻结七文件identity、实际required模块绑定和assetprovenance、解释器/UUID来源、layout/livecontract、全1024初始随机化、fullchunks/measurement/accounting、POST_CLEANUP hash/PID/run-ID/native共同门槛全部通过。输出baseline_common_passed=true、strict_acceptance_claimed=false。verifier3930483e477e0a1c6faa15c3a66dea97a20289d8e78cec9d9f4e6ca708dc79c5；reportSHA a0f590f5832fff44a6c6f2168c1d28cd85c9429435eb4416ce7de243f0c5dc0f。
- GNUwall41:32.16、maxRSS10,048,328KiB、swap0；step1600elapsed2473.439s。外部整卡2530samples峰值11338MiB；进程监测从22:15开始2128rows峰值11294MiB（不涵盖前期初始化）。Torchallocated峰值3,094,029,312bytes；output751,937,633bytes；NPZ写入57.292s、sensor采集10.815s。
- 核验后仅停止本次m1scale18_monitor和m1scale18_process_monitor两个nvidia-smi会话，其PID/命令先被重新确认。没有停止其他tmux。
- 22:53:57重查GPU7空闲/UUID、根盘14.182GiB、data6673.63GiB、冻结snapshotdiff0及不存在的新输出后，按批准计划启动一次[candidate19](2026-09-18-m1-scale-candidate19.md)。CPU审计继续区分首次跨越前负例和跨后尾段，不能假设跨后同步能解决所有baseline缺陷。

以下为运行过程记录，不覆盖上述最终结果。

2026-09-18 22:09:08 +08:00，在run17的1024×32容量与独立startup verifier通过后启动一次。重新确认GPU7空闲/正确UUID、磁盘>=12GiB、候选与task3_accepted diff-qr0、输出/外部日志不存在，并程序化检查run17全1024startup verdict/native/wrapper0。

- GPU7：`GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e`。
- Python：`/home/hexinkun/miniconda3/envs/amp/bin/python`。
- PID132238；run-ID `d1de2461-46d1-418b-887c-ce1ce20c3d24`。
- tmux `m1scale18`，独立每秒GPU采样 `m1scale18_monitor`。
- 输出：`/home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_1024x1600_18_scale_baseline`。
- stdout/GNUtime：同前缀 `.launch.log`；外部GPU采样：同前缀 `.gpu.csv`。

```bash
ulimit -c 0
/usr/bin/time -v bash /home/hexinkun/m1_debug_tools/scale1024_20260918/adapter/run.sh \
  --num-envs 1024 --steps 1600 --controller-mode reference \
  --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_1024x1600_18_scale_baseline
```

此模式仅为原reference控制器基线，不启用SyncBridge，没有sync sidecar，不宣称policy-only、同步strict或10000训练。保持同一冻结layout/scene/seed/randomization/source，与稍后的candidate做严格可比检查。无重启逻辑。

22:14:36观察：同PID132238已完成64/1600步（总elapsed289.725s），第32步elapsed243.399s，近期32步46.327s，约1.45s/step。场景创建24.143362s、物理初始化150.721877s；GPU7唯一compute任务仍为该amp进程，进程显存11096MiB。没有在32步结束/重启；它是新的完整基线，run17是明确预算为32的已完成容量测试。

除自启动即持续记录的整卡GPU CSV外，22:15:08起增加本次独有tmux `m1scale18_process_monitor`，每秒记录GPU7实际compute PID/解释器/used_gpu_memory到同前缀 `.process.csv`。其进程显存峰值只覆盖采样启动后时段，不能声称涵盖此前初始化；整卡峰值覆盖完整运行。任务结束后只停本次两个监测会话，不触碰其他tmux任务。

## 运行中只读核验与磁盘审计

22:16:58重新核对PID132238起始时间22:09:07、完整amp命令、tmux pane PID132227/time仍存活，进度160步。上一任务回合已完成Task3及真实startup并启动baseline，属于progress；当前是对真实存活进程的verified wait，不因日志观察超时重启。

随后只读加载完整chunk：run17与run18首32步28个非计时字段的dtype/shape/bytes全部相同；最新sample192..223覆盖(32,1024,3)root数组，全字段finite、terminated/timeout计数0、substeps全部4。此为运行中诊断，不代替1600步最终验收。22:21:12同PID已到352/1600步，总elapsed709.160s。

根盘资源出现外部于已审目录的占用变化，来源尚未证实：22:02 df-h显示可用25GiB；22:18:17精确18,182,676,480bytes（16.934GiB），22:19:21为17,344,593,920bytes（16.153GiB），64秒下降0.781GiB，但baseline同期仅增长约17MiB。只读审计发现/tmp/pytest-of-hexinkun总3.323GiB且22:02后无新修改，candidate1.56MiB且无新修改；限定Isaac缓存/日志ov3.59MiB、warp160KiB、.nv216KiB、Omniverse logs总327.86MiB，不能解释新增占用。没有扩大到其他用户目录、删除任何缓存/模型/证据或停止其他任务。

22:21:12再测可用17,308,504,064bytes，随后约两分钟仅下降约34MiB，不能把前一突发下降速率假设为持续线性消耗。baseline剩余数据保守估算不足0.75GiB，当前仍超过启动门槛12GiB，继续监测；若继续明显下降，在扩大后续运行前重新评估。/data为独立7TiB文件系统、可用约6.5TiB，/data/hexinkun不存在，目前仅检查挂载/目录权限，未迁移或创建任何文件。保留pytest-227最终工件和全部真实run，不把未知临时目录当作可随意删除对象。

后续磁盘继续下降：22:23:40为15.563GiB、22:26:05为13.358GiB、22:28:14为12.058GiB。同PID持续推进448→544→640步，未提前退出/重启。额外只读统计：整个M1 reference validation约485MiB、run_logs约603MiB、m1_rl/logs约1GiB、m1_debug_tools约23MiB，不能解释或充分缓解全盘下降。已向用户发异步问题，请释放根分区或指定确切可迁移的大目录；未经确认不处理其他数据/任务。此为新出现的外部存储风险，不得误称训练逻辑卡住或已查明根因。

独立只读存储路径审计确认：future candidate19仅改变--output位置，不进入configuration/provenance/初始随机化/scene/layout的配对数据，native/PID/run-ID/内容hash仍在所传目录验证。源码、reference和cwd不搬，预算和控制/阈值不变。当前parser/verifier仅支持既定8/1024×32/1600，不由路径改变获得10000训练能力。

为后续新产物准备 `/data/hexinkun-m1-acceptance-20260918`，新建前确认/data真实挂载、可写且目标不存在；实际创建为hexinkun:0700，写入878byte storage-origin.txt成功。没有迁移当前baseline或任何旧文件。/data独立可用约6.5TiB；未把配额查询无输出等同于无限配额。未来run19最终输出子目录必须不存在，由run.sh自行创建，外部launch/GPU/process日志也放该私有父目录。原根盘notes保留路径映射。此措施减少未来本任务根盘写入，但不解决来源未知的根盘占用增长，也不允许在baseline公共验收失败时启动candidate。

22:46:04同PID已到1408/1600，总elapsed2203.200s，GPU进程11294MiB；未重启。根盘降至11.675GiB后，仅归档本任务已结束的pytest-227 CPU fixture：全部2816文件校验一致、22链接实际可解析，旧路径保留为symlink；移除唯一已校验重复副本后，22:46:29 root可用15,345,942,528bytes（约14.29GiB）。全部证据保留/data，未动真实run或旧模型。详见[存储核验](2026-09-18-m1-scale-fixture-storage.md)。外部占用增长原因仍未解决，后续启动仍要重查。

## 完成后、candidate启动前必须检查

1. actual native0、完整1600步、50个32步sample chunks、6400sensorupdates、每步原prepare/IK各一次、正常post-cleanup/run-ID/PID/hash绑定。
2. 独立verifier已有 `_completion(..., RunBudget(1024,1600), baseline=True)` 和 `_sample_accounting(..., baseline=True)` 校验共同运行/测量/scanner/source/scene、全1024记录及首次episode记账。wrapper3仅可来自行为负例，不能来自共同测量失败。保留所有原始per-env负结果。
3. 用实际reference bindings/provenance和固定七文件identity，检查mode=reference且无diagnostic_candidate；调用 `_scale_layout`、`_live_contract`，检查完整1024初始随机化字段/float32/shapes/origins。实际绑定边界用 `runtime.validate_source_bindings(..., required=REQUIRED_MODULES)`、`audit_provenance(REFERENCE)` 和amp解释器证据；只读CPU，不初始化torch/simulator。
4. 这只能输出 `baseline_common_passed`，不能输出 strict accepted。candidate与baseline的完整配置/源/场景/实际初始随机化bitwise、激活前全部物理动作prefix、独立状态/控制replay和strict全1024门槛仍必须等run19配对验证。

独立read-only子代理已用当前冻结verifier，在实际完整synthetic fixture的baseline运行上述共同helper（6.5s）：native0、wrapper3、50chunks、原passed_envs1023、原passed=false，baseline_common_passed=true/strict_acceptance_claimed=false；没有修改原报告。真实来源附加检查不能用synthetic伪造：synthetic run_start.reference/单模块bindings与真实reference不符，完整实际来源检查按预期拒绝。最终真实baseline必须自行通过这些检查。

占位状态：仅原PID2795762已于run17前核验后暂停，脚本/解释器保留。仍有run18计算任务时不恢复。待本任务不再计算且GPU7无其他用户任务，再用 `/home/hexinkun/miniconda3/envs/m1/bin/python /home/hexinkun/sleep.py`，cwd `/home/hexinkun`、CUDA_VISIBLE_DEVICES=7、CONDA_PREFIX=/home/hexinkun/miniconda3/envs/m1、CONDA_DEFAULT_ENV=m1 恢复15GiB占位。不得在未核验新GPU状态时盲目启动。
