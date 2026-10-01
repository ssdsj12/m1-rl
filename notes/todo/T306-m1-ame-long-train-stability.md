# T306 M1 AME Long-Train Stability

## Current State

2026-10-01 latest: T306.stance-encoding CPU verified, T306.episode-rearm
CPU fixed and physical verification pending (children of teacher lifecycle).
Actual step replay proves episode latches survive done. Minimal row-local
cleanup passes with live-row preservation. 45 focused tests pass. Warmup
stopped after teacher0/collision-.95; new bounded LR0 55-update reset probe
is not long training or crossing acceptance. See
[experiment evidence](../log/2026-10-01-m1-reset-stance-evidence.md).

2026-10-01: T306.approach-gate is an OPEN child of online teacher lifecycle.
Actual-method CPU replay holds the near trigger false: leg action max is
0.0, 0.08, 0.08 on three consecutive calls. The one-shot initial fallback
suppresses legs only once. This is a proven gate defect, not proof of the
entire physical failure cause. No production change or new GPU run this audit.
Next: define approach/swing/touchdown transition ownership, regression-test
episode resets and large-obstacle cancellation, then fix only this gate and
verify pre-reset physical traces. Prior replan/phase hypotheses remain unproven.
See [evidence and corrections](../log/2026-10-01-m1-approach-gate-audit.md).

当前ACTIVE（2026-09-20 registry/lifecycle core）：registry394ea67/core d27e26c均SPEC→QUALITY通过；coordinator有完整身份/每次有序事件/DEPARTING/CLEAR/再次接近和下一对象选择的纯CPU实现，最新main2317full/252.31s/0skip/exit0，最终联合184focused/1.44s。没有key的初始phase和无合法boundary的再次phase0被严格拒绝；合法CLEAR+phase11允许形成新boundary，下游必须先行级重置phase再进入helper，不强求rawgate空隙。关联CPU1024单ray/row从12.5145s降0.3608s，通过独立暴力oracle，未减少检查对象/改变阈值。.2c.2a核心CLOSED，.2c.2b下一步vendor instance hook/行级nominal重捕获/sync release/begin/raw sidecar/独立replay。未接runtime、未启动新Kit/PPO，不称行为或10000完成。GPU7仅本人占位3919095/15744MiB，本轮未动；root508GiB空闲，无存储操作。[本轮证据](../log/2026-09-20-m1-encounter-registry-coordinator.md)。下方为历史。

当前ACTIVE（whole-body向外投影已接线并实测）：代码9dc0dc7，主代理2128full/237.61s/exit0/0skip、SPEC→QUALITY通过。唯一amp/GPU7 `pose-projection-live-20260919` PID68017/run_id=a16b3848-3bc6-4c02-836d-6f6fb3be2836完整8×32/native0/wrapper0，无重启；32×136collision bounds及32×8整机s/q/z，4352 colliderstep/3精确映射独立回放PASS，最大额外外包1.954e-6m，不增加物理容差。23rawguard不变，28旧非计时字段和rawbodypose逐位一致；先close lease后env/app，rawfailed40保留。唯一测试oracle Minor修复：真实RED2failed→GREEN64，生产hash不变。GPU7仍原占位351307，本次未暂停；下一步registry/coordinator/reference hook与sync交接，不重复旧基础审计。新三次G1/1024/G2/AME/policy/单进程10000仍未完成。[投影实现和实测](../log/2026-09-19-m1-pose-projection.md)。下方为历史。

当前ACTIVE（live ownership/raw pose子包完成）：代码47167e8，主代理2026full/226.43s/exit0/0skip，SPEC→QUALITY PASS。唯一实测live-provider-20260919-1830，amp/GPU7/PID4142213/run_id=d6fc8103-c81d-4a95-94d8-09bea634f401，完整8×32/native0/wrapper0，无重启；23raw守卫逐位相同、32×8×17×7float32姿态、全部episode0、物理tick每步+4、source COMPLETE→CLOSED且无pending，先关lease后env/app。28个旧startup非计时字段逐位相同。原rawfailed40和旧负例SHA不变，新增几何SHAaa88041dde277ad1ec78232b7033045ae4f43dd99d18224761bf0cf37978f517。实际q norm²范围0.999999650100963..1.0000003531076134，未归一化。完整投影/CLEAR/coordinator/G1/1024/G2/AME/policy/10000尚未完成；下一步版本化向外pose envelope，无新增权限阻碍。GPU7仍仅原占位351307，本次未动；主源码/SDK/参考未改。[实现与现场证据](../log/2026-09-19-m1-live-provider.md)。下方为历史。

当前ACTIVE（局部geometry子包）：3d97e9b已新增纯保守构造及144tests，focused222/main1929full178.99s/exit0/0skip；SPEC→QUALITY复审通过。主代理真实旧负例回放136colliders/104Mesh/3664vertices/32nativeCylinder全覆盖、384个source+float32解析极值覆盖，原40failed和原JSON SHA不变；derived SHA9cecf087d7103a8930ce8e5bc6a9e2bd55b422041de73f1a9b4a965058068fae。最大外扩8.308887480823479e-9m含Cylinder，不增加clearance容差。只支持实际identity collider→body/unit/meter合同，不是live provider/world extent。下一步open lease→同一步17body rawposes→逐运算向外保守投影，正常close必须在env.close之前。未改collector/SDK/参考/旧run/占位，GPU7仅351307，无新Kit或训练；本轮有实际代码进展，无新增授权阻碍。[实现和验证](../log/2026-09-19-m1-conservative-geometry.md)。下方为历史。

当前ACTIVE：G0-B2 live cooked证据代码c02bde0完成，主代理1785full/178.11s/0skip、SPEC→QUALITY PASS；唯一现场cooked-live-20260919-1703（启动b0d4270、amp/GPU7/PID3824745）取得104hulls/3664vertices、无unavailable及32native Cylinder。136query/408callbacks完整、23raw前后bytes与46metadata一致，额外physics0/pump0/leaseCLOSED/callbackremoved。40hulls因raw query盒向内1float32 ULP被严格诊断拒绝，完整关闭后native1/wrapper2，POST_CLEANUP steps0；未执行32budget steps，未重启，不称startup/G1/10000通过。最大差7.450580596923828e-9m，624/624边界可由实际hull min/max的float32 center/extent重建精确复现；只能据此说数值机制可复现，不声称读到native实现。新.2c.1保守geometry边界继续，无容差/SDK/raw数据修改。root944G/497G可用，GPU7仅保留原占位351307。[现场证据](../log/2026-09-19-m1-live-cooked-evidence.md)、[实施与回归](../log/2026-09-19-m1-live-cooked-evidence-implementation.md)。下方“尚未采集”等为历史。

当前ACTIVE：2026-09-19管理员执行500GiB扩容，主代理fresh确认root944G/约498G可用，旧root不足阻碍已解除；未迁移pip缓存。b16168b clean上仅启动一次实际query-init，amp/GPU7/PID3669456/8×32完整，136body-query、23组before/after字节一致、零额外physics事件；128sensor、32prepare/IK、8行零reset，正常env/app关闭与native/wrapper0，POST_CLEANUP SHA/ID对应。主代理独立assert通过，旧CPU1687与双审未重复。GPU7原占位351307全程保留，诊断已terminal，无新长训。下面历史BLOCKED与待启动段落不再表示现状。[现场记录](../log/2026-09-19-m1-collision-query-live.md)。

当前B2后续：真实query source-bound已成立，但实际cooked hull顶点未采集，不称geometry/CLEAR通过。全136collider查询盒八角点及逐body native pose离线重建，矩阵与直接quat运算差3.55e-15m；104mesh查询盒与authored bounds非同（max6.334mm），32native Y-cylinder与声明尺寸差8.31e-9m。额外乘query local_rot会错误重旋轮轴（差72.65mm），禁止该双乘；无阈值放宽。这是.6h.6a.1a.2c/G0-B2的具体后续子项，下一步同stage live cooked读取＋无额外step守卫，不能用sourcebbox代替。之后仍按B provider/registry→C/D/E→三次新8×1600→1024×32→1024×1600→G2/AME/named-actions/policy/10000推进。

