# M1 encounter 证据容量只读核验

时间：2026-09-19 10:54–11:02 CST。阶段：sensor→原始记录→独立验收的资源前置检查。节点：T306.6h.6a.1a.2b，依赖父节点具体规格审阅，不是新控制实现或物理验收。

## 输入与方法

Baseline Ref：formal646f486 / scale Task3 frozen；当前HEAD为设计提交e25e805。Candidate Ref：无新实现，run19仍为原失败样本。Key Files：原reference semantic_ray_caster.py、SDK grid_pattern、scale adapter runtime.py/sync_bridge.py/sync_verdict.py、run18 configuration.json与NPZ、run19 NPZ。

主代理读本地安装源码与run18 before/after配置，用amp Python在CPU执行同样torch.arange（CUDA_VISIBLE_DEVICES为空、PYTHONDONTWRITEBYTECODE=1、cuda_initialized=False），得到每轴151、每env22801条ray。未导入Isaac或开启仿真。并行只读审计用stdlib ZIP目录/NPY headers统计，主代理独立复核首末块字段及全部50/8/8块ZIP字节总量；未加载完整数组、未运行新回归测试。

## 已有数据实测

| 证据 | 块数/实际步数 | ZIP未压缩bytes（含NPY头） | NPZ文件bytes |
| --- | --- | ---: | ---: |
| run18 samples | 50 / 1600 | 1,473,337,600 | 730,912,958 |
| run19 samples | 8 / 247 | 227,447,536 | 119,748,011 |
| run19 sync | 8 / 247 | 120,169,400 | 25,370,366 |

run18首、末samples块均29字段，未压缩29,466,752B，压缩文件分别12,431,968/14,436,663B。root_state_w=[32,1024,13] float32，wheel_pos=[32,1024,4,3] float32；scanner_own_counts/foreign_counts为[32,1024] int64。旧日志没有17-body pose、raw hits、semantic map。run19尾块只有23步，不能冒充完整1600。当前schema完整baseline+candidate+sync理论raw约3.469GiB，这不是新增证据后的预算。

## 扫描器与新增证据预算

实际配置resolution=.01、size=[1.5,1.5]，对应151×151=22801；策略16×16是后续观测尺寸，不是raw scanner分辨率。max_update_envs_per_call=512不减少最终1024env的ray总数。源码语义映射输出float32，invalid face映射为semantic0；因此semantic0不能单独证明有效地面命中，也不能将旧int64计数字段误当raw map类型。

下列是**每步保存全部22801条ray的world xyz float32**的容量推算，不是规格强制该编码，更不是实测新文件大小：

- 1024env单步：280,178,688B，267.199MiB。
- 32步：8,965,718,016B，8.350GiB。
- 1600步：448,285,900,800B，417.499GiB；不含语义、validity、IDs、旧字段或文件头。
- 若另存17body×7float32 pose：32步15,597,568B/14.875MiB；1600步779,878,400B/743.75MiB。

现规格要求selected rays/hit关联及可重建输入，未要求全部ray密集坐标逐步落盘。后续编码仍须支持独立重建全部env/step的候选与歧义、合法未命中和unknown/foreign判断，不能只录成功点或减验收分母。

## 已证限制与开放实现条件

1. sync_verdict.py:99–109 的256MiB限制针对每NPZ中ZIP entry的未压缩file_size总和；压缩比无法绕过。密集全ray xyz单步就超过该上限，不能直接加到旧32步samples块。
2. _chunks:166–169累积全run再concatenate；evaluate同时持有baseline/candidate/sync，replay还建float64副本、events、masks。旧流程不是按块有界RAM。新增大证据应独立版本化、按字节有界分片并流式重放；具体格式需在审阅后的实施计划中明确，不在本审计实现。
3. runtime.py:1007–1009明确ray miss可以合法为inf，目前仅即时检查后保存计数。旧_npz所有字段isfinite会拒绝这些合法miss。新记录必须显式区分validity和有限坐标，保留真实无效状态；不可把miss静默改成有效零点或把所有inf当物理爆炸。
4. runtime snapshot保留输入dtype，但clone/CPU/np.copy与writer np.stack会产生并存副本。新容量必须计峰值，不只计压缩后大小。

这不授权降低传感器分辨率、改控制/奖励、删除保护、抽样环境或放宽验收。原规格e25e805未修改。

## 磁盘与保留核验

11:02:03根分区available=3,764,977,664B（约3.51GiB，df显示100%）；/data available=7,116,289,691,648B。根盘增长原因未查明，不归因于Isaac或其他用户任务。只读du显示本任务reference_validation约973MB、scale诊断约1.63MB、/data本任务目录约2.97GB；没有删除、移动或清理文件。后续启动须把本任务新证据/临时大文件纳入/data容量预检，不能依赖根盘剩余空间。

新鲜diff -rq（排除Python/pytest cache）确认scale adapter与task3_accepted一致。GPU7 UUID尾部fd66e仅原占位PID351307/hexinkun/python sleep.py，启动Sep18 23:05:13，15744MiB；未暂停或启动计算。已有run/模型、SDK、原参考、正式控制器均未改。

## 结论与下一步

只读资源审计完成；新增T306.6h.6a.1a.2b“有界、可独立重建的encounter证据”子项，dashboard/T306/log index同步。现行观测/动作/奖励合同没有改变，不将此结果写为已上线能力。具体规格用户审阅仍待完成，再writing-plans/TDD；三次新8×1600→1024×32→1024×1600以及G2真实再次跨越、AME/policy/10000门槛不变且未完成。

关联：[规格](../../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md)、[设计审阅](2026-09-19-m1-encounter-design-review.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
