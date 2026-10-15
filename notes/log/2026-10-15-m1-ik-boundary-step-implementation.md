# v26受限IK候选步

状态：候选实现/专项54CPU通过，完整回归和独立审查尚待完成；未v26原生，无生产训练。
最新状态（覆盖下方历史进度）：独立审查1项Important已以8个RED反例修复，投影前逐腿有限性保留；完整759项通过152.25s。最终IK SHA c4e284c2fc1b3ce3ddfb8da7c6b3b53ccdc303cf8adc47e5079228e8d29d1821本地/远端一致。GPU1MiB、无并发检查通过后，服务器2026-10-14T20:35:19Z唯一启动runner364325，输出evidence-first-obstacle-ik-boundary-v1。原生仍运行，不能宣称抬腿/跨越成功；生产训练未启动。

## 修改

solve_constrained_ik中的q+dq候选，仅将knee投影到已有分支的cfg.min_knee_abs_rad半空间，再执行原有限性/关节/分支/残差严格改善检查。不改变seed资格、目标、迭代32上限、.25rad步长、最终残差、外层编码限速和实际跨越要求。不是最终结果裁剪后伪造valid。fingerprint=v26-ik-boundary-step。

替代方案整体缩步会继续丢失合法ABAD/HIP切向进展；放宽边界/残差或抬支撑目标不符合已证实的同目标可解证据，未采用。设计与计划见docs/superpowers下2026-10-15-m1-ik-boundary-step文件。

## 测试证据

新22项覆盖真实123/126两dtype、四腿两dtype和.1/.3配置边界、非法seed/非有限/不可达。旧算法12fail10pass（真实4例与前腿8例），修正后新测试全通过。已有两项强制branch/straight提议测试原要求整腿保持，按新设计仅修改这两项期望为合法边界进展、最终残差仍失败。所有54专项最终通过2.14s。

完整prior729+new22运行中。独立最终审查后才允许唯一4env10cm native，不运行训练。

## 候选来源

本地candidate两runtimeSHA一致：ik=df2a405a30d82b0659b3ee045b9849da57529f195bce1131cf2588165fee4681；teacher=973e1522c256b081581637c758e1a782e0cc565427c0f531aa3c92c08447c90a。production未动，旧证据完整保留。

用户直接运行授权沿用，不重复设计审批；已有隔离分支，Gitidentity未配置、不改全局设置，以精确基线副本和SHA留证。

## 原生中间证据与下一步诊断（尚未完整收尾）

本次4环境已记录各142帧；env1–3在137帧锁定，env0未锁定，最终episode审计仍运行。相比v25锁定127帧，当前越过旧拒绝点但依然没有实际抬轮：active bottom最大0.0531mm。不得以延后失败代替跨越成功。runner364325/child364327现场仍活跃，未重复启动。

137帧左后腿执行残差约0.1085mm高于原0.1mm门槛。CPU冻结同一目标重复求解停在0.1088666mm，膝角0.10000000149rad；固定该合法膝角、仅沿ABAD/HIP切向优化可降至0.0642363mm，距原关节目标最大改变量0.00109732rad。说明仍存在受约束求解方向问题的证据，不能直接认定目标不可达。此诊断不是新增生产迭代预算，也不是物理成功；下一步先收齐原生审计，再设计同预算切向求解回归。证据见.superpowers/sdd/2026-10-15-m1-ik-boundary-step/frozen-diagnosis.json及frozen_check.py。