最新资源门槛：BLOCKED / 等待用户批准仅/home/hexinkun/.cache/pip迁/data并保留软链接，或用户自行释放根盘。原实现目标轮+两次自动续行共3轮同一阻碍；freshroot533224KiB，/data6894435612KiB，b16168b clean，GPU7仅原占位351307/15744MiB。没有真实query运行handle，不是verified wait；前置CPU与双审已完成，当前没有可推进既定现场链路的安全动作。未迁移/删除/重跑CPU/启动Kit，完整G1/G2/AME/learned/10000未完成。收到授权或外部空间恢复再fresh核验，避免再次基础审计。下段ACTIVE/第2轮为此前历史。[阻塞证据](../log/2026-09-19-m1-collision-query-initialization.md)。

Current G0-B2b2c代码CPU门槛完成：92278b7，main1687full/169.98s/exit0/0skip；SPEC→QUALITY PASS。旧scale fixture兼容f82da92，BaseException绕过close的P1修复6ed4b42，首次报告过早成功的P2修复92278b7；负证据保留，未放宽阈值/预算。实际8×32 query仍未启动：root约0.5GiB不足1GiB门槛，精确pip缓存迁移授权待返；无缓存移动/删除，GPU7占位351307保留。最新自动续行fresh b16168b clean/root530612KiB/GPU7仅占位；该资源权限阻碍连续第2轮，当前仅核验非实现进展，完整目标仍ACTIVE，未达三轮BLOCKED。下一步资源恢复后直接唯一真实query，不重复已完成CPU审计。[初始化记录](../log/2026-09-19-m1-collision-query-initialization.md)。

Current B2b2b完成：code8a3746f，main1565full/152.72s/exit0/0skip，实际Carb/M1 CPU probe PASS；SPEC→QUALITY PASS，构造清理P2以公开CollisionLeaseCleanupError.cleanup_owner关闭。仅lease两文件；未接runtime/启Kit/GPU，原占位与SDK/参考不变。下一步8-env实际query初始化，证明等待不额外推进physics/time/root/joint/RNG/prepare/IK/recorder；source-bound不等于geometry/G1。完整coordinator/G1/G2/AME/policy/10000仍未完成，目标ACTIVE，本轮progress。[lease实施](../log/2026-09-19-m1-collision-scene-lease-implementation.md)。

Current B2b2a完成：代码c608945，main1452full/146.49s/exit0/0skip，SPEC→QUALITY PASS。实际proxy ID延后解码3/3 SIGSEGV被定位为裸编码无Sdf.Path引用，显式CollisionPathScope修复；反射漏洞也RED→GREEN。两次主代理正式scope真实8内存实例136body/136collider/104proxy全解码、运动hash不变、只读和closed拒绝通过。下一步watch/lease与无额外physics-step初始化query；未接runtime/启GPU，不改SDK/原参考/旧run。见[scene binding记录](../log/2026-09-19-m1-collision-scene-binding-implementation.md)。完整目标继续ACTIVE；下方query完成等是历史阶段。

Current实施：用户已明确“按规格实施”，书面审阅等待解除。隔离branch codex/m1-encounter-lifecycle；A1/B1/B2a＋B2b1非阻塞query协议完成，代码f85c7ea，主代理1338full（145.24s、0skip）、SPEC→QUALITY PASS。共八个新增源码/测试，未接runtime/启GPU；17408请求CPU协议开销27.19→2.34s，不是实际PhysX耗时。现继续薄USD/SDK actual stage/path/settings/source绑定、geometry失效监控和8-env无额外physics-step初始化诊断；source mesh bounds不能直接充当cooked包络。完整状态机/owner/证据/G1/G2/AME/learned/10000仍待完成。[实施证据](../log/2026-09-19-m1-collision-query-batch-implementation.md)。下方等待状态均为历史。

Current2026-09-19 11:05：目标BLOCKED / 等待e25e805具体书面规格审阅。用户方向同意已保留；当前新门槛自用户触发轮至两次自动续行共三轮未解除，设计与容量审计已完成，不再重复检查代替确认。GPU7仅原占位351307；无任务训练/仿真，无源码改动，完整10000及learned目标保留但未完成。恢复条件与fresh检查见[书面审阅阻塞核验](../log/2026-09-19-m1-written-spec-review-blocked.md)。

Resource audit2026-09-19 11:02：新encounter证据不能直接扩充旧32步NPZ。实配22801ray/env，密集xyz单步1024约267.199MiB已超256MiB未压限制；旧verifier全run拼接，需另定有界分片/流式且可重建的schema，包含合法miss。根盘仅约3.51GiB，/data约7.12TB可用；无删除/源码修改/仿真。新增子项.6h.6a.1a.2b。书面规格审阅仍待返回，所有物理/10000目标未完成。见[容量核验](../log/2026-09-19-m1-encounter-evidence-capacity.md)。

Latest2026-09-19：用户已同意修正版A（防同次重复、离开后可再次遇同物体、连续新障碍独立判断），旧A/B等待解除。具体规格e25e805已完成主代理自审与两项独立边界复审，待用户审阅书面合同后进入计划/TDD。明确稳定物体+encounter身份、几何离开/重新接近、owner预先交接、raw-world/frame分层、G1旧IK前缀和G2真实二次跨越；未改控制源码/阈值、未启动仿真，GPU7占位351307保留。见[规格](../../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md)、[审阅证据](../log/2026-09-19-m1-encounter-design-review.md)。旧BLOCKED及A reset-only草案为历史，完整10000/learned目标仍未完成。

Latest23:36：目标已标记 BLOCKED / 等待用户选择 phase 重入行为方案 A/B。该待选条件跨三次连续目标轮仍未解除；期间已完成几何与后续接入只读审计，不能继续用重复检查代替实现。当前无训练/验证计算进程，GPU7原占位351307保留，完整目标及已有证据不变、未标完成。收到选择后从隔离设计/计划继续。见[阻塞核验](../log/2026-09-18-m1-design-choice-blocked.md)。

Latest23:32：首次几何 CPU 诊断推进。FAR 原函数回放 9env×14steps 与记录 IK 最大差6.85e-7，6失败者经过障碍时重建 world-z 目标也低于.1609；RAR横向分解证明 root平移/yaw参与，4案例原函数回放差<3e-7。质量相关性不是独立因果（近等质量一成一败）；未改阈值/随机化/源码，未开新仿真。phase修复A/B仍待用户确认。GPU7仅原占位351307/15744MiB；10000/learned仍未完成。见[首次几何审计](../log/2026-09-18-m1-scale-first-cross-geometry.md)。下列23:07为物理run状态。

Latest23:07:baseline18完整1024×1600/native0/commonPASS、行为615/1024。candidate19在完成247步后prepare247触发env523wave/legs重入保护，正常清理但native1/wrapper2/独立verifier3，拒绝验收且无重启。新鲜数据证明env523刚凑齐5稳定样本的下一prepare即回到phase0；另18首次跨越事件缺失独立登记。转CPU根因/新合同设计，不改保护/阈值/SDK。原占位已恢复PID351307/15744MiB，formal646f486不动；未启动10000/learned验收。[run18](../log/2026-09-18-m1-scale-baseline18.md)、[candidate19](../log/2026-09-18-m1-scale-candidate19.md)、[行为负例](../log/2026-09-18-m1-scale-baseline-behavior.md)。

Resource update22:46:run18同PID1408/1600。root未知增长曾降至11.675GiB；完整校验归档本任务已结束pytest-227到/data并保留旧路径链接，只移除重复副本后回到约14.29GiB。2816文件hash一致、22links实际可解析，所有证据保留；未动旧模型/真实run/其他任务。未来candidate新输出用/data私有父目录，baseline与源码不搬。外部根盘增长仍未查明，下一启动仍须再查容量/完整baseline门槛。见[存储核验](../log/2026-09-18-m1-scale-fixture-storage.md)。

