# M1 query 初始化现场验证与真实边界核对

2026-09-19，T306.6h.6a.1a.2c / G0-B2。上一目标轮为progress：管理员实际扩容且fresh SSH确认空间恢复，改变下一可执行动作；不是重复状态，也不是verified wait。完整目标保持ACTIVE，不标总验收完成。

## 前置与资源

管理员按用户确认将nvme1n1的新500GiB分区加入ubuntu-vg/root XFS；fresh根卷944G、已用447G、可用498G、48%，/data仍7T/约6.4T可用。无需再等待pip缓存迁移授权，也没有迁移/删除缓存。

独立资源核验16:17+08：GPU7 UUID GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e，15754MiB used/8328MiB free，仅本人原占位PID351307（hexinkun/python sleep.py，Sep18 23:05:13，cwd/home/hexinkun，CUDA_VISIBLE_DEVICES=7，15744MiB）。GPU0–6无compute PID；无现存训练/Kit/诊断冲突。既往8env约4.9GiB，因此保留占位。未改SDK/驱动/原参考/主工作区源码/旧日志/模型。

隔离linked worktree branch codex/m1-encounter-lifecycle，启动HEAD=b16168b121963bad2637789dba2be0c10cfc9bfc且clean；git-dir与common-dir不同，非submodule，不另建worktree。实际query模块SHA=e82b130ac9b40ec454589354a2ed24e9fc2746163605c338ee63f783007742e6，test SHA=35063dfde6bed50062c7575532091ba33e0f670ee4ed1c51880fea4ade1157ab；与既有1687full/0skip＋SPEC→QUALITY门槛一致，没有重复该基础审计。

## 唯一现场过程

远端输出根为/data/hexinkun-m1-acceptance-20260918，唯一run目录query-init-live-20260919-1618，旁query-init-live-20260919-1618.console.log。运行时TMPDIR=encounter-temp、ulimit -c 0；未装包或清缓存。

```bash
cd /data/hexinkun-m1-acceptance-20260918/encounter-worktree
export TMPDIR=/data/hexinkun-m1-acceptance-20260918/encounter-temp
ulimit -c 0
bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 \
  --collision-query-probe \
  --output /data/hexinkun-m1-acceptance-20260918/query-init-live-20260919-1618
```

本次实际命令另以tee保存console，pipefail保留退出状态。外部exec session33380，native PID3669456，run_id=db7756fe-bea7-4b95-a7a7-7d5b4b728e7a。启动一次，持续poll同一handle至实际exit0；未因观察timeout重启，无resume或轮次拼接。

实际runtime为amp/bin/python、cuda:7、指定GPU7 UUID；CUDA_VISIBLE_DEVICES unset，multiGpu disabled、pathStatCache disabled、fast_shutdown=False、replicate_physics=False。按原单杆场景exposed_height=0.045m，不冒称实际60mm暴露难度。此runner用参考动作，不是policy-only或PPO。

原生末尾完整出现ENV_CLOSED、LAUNCHER_OWNERS_DETACHED、RUNTIME_REFS_RELEASED、APP_CLOSED、POST_CLEANUP、NATIVE_EXIT code0、WRAPPER_RETURN code0。最终PS无3669456；GPU7回到仅原占位15754MiB used/8328MiB free，无需另行恢复占位。

## 主代理独立验收

从真实JSON/NPZ重算，而非信任COMPLETE日志。可复现脚本verify_live_query.py保存于本轮evidence目录；使用amp Python CPU读取原始run，退出0。

