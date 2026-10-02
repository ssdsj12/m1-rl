# M1 同 stage live cooked 碰撞证据实施

2026-09-19，T306.6h.6a.1a.2c / G0-B2。完整目标 ACTIVE；本包仅补齐query之后可得的cooked顶点证据，不是跨障/10000验收。

## 范围与基线

Baseline Ref=6b1b565，Last Feature Commit=92278b7，Last Verified Code Ref=b16168b。计划ff0cc39，现隔离branch codex/m1-encounter-lifecycle。实现只允许新增collision_cooked_evidence.py及测试，修改query_initialization_probe.py及测试、runtime.py/run.py，共六文件。主源码dirty工作树、SDK/驱动/原参考/旧run/模型不动；run.sh和现有lease不改。

上一唯一现场query-init-live-20260919-1618已经136query/408callback、23组before-after字节、零额外physics、8×32/128sensor、normal close和native/wrapper0闭合，不重跑该基础审计。管理员扩容后root约497GiB可用；未迁移pip缓存。

## CPU baseline

从隔离adapter目录，使用既有amp USD/Physx schema路径、CUDA_VISIBLE_DEVICES空、PYTHONDONTWRITEBYTECODE=1、PYTEST_DISABLE_PLUGIN_AUTOLOAD=1、OMP/OPENBLAS线程1、TMPDIR在/data，执行：

```bash
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short \
  -p no:cacheprovider tests/test_query_initialization_probe.py \
  --basetemp=/data/hexinkun-m1-acceptance-20260918/cooked-evidence-baseline
```

实际需包含[实施计划](../../docs/superpowers/plans/2026-09-19-m1-live-cooked-evidence.md)中的完整环境前缀；此处Python行不是单独可替代USD配置的命令。真实输出122 passed in17.56s/exit0。旧联合194不是本单文件计数。没有启动Kit/CUDA。

## API证据与决定

主代理与独立审计读取安装omni.physx106.5.7的_physx.pyi与demo/tests。旧get_nb_convex_mesh_data(path)/get_convex_mesh_data(path,index)仅声明simulation-running；旧接口顶点元素类、instance proxy、非单位scale与非法path返回语义没有完整保证。官方旧示例以source mesh LocalToWorld绘制，支持mesh-local解释，不足以证明全部scale/instance情形。

本包使用已绑定的完整实际collider instance路径，在同一live lease finalize之后、最终source poll和23raw after之前读取。无force_load、release、request新cook或pump。count0单独记录unavailable，不当作无碰撞；Native Cylinder不调用convex getter。全部可用hull顶点立即深拷贝，严格校验数值类型/维数/有限值，并保存每轴实际超界量；不加容差、不移动查询盒、不重乘local_rot。

只验证vertex-box包含，不声称mesh拓扑或内部PxShape指针身份；不因公开API缺少该指针而新增超出原规格的要求。弃用警告保留，不能自动切换新request冒充当前物理形状。

## 实施与验收状态

- 六文件实现提交06f35269037db6bc14b88955779a174669469996，711insertions/4deletions。真实USD/lease/query fixture；仅SDK getter边界用double。RED1缺模块1failed；RED2同缺模块73failed；GREEN1为73passed/1.21s；RED3接线及计数/错误文本23failed、193passed；GREEN2为216passed/27.48s。日志cooked-impl-{red1,red2,green1,red3,green2}-20260919.log存于本/data任务根，主代理已直接查看RED1/GREEN1/GREEN2尾部。
- 主代理发现并在RED3中补回归：第二hull读取失败时不得计为available mesh，但保留第一hull原始顶点/计数；outside errors保留path/index以及lower/upper实际数值。并未新增容差或修饰raw证据。
- 主代理CPU保存产物适配核验：读取上次现场collision_query_initialization.json的真实artifact，以返回0的get_count替身检查完整目标，得到136records/104mesh/32native、104unavailable/0vertices/0errors。只证明实际schema兼容，不是live getter或几何通过。无SDK/physics调用，未更改原产物。
- 主代理已验证run.sh bash-n和git diff --check通过，严格六文件代码提交；完整tests新basetemp=cooked-evidence-main-full完成：1781passed/177.59s/exit0/0skip。其运行期间源码冻结至实际terminal，之后才允许P2修复，不能将此baseline full冒称修后验证。
- 独立SPEC发现唯一P2：先maximum(...,0)再检查finite会裁掉负向subtraction overflow，违反“任何非finite差值拒绝”。以float64 max=m、query[-m]*3..[m]*3、vertex[m/2,0,0]实际复现原collector captured；无效raw lower第一项为-inf。修复c02bde0仅两文件26insertions/2deletions，先查两侧raw差值再clip；正/负方向四例RED为2failed/2passed，修后focused220passed/28.02s/exit0，主代理已读实际日志。
- 同审查者复核SPEC PASS：原反例现在公共collector failed/104nonfinite errors/0available，native32保留；独立四例4passed/.49s，无新规格缺口。随后QUALITY PASS，无Critical/Important。主代理修后full独立cooked-evidence-main-full-v2完成1785passed/178.11s/exit0/0skip，bash-n/diff-check通过；代码冻结c02bde0。
- 独立只读现场verifier已交付verify_cooked_live.py，从真实JSON/NPZ计算，不导入collector/SDK/Torch作oracle。主代理重新执行17项自测PASS/exit0，包含dtype/shape/count、1ULP、负向溢出、全unavailable、identity/guard篡改；只创建并清理自己的新temporary目录。远端脚本verify_cooked_live_20260919.py在本/data任务根，旧真实run读取仅应缺少cooked字段，不能冒充新的成功。
- 全部门槛通过后fresh资源检查，唯一现场已执行并跟踪session23349到terminal：读取104hulls/3664vertices；40hulls越raw query边界1float32 ULP，诊断主动failed/0budgetsteps，normal cleanup/native1/wrapper2，未重启。23raw/136query来源守卫有效；这不是startup通过。完整见[现场负证据及数值根因](2026-09-19-m1-live-cooked-evidence.md)。

本包真实cooked读取已经执行，严格包含门槛未通过，新增.2c.1保守边界子项；没有开始10000训练。后续source-bound provider/registry/coordinator、三次新8×1600→1024×32→1024×1600、G2真实重遇、AME/named-actions、policy-only小跨越/大绕行及单进程10000仍未完成。阶段AI/human接口未改变，本包是独立诊断入口。

关联：[T306](../todo/T306-m1-ame-long-train-stability.md)、[上次现场](2026-09-19-m1-collision-query-live.md)、[具体计划](../../docs/superpowers/plans/2026-09-19-m1-live-cooked-evidence.md)。