T306.6h.6a.1 CONTINUOUS EXECUTION：用户要求持续至验收。run14/15/16相同冻结候选三次独立单进程均exact8×1600、6400子步、strict8/8、native/wrapper/verifier0、zeroreset；15/16各2700非计时数组与14逐位相同。正式8files原样接入/新鲜CPU回归正在进行；新增.6a.1a为1024布局与预算适配。现1×1024长条有768/1024局部横杆中心超现有2e-5m门限，32×32需确定性unique origin及bar映射；不能只改num_envs。1024与10000仍未启动；控制器通过不能替代policy-only跨越/大绕行。[run15](../log/2026-09-18-m1-sync-repeat15.md)、[run16](../log/2026-09-18-m1-sync-repeat16.md)、[尺度审计](../log/2026-09-18-m1-1024-readiness-audit.md)、[1024设计](../../docs/superpowers/specs/2026-09-18-m1-reference-1024-scale-design.md)。

### 上一阶段单次通过记录（现已完成三次重复）

T306.6h.6a IMPLEMENTED, ONE ISOLATED PHYSICAL PASS：用户批准具体设计后实现独立有序事件＋5稳定样本接管、慢速有界差动积分、reset失效与独立NumPy验收。373CPUtests与spec/quality通过。唯一run14 amp/GPU7单进程exact8×1600、6400子步、native/wrapper/verdict0，strict8/8（run12为4/8），0reset/重启。接管action[249,253,248,251,245,248,248,247]；接管前全部物理/动作字段与run12逐位相同，腿输出不变，轮均速差.01966..03224<.08。正式a86cbf5/SDK/AME未改；15GB占位2795762保留；无后续仿真/推广/1024/10000。下一阶段需正式接入和严格重复门槛，不能当作policy-only跨越或大绕行完成。[实施计划](../../docs/superpowers/plans/2026-09-18-m1-post-cross-wheel-sync.md)、[实现与实测](../log/2026-09-18-m1-post-cross-sync-implementation.md)。

### 最近负结果（设计依据，不是当前仍待执行的消融）

T306.6h.6 DIAGNOSTIC COMPLETE, CANDIDATE REJECTED：唯一批准gain3→0隔离A/B已执行，225CPUtests24.77s/spec/quality通过；run13 amp/GPU7 exact8×1600/native0/completedtrue，但strict1/8、wrapper3（基线4/8）。七个完整首回合尾段target差分RMS.848488→0，actualspeed.784206→.237260；均速门槛仍7/8失败。Env1step134触发原参考几何/载荷终止判据，非实测横杆力；env2/5 RAR横向出界16.65..20.04mm错过overbar。新.6a处理同步与跨障时序/轨迹耦合。正式a86cbf5未动、不推广、不追加仿真、不扩1024/10000；15GB占位2795762一直保留。[证据](../log/2026-09-18-m1-wheel-equalizer-ab.md)。

### Historical investigation chronology（下列旧状态不覆盖上面的当前结果）

T306.6h.5c.1 DIAGNOSIS COMPLETE: approvedAimplementedandreviewsPASS;22CPUdiagnostictestsplus170copiedadaptertestsPASS. Realrun10full8×32→native134afterclose;53,562registrations294invocations,oneunreturned_physxcb+0xef080/staticarg+0x371d70/registrationcaller+0xed4ed. Binaryandcross-versionNVIDIAsourceidentifyfunction-staticpy::listfromreplicator_attach_fn survivingPythonfinalization. Publicunregister/interface-scriptingrelease donotdestroythatstaticlist. New.5c.2proposedisolatedreplicate_physicsFalseA/B;userquestionpending. NoSDK/productionpatchor10000training; reservationunchanged. [Evidence](../log/2026-09-18-m1-physx-exit-owner-capture.md).

T306.6h.5c ROUTE A APPROVED (supersedes historical WAITING SCOPE below): user approved isolated callback-owner diagnosis without SDK edits/upgrades or reservation changes. Design6addb50 written; implementation not begun, written-spec review still pending. Three independent read-only audits complete:22 selectedfiles matchRECORD, installedversions matchdeclaredSDKdependency,09 libc callsite identifiesef_cxa butnotregisteringDSO. Main independentlyrecheckedlibc Build-ID/callbytes,adapterdiff0againstb60ca0f,andreservation2795762alive/GPU7free8328MiB. NoIsaacrun thisturn. Usercorrectlychallenged rollback/early-stop wording: onlyrejectedcacheoffpatchwasreverted,notlearnedmodels; 120/1000updatecompletionisnot10000guarantee. Current8×32 executesallstepsandfailsduringclose,notanobservedmidrunshortfall. [Audit](../log/2026-09-18-m1-native-exit-owner-audit.md),[design](../../docs/superpowers/specs/2026-09-18-m1-native-exit-owner-design.md).

T306.6h.5a diagnostic COMPLETE, .5b REJECTED native gate, .5c WAITING DESIGN/SCOPE. Cacheoff candidate passed170CPUtests/spec+quality and actual/effective/hook guards, but real08 full8×32 stillaborts134 afterappclose. Lastdiagnostic09: Py_Exit(sts0) -> libc.exit handler -> list_dealloc -> PyThreadState_Get(NULL) -> abort. Thisdoesnotidentifytheregisteringnativeowner. Three lifecyclehypotheses notsufficient; stopaddinglocalpatches. Archivecandidateandrestoreonlyitsfourfiles to b60ca0f; originalcleanup/fataldiag untouched. Need discuss SDK shutdown ownership/compatiblelifecycle beforefurtherfix. amp/SDK/driver/reference/reservationunchanged;no1600/1024/10000. [Frame evidence](../log/2026-09-18-m1-reference-gdb-frames.md),[negative test](../log/2026-09-18-m1-reference-stat-cache-gate.md).

T306.6h.5a ACTIVE: user-approved isolatedGDB12.1 ready,5CPUtestsPASS. Capture06 completed8×32 then native139; C++stack showsPhysX tensor destructor duringretainedPythonframe destruction afterappclose. GDB shell0 isseparateandnotchildsuccess. Addingread-onlyframemetadata toidentifyretainer; noamp/Isaac/driverchanges. Reservation2795762preserved. No1024or1600. [Native capture](../log/2026-09-18-m1-reference-gdb-capture.md).

Latest run05: launcher subscriptions detached and runtime owners released beforeappclose, yetfull8×32stillends withGC SIGSEGV139. Two lifecyclefix hypotheses insufficient; diagnostic improved. CPU164passed/spec+qualityapproved. T306.6h.5a awaitspermissionforisolatedgdb/nativeC++stack; noinstalledtool/newSDKchanges, nofurtherblindruns. User15GBreservationpreserved, no1024/1600. [Latest verification](../log/2026-09-18-m1-reference-launcher-cleanup.md).

Latest run04 successfully restoredfataltrace: post-close native139 occurs during interpreter `Garbage-collecting`, `<noPythonframe>`. Diagnostic union161passed, real8×32stillnotaccepted. Nextsecond lifecyclehypothesis detaches AppLauncher timeline/signal ownersbeforepluginunload; noSDK/sharedinterfacepatch. [Fatal trace](../log/2026-09-18-m1-reference-fatal-diagnostics.md).

T306.6h.5 latest: first owner-release lifecycle patch passed157CPU/spec+quality but realattempt03 stillnative139 afterRUNTIME_REFS_RELEASED/APP_CLOSED/POST_CLEANUP. Hypothesis insufficient. Next diagnostic re-arms faulthandler after oldAppLauncher SIGSEGV replacement; no blind native-interface release. No1600/1024. [Fix verification](../log/2026-09-18-m1-reference-owner-cleanup.md).