- query schema=m1_collision_query_initialization_v1；representation=initialization_diagnostic_only；result=complete_unchanged；errors/changed_fields均空。
- 136个body请求与136个响应，对应8env×17body；query COMPLETE、query_protocol_complete/source_bound。源snapshot与artifact.scene一致，物体与stage/path身份不混用。
- 23组原始before/after数组：keys/dtype/shape/原始bytes全部一致，逐组SHA与报告一致；不是allclose。
- 额外physics callback count=0、dt_sum=0、pump_count=0；callback已移除；lease CLOSED、pending_unsubscriptions=0、cleanup_errors=[]。
- 原预算8×32完整；128个物理sensor更新；prepare_calls=32、ik_calls=32；8行active_sample_count各32、reset_count全0。
- report completed/startup_passed true、native_exit_code=wrapper_return_code=0、finalization_errors=[]。
- POST_CLEANUP的run_id/PID/32steps与run_start/report相符，candidate SHA对实际文件重算一致。
- report.passed=false是32步startup不满足完整1600步strict的正常区别，不能将其改为true，亦不将startup当跨障通过。

独立现场证据审查PASS：重新匹配136请求/响应与408accepted callbacks，重算source/settings fingerprints及全部46份before/after metadata SHA；原始samples确为32×8，sync prepare时点episode_length为0..31。审查自身最初额外断言误用1..32，经源码核验纠正，原始产物无缺口。最终证据门槛仅初始化/startup，未扩展为strict或PPO。

## 实际边界离线分析（不是最终geometry证书）

analyze_query_bounds.py从同一source-bound report提取全部136collider实际query min/max、collider-to-body矩阵及23组guard里的逐body原生LINK pose/xyzw。通过既有make_body_supports/world_support_points生成全部8角点，再用独立逐点affine与直接四元数交叉积公式复算，最大world差3.552713678800501e-15m。所有shape/query完整覆盖；本现场collider-to-body均identity，不借此宣称实际非零affine测试已完成。

104个Mesh（13×8）查询盒与原始authored diagnostic bounds均非完全相同，最大6.333999mm；因此authored bbox不能替代实际query。该差异本身不是新崩溃或已证明cooking bug，live cooked vertices仍需采集交叉核验。

32个Cylinder使用真实设置collisionApproximateCylinders=False、axis=Y、radius=.0959/height=.0465。实际查询盒与其声明轴向尺寸最大差8.308887e-9m。query.local_rot为绕Z约90°的native形状局部旋转，但其AABB已体现USD Y轴；把这个local_rot再乘到query盒会制造最大.0726499849m的轴错位。因此后续采用query collider-local box→完整USD collider-to-body→body pose，不能双乘local_rot；没有把float差当作放宽physical clearance。

native quaternions norm²最大偏差2.537292e-7，本离线诊断未偷偷归一化；上述两条相同raw-quat计算相符不是旋转适用域/误差包络的最终证明。初始全机盒world-z min约-.01564也不是精确碰撞穿地证明（保守AABB角点不都在实体内）。禁止从这些诊断直接生成geometry_verified、CLEAR或跨障成功声明。

## 后续与未验收

本初始化门槛已经有真实同步fastpath，无需新增无依据的App.update/paused pump或重启方案。下一具体子项是同一live stage的可用cooked hull getter、完整136query/逐body变换交叉证据，再完成provider/registry/coordinator和动作owner接线；已有SDK getter只在simulation running有效，不对已结束stage使用或以新cooking请求冒充旧shape。

新候选三次8×1600→1024×32→1024×1600、G2同物体真实返回与连续障碍、首次几何负例、AME正常退出/命名物理动作、policy-only小跨越/大绕行、单进程10000actual PPO均仍未验收。没有启动10000长训，完整目标不缩小。

Git：Baseline Ref/Candidate Ref均b16168b；Last Feature Commit=92278b7，Last Verified Code Ref=b16168b；本轮无生产代码修改。仅更新计划Task4与todo/T306/logindex及本日志；runtime/奖励/阈值/控制合同不变，AI/human阶段接口不变。

关联：[初始化计划](../../docs/superpowers/plans/2026-09-19-m1-collision-query-initialization.md)、[原query合同](2026-09-19-m1-collision-query-contract.md)、[前次CPU和历史阻塞](2026-09-19-m1-collision-query-initialization.md)、[T306](../todo/T306-m1-ame-long-train-stability.md)。
