# M1 live cooked 顶点现场与 query 边界舍入负例

2026-09-19；T306.6h.6a.1a.2c / G0-B2。结果：来源、读取和状态守卫证据有效，raw query box精确包含判据FAIL。本轮是有实际新证据的progress，完整目标保持ACTIVE，不标总完成或权限阻塞。

## 前置和唯一执行

Baseline Ref=6b1b565；Feature Ref=06f3526；溢出修复/Last Verified Code Ref=c02bde0；实际启动HEAD=b0d4270086c9f906cbbc8eec28d5c67a27111954，worktree clean。主代理修后完整1785passed/178.11s/exit0/0skip，bash-n/diff-check及SPEC→QUALITY通过；独立verifier17self-tests主代理重跑PASS。详见[代码验证](2026-09-19-m1-live-cooked-evidence-implementation.md)。

17:02:34 fresh资源：根XFS 944G/447Gused/497Gfree/48%；/data7T/667Gused/6.4Tfree。管理员500GiB扩容已成功，不移动缓存。GPU7 UUID GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e，15754MiBused/8328MiBfree，仅本人原占位351307，hexinkun、Sep18 23:05:13、cwd/home/hexinkun、CUDA_VISIBLE_DEVICES=7、15744MiB。原占位全程保留，其他卡无compute进程。

只启动以下一次，TMPDIR位于/data、ulimit -c 0，新目录与console均先检查不存在：

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree
export TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp
ulimit -c 0
bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 \
  --collision-query-probe --collision-cooked-probe \
  --output /data/hexinkun-m1-acceptance-20260918/cooked-live-20260919-1703
```

实际执行以pipefail/tee保存同名.console.log。exec session23349持续跟踪到terminal，没有因观察超时重启；native PID3824745，run_id=d93a9d00-6b98-48d2-b7aa-5540eea22060。amp/bin/python、cuda:7；原参考/home/hexinkun/m1/Go2Pvcnn；SDK、驱动、奖励、阈值、reference与dirty主源码未改。

## 实际获取与失败位置

104个Mesh完整instance路径全部返回1个hull，共3664个顶点；available104、unavailable0、failed mesh0。另32个Cylinder保持native_query_only，不调用convex getter、不制造顶点。原始数组、dtype/shape/num_vertices和逐hull极值/违反量完整保存。

136requests/responses与408accepted callbacks身份完全对应。逐顶点精确复算64hulls inside、40outside：8个BASE_LINK下侧z外溢7.450580596923828e-9m；32个ABAD的y边界外溢3.725290298461914e-9m。所有自报极值/违反量/包含bool与独立逐点复算一致。没有加epsilon、改变box、旋转或缩放到“通过”，原始失败仍保留。

诊断在RuntimeSink创建和预算循环开始前抛出明确Python RuntimeError，所以received_steps=POST_CLEANUP.steps=0；没有samples_0000_0031.npz是预期负例，不是文件丢失。ENV_CLOSED→LAUNCHER_OWNERS_DETACHED→RUNTIME_REFS_RELEASED→APP_CLOSED→POST_CLEANUP完整；native1/wrapper2，PID已不存在。completed/startup_passed=false正确；本次没有完成32预算步、不是G1重复或PPO，不与上次query-only正例拼接。

POST_CLEANUP中的runID/PID及candidate SHA c27a5edc77861ccdd7819df841fda81969960ba6a1967b3b2650e1458a207b26对应实际candidate_report。没有native crash marker；这是严格诊断判据主动错误退出，不是之前的SDK收尾原生崩溃。

## 状态与来源守卫

主代理与独立审查重新读取真实JSON/NPZ，不只信成功标志：

- source/settings fingerprints重算一致；stage/path/body/collider映射和136/408覆盖正确。
- 23组before/after的key/dtype/shape/C-order原始bytes全同；46份metadata SHA全部重算匹配。
- query_state=COMPLETE；额外physics count=0、dt_sum=0、pump_count=0、changed_fields=[]。
- callback已移除；lease/query CLOSED、pending_unsubscriptions=0、cleanup_errors=[]。
- 原始cooked负例全部保留。当前严格verifier保持FAIL/exit1，不改成PASS；其成功schema假设产生的missing gpu/samples附加错误不代表JSON/NPZ损坏。
- 结束后GPU7仅原占位351307/15744MiB，不需另启占位；没有本任务训练或仿真进程残留。

独立负证据审查结论：raw containment FAIL，来源、守卫、退出链有效。不是104hulls获得就等于geometry_verified。

## 数值机制的独立复现

主代理analyze_live_rounding.py以保存的实际hull顶点min/max计算float32 center=(lo+hi)*.5、extent=(hi-lo)*.5，再算center±extent。全部624/624 query边界分量精确相等；原始顶点与query数字均可无损表示为float32。40个向内分量恰好各差一个向外float32 nextafter。

独立审查用struct在每步强制float32舍入，而非复用主代理NumPy表达式，也复现624/624和40个单ULP差异。只据此说明“全部差异可由center/extent float32重建复现”；未读取native实现，不能声称直接证明内部代码。没有在当前产物里生成外扩框或成功判定。

证据根/data/hexinkun-m1-acceptance-20260918：run目录cooked-live-20260919-1703、同名.console.log、同名前缀-rounding.json与-verification.json；只读脚本analyze_live_rounding_20260919.py、verify_cooked_live_20260919.py。原始产物不变。

## 新子问题与下一步

新建T306.6h.6a.1a.2c.1（G0-B2子节点）：query-bound向内舍入。读取可用性已经有真实证据，无需盲目重复本次失败启动。下一步直接从这些source-bound证据建立显式、可追溯、只向外保守的几何包络；raw query与raw hull永久分别保留，不能修改它们来制造本诊断通过。需要CPU数学与转换验证，包含native Cylinder，再接provider/registry/coordinator。

这不是请求改SDK，也不是放宽physical clearance。新三次8×1600→1024×32→1024×1600、G2同物体真实返回、AME正常退出/命名物理动作、policy-only小跨越和大绕行、单进程10000actual PPO均未完成。现无10000训练进程。

主todo/T306/logindex与本日志对齐；阶段AI/human接口未改变。本包默认关闭，不给正常训练入口增加本次诊断失败条件。[计划](../../docs/superpowers/plans/2026-09-19-m1-live-cooked-evidence.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