2026-09-18 current: user approved amp/GPU7 8-env start while preserving15GB reservation PID2795762. Bindingddad702 passed151 CPU tests. Two8×32 attempts have complete per-env/substep evidence but reproducible native139 afterAPP_CLOSED/POST_CLEANUP; external finalizer correctly rejects completion. NewT306.6h.5 investigates normal shutdown lifetime. No1600/1024/10000. Actual exposedbar45mm confirmed, source unchanged. [First run](../log/2026-09-18-m1-reference-gpu7-smoke.md),[diagnostic](../log/2026-09-18-m1-reference-gpu7-faulttrace.md). Prior hold/resource entries below are historical.

2026-09-18 14:42CST USERHOLD: requestedGPU7thenexplicitlychosepreserveownsleep.pyPID2789351anddonotstart. NoIsaac/noGPUbindingedits. CurrentadapterstillGPU4-bound; futureGPU7changeandtestsrequiredonresume. T306.6h.4nowuser-heldresourcegate,notpermissiontokillreservation. [Decision](../log/2026-09-18-m1-reference-gpu7-hold.md).

2026-09-18 14:22CST T306.6h: standaloneadapterf5842d4ready,150CPUtestsPASS/spec+qualityPASS. PhysicalTask5blockedbeforelaunch:GPU4occupiedbyotheruserliuxx,21710MiBused/2372MiBfree,100%utilization. NoIsaacrunstarted,no1024,no10000,noforeignprocessinterrupted. NewT306.6h.4requiresresourcecoordination. [Runtime](../log/2026-09-18-m1-reference-runtime.md),[GPUblocker](../log/2026-09-18-m1-reference-gpu-resource-blocker.md).

Task3metricscompleted:77focused/112unionCPUtestsPASS;originalhelperindependentflagsmatch80steps×8envCPUparity;specandqualityapproved aftercorrectingmissingnonwavesamplesandexactheightmeanformula. Task4source-boundruntimeadapterunderimplementation;noIsaacsimulationyet. [Metrics evidence](../log/2026-09-18-m1-reference-metrics.md).

2026-09-18 T306.6h IMPLEMENTING: userconfirmeddesign. Provenanceguard35tests/spec/qualityPASS; referenceCPU88PASS; mainUSDcomposition confirms3layers,1built-inMDL,0unresolved,17bodies,16revolutejoints,floatingBASE_LINK,13mesh+4cylinder(.0959radius)colliders. NoIsaacsimulationyet. Task3metricsandTask4source-boundrecorderadapteractive. Newdiagnosticallbodycontactsensor neededfornonwheelbarcontacts andsubstepp eaks; existingreferencecrossbartermusesgenericnetforce andmustremainunchanged. [Preflight](../log/2026-09-18-m1-reference-preflight.md). No10000/restart/monitor.

2026-09-18 reference follow-up: user approved the reference-crossing direction and changed the simulation sequence to8env then1024env. T306.6h [stage-one design](../../docs/superpowers/specs/2026-09-18-m1-reference-controller-validation-design.md) now removes1-env simulation:8×32 startup,three8×1600 strict passes,then1024×32 capacity and1024×1600 strict controller verification. This is not10000-iteration training. Reference code has controller-assisted fixed60mm crossing records but no available accepted weights/JSON; M1 does not enable Go2 MPC avoidance. Original no-checkpoint play bypasses the wrapper; USD dependencies contain missing legacy paths. No controller adapter implemented or Isaac run started. Existing AME and paused monitor remain unchanged. [Investigation evidence](../log/2026-09-18-m1-reference-controller-design.md).

2026-09-18 latest: approved wheel reward implementation passed127tests/1skip and both reviews; physical8×600 andfresh8×2 gates passed. amp/GPU4 fresh1024×120 completed exact0..119 inoneprocess,complete+exit0,138checkpoint tensors/35TB tags finite. Final fixedflat/small/large evaluations allcomplete+exit0: safe flat8/8,crossing0/8,avoidance0/8,zero collisions/failure/invalid terminations. Forward4.89728/1.07456/0.50969m. Learned obstacle behavior remainsred. T306.6g.1a: one-off profiling diagnosis produced no exposure data in two500-step runs andone1-step probe despiteCPUtests passing; stopthatmechanism pending explicit-interface design approval. No activeIsaac process orformal10000run;monitorpaused. See[pilot](../log/2026-09-18-m1-wheel-reward-1024-pilot.md),[tail+behavior audit](../log/2026-09-18-m1-wheelreward-tail-audit.md),[diagnostic limitation](../log/2026-09-18-m1-reward-hook-bootstrap-probe.md).

Updated 2026-09-17: the current requirement is a fresh single-process 10000-update run in the `amp` runtime on physical GPU4, with real M1 locomotion. The old supervisor narrative below is historical and is not the current running workflow.

- T306.3 physical contract: fixed USD root released with articulation-root API migration; 12 leg position targets + 4 continuous wheel velocity targets retain 16-column action order. Balanced training stance and simulation-calibrated gains pass the flat rolling gate: 8 env x 300 steps, 1.6044m mean forward displacement, zero resets/body collision. Old wheel gain under otherwise identical conditions advances only 0.0025m.
- T306.4 reward contract: planner posture/limits exclude wheel angles; named M1 geometry collision and wheel contact-point rolling residual replace Go2 selectors. Scanner axis ordering and quad-face triangulation are corrected. Policy/critic are now 1581/1584; old 1585/1588 checkpoints are incompatible.
- T306.5 stability: fresh AME and AME-AMP each completed 8 env x 2 updates. The fresh 1024 x 120 validation completed exact iterations 0..119, exit 0 and completion marker, with finite checkpoint and all 35 scalar tags; no restart. This is not a 10000-update completion.
- T306.6 behavior: unchanged-config1024x1000 completed exact0..999 but collapses by iteration400 and ends with bad-orientation0.8826. Final flat success1.0/3.9328m; small/large success0 at0.7888/0.5429m. More iterations do not fix the stopping behavior.
- Latest semantic1-contact fix pilot also completed exact0..119,138 checkpoint tensors/35 TB tags finite,exit0. Final episode980.02/bad_orientation0.001953. Flat8/8; small/large0 at1.0342/0.5074m. The simulator completed; obstacle behavior remains red.
- 2026-09-18 diagnostic closure: the72 residual knee events came from a neighboring collision-filtered obstacle scanned at2.5m env spacing. Probe-only spacing8m reproduces all-wheel8/8 at0.05m with3.10m progress,0 resets and0 geometry events. Evaluator already used8m; learned-policy results are unchanged. Current relevant regression rerun:97 passed,1 skipped. No Isaac training/probe/eval process is running.

### Historical 2026-09-16 state (superseded)

The M1 AME 1024-environment run reached checkpoint `model_1030.pt`, then
entered repeated clean-looking exits and finally hung during Isaac Sim
shutdown. The Python process reported exit code `0` without traceback, OOM,
NaN, or Inf. The host Vulkan ICD independently fails a minimal
`vkCreateInstance` call with `VK_ERROR_INCOMPATIBLE_DRIVER`.

The single-GPU M1 launcher now avoids CUDA device remapping, disables Isaac
Sim renderer multi-GPU, selects physical `cuda:4`, and preserves policy noise
std on resume. Vulkan still initializes on Linux and reports the broken host
ICD, but a controlled 1024-env A/B proved that the two renderer multi-GPU
flags are sufficient for training to proceed without the invalid
`app.vulkan=false`/DX12 setting.

The supervisor now owns an isolated process group and checkpoint lineage,
uses a single-instance lock, validates checkpoint contents, and recovers a
five-minute checkpoint stall with bounded TERM/KILL cleanup. AME checkpoints
are atomically replaced and record `next_iter`, so resume no longer repeats
the last completed optimizer update. The final real 1024-env supervisor smoke
resumed `model_1040.pt`, performed exactly three updates, and completed at
`model_1043.pt` with exit code `0`.

The committed target-10000 run is active in `m1ame_supervisor`. Its first
attempt advanced from `model_1043.pt` through validated `model_1100.pt`
without restart or stall, exceeding the earlier approximately 50-update exit
window while preserving policy noise std.

