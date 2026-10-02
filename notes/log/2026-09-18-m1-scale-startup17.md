# 1024×32 容量实测 run17

Task：T306.6h.6a.1a / Task4。2026-09-18，物理 GPU7，amp 环境。结论：**startup容量门槛通过；不是strict跨障或10000训练通过**。

## 进入条件

Task1/2/3 CPU 与独立 SPEC/quality 均通过；Task3 full506passed146.22s、主代理修复后新旧verifier102passed78.81s（含全1024×1600合成数据回放）。源码已保存到 `scale1024_20260918/task3_accepted/adapter`，启动前与工作候选 `diff -qr` 无差异。

运行源码 `/home/hexinkun/m1_debug_tools/scale1024_20260918/adapter`；解释器 `/home/hexinkun/miniconda3/envs/amp/bin/python`。保持原冻结控制器、桥接、metrics、native finalizer、run.sh，未改 SDK 或 reference。

## GPU 占位核验与暂停

22:02:05 +08:00，GPU7 UUID=`GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e`，唯一 compute PID2795762，15744MiB。再次逐项核验 owner=hexinkun、start=Fri Sep18 14:42:34 2026、cwd=/home/hexinkun、cmd=`python sleep.py`、exe=`/home/hexinkun/miniconda3/envs/m1/bin/python3.10`，脚本SHA256=`8a487ab7afb27364049eb89edf1ba2104d6dcb84eb1157cfa417e2b9a4b683c0`，CUDA_VISIBLE_DEVICES=7、CONDA_PREFIX=/home/hexinkun/miniconda3/envs/m1、CONDA_DEFAULT_ENV=m1。

仅向该已核实的本人15GiB占位进程发 TERM；未触碰其他GPU上的其他用户任务。再次确认该 /proc/PID 消失且GPU7无compute进程后才启动容量测试。占位脚本保留不改，任务无计算进程且GPU7安全空闲时按原解释器/脚本/环境恢复。占位用m1不代表此次验证用m1。

启动前根盘可用25GiB（门槛12GiB），RAM available885GiB，swap0。输出目录及两个外部日志文件均确认不存在，未覆盖历史证据。

## 单次启动

22:02:41 +08:00，tmux `m1scale17`；独立只读GPU采样会话 `m1scale17_monitor`，每秒记录GPU7显存/利用率/功耗。无重试或自动重启逻辑，core dump关闭。

```bash
ulimit -c 0
/usr/bin/time -v bash /home/hexinkun/m1_debug_tools/scale1024_20260918/adapter/run.sh \
  --num-envs 1024 --steps 32 \
  --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_1024x32_17_scale_startup
```

外部 stdout/time：`/home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_1024x32_17_scale_startup.launch.log`。

外部 GPU CSV：同前缀 `.gpu.csv`。run.sh 固定 amp、物理cuda:7、headless、multiGPUfalse、path-stat-cacheoff，并记录实际 native code 后运行外层 finalizer。

验收尚待：exact32、1024完整首回合、128sensorupdates、native/wrapper0、正常收尾、独立 startup verifier；不需要baseline、不宣称跨越/同步strict或训练10000完成。若失败，保留全量现场并停止后续baseline/candidate升级。

## 实际完成证据

PID105919 单进程运行完整32步，全部1024环境 active_sample_count=32、reset_count=0，prepare/IK各32，physical_sensor_updates=128，samples/sync各1个32-step chunk。source_bindings_valid=true、measurement_issues=[]。

日志依次出现 ENV_CLOSED、LAUNCHER_OWNERS_DETACHED、RUNTIME_REFS_RELEASED、APP_CLOSED、POST_CLEANUP，随后外层观测真实 `NATIVE_EXIT pid=105919 code=0`，wrapper0。`report.completed=true,startup_passed=true,passed=false`。进程结束后GPU7回到4MiB，无compute任务；只停止本次 `m1scale17_monitor` 采样会话。

主代理执行固定verifier CLI显式 `--num-envs 1024 --steps 32`，无baseline：exit0、accepted=true、sync_checks_passed=true、errors=[]、validation_kind=startup、strict_behavior_passed=false、per_env1024。独立回放wall1.24s、RSS141,956KiB。

资源：场景创建24.381753s、物理启动158.320811s、到第32步总258.814858s；含正常清理的总wall4:38.75。原生进程树GNU time maxRSS10,026,248KiB、swap0；每秒外部GPU采样峰值**11148MiB**（315样本），Torch peak allocated3,094,029,312bytes，不能拿Torch数代替整卡峰值。证据目录35,501,585bytes（verdict落盘后计）。

容量通过后于22:09:08启动独立reference baseline run18。占位暂不恢复，以免与马上开始的1024物理任务争用；没有自动重启run17，也没有改阈值/分母/SDK。
