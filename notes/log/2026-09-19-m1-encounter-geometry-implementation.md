# M1 encounter 几何基础包实施

2026-09-19；T306.6h.6a.1a.2c。用户已明确“按规格实施”，此前书面审阅等待解除；本日志持续记录真实实施证据，不把首包当作状态机/物理/学习完成。

## 范围、输入和工作区

批准规格原commit e25e805，正文不变，仅勾选批准状态。首包[实施计划](../../docs/superpowers/plans/2026-09-19-m1-encounter-geometry.md)：不可变EncounterKey/Frame、canonical投影、已提供碰撞support点的包络、strict离开/前方谓词、前轴/必需轮分离的接近检查。后续真实碰撞采集/provider、coordinator、reference/sync hook、证据重放、G1/G2仍为必需依赖，未实现时不能把任何bool当运行时允许跨越。

隔离sparse worktree `/data/hexinkun-m1-acceptance-20260918/encounter-worktree`，branch `codex/m1-encounter-lifecycle`，原HEAD e25e805。未改用户主工作树源码；Task3冻结副本逐字节复制到此新worktree的tools/m1_reference_validation，diff-rq除cache无差异。260c8e4只记录8个既有scale差异快照，非新修复/正式推广；19ba31d提交首包计划。

## Baseline检查

- 初次sparse checkout --no-checkout未物化文件，复制报不存在；用新空worktree的read-tree -mu HEAD物化后再次复制，无删除或覆盖用户文件。
- 首次裸amp CPU测试在collection失败：ModuleNotFoundError pxr。原因是命令未包含已有USD库路径；未安装/升级环境，没有跳过测试。
- 对照此前scale验证日志补上PYTHONPATH与LD_LIBRARY_PATH指向amp自带omni.usd.libs；完整基线 **506 passed in 141.11s，exit0，0skip**。bash -n通过。CUDA_VISIBLE_DEVICES为空，未启动Isaac。
- 大fixture使用全新 `/data/hexinkun-m1-acceptance-20260918/encounter-baseline-pytest-20260919b`，旧failed collection的原basetemp保留，不让pytest清旧证据。

复现命令见首包计划Baseline段。Baseline Ref=260c8e4，计划Ref=19ba31d，Last Feature/Physical Ref仍为formal646f486及原历史run，不能被文档commit覆盖。

## 实施进度

先由独立只读审计给测试向量，再使用TDD实现指定两个新文件。新建子代理遇thread limit，复用已结束的几何审计代理执行有界实施任务；仍由其他代理承担独立规格与质量审查，主代理独立复核。GPU7占位不动。

当前状态：A1几何基础包完成。1cb83bc新增两个文件，f8ce0af修复独立SPEC审查发现的合法混合Integral轮索引被NumPy promote为float64误拒。原IK锚点/控制/奖励/阈值/分母全部不变。无新仿真或训练，不宣称再次抬腿或10000迭代已通过。

## RED/GREEN与独立验证

- 实现者：missing-module assertion RED；descriptor120 RED→120GREEN；projection新增43RED→163GREEN；extent/strict/approach新增134RED；mixed bool/prim-path补充后154RED+163GREEN→317GREEN。
- 主代理修复前focused317 passed1.51s；完整旧506+新317=823 passed140.70s，exit0、0skip。bash-n run.sh通过；与Task3冻结adapter diff-rq排除cache/两个新文件完全相同。
- SPEC独立审查复现 `[np.uint64(0), np.int64(2)]` / `[np.uint64(0), 2]` 被拒；主代理amp NumPy1.26.4同样复现。新增6合法mixed signed/unsigned list/tuple用例先6RED，最小修正后323GREEN，不放行bool/float/object ndarray。
- SPEC复审PASS（独立7合法/27非法＋冻结/使用核验）；其后独立QUALITY PASS（323 passed1.60s，额外斜向/非本机字节序/noncontiguous/无Torch或Isaac导入检查）。minor：canonical/projected_extent存在重复验证/复制，正确性无影响；后续provider不应把4.5M source points逐step输入该函数，此minor不阻塞。
- 主代理最终focused323 passed1.55s；完整回归 **829 passed in140.27s，exit0，0skip**。独立完整测试包含全部旧sync/metrics，未只引用代理输出。新版全量basetemp为`/data/hexinkun-m1-acceptance-20260918/encounter-geometry-full-r1`；修复前full和旧baseline均保留。

验证命令为首包Baseline完整命令加`TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp`并替换全新basetemp；focused同环境仅传tests/test_encounter_geometry.py。git范围88ba05f..f8ce0af仅两个新文件，原source未改变。

## 后续与资源

进入G0-B完整collision输入/provider。只读核验表明source mesh bounds不保证覆盖cooked shape，必须绑定实际PhysX query/完整shape清单；当前几何函数不具整机CLEAR授权。详见[碰撞输入](2026-09-19-m1-encounter-collision-inputs.md)。G0-B/C/D/E、新三次8×1600、1024×32/1600、G2实际再次跨越、AME/learned/10000全部继续。

根盘本次一度82MiB，之后自行恢复2–3GiB；未查明增长原因，未清理或移动文件。已询问是否备份校验后仅迁移用户pip缓存，尚未得到该权限，不执行。所有新大fixture在/data，GPU7占位不动。旧USD/SDK、模型、日志保持。

Candidate/Last Verified Ref（仅A1 CPU）=f8ce0afb02b6eea8fe260e20b41e11d4ecda8259；Last Physical Ref仍formal646f486及历史run，不能以本包替代。

相关：[规格](../../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md)、[容量约束](2026-09-19-m1-encounter-evidence-capacity.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。dashboard、branch memory和log index按本记录同步；human/ai现行行为合同未改。
