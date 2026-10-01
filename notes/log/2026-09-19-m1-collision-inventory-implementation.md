# M1 完整碰撞清单实施与坐标核验

2026-09-19；T306.6h.6a.1a.2c。阶段：G0-B1只读USD输入；不是包络/状态机/物理跨障验收。

## 输入与计划

Baseline：A1 f8ce0af，main829full/0skip且SPEC→QUALITY已PASS。工作branch为`codex/m1-encounter-lifecycle`，隔离worktree仍`/data/hexinkun-m1-acceptance-20260918/encounter-worktree`。本包计划e9f0669：[collision inventory](../../docs/superpowers/plans/2026-09-19-m1-collision-inventory.md)。Key Files限定新增collision_inventory.py与tests/test_collision_inventory.py。

完整USD清单需遍历robot root内instance proxies，验证所有声明刚体/所有collider的最近body归属，记录完整collider→body变换、source几何摘要及稳定path；只返回`usd_inventory_only`。mesh authored bounds仅诊断，不能用来授权CLEAR。实际query/cooked来源与包含性、逐body动态包络、obstacle registry/selection均属于后续G0-B依赖。

## 主代理独立变换用例

使用amp自带pxr CPU和in-memory USD，无Isaac/Kit/cooking/GPU。定义body世界translation=(100,200,300)；child依次AddTranslateOp(2,0,0)、AddRotateZOp(90)、AddScaleOp(2,3,4)。用XformCache.ComputeRelativeTransform(child,body)并将Gf行向量矩阵转置为列矩阵。

独立手算输入point=(1,2,3,1)，期望=(-4,2,12,1)。np.asarray(matrix).T @ point及Gf.Transform各自与同一手算expected以rtol0/atol1e-12比较，均PASS、exit0、reset=False。返回列矩阵约为：

```text
[[ 0, -3, 0, 2],
 [ 2,  0, 0, 0],
 [ 0,  0, 4, 0],
 [ 0,  0, 0, 1]]
```

90°三角函数残差约4.44e-16/6.66e-16，未修改输入消除。body世界translation未混入相对变换。独立stage默认.01/Y如实记录，不据此重缩放实际M1资产。

环境命令为amp python+PYTHONPATH指向amp已有omni.usd.libs、LD_LIBRARY_PATH其bin、CUDA_VISIBLE_DEVICES为空、PYTHONDONTWRITEBYTECODE=1；脚本通过stdin只读/内存执行，无本地写文件。实际完整函数测试由本包TDD后另记。

## 当前状态与后续

本包已完成：实现者复用已结束的有界代理（fresh spawn thread limit限制），按TDD实施；SPEC→QUALITY由其他代理独立审查，main独立真实asset/full验证。以下保留首轮及修复过程，不将旧中间状态作为当前待办。

首轮73 RED（缺模块assert，无collection/SDK fixture错误）→73 passed0.96s。实现者实际asset CPU核验17body/17shape、13proxy mesh+4Cylinder、4,544,118 points/全部relative identity，representation仍usd_inventory_only；主代理最终独立asset核验尚待修正后运行。

主代理完整读两文件后实际复现三项需修正的遗漏：①rigidBodyEnabled defaultTrue、time1=False；②collisionEnabled同样配置，二者numsamples1仍返回清单；③Robot/B0内的Extra payload卸载后root.IsLoaded仍True，默认PrimRange不返回该child，仍返回原两shape。处理方向为检查enabled静态属性，以及含instanceproxy但不预筛loaded的active/defined/nonabstract遍历，遇未加载子树直接拒绝（不能自行Load）。这些是静态完整合同缺口，已交实现者补RED→GREEN，不将73GREEN先宣称本包通过。

修正结果：enabled两项2 RED（DID NOT RAISE）→75GREEN，child payload 1 RED（DID NOT RAISE）→76GREEN。B1提交`bd841a9fa1c8a3ec7bf1d7e5d913c992d19cc056`仅新增collector/test两个文件。主代理独立focused **76 passed1.58s、exit0**，bash-n和diff-check通过。SPEC/QUALITY及完整回归尚在进行，不以定向通过代替完整门槛。