## Open Children

- T306.6h.5c.3 CLOSED REFERENCE LIFECYCLE：a86cbf5首测完整1600/native0、strict4/8；后续同步646f486的run14/15/16三次strict8/8。不能混用不同控制器的通过次数或把正常reference关闭外推AME。1024转.6a.1a。[旧基线](../log/2026-09-18-m1-reference-strict-run12.md)、[新候选](../log/2026-09-18-m1-post-cross-sync-implementation.md)。
- T306.6h.6 DIAGNOSTIC CLOSED, REPAIR OPEN：run13仅gain3→0，所有场景/来源/初始随机化匹配。平地目标交替消失但strict4/8→1/8，否决直接关闭反馈；候选留在隔离目录不推广。[结果](../log/2026-09-18-m1-wheel-equalizer-ab.md)。
- T306.6h.6a IMPLEMENTATION COMPLETE：run14首次候选strict8/8、native/verdict0，跨障前缀不变；用户随后持续执行授权下run15/16也全通过，正式feature/CPUverified646f486。旧“单次批准已用完”仅是run14结束时的历史边界，不覆盖最新持续任务。冻结候选post_cross_sync_20260918与[五文件hash](../log/2026-09-18-m1-post-cross-sync-implementation.md)保留供旧证据重验。
- T306.6h.6a.1 PROMOTION/REPEATS COMPLETE：run14/15/16三次严格重复全通过，正式646f486；373CPU/spec/quality通过。1024转子节点.1a；保留env5瞬时尾段波动诊断，不能当作完全瞬时同步。
- T306.6h.6a.1a ACTIVE / PHYSICAL CANDIDATE REJECTED：Task1/2/3及run17startup完成；baseline18全1600/native0/commonPASS，原strict615/1024。candidate19完成247后prepare247env523reentry保护失败，native1/wrapper2/verifier3。冻结副本保留、不推广、无重跑；占位351307已恢复。以下两个子问题由全量baseline与实际candidate现场共同触发。[run19](../log/2026-09-18-m1-scale-candidate19.md)。
  - T306.6h.6a.1a.1 OPEN / FIRST-CROSS GEOMETRY：18env有序事件缺失，FAR6高度不足、RAR17横向越界；原函数CPU回放FAR9×14最大差6.85e-7，失败者world目标自身偏低且与root/姿态耦合。RAR主代理精确分解与4源函数回放证明root/yaw影响，不能简单调腿横向；质量仅有关联、尚缺力矩/接触向量隔离因果。需独立行为设计；不能翻所有腿补偿符号、删随机化或改阈值/半径/分母。[行为审计](../log/2026-09-18-m1-scale-baseline-behavior.md)、[几何与源函数回放](../log/2026-09-18-m1-scale-first-cross-geometry.md)。
  - T306.6h.6a.1a.2 ACTIVE / WRITTEN SPEC APPROVED：用户2026-09-19已明确“按规格实施”，书面审阅等待解除；每次encounter，不永久屏蔽物体、不只reset解锁。phase11→-1→0源因仍保留，不能把root1.15mask套legs截断首次恢复。隔离实现推进identity/唯一选择、行级缓存、sync owner交接及版本化独立replay；首次几何负例不由此自动修复。[规格审阅](../log/2026-09-19-m1-encounter-design-review.md)、[原根因](../log/2026-09-18-m1-scale-wave-reentry-diagnosis.md)。
    - T306.6h.6a.1a.2c ACTIVE / APPROVED IMPLEMENTATION：基础几何/清单/query/source lease与query-only现场完成；c02bde0/1785full/双审后的实际cooked读取已建立，负例揭示边界舍入。provider/registry及C/D/E仍待完成。[cooked现场](../log/2026-09-19-m1-live-cooked-evidence.md)、[query正例](../log/2026-09-19-m1-collision-query-live.md)。
      - T306.6h.6a.1a.2c.1 CLOSED / OUTWARD_POSE_PROJECTION_STARTUP：9dc0dc7、2128CPU、SPEC→QUALITY、真实amp/GPU7单次8×32/native0以及全部4352colliderstep独立精确重建通过。公开raw quaternion两图+normalized三映射及逐运算舍入/FTZ保守外包，无物理余量放宽。它提供整机离开判断的输入，不自行授权CLEAR；后续registry/coordinator仍OPEN。[在线投影证据](../log/2026-09-19-m1-pose-projection.md)。
        - T306.6h.6a.1a.2c.1a CLOSED / LIVE_RAW_CAPTURE_STARTUP：47167e8/SPEC→QUALITY/2026CPU和唯一live-provider-20260919-1830完整8×32通过；修复采样期间绑定漂移与persistent pending cleanup后错误unload两个P1，保留rawfailed40；不是projected extent/CLEAR/PPO验收。可选质量后续为纯CPU真实sink→NPZ行为测试，实际NPZ已独立回放。
      - T306.6h.6a.1a.2c.2 OPEN / REGISTRY_COORDINATOR_INTEGRATION：直接复用完整live geometry+raw poses+fixed-frame bounds，实施静态own-obstacle注册/唯一hit关联、AVAILABLE→CROSSING→DEPARTING→CLEAR、有序完成与几何离开历史，以及prepare前reference gate和sync owner交接；不能将短测、旧成功或raw gate闪断作新encounter资格。此后新G1/G2物理门槛与AME/policy/10000仍全部需要。来源和合同沿用已批准encounter设计§§3–9。
        - T306.6h.6a.1a.2c.2a CLOSED / CPU_CORE：registry394ea67/core d27e26c，121+63focused、2317full；两组件均SPEC→QUALITY通过。保守all-owner broadphase解决实测1024的12.5s Python全扫描，精确窄阶段不变。所有CPU轨迹明确非实机、非G2。[实现/负例/性能](../log/2026-09-20-m1-encounter-registry-coordinator.md)。
        - T306.6h.6a.1a.2c.2b OPEN / PRE_HELPER_ACTION_HANDOFF：依赖.2a，新增可追溯vendor snapshot及instance typed hook，在原helper前消费合法boundary；仅相应行重捕获nominal/清cache，sync独立release/begin保留episode与全局连续性；处理4/5、5/5、active交接及raw-world/frame分层，加入lossless射线sidecar和独立replay。未实现不能开启新G1/G2物理验收；父.2c.2继续OPEN。
      - G0-B2b2c COMPLETE（仅query初始化）：query-only唯一8×32/136query/23rawguard/0额外physics/native0实际通过；cooked模式唯一负例也完整清理，但未跑budget，不合并成成功重复。[query正例](../log/2026-09-19-m1-collision-query-live.md)。
      - G0-B1 COMPLETE（仅USD输入）：0196f6f；全部enabled静态/loaded子树/raw变换order遗漏均先RED后修复，84focused＋main913full/0skip，SPEC→QUALITY PASS。真实root17body/13proxy凸包mesh+4Cylinder、4,544,118 authored points复核通过。source bounds不代表cooked；B2实际query/包含性和动态包络继续，可依赖SDK公开query合同但必须现场stage/path/scale/完整回调核验，不新增C++内部指针门槛。见[实施](../log/2026-09-19-m1-collision-inventory-implementation.md)、[query合同](../log/2026-09-19-m1-collision-query-contract.md)。
      - G0-B2a COMPLETE（仅数学核）：c12e0af，2RED→2GREEN、51RED54GREEN→105GREEN，main下溢补测2RED→107GREEN；main1020full/0skip，SPEC→QUALITY PASS。实际USD17collider136角点vsGf独立数学对照maxerror0，非actualquery/整机物理来源验证。[实施](../log/2026-09-19-m1-collision-supports-implementation.md)。
      - G0-B2b1 COMPLETE（仅协议）：f85c7ea，318focused、main1338full/0skip，SPEC→QUALITY PASS。严格全manifest/真实finished/线程/时钟/metadata失效/weakref及JSON，17408请求线性完成判定。不能把protocol_complete当作真实geometry_verified。[实施](../log/2026-09-19-m1-collision-query-batch-implementation.md)。
      - G0-B2b2a COMPLETE（静态绑定/串行scope）：c608945，main1452full/0skip、SPEC→QUALITY PASS。实际stage/cache/path/settings/source绑定，原P1 proxy裸ID生命周期与P2相消反射均已修复；两次真实8内存实例136collider延后解码/运动hash不变验证通过，非livequery。[证据](../log/2026-09-19-m1-collision-scene-binding-implementation.md)。
      - G0-B2b2b COMPLETE（source lease）：8a3746f/1565full/双审，并在后续真实query/cooked现场验证订阅及scope关闭、无额外physics；不抵扣G1重复。[实施证据](../log/2026-09-19-m1-collision-scene-lease-implementation.md)。
    - T306.6h.6a.1a.2a OPEN / G2 DEPENDENCY：真实再次遇障要求统一方向frame、正确轮侧、多物体接触归属及连续运动路线/掉头；当前fixed +X/右轨单杆不支持直接外推。G2无reset/teleport的同物体二次跨越及连续新障碍是必需验收，CPU/G1不能替代。见同一[规格G2](../../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md)。
    - T306.6h.6a.1a.2b OPEN / EVIDENCE RESOURCE DEPENDENCY：全env/step的hit身份与整机包络需可重建，但密集全ray扩入旧32步NPZ超256MiB，旧verifier全run拼接也非有界。新增版本需字节上界、流式重放、validity/未命中明确且不丢歧义负例；编码不预设必须全ray密集存储，控制/扫描精度和分母不改。根盘只余3.51GiB，后续本任务新大输出及临时数据须/data预检。只读审计完成，实现待父规格审阅后的计划，见[证据容量](../log/2026-09-19-m1-encounter-evidence-capacity.md)。