后续结果：bd841a9 main full **905 passed144.31s/exit0/0skip**（506旧+323几何+76inventory）。SPEC独立76focused+21额外真实USD断言PASS。但QUALITY发现1个Important：raw xformOpOrder引用missing、blocked或unset操作时USD跳过并返回identity，非法op未包装Tf.ErrorException；main同样实证全部四种。此full通过仅是修正前baseline，不抵消质量问题。已交实现者先RED后修正原order完整解析/静态default与ValueError，并保留合法inverse pivot/正常no-op，之后再次审查。

## 主代理实际资产复核

最终修复提交`0196f6f43e5847fde7f19f2a228b0b4b51ef70b3`。新增8例先4 failed/4 passed：missing/blocked/no-default为DID NOT RAISE，unknown opcode为未包装Tf.ErrorException。逐raw order验证属性、SDK解析、静态default和完整顺序后，84 passed1.09s。SPEC独立84passed1.04s＋10项额外真实USD检查PASS；随后QUALITY独立84passed1.08s＋ancestor/proxy共8项额外检查PASS，无未解决问题。

主代理最终全量 **913 passed140.94s，exit0、0skip**（506旧+323几何+84inventory），唯一basetemp=`/data/hexinkun-m1-acceptance-20260918/encounter-inventory-full-r1`。在该HEAD重新执行下述实际asset/来源检查，全部PASS。bash-n、git diff --check以及排除四个新文件/cache后的冻结adapter diff均PASS。GPU7仍仅原占位约15754MiB/0%，根盘4.1GiB、/data6.5TiB；未清理或迁移缓存，未启动仿真。

因此G0-B1 USD输入包通过；下一步G0-B2完整query绑定/全部碰撞盒变换及动态body pose，不能把913CPU测试称为物理包络或遇障修复验收。

在amp、CUDA不可见/无bytecode、已有USD库路径、OMP/OPENBLAS=1、TMPDIR=/data条件下，通过stdin脚本：先调用旧`audit_provenance('/home/hexinkun/m1/Go2Pvcnn')`，再Usd.Stage.Open真实overlay，用固定CONTACT_BODY_NAMES声明顺序调用新collector。断言body/collider=17，Mesh13且均proxy、Cylinder4且均非proxy，points总4,544,118，每个relative matrix精确identity，Y/.0959/.0465圆柱参数，layer dirty映射前后相同，json.dumps allow_nan=False成功，无torch/omni导入。全部PASS，exit0。

原来源guard通过，portable overlay SHA=`a637f1a384560b2059d5aaf71c928e5c2cbb4bf074dfe80b8aae9914db3aa187`。输出仍`usd_inventory_only`，单独诊断显式physical_geometry_verified=false；这不是新schema的verified字段，也不是PhysX geometry或physical crossing验收。

全回归采用A1记录的完整amp CPU命令，唯一新basetemp=`/data/hexinkun-m1-acceptance-20260918/encounter-inventory-full`。旧全部fixture/失败证据不删除或覆盖。

只读额外source核验：m1_curriculum.py仍SHA6e630a8f7be6e31d4fbebeec87d1736ab8ac1e764532fca7026ad0c51ecacb5b；m1_rsl_rl_wrapper.py仍d6c7056d422a83efb028e1053d8ce496879e14b25410d6cf14a789734c82100a，与批准spec冻结来源相同。

旧源码/SDK/资产/模型/日志不变，GPU7占位不动；没有新的8-env或1024-env仿真。已批准完整G0-C/D/E、三次新8×1600→1024×32→1024×1600、G2真实再次遇障及AME/learned/10000目标全部未被本包替代。

关联：[A1证据](2026-09-19-m1-encounter-geometry-implementation.md)、[实际USD/PhysX接口审计](2026-09-19-m1-encounter-collision-inputs.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