- T306.6i OPEN / READINESS AUDITED：AME训练入口仍默认fast_shutdown与replicateTrue；完成标志在app.close之前，wrapper只检查native0+任意完成标志，不足正式退出审计。实际AMEfresh计数正确0..9999/next_iter10000，不改loop。CPUimport证明amp环境当前runner/PPO来自m1_rl，cuda_initialized=False；旧摘要amp算法目录不是当前事实。需独立lifecyclehelper释放runner/wrapper/env/writer/obs/异常frame并normalclose，mixedterrain碰撞/8env/1024必须重新验证，不照搬reference通过。[完整只读审计](../log/2026-09-18-m1-ame-lifecycle-readiness-audit.md)。
- T306.6i.1 OPEN / AME-AMP COMPATIBILITY：审计发现AMP fullresume直接读iter、save无next_iter，与AME不同；本次仅登记，不改、不将AMEfresh计数结论套用AMP。当前主目标先AMEfresh；后续若AMP恢复纳入验收需单独修复/测试。来源同[审计](../log/2026-09-18-m1-ame-lifecycle-readiness-audit.md)。
- T306.6j OPEN：参考到AME需named physical q/qd target桥和版本化观测，动作顺序/缩放不同；teacher-assisted与policy-only分开。窄45mm横杆不可冒充AME100mm全宽通过。
- T306.6k OPEN：大绕行需M1可执行(v,yaw_rate)路线、全身扫掠净空、到达/回线验收；不直接套Go2侧移planner。依赖基本轮式控制与动作合同明确。
- T306.6h.5c.1 CLOSED IDENTIFIED: nativecallbackowner/staticlistregistrationproven;thisisdiagnosis,notclean-exitrepair. Historicalapprovalentrybelowissuperseded.

- T306.6h.5c.1 历史批准事项已完成，证据归档于[责任库定位](../log/2026-09-18-m1-physx-exit-owner-capture.md)。

- T306.6h.5c SDK关闭调查已定位并通过一次隔离规避短测；正式接入与行为验证转.5c.3，不能外推历史所有训练中断均修复。
- T306.6h.5b CLOSED NEGATIVE: effectivecacheoff verifiedbut full8×32 ends134; candidatearchived/reverted, no acceptedfeaturecommit. [Verification](../log/2026-09-18-m1-reference-stat-cache-gate.md).

- T306.6h.5a CLOSED DIAGNOSTIC：原生栈与frame归属调查已完成，后续static-list归属及规避见.5c.1/.5c.2。[原始诊断](../log/2026-09-18-m1-reference-gdb-capture.md)。

- T306.6h.5 CLOSED FOR REFERENCE PATH：最初8×32关机SIGSEGV139的历史调查已推进到owner释放/正常复制组合，run12及run14/15/16完整1600/native0得到验证；不再作为等待gdb/短测的open blocker。AME迁移仍为独立.6i，不能宣称历史全部训练故障同因。[原始负证据](../log/2026-09-18-m1-reference-gpu7-faulttrace.md)。

- T306.6h.4 RESOLVED FOR8ENV /1024RESOURCE PREFLIGHT PENDING：用户指定GPU7且后来明确允许先停止本人占位、任务无计算进程后恢复；原先hold不再是当前授权。只准核验后操作本人sleep.py，绝不停止其他任务。2795762/15GiB已在三次8env中保留；1024前重新核验。当前脚本/home/hexinkun/sleep.py SHA8a487ab7，cwd/home/hexinkun，m1Python3.10，CUDA_VISIBLE_DEVICES=7；这是占位runtime，不是训练runtime。训练仍amp。[历史暂停决定](../log/2026-09-18-m1-reference-gpu7-hold.md)。

- T306.6h.3 MEASURED baseline boundary:8-env actualexposedbar0.044999999–0.045000476m confirms15mmembed/45mmexposure. No60mmphysicaldifficultyclaim. Preserveexactsourceandstrict.1609wheelcenterthreshold; raisingbarrequiresusercomparisonchoice. [Measurement](../log/2026-09-18-m1-reference-gpu7-smoke.md).

- T306.6h.1 CLOSED: provenance/USDclosure preflight; separateM1bundle historicalhashesmatch,portableoverlayequivalentexceptpath+newlines; noPandaassemblysubstitution.
- T306.6h.2 CPUIMPLEMENTATIONCOMPLETE: metrics/sourcebinding/pre-resetrecording/substepcontacts/8misolation atf5842d4, GPU7bindingddad702, ownerreleasecc5fae3 with157CPUtests. Physicalstartup blockedby.6h.5 native139, notoldresourcehold. No1024untilthree8-envstrictpasses.

- T306.6h ACTIVE DESIGN: independent amp/GPU7 reference controller validation (userGPUamendment supersedes4), sibling of.6g and prerequisite to reference-assisted policy integration. User scale amendment is8env→1024env,no1-envsimulation; asset/source preflight andthree8×1600strictpasses mustprecede1024capacity/1600-stepvalidation. Controller/oracle success isnotpolicy-onlysuccess. NoGo2MPCport/formal10000training authorizedbythisamendment. [Design evidence](../log/2026-09-18-m1-reference-controller-design.md).

- T306.1: repair the host NVIDIA graphics/Vulkan userspace installation with
  administrator access, then require `vulkaninfo` to enumerate all eight GPUs.
- T306.2: superseded by the user's single-process requirement; do not restart the old supervisor.
- T306.5: 120-update gate passed; eventual 10000 single-process verification remains open after behavior acceptance.
- T306.6: compare the pilot policy with fixed-seed small/large baselines, improve actual crossing/avoidance, and then run the fresh 10000-update single process.
- T306.7: investigate inherited reset clearance (0.30m obstacle-center exclusion versus M1 footprint and random reset offsets), disabled terrain-level curriculum, and the inherited 0.5s obstacle airtime threshold before behavior acceptance. These are code-review risks, not yet proven causes.
- T306.6a: initial std0.2 materially improves survival and [learned flat rolling](../log/2026-09-17-m1-noise02-flat120.md). At120 updates std has grown to0.3694 and rewards/geometry penalties worsen, so long-horizon learning remains unverified. Do not resume the collapsed std1 checkpoint.
- T306.6b: [1000-update learning-horizon gate](../log/2026-09-17-m1-noise02-1000-learning-gate.md) completed and failed: obstacle success remains0 and late policy collapse returns.
- T306.6c: semantic1 wheel-contact correction verified in tensor and physical contact tests. [Fresh1024x120 A/B](../log/2026-09-17-m1-semantic1-wheel-120-training.md) completed, but small/large behavior remains0. The earlier1.2245m root-progress probe did not prove all four wheels passed.
- T306.6d CLOSED: [evaluation failure-mask fix](../log/2026-09-17-m1-evaluation-terminal-failure.md) passes13 focused and91 broader tests (1 skipped); three real hardened reruns complete+exit0, all failure rates0, flat1.0/small0/large0 unchanged.
- T306.6e: [matched-height full-wheel probe](../log/2026-09-17-m1-step-height-matched-probe.md) shows0/8 complete0.10m crossing with fixed legs,0 resets/collisions,all600 steps executed. Isolated0.05m control completes8/8,0 resets and0 geometry events. The user has now approved wheel-appropriate progress/climb rewards; implementation is T306.6g.
- T306.6g: [approved wheel reward plan](../../docs/superpowers/plans/2026-09-18-m1-wheel-obstacle-rewards.md) implementation and120-update runtime gatescomplete; actualsmall/large behavior acceptancefailed0/8. Preservedsemantic2/non-wheel safety and no restart. This is a measured negative learning result,not implementation completion of the fullM1goal.
- T306.6g.1 ACTIVE: fixedsmall trajectory conditional-gate diagnosis is triggered bycrossing0/8 despite nonzero newterms. Live velocity curriculum reachesx upper1.0 byTBstep63; initial±0.1 config doesnotexplain this. Capture validsemantic1 opportunities,patch validity/large veto andforward/articulated-up gates fromactual reward calls before auto-reset,withfirst-episode denominators andtimewindows. Do not changeweights/commands/curriculum while gathering evidence. [Tail+behavior audit](../log/2026-09-18-m1-wheelreward-tail-audit.md) also recordsbad_orientation mean8.74×oldbaseline andincreasingstd;conditionalfixed-eval exposure mustnotbe generalized totraining-distribution frequency.
- T306.6g.1a BLOCKING .1: [one-off profiling diagnostic](../log/2026-09-18-m1-reward-hook-bootstrap-probe.md) has50CPUtestspassing butnoacceptedruntimecapture inthreeattempts. Lastprobe confirmsownhookstillpresentandcorrectcodepaths,notasimplemissing-hookissue. Stopthisroute;proposeexplicitopt-inreward/evaluator diagnostics withdefaultmathandreturnsunchanged. Awaituserdesignapproval;do notrepeattheseevaluationsorchangeweightsfrommissingdata. Monitorpaused.

## Closed Children Archive

- T306.6h.5c.2 CLOSED ISOLATED STARTUP VERIFIED：run11完整8×32/native0，无重启；212tests与两轮审查通过。只读组图与短测数据核验通过，动态过滤/行为/10000未验证。[证据](../log/2026-09-18-m1-normal-clone-ab.md)。

- T306.6f CLOSED: [event-level replay and isolated A/B](../log/2026-09-18-m1-probe-neighbor-contamination-fix.md) localize all144 front-knee records tosteps574..599 and neighbor-box x3.4..3.6m, not own-box x0.9..1.1m. Live FK/named PhysX pose error is at most0.212mm; actual reporter threshold1N. Source-hull LP shows all144 separated from own box. Probe spacing8m removes72/4800 geometry events while retaining8/8 crossing; reward masks, colliders and thresholds unchanged. Static proxy volume+35.98% and3-frame/4-substep contact sampling remain modeling limitations, not the proven cause of these events.
- Identified that the prior supervisor was not limited by `MAX_ITERATIONS`;
  all 22 premature runs stopped before `Training Complete`.
- Removed `CUDA_VISIBLE_DEVICES=4` / `cuda:0` ordinal mismatch from the M1
  launcher; physical GPU selection now uses `DEVICE=cuda:4`.
- Resume now keeps checkpoint policy std by default instead of resetting it to
  approximately `1.0` on every restart.
- Added a single-instance, process-group checkpoint-progress watchdog with
  bounded TERM/KILL cleanup and signal-safe shutdown.
- Added atomic AME checkpoint writes, strict metadata validation, isolated
  attempt lineage, and correct zero-based resume math.
- Verified the single-GPU launcher and supervisor against real 1024-env Isaac
  runs; the focused AME baseline suite is `30 passed`.

## Related Logs

- [Reference runtime adapter CPU/API verification](../log/2026-09-18-m1-reference-runtime.md)

- [Reference controller source/entrypoint/asset audit and stage-one design](../log/2026-09-18-m1-reference-controller-design.md)

- [Floating-base and wheel-drive gate](../log/2026-09-17-m1-floating-drive-gate.md)
- [AME smoke](../log/2026-09-17-m1-floating-ame-smoke.md)
- [AME-AMP smoke](../log/2026-09-17-m1-floating-amp-smoke.md)
- [Small baseline](../log/2026-09-17-m1-small-baseline.md)
- [Large baseline](../log/2026-09-17-m1-large-baseline.md)
- [Regression](../log/2026-09-17-m1-floating-regression.md)
- [1024 stability gate](../log/2026-09-17-m1-floating-1024-stability.md)
- [Final std=1 flat](../log/2026-09-17-m1-std1-flat120.md), [small](../log/2026-09-17-m1-std1-small120.md), [large](../log/2026-09-17-m1-std1-large120.md)
- [Low-noise physical gate](../log/2026-09-17-m1-noise02-drive-probe.md)
- [Low-noise fresh training A/B](../log/2026-09-17-m1-noise02-1024-training.md)
- [Low-noise final flat](../log/2026-09-17-m1-noise02-flat120.md), [small](../log/2026-09-17-m1-noise02-small120.md), [large](../log/2026-09-17-m1-noise02-large120.md)
- [1000-update learning-horizon gate](../log/2026-09-17-m1-noise02-1000-learning-gate.md)
- [Semantic1 wheel-contact audit and physical probe](../log/2026-09-17-m1-obstacle-stop-reward-audit.md)
- [Semantic1 wheel-contact training A/B](../log/2026-09-17-m1-semantic1-wheel-120-training.md)
- [Terminal-failure evaluation fix](../log/2026-09-17-m1-evaluation-terminal-failure.md)
- [Matched-height full-wheel physical probe](../log/2026-09-17-m1-step-height-matched-probe.md)
- [Knee proxy and contact source audit](../log/2026-09-18-m1-knee-proxy-source-audit.md)
- [Probe neighbor-obstacle event trace and isolation fix](../log/2026-09-18-m1-probe-neighbor-contamination-fix.md)
- [Wheel reward implementation and RED/GREEN evidence](../log/2026-09-18-m1-wheel-reward-implementation.md)
- [Wheel reward physical probe](../log/2026-09-18-m1-wheel-reward-physical-probe.md),[8envtraining smoke](../log/2026-09-18-m1-wheel-reward-smoke.md),[fresh1024pilot](../log/2026-09-18-m1-wheel-reward-1024-pilot.md)
- [Wheel reward final flat](../log/2026-09-18-m1-wheelreward-flat120.md),[small](../log/2026-09-18-m1-wheelreward-small120.md),[large](../log/2026-09-18-m1-wheelreward-large120.md),[tail+behavior audit](../log/2026-09-18-m1-wheelreward-tail-audit.md)
- [One-off trace attempts](../log/2026-09-18-m1-wheelreward-exposure-trace.md),[bootstrap one-step probe and stopped profiling route](../log/2026-09-18-m1-reward-hook-bootstrap-probe.md)

- [2026-09-16 M1 AME long-train Vulkan/watchdog fix](../log/2026-09-16-m1-ame-long-train-vulkan-watchdog-fix.md)

## Git Refs

Encounter子包：registry LastFeature/LastVerified `394ea67`；coordinator LastFeature/LastVerified `d27e26c`，main2317full及最终184focused，两组件均SPEC→QUALITY通过。隔离CurrentWorkRef `/data/hexinkun-m1-acceptance-20260918/encounter-worktree` / `codex/m1-encounter-lifecycle`。未推广主源码；旧formal/AME refs不覆盖。

Independent reference adapter scope: LastFeature/LastCPUVerifiedCommit **646f486**,8files exactpromotion,373CPUtests74.37s(main)/75.02s(implementer),SPEC/qualityPASS. Its byte-identical isolatedcandidate has3physicalstrict8/8passes(run14/15/16),butnoadditionalformal-pathphysicalrun claimed. NewscaleCurrentWorkRef is isolated`/home/hexinkun/m1_debug_tools/scale1024_20260918/adapter`,design/plan5553e84; no1024or10000proofyet. Existing metrics/clone/provenance/run.sh unchanged. Production AME refs below remain separate.

- Current Work Ref: `4b5251f` + uncommitted M1 contract/reward/validation changes
- Last Feature Commit: `375e5f5`
- Last Verified Ref: `375e5f5`
- Key Files:
  - [M1 AME headless launcher](../../Go2Pvcnn/scripts/train_m1_cross_large_complex_ame_headless.sh)
  - [M1 AME long-train supervisor](../../Go2Pvcnn/scripts/supervise_m1_ame_long_train.sh)
  - [launcher regression](../../Go2Pvcnn/tests/ame_baseline/test_m1_ame_long_train_launcher.py)

## Next Step

2026-09-20最新入口：registry/coordinator核心与双审已完成，直接Task C vendor+pre-helper边界接入及sync行级release/begin，原始sidecar/独立重放随接线实现。合法CLEAR+phase11的新boundary先将该行phase/steps/drive_allowed初始化，再调用原helper一次，不能为等-1而强制全局扫描空隙。Task B最后两项（真实cache/sync4/5/active/旋转raw连续性）仍未完成，见[计划](../../docs/superpowers/plans/2026-09-19-m1-encounter-integration.md)。CPU不是实机：之后冻结新候选8×32→三次8×1600→1024×32→1024×1600→G2实际返回/连续新对象→AME/named-actions/policy/单进程10000。完整目标ACTIVE，无新增授权阻碍，禁止重新基础审计代替接入。

最新入口：live owner/raw pose及唯一8×32已完成47167e8/main2026CPU/native0、完整采样和清理证据已落盘；直接实施版本化向外public-pose envelope，不重跑旧query/局部geometry/源句柄基础审计。使用已冻结actual32×8×17原始float32姿态与geometry，逐运算外包PxQuat/PxTransform和PxMat33公开映射及必要normalized数学映射，并做独立精确数值回放；明确只承诺公开消费合同，不再追内部SDK指针。之后registry/coordinator/G1三次/1024/G2/AME/named-actions/policy/10000，完整目标继续ACTIVE。详见[现场及下一门槛](../log/2026-09-19-m1-live-provider.md)。下方为历史入口。

最新：局部bounds已完成3d97e9b/main1929CPU与真实136记录回放；直接实施live provider小包，不重复旧全量基础审计/原样负例。初始化复用23raw守卫、同live lease内query→cooked→build，成功后唯一owner持有lease；失败与正常退出都在env.close前关闭。每步复制native17body link pose_xyzw并绑定step/episode/env/body/generation/hash。数学投影必须每算术操作向外包络，显式处理raw q非exact-unit（实际norm²偏差2.54e-7），不可只给最终结果加epsilon。之后接registry/coordinator、三次新8×1600→1024×32→1024×1600、G2真实再遇、AME/named-actions/policy跨绕/单进程10000。原精确失败/物理阈值/分母不变；完整目标ACTIVE，无新权限阻碍。[本轮代码/证据/下一合同](../log/2026-09-19-m1-conservative-geometry.md)。下方历史BLOCKED不代表当前。

当前执行状态为BLOCKED等具体书面审阅；收到用户确认或修订要求后恢复，不重复同一审计或启动旧候选。后续入口仍为下方e25e805→writing-plans/TDD，资源.2b纳入计划。

2026-09-19当前入口：用户已批准具体规格并要求实施，勿再次等待同一批准。A1 f8ce0af全回归/双审查完成，继续G0-B实际collision清单与query绑定，再coordinator/reference-sync/replay。新候选必须三次8×1600→1024×32→1024×1600，G2真实再遇障另有必要路线/场景实现包，均不得冒用旧通过次数。下方A/B/规格待审为历史。

当前 phase 重入源因已闭合，A完成锁存/B延迟接管的用户选择仍待返回；不再重复只读定位同一状态机。首次几何的可重建链已经记录，后续设计需要区分 active swing 的 world 高度与支撑补偿，以及 root/yaw 轨迹控制。不得把两个模块与重入补丁混成未审查的一次试参，也不得在未有设计确认时启动下一物理候选。

Currentuserfocusremainssingle-process10000pluslearnedcross/avoidancewithcontinuous execution. The[1024plan](../../docs/superpowers/plans/2026-09-18-m1-reference-1024-scale.md) reachedactualbaseline18fullrunandcandidate19negative. Nexttraceanddesignphase-completion/reentrycoordinationfrom523witness; keepfirstcrossgeometry18envasseparatechild. Noautomaticretry,noguardremoval,nothresholdrelaxation,noformalpromotion. CurrentGPU7onlyverifiedoriginalreservation351307;stoponlyfreshlyreverifiedownplaceholderwhenafutureapproved/CPUreviewedexperimentneedsGPU. AMElifecycle/namedtargetbridge/learnedavoidanceand10000remainunfinished. Prior8envandbaselinefullexitproofdonotguaranteethese.

Theapprovedplan's120-update run andthreebehavior evaluations arecomplete. Theprofile-basedobserverdidnotproducereliabledata,andthethree-attemptdebugginggateisreached. Askforapprovalofanexplicitopt-indiagnosticinterface:actualrewardmathunchanged,defaultreturnsunchanged,pre-reset/first-episodecollector,CPUequivalenceandone-steprealoutputgatebefore500-stepreplay. Do notchangeweights/curriculumorlaunchformal10000basedonabsentexposuredata. Themonitorispausedwhilethisarchitecturechoiceawaitsapproval;do notreviveoldsupervisororrepeatclosedneighbor/CPUaudits.

## Node Details

The supervisor interprets `TARGET_ITERATIONS=10000` with the runner's
zero-based iteration labels, so successful completion is checkpoint
`model_9999.pt`. It uses per-attempt logs and the cumulative supervisor log.
The default five-minute no-checkpoint window is comfortably above the current
ten-iteration checkpoint interval while still recovering shutdown deadlocks.
`model_N.pt` means update `N` is complete and `next_iter=N+1`; therefore the
10000-update run ends at `model_9999.pt` without replaying the checkpointed
iteration.


### 2026-09-29 M1 10 cm crossing contract checkpoint

The active runtime is M1-specific even though the IsaacLab compatibility
package remains named go2_pvcnn. The current patch fixes forward-probe false
clearance, unknown-cell collision false positives, semantic-2 wheel-support
exemption, single-leg teacher leakage, and layout fallback spacing. M1 uses
0.10 m small obstacles, 0.30 m nominal swing, 6.5 cm planned wheel-bottom
margin, 8--10 separated obstacles, and collision weight -18. Focused evidence
is 65 passed, 1 skipped including the 10 cm planner test. A 100-step PhysX probe
confirmed max_swing_legs=1 and zero collision events but did not provide a
repeatable >=5 cm clearance under the current random obstacle/foot alignment;
the physical gate is therefore still open and no long training was started.
See [M1 contract fix](../log/2026-09-29-m1-10cm-crossing-contract-fix.md).
