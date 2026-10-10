# T306 M1 AME Long-Train Stability

## Current State

只读跟进terminal-obstacle-space：stage2标称后轮严格远侧落足剩余root边界余量.411292m；stage3欠.488708m（+X、585mm标称水平姿态）。不能泛化为所有策略姿态不可能；stage2/3原probe摆放均越界不等于两者都不能跨。候选仅stage3整列后移.6m，仍需动态恢复余量验证，尚未改地形。当前stage1 PID14800继续；raw增量非零但2cm事件/严格成功0。[监控与静态审计](../log/2026-10-10-m1-persistent-monitor-2218.md)。

OPEN同级子节点 terminal-obstacle-space：最终probe的stage2/3末slab外摆放触发现有tile包络timeout。不要放宽边界；需在stage3全程验收前核对最后10cm障碍后轮越障/恢复余量，必要时提出最小布局调整。本轮恢复当前stage1奖励学习不以此冒充8障碍全程通过。[证据](../log/2026-10-10-m1-persistent-crossing-repair.md)。

最新：用户已批准修复后恢复长训。persistent-reward子节点实现逐障碍严格恢复凭据和持久奖励屏蔽，并把实际单轮增量延伸至top+3cm；保持纯PPO/2048和严格成功定义。离线真实旧轨迹及4env2000步新奖励回放均验证绕行后正收益已剥除；最终版本验证/实际resume身份见[记录](../log/2026-10-10-m1-persistent-crossing-repair.md)。恢复后重点核对是否转为原地停滞、真实prelift/clearance/strict recovery，不凭总reward宣称学会。以下等待确认是历史。

最新OPEN子节点 policy-contact-stall：12707已在model600校验后停下；诊断13222完成2000策略步后退出。真实轮底未提前2cm、严格跨越0；恢复门槛失效是策略关节/root偏离而非robot绑定复发。下一步完成未成功越障不得恢复正奖励的有界设计，并处理奖励高度空档；没有部署新奖励或重启长训。[现场记录](../log/2026-10-10-m1-model600-contact-replay.md)。

diagnostic-wiring已修复，212相关测试和4env原生恢复/地图/奖励接线通过。恢复默认路径不依赖debug，.3单遭遇奖励预算按真实轮底新增高度支付；地图保留真实顶部。model_500边界部署，恢复本次谱系；真实跨越/视频验收仍OPEN。[证据与上传](../log/2026-10-10-m1-recovery-prelift-pooling-repair.md)。以下未修复状态为历史。

OPEN子节点pure-ppo-learning/required-crossing/diagnostic-wiring：默认无trace/debug时，ame_env_wrapper恢复块robot未赋值并被except吞掉；CPU原代码重放false，先绑定则true。阻断稳定恢复奖励与课程晋级，但不解释零预抬。stage1 iteration372窗口4322尝试/0成功；本轮用户只要求探查，未修复/停训。地图池化和小探索幅度另作证据分级。[诊断](../log/2026-10-10-m1-perception-reward-diagnosis.md)。

最新required-crossing覆盖下文历史：旧8573停止；用户要求fresh2048/10000，不接旧PT。134相关测试、原生奖励接线通过，能力仍OPEN。[记录](../log/2026-10-10-m1-required-crossing.md)。

用户明确取消速度误差晋级门槛，其他条件不变。20测试通过；一次性watcher8491等待7747的model_500，随后从501续训9499轮，保留optimizer/std/课程。需核实切换结果和更新TensorBoard。[变更与待验证](../log/2026-10-10-m1-remove-speed-gate.md)。[出界异常仍待诊断](../log/2026-10-10-m1-flat-first-boundary-watch.md)。

部署：PID7747，run2026-10-10_14-16-08/bb57e7d，日志/tmp/m1-ppo-flat-first-20261010.log，fresh2048/10000，model_0保存。118测试+最终原生验证通过，生产断言全部2048环境stage0障碍0。TensorBoard/监控已切换。能力未验收。

最新flat-first：旧6169停止，按用户确认从零先训真正空平地，再3/6/10cm和混合地形。三窗口各>=2048完成回合、>=90%完整无失败且误差<.08；障碍阶段另要求稳定跨越率>=.5。课程状态随PT保存，边界保护避免误入邻地块。[实现/验证](../log/2026-10-10-m1-flat-first-curriculum.md)。

新子节点585mm-stance：用户确认按585mm总高度校准初始姿态（非root高度，且较旧姿态低100mm）。99回归与独立4环境5秒静立通过，0重置，最大倾角0.438度，承重后高577–578mm。用户随后要求从零，旧4930和等待400的watcher已停，新6169训练2048环境10000轮，无resume/旧checkpoint。实际抬轮/跨越尚未验证。[记录](../log/2026-10-10-m1-585mm-stance.md)。

新子节点 narrow-probe-repair：15cm间隔奖励采样漏掉5cm障碍；加密为2cm且保持原探测范围，7RED→117GREEN。已在model_300边界部署、2048两轮通过；model_302续训9699轮，启动PID4930，日志/tmp/m1-pure-ppo-denseprobe-20261010.log。不能把测试等同学习成功。[记录](../log/2026-10-10-m1-ppo-narrow-probe-repair.md)。

最新用户更新：2048环境，前方加密单轮10cm障碍。dense-forward-2048子节点已实现布局、固定朝向及命令边界，108测试通过；256训练已停在已保存model_100之后。原生几何、2048两轮更新均通过，model_102续训9899轮，启动PID3886，不宣称跨越成功。[日志](../log/2026-10-10-m1-dense-forward-2048.md)。

2026-10-10 新子节点 pure-ppo-learning：按用户要求停用 MPC/模仿/接管，奖励地形调优。
新服务器 GPU0；旧 GPU7 状态不可推用。103 项测试和最终256环境2轮 smoke 通过。
目标长训10000轮、保存100。跨越能力仍未验证，不用代理奖励冒充严格成功。
开放：学习效果/严格成功、课程初始层级观察、奖励刷分检查。
Baseline/Last Feature Commit: bb57e7d; Current Work Ref: codex/m1-contact-recovery (uncommitted).
Last Verified Commit: bb57e7d plus tested diff, no physical crossing acceptance.
[验证/下一步](../log/2026-10-10-m1-pure-ppo.md)。下文为历史状态。

2026-10-09 user-requested current-version upload: child contact-transition-consistency
now includes contact_inventory (retains zero-force geometry without inventing
support) and near_contact_gap_constraints (material-point semiimplicit preview
at every substep, acceleration inequalities only). Fresh215WBC tests pass.
Not integrated into live control and not physical crossing acceptance. Native
capture794230 was still running at upload precheck; no result claimed here.
Source baseline eaa2c30; publication preserves GitHub parent951c6e4, no force push.
[Verification](../log/2026-10-09-m1-current-upload.md).

2026-10-09 contact-transition-consistency progress: raw history proves FAR
new point exists while force0 and gap decreases64.79->46.65->28.14um before
impact. Current strength<=.001filter discards it. Attransition oldvn+8.04mm/s,
newvn-5.81mm/s; all-attached is invalid. However simply releasing eitherpoint
is also infeasible with full dynamics/original20Nm/s slew; never applied.
Next dependency: retain near-contact geometry and verify anticipatory/impact
mode feasibility, preserving every point's wrench/nonpenetration.
Child released-material-bias fixed byTDD: transport bias only attached,
material bias released;200WBCtests pass. All-attached live behavior unchanged.
No active native job or train; GPU7 placeholder1768831 untouched.
[Native evidence](../log/2026-10-09-m1-wbc-patch-transition-history.md),
[model correction](../log/2026-10-09-m1-wbc-released-material-bias.md).
Current baseline/lastverified before this change:c90bb1d; prior uploaded
snapshot remains951c6e4. Physical release/lift/roll/landing/crossing still OPEN.

2026-10-09 child execution-physical/handoff-transient/braking-allocation OPEN:
native clock now verified; stronger294ms settle does not prevent default
support runaway (500tick probe fails498,speed.080146m/s).
Full frozen LP atnative294/400/700 confirms current one-step braking target
infeasible under original20Nm/s slew. Frozen30step base-first ramp reaches
target whereas equal22DOF objective does not. This motivates diagnostic-only
base-first priority, not a slew increase or claimed physical rollout.
New opt-in `--base_priority`, default off,197WBCtests pass. Native candidate
maxspeed.006235,last.003269m/s, but contact equations fail atfeedback471.
New child contact-transition-consistency must resolve actual rejected
multi-contact equations before lift/roll/landing. Do not restart long train.
Captured native764 failure has5points/[1,2,1,1] perwheel. Contact-only full
equations plus originalaccelbox independently infeasible; normal-only and
tangent-only separately feasible. Current all-loaded-points-attached model
requires a verified patch transition; do not silently delete a point.
[Settled support](../log/2026-10-09-m1-wbc-settled-support.md),
[feasible-set audit](../log/2026-10-09-m1-wbc-braking-feasibility.md),
[priority experiment](../log/2026-10-09-m1-wbc-base-priority.md).
Latest feature ref223a0ec; candidate codex/m1-contact-crossing uncommitted.
Uploaded snapshot951c6e4 onGitHub m1-10-9 remains the prior exact223a0ec tree.

2026-10-09 child T306/execution-physical/handoff-transient OPEN: native snapshot
replay changes next action. Same complete contact model: loosening only torque
slew offline changes qdd_x+1.326 to-0.190m/s2; zeroing only normal RHS leaves
+1.327. This does NOT authorize slew relaxation. Snapshot was captured at22ms
with knee velocity~.20--.23rad/s: investigate premature handoff, collect stronger
settled evidence before physical WBC use.
[Counterfactual](../log/2026-10-09-m1-wbc-handoff-counterfactual.md).
Production-PD PREPARE corrected to4s and8/8ready; PD UNLOAD fails0/8.
Selected world-height correction also failed atstep19; no actual lift/crossing.
[PD evidence](../log/2026-10-09-m1-pd-unload-diagnosis.md).
These current results supersede older400step readiness and pending-unload notes.

2026-10-09 new child T306/mixed-terrain-registry: requested reference mixed
terrain and flat small density x1.5, M1 retained. Dependencies are safe exact-count
placement, actual grounded obstacle registry, reset/terrain mapping, direction-aware
strict event metrics; fixed-six generation and tracker cannot be used unchanged.
CPU old random sampling165small+3large failed10/10seeds. Approved implementation
uses structured candidates, now20/20seeds exact-count with.45m clearance. Mixed train
profile wired with M1 retained. Independent review4important fixes have regression
coverage;148passed/1skipped final expanded suite. GPU0 native scene/scan passed:
2376records,2280small10cm bounds,172semantic-small rays,2neutral steps.
Probe ended; physical crossing OPEN, no long training.
[Verification](../log/2026-10-09-m1-mixed-terrain-verification.md), [Progress](../log/2026-10-09-m1-mixed-dense-progress.md),
[design](../../docs/superpowers/specs/2026-10-09-m1-mixed-dense-terrain-design.md).
Prior live2step measured-bottom marker recovered: finite4wheel values, strict0;
physical lift/crossing still open. GPU7 placeholder1768831 unchanged.

2026-10-09 clearance measurement child: oriented authored mesh bottom now feeds
strict tracker;52tests passed and CPU USD/full-mesh extrema oracle agreed.
No controller/pose edit or physical crossing acceptance; live-stage geometry
readback remains next dependent check. Climb numeric pose still pending after
protocol PDF audit. [Evidence](../log/2026-10-09-m1-oriented-wheel-bottom.md).

2026-10-09 user clarification: use vendor Climb posture, not maximum extension.
New child T306/climb-posture-source OPEN: Climb/state8 differs from Stair and
HighLowStance; inspected public files do not define numeric pose. Obtain vendor
preset or settled joint/IMU capture and verify USD mapping. No guessed height
deployed; bottom-clearance focused tests47passed, physical gates still open.
[Evidence](../log/2026-10-09-m1-climb-sdk-and-bottom-clearance.md).

2026-10-09 measured PREPARE update: new shared per-row production-PD controller
uses COM/contact feedback, frozen wheel anchors and bounded acceleration.
Final observation retains the last executed reference.92focusedtests passed.
GPU0 production-PD400step run ended8/8ready; fresh support margins31.31--34.40mm,
max tilt component0.533deg, non-wheel contact force0. This only proves PREPARE.
[Evidence](../log/2026-10-09-m1-batched-prepare-controller.md).
T306/execution-physical remains OPEN: next measured UNLOAD handoff preserving
actual actuator ownership, then lift/roll/landing; never fake effort-allocation
evidence. No long training, no live bounded probe; GPU7 placeholder untouched.

2026-10-09 latest: official41kg robot +30kg payload clarified; freshUSD mass
41.045319557kg matches. Corrected post-IK knee corruption, Cartesian rate
limiting/event-hold references, 50% runner teacher attenuation, absent wheel
observations, worktree launcher defaults, and non-10cm course shapes/embed.
Focused124passed/1skipped; new actor/critic dims1589/1592 verified in real Isaac
and require fresh training. Physical gate FAILED: first selected-wheel lift
loses support; first post-step COM19.36mm outside three-wheel triangle.
Holding stance joints fixed also fails (selected lift19.32mm, tilt.444rad).
Raw reference validity is now separate from safe fallback execution/imitation;
100-update checkpoint watchdog no longer mistakes healthy updates for stalls.
No long training; GPU7 placeholder1768831 untouched, all bounded probes ended.
Do not call CPU success physical crossing or start training without the
lift/roll/landing gate. WBC attribution from old shadows was confounded and
has been corrected in the [new evidence log](../log/2026-10-09-m1-parameter-and-execution-repair.md).

Open child T306/execution-physical: port existing measured PREPARE->UNLOAD
ownership into the production-equivalent execution path, with per-env state,
then verify all wheel/obstacle pairs and integrate verified WBC ownership.
Older original-SDF diagnostic lifted159.4mm but failed LAND; it used effort
compensation absent in current PD teacher and is not a ready crossing policy.
Sibling T306/wbc-contact-oracle: same-state snapshots and
single-variable normal/effort-slew/force-point comparisons remain needed.

2026-10-09: crossing remains the first gate; post-crossing balance recovery is
separate. The live-USD six-obstacle swing geometry probe predicts 5 cm wheel
clearance and 22 cm far-side landing margin, but this is not physical evidence.
Teacher PhysX probes at 320 and 64 control steps both ran >7 min without a
final report and were stopped by exact PID; no training/checkpoint write
occurred. Added stage/per-eight-step progress telemetry and its test (1 passed).
Latest GPU7 audit: user's placeholder PID 2803 restored; separate `python3`
PID 4139569 uses 3194 MiB and GPU7 utilization is 100%, untouched. Do not
restart the physical smoke until that shared GPU7 process is absent or the user
confirms it may be shared. Training stays stopped; the swing/QP path still
needs actual controller integration and strict single-obstacle clearance plus
far-side touchdown proof. [Evidence](../log/2026-10-09-m1-teacher-physx-probe-performance.md).

2026-10-08 latest WBC flat-support investigation: damping target now uses the
root-COM velocity coordinate, with 31 focused tests passing. The physical
recheck still fails at step 48: speed reaches 0.08098 m/s while all wheel
loads and attitude remain stable. Full rolling constraints select +1.39 m/s²
forward acceleration even without effort slew, whereas the invalid
normal-only ablation tracks the requested braking acceleration. This points to
the rolling-contact kinematic constraints, not rapid balance recovery; do not
relax hard constraints or attempt crossing until the live rolling oracle is
resolved. Same-state diagnostics show that dropping either local tangent alone
still produces +1.33/+1.38 m/s²; only dropping both (invalid normal-only model)
tracks the target. The interaction remains unresolved. GPU7 placeholder
restored; training remains stopped.
[Evidence](../log/2026-10-08-m1-wbc-support-hold.md).

2026-10-08 newest scene finding: the previous fixed course at `y=+/-0.35 m`
missed measured wheel tracks at `y=+/-0.215 m` by about 8.7 cm after envelope
widths. Corrected all six alternating blocks to `+/-0.215 m`; a fresh GPU7 USD
probe verified 48 mm target-track lateral overlap and 382 mm clearance to the
opposite track. This is layout exposure evidence only, not a crossing. Five
blocks are 10 cm high and one is 5 cm by actual bounds. Focused WBC/course suite
is 173 passed; training remains stopped. Next: use the actual bounds and
single-wheel swing/QP task in a physical crossing probe, with three-wheel
support and collision/clearance/far-side touchdown gates. Balance recovery is
tested only after strict crossing passes. [Evidence](../log/2026-10-08-m1-obstacle-track-alignment.md).

2026-10-08 latest: added a test-verified single-wheel swing trajectory and
acceleration-bias-compensated QP task (165 focused WBC tests pass). It is not
yet integrated with an obstacle scene/controller loop; no crossing has been
physically demonstrated and training remains stopped. Next verify actual M1
wheel-center Jacobian/obstacle collision filters, integrate the swing task,
then test one wheel at a time while the other three support. Strict crossing
success is the first gate; only after landing beyond the obstacle with the
required clearance/no collision will rapid balance recovery be evaluated.
[Evidence](../log/2026-10-08-m1-single-wheel-swing-reference.md).

2026-10-08 WBC ground-contact probe: CPU adapter/QP tests plus contact contract
pass, full `tests/test_m1_wbc_*.py` is 142 passed. One-env GPU7 flat smoke
observed four native wheel contacts by raw tick 8, after seven zero-force ticks;
touchdown loads were unequal/transient (about 102/218/226/218 N), so this is not
stance or balance evidence. [Contact evidence](../log/2026-10-08-m1-wbc-ground-contact-observability.md).
GPU7 `sleep.py` placeholder restored, no training. Next: implement a measured,
same-state transfer from settled native PD support to explicit WBC effort with
no physics tick between removing K/D and writing equivalent torque; verify
named 16-DOF order, sustained support and slow roll before attempting individual
wheel obstacle crossings. Cross success remains the first acceptance; recovery
is measured only after crossing. Do not start PPO training yet.

2026-10-08 actual free-execution child:125tests;8rows x3ticks QP efforts
actually applied, nativeK/D0 andreadback verified, explicit prior-tick history.
Max dynamicsresidual.0057068<.02; kinematiclinear.000747/angular.000653.
[Evidence](../log/2026-10-08-m1-wbc-execution.md). Contacts0, no support/stance
claim. Nominal20Nm/s slew exceeds by5.483e-8Nm/tick within1e-6Nm numericalcheck;
report qualified, not exactbound. Next grounded initialization/continuity,
then stance/roll. Baseline60906c0, feature/verifiedthiscommit, placeholder1018794.
No gravity/sourceUSD/display/driver changes, no training/crossing acceptance.

2026-10-08 limits child:124tests; explicit named leg.5rad/s diagnosticcap,
wheel existingcap; pure20Nm/s planned total-command interval requires fresh
same-episode explicit history, no implicit zero/estimate. Native shadow still
feasible; no actuator consumer. [Evidence](../log/2026-10-08-m1-wbc-limits.md).
Ownership child: directactuation0, projectedmax15.94Nm, cachedapplied27.79Nm,
K/D800/40 legs,0/5wheels. Cannot label any as verified total command without
oracle. Next fresh diagnostic environment explicit-total initialization and
continuity, no PD hot-switch. Baseline359c5d3, feature/verifiedthiscommit;
placeholder982669 restored, no physical stance/crossing or training.

2026-10-08 joint-state-bound child:116tests. Rearrelease shadow now feasible
using native/configured q/v-derived next-step bounds, maxeffort12.518Nm,
residual7.8e-7, legaccelmax1.0942. Original diagnostic box retained as failing
control. [Evidence](../log/2026-10-08-m1-wbc-joint-bounds.md).
New dependent child: leg speed limits are unset sentinel5.939e36 (source legs
actuator has no velocity_limit_sim); wheel limit20.84245 explicit. Thus no
real motor speed certificate. Require explicit conservative diagnostic speed
policy and total effort-slew/sole-owner handoff before actuation; source USD/
training config unchanged. Baseline8751554, feature/verifiedthiscommit,
placeholder943133 restored. No physical stance/crossing/training accepted.

2026-10-08 live-step child:113tests, full nativeh/materialbias/actualvelocity
in read-only semiimplicit contact predictor. All3modes rejected, no command.
CPU attribution: allattached equalities inconsistent (maxfiterror.0002458);
rearrelease consistent but contact+separation already exceeds diagnostic
acceleration box (minimumuniformfactor1.0543, NOT adopted); oppositerelease10.5667.
[Evidence](../log/2026-10-08-m1-wbc-contact-step.md). Next child: distinguish
reference limits from actual state constraints, finite-step convergence and
actuator handoff. No velocityreset/guard relaxation. Baseline0bce18a,
feature/verifiedthiscommit diagnostic-only; placeholder913319 restored.

2026-10-08 live-motion child:109tests; added all-entry native contact separation
and material-point normal/tangent velocity relative to fixed terrain. FAR rear
separates2.374mm/s, front approaches1.652mm/s, maxslip2.682mm/s. Ten entries,
one zero-force duplicate. [Evidence](../log/2026-10-08-m1-wbc-motion.md).
New dependent child: velocity convergence/unilateral impact transition, required
before physical stance/rolling because zero acceleration does not eliminate
existing closing/slip velocity. Do not reset velocity or relax guards to proceed.
Baseline0b73832, feature/verifiedthiscommit; placeholder889301 restored.
No applied WBC or training. Snapshot scope env0, not multi-seed motion acceptance.

2026-10-08 numerical fallback child:105tests; OSQP .03s plus active-set within
remaining .05s total stage budget, original full constraints retained. Native
allattached solved via4.40ms fallback, violation5.53e-7, but rollingerror.5210482.
Correct rearpointrelease still rollingerror2.286e-7. No feasibility/success
conflation. [Evidence](../log/2026-10-08-m1-wbc-active-set.md).
Baselinef0c1364; candidate/verifiedthiscommit (CPU/native counterfactual only).
Next moving-state validity and physical stance/roll. Placeholder867270 restored;
no applied WBC or training. Scaling/dedup-only variants rejected, no guards relaxed.

2026-10-08 native point-mode child:100tests. Exhaustive3geometric rest candidates,
duplicates preserved. FARrearpointrelease: forward.04999985, wheelangular~.5210612,
rollingerror2.29e-7, stable-rooterror1.05e-7, releasednormalacc+.02868, releasedforce
4.36e-8N, maxhardviolation4.29e-8. Opposite releasevalidbut rollingerror.521;
allattached solvedinaccurate at10000iterations rejected (NOT proofinfeasible).
[Evidence](../log/2026-10-08-m1-wbc-candidates.md). Open sibling: allattached
QP conditioning/degeneracy; no solverguard relaxed. Next movingstate gap/slip/
velocity validity and actual soleowner stance/rolling; no appliedcontrol.
Initial probe missingradiusimport fixed after traceback/RED regression.
Baseline8a145fb, feature/verifiedthiscommit (CPU/restshadowonly); placeholder786369.

2026-10-08 rolling mode child:95tests. QP separation lower bounds are hard,
residual-checked and task-independent. Explicit candidate adapter forces released
points tozero force while preserving normalacc bounds and point ordering.
Synthetic rearpoint-release/frontpivot test passes; allfixed correctly rejects.
[Evidence](../log/2026-10-08-m1-wbc-modes.md). Native automatic mode selection,
current gap/slip/normalvelocity validity, transitions/impacts still open; no
claim that the helper determines physically valid modes. Baseline4d8e577,
feature/verified ref this mode-constraint commit, CPU-only. No GPU/processchange.

2026-10-08 WBC transport child:86CPU tests, formula distinguishes moving geometric
evaluation point from material point; independent finite difference and coupled
rolling QP tests pass. Native env0 counterfactual static allocation feasible:
maxresidual3.56e-15, maxeffort14.25Nm, wheel loads101.56/118.92/105.75/86.44N.
[Evidence](../log/2026-10-08-m1-wbc-transport.md). No WBC efforts applied.
New explicit open child: native polygon contact-mode/point-release transitions,
needed because multiple simultaneous fixed material contacts can lock wheel spin;
smooth-circle test does not justify circular M1 collision approximation.
Then actual torque stance/rolling, single-leg stages. Baselinefcfd151, current
feature/verified ref this transport commit, scope numerical/staticonly.
Placeholder736509 restored; no training/crossing claim.

2026-10-08 WBC material child (dependency of contact QP):77tests, env0 live
mu boundsFBL.5992/FAR.5486/RBL.7072/RAR.5856, not assumed1.0. Ground1/multiply,
robot modes from installed schema defaultaverage; robot coefficients MUST come
from native runtime because startup randomization is not reflected in USD.
[Evidence](../log/2026-10-08-m1-wbc-materials.md). Fixed diagnostic observability
for exception hidden by Kitclose; raw failures retained, success markers mandatory.
Baseline dfdcfe2; current feature/verified ref this material commit (audit only).
Next rolling migration constraint/native stance. Placeholder706235 restored;
no training or physical crossing claim. Per-episode multi-env integration open.

2026-10-08 dynamic-WBC kinematic child: recursive Jdot*v-equivalent body bias
with root-COM generalized coordinates and actor-frame authored joint tree.
63CPU tests; native8rows x3ticks maxlinear.000743m/s², angular.001352rad/s²,
both <preset.02. [Evidence](../log/2026-10-08-m1-wbc-kinematics.md).
Baseline/previous feature eecc94f; current work ref codex/m1-contact-crossing;
feature and verified refs: this kinematic-bias commit (limited dynamics scope).
Next rolling contact migration/effective friction, then stance; no crossing or
training yet. Placeholder650836 restored. Material-point bias must NOT be
silently turned into zero material acceleration for a smoothly rolling wheel.

2026-10-08 contact adapter:52tests, preserves point momentarms and ownergroups;
native env0 has9points/4wheels, normalclosure7.63e-6N, pointvelocity9.40e-9.
[Evidence](../log/2026-10-08-m1-wbc-contacts.md). Next rollingacceleration and
effectivefriction before stance; no motioncontrol/training change. Placeholder532072.
Baseline82fa957; verifiedgeometry only, otherenv/physicalcrossing unverified.

2026-10-08 WBC CPU QP:45regressions/15solver tests pass; fullM+3Dforces,
friction/normal/effort/qdd/contact constraints, taskhierarchy and post-solve rejection.
[Evidence](../log/2026-10-08-m1-wbc-qp.md). No native contact wiring yet;
next measured geometry/rolling constraints then stance. Baseline6b41093;
verifiedCPUonly. Placeholder354723untouched, no training/crossing claim.

2026-10-08 free-body oracle:30tests; native gains0 and requested efforts match;
24row-ticks contact0, dynamic residualmax.00562<.02. Correct C far outperforms
omission/reversal (~.0005 vs .062/.124 RMS). [Evidence](../log/2026-10-08-m1-wbc-free.md).
Next contact/effort QP, then physical stance/rolling/crossing; no training.
Placeholder354723restored. Baselineb4793da; verified free-body scope only.

2026-10-08 WBC model child: independent fullM initially0.009 mismatch; isolated
installed inertia actor-vs-principal-frame convention, corrected observer only.
28tests and8row native fullM3.81e-6/velocity5.96e-8/energy2.24e-8J pass.
[Evidence](../log/2026-10-08-m1-wbc-energy.md). Next Coriolis/actuator response,
not training. Placeholder275143restored; baseline029a543, verified scope model only.

2026-10-08 native snapshot:22CPU tests,8row fullM SPD; gravity3.05e-5,
translationmass3.81e-6 errors pass static1e-3 thresholds. Read-only afterwarmup,
no PREPARE/lift. [Evidence](../log/2026-10-08-m1-wbc-native.md).
Next dynamic velocity/frame/energy oracle before actuator/QP. No crossing/training;
placeholder240899restored. Baseline2d1ee63; verified scope staticnative only.

2026-10-08 written design approved by user. Implemented isolated full dynamics
snapshot (22coordinates, named permutation, SPD/finite/freshness, no buffer alias).
21tests pass after RED. Next native oracle before any actuator/QP integration.
[Evidence](../log/2026-10-08-m1-wbc-snapshot.md). Baseline Ref:7b74415;
Last Feature/Verified: this snapshot commit (CPU contract only), full crossing open.

2026-10-08 read-only installed API audit: generalized M and full gravity/Coriolis
compensation wrappers available; old APIs omit root. Effort API adds to native PD,
so total torque ownership needs native-drive verification. No runtime changes.
[Evidence](../log/2026-10-08-m1-wbc-api.md). Written-spec review still pending.

2026-10-08 user approved dynamic whole-body control before retraining. Child of
rolling-support failure: [written WBC design](../../docs/superpowers/specs/2026-10-08-m1-dynamic-wbc-design.md)
ready for review; next implementation plan, not training. Full torque ownership,
rolling constraints and unchanged guards specified. GPU7 placeholder99388 untouched.
[Design evidence](../log/2026-10-08-m1-wbc-design.md). Baseline Ref:6db197a;
Last Feature/Verified refs below unchanged (documentation-only update).

2026-10-08 measuredhandoff:55tests, all8settled at96; rollstarts then, same4sbudget.
ROLL5 row7FBL21.16N stillrejects, so settledentryfixed butrolling supportunsolved.
Next dynamiccontactwrench/stancecontrol, noadditionalentrywait/mesh sweep.
Placeholder99388restored; no training. [Evidence](../log/2026-10-08-m1-lift-handoff.md).

2026-10-08 opposite mesh-pair diagnostic:13tests;10internalfaces canceled perwheel,
outer sampled supportunchanged. PhysicalROLL0 underload18.72/26.06N, notpromoted.
Next event-gated LIFT→ROLL settling rather than fixedtimehandoff, samebudget/guards.
Placeholder62471restored; no training. [Evidence](../log/2026-10-08-m1-mesh-pairs.md).

2026-10-08 entry capability mismatch fixed: runtime now selects only executable
translation candidates,20tests, actual2.5msentry8/8valid;5msbaselineplanunchanged.
2.5msphysical passes entry but fails PREPARE62/RBL0N, so refinement not promoted.
Next contact/stance robustness, no resolution sweep. Placeholder13723restored.
[Evidence](../log/2026-10-08-m1-entry-capability.md).

2026-10-08 patch attribution: unchanged128trajectory shows constant targets,
smooth wheel torque, contact minseparation.987→1.182mm during load loss.
256-onlycomparison keeps mass/inertia/materials but fails earlier LIFT5/FBL9.62N;
not a fix,128defaultunchanged. Next collision continuity/contact coupling audit.
7tests;placeholder4171104restored,no training. [Evidence](../log/2026-10-08-m1-roll-patches.md).

2026-10-08 native5ms rolling audit:153tests, full lift_samples exactly baseline.
Action95 finalsubstep FBL46.29→12.21N with COMvertical acceleration-.862m/s2
and root angular impulse. Healthy earlier samples cannot replace force guard.
Next contact/stance-actuator coupling, not scalar speed or averaged COM tuning.
Placeholder4135886 restored; no training. [Evidence](../log/2026-10-08-m1-roll-substeps.md).

2026-10-08 rolling dynamics child:149tests pass. Existing zero-start ramp fails
ROLL3; initial-aware opt-in ramp removes zero reset but fails ROLL6 with row7
FBL12.21N, margin37.67mm and nearly-level body. No LAND/training. Static support
is insufficient for acceleration/braking; next coupled load/COM control audit,
not further scalar profile/gain sweeps. Placeholder4102845 restored.
[Evidence](../log/2026-10-08-m1-roll-continuous.md).

2026-10-08 measured-support child progresses: instantaneous35N recovery needs
78.8446mm within80mm. Opt-in UNLOAD actual-COM feedback initially timed out;
fixed double limiter by sending feasible desired_root to acceleration ramp.
144tests; physical all8 UNLOAD ready84, LIFT159.36..159.80mm,20ROLL steps;
LAND11 row5/RBL force8.193N stops while static allocation remains feasible.
Next braking/lowering overlap dynamics child, not static reserve relaxation.
Placeholder4039652 restored,no training/crossing claim.
[Evidence](../log/2026-10-08-m1-unload-support.md).

2026-10-08 support-drift child refined: common global translation does not change
support loads. Counterfactual actual-joints/entry-attitude gives35.107N vs actual
29.991N, but physical bounded attitude feedback reduces tilt without support gain:
still29.990N/LIFT36 rejection.103 tests; defaultoff, no training; placeholder3976474.
Next direct measured support-relative COM placement feasibility/control, not more
attitude gain or threshold relaxation. [Evidence](../log/2026-10-08-m1-attitude-feedback.md).

2026-10-08 anticipatory runtime child: default-off fixed entry reference through
PREPARE/UNLOAD,74 tests pass. GPU7 all8 PREPARE ready, UNLOAD66 then LIFT36
allocation rejects row0/FBL: nominal36.446N vs actual static29.99065N; measured
support32.727N does not establish static feasibility. Support anchor drift18.15mm,
actual rise52.62..56.59mm, no ROLL/LAND/training. Placeholder3872161 restored.
New blocking child: anchor drift/compliance and measured-geometry feedback;
do not promote fixed-entry open-loop candidate or relax safety limits.
[Evidence](../log/2026-10-08-m1-anticipatory-runtime.md).

2026-10-08 userconfirmedPREPARE4sonly; design/probe200stepcapupdated,33tests
pass, goalactive/noapprovalpending. Next opt-inentryforecastreference and
continuousUNLOAD, then physical200stepcomparison. Otherboundsunchanged.
[Evidence](../log/2026-10-08-m1-prepare-four-seconds.md).

Transferdeadline child:actualramp70/75mm needs3.44/3.56s;2sabsolute
rest-to-restbound48mm. Offline4s8rowIK/slew pass max.122943rad/s, noforceproof.
Historical userchoice resolved by confirmation2026-10-08; PREPARE4sonly approved.
Goalactive/no training. [Evidence](../log/2026-10-07-m1-transfer-budget.md).

Causalentryforecast child:19tests, trueentrysnapshot CPU2401posesx17heights
finds8/8eligible, RPdelta0 shifts20..75mm, worst35.25N. Next selectedreference
boundedtransfer/path/effort+physicaltracking, notrepeatstaticinventory.
Placeholder656674restored,no training. [Evidence](../log/2026-10-07-m1-entry-forecast.md).

Candidate selector child:20tests, allsuppliedliftheights mustmeet35N/20mm/IK,
unchanged80mm/posebounds; invalidrows index-1. Next actualentrysnapshot and
causalforecastgeneration (historicalPREPARE lacksquat/joints), then pathslew
and physicalsupport. [Evidence](../log/2026-10-07-m1-anticipatory-selector.md).

Anticipatorypose child:offline1715poses/row entryanchors+160mmlift gives35N
solutionsall8;lateFBLanchorsnoneinfinitegrid. FBLactualroot86.95..86.98mm
despite80mmreferencebound. Next causalentrycandidate/fullpath/driftcontrol.
No dynamicproof/physicalrun. [Evidence](../log/2026-10-07-m1-support-pose.md).

Predictor implementation child:8tests, puretorch namedjointcandidateFK,
792nativeposes float32COM/body<5.74um,float64<4.27um; reversednamedcolumns
exactlyequivalent. Next anticipatorysupport feasibility/integration; predictor
notyetwired, no newphysicalrun. [Evidence](../log/2026-10-07-m1-mass-predictor.md).

Directnativepose replay child verified:3tests,792rowposes, wholeCOM4.27um,
bodyCOM3.67um. Observer preserves exact baseline99samples andROLLrejection.
Next testedcandidatepose predictor/anticipatorysupport, not another massaudit.
Placeholder424671restored,no training. [Evidence](../log/2026-10-07-m1-native-com.md).

Anticipatory-support FK replay:792 recorded row-samples, maxCOM4.33um and
wheel/root rigidfit3.12um. Wheel-fitted attitude is not independent rootpose
validation. Next testedpredictor and directroot/bodyCOM comparison, then
anticipatorysupport. [Evidence](../log/2026-10-07-m1-com-replay.md).

Anticipatory-support source inventory:17bodies,16revolutejoints,total41.045319557kg
matches native total. Eachleg5.19883kg; preserve baseCOM offset and FBL_HIP
nonidentity parentrotation. Next named-joint FK versus nativeCOM, then support
reference change; no physical validation claimed. [Evidence](../log/2026-10-07-m1-mass-tree.md).

Anticipatory-support child:12tests; currentSDFROLLloadfeedback rejects9,row4
reason3. Needed35Ntarget requires80.76mm; optimal halfplaneentryprojection
still80.713mm>80mm. Proveninfeasibleonlywithin fixedpose lineartranslation
model, notfullrobot. Fullswingfrontgravityreserve~31N vsPREPAREtarget35.
Next anticipateliftedlegCOM/geometry and boundedposture, not relaxbounds.
Placeholder134617restored,no training.
[Evidence](../log/2026-10-07-m1-sdf-load-feedback.md).

LIFT gate-wiring child FIXED: activeworldmode passedNone althoughadvancewas
computed. Earliernotesclaimingheightpaused werewrong.29tests; actualphysical
targetincrements onfailedgate14/14baseline→0/9candidate. UNLOADunchanged.
StillROLL13reject row0RAR28.21N,travel1.8..3.0mm,noLAND. Nextproactive
supportredistribution; no thresholdrelaxation/training. Placeholder65616restored.
[Evidence/correction](../log/2026-10-07-m1-lift-gate.md).

LIFT/ROLL support child:18tests; no-ramp handoff comparison preserves exact
UNLOAD/LIFT, advances0.8..1.5mm thenrejectsROLLoffset10(row5RBL27.72N).
Notsolecause: LIFTbelow30 counts[0,4,3,1,0,3,1,2], worst17.37N beforeROLL.
Next proactive support redistribution/boundedCOM using currentcontact model,
not thresholdrelaxation. Placeholder4155417restored; no controlcodechange.
[Evidence](../log/2026-10-07-m1-roll-handoff.md).

UNLOAD acceleration child:49tests; opt-in existingcom_step fixed-entryroot
wrapper lowers referenceacceleration~2→.029m/s2.8/8unloadready64, alllegs
rise159.6..159.8mm, tiltmax.013rad. LIFTsupportmin17.37N (notuniform>=30);
ROLLoffset5 rejects row1RBL29.69N. No meaningfultravel/LAND/obstaclesuccess.
Next LIFT/ROLL supportcontinuity and residualCOMvelocity; keepguards.
Placeholder4054047restored,no training.
[Evidence](../log/2026-10-07-m1-unload-ramp.md).

Dynamic-support/friction child:7tests and exact baseline physical outcome.
True friction moments4.18..5.12Nm, horizontalforces match mass*COM acceleration
to~1e-5N; lowwheel gravity-only34N -> friction-balanced19..21N,actual23..27N.
Remaining angular/vertical dynamics explain model scope, not exact WBC proof.
Next commanded COM braking/acceleration and settled unloading coordination;
do not subtract measuredfriction blindly into Z-onlysolver. Placeholder3932345
restored,no training. [Evidence](../log/2026-10-07-m1-friction-substeps.md).

Dynamic-support child: mass-weighted COM velocity and normal XYZ telemetry
added read-only, 3 tests and exact baseline UNLOAD reproduction. At48..52
lateral mean acceleration magnitude0.16..0.18m/s2; normal-force API omits
friction, so wheel-traction causality remains unproven. Next friction/momentum
measurement before control change. Placeholder3835014 restored, no training.
[Evidence](../log/2026-10-07-m1-com-substeps.md).

Namedforce/substep child: authoritativeplanner orderFBL,FAR,RBL,RAR; prior
row0/4FAR humanlabels wrong, numeric data unchanged; runtime mapsnames.
Underloadedrear kneePD-.405..+.602Nm aftercorrectmapping, not~-18Nm.
Read-only53UNLOADactions reproducebaseline exactly;5mssubsteps prove declining
support, finalmeans22.65..26.55N andallfinalsubsteps<30N. Notendpointnoise.
Next dynamicCOM/momentum/contactcoordination, notPDcancellation/thresholds.
Placeholder3692792restored,no training.
[Evidence](../log/2026-10-07-m1-support-substeps.md).

Settled-height activation child:39tests, activation31..41; UNLOAD52 allselected
0N but FAR/FBL otherwheel26..29N<30N. Row4desiredshift80.275mm>80mm rejects53.
NoLIFT/acceptance. Next three-support target/actualforce andstancecoordination,
not more height/bounds tuning; keepdefaultoff. Placeholder3579350restored.
[Evidence](../log/2026-10-07-m1-height-settled.md).

Height-only candidate child:46tests, exactFKworldZ/bodyXY/stance9 verified.
Physicalphasehold+heightonly rejectsUNLOAD12, FARdesiredrootshift80.61mm>80mm;
heightreference0, selectedcontact34..52N at11. NoLIFT/physicalheightproof.
Next earlytransferCOM/support/effort/correction-timing comparison; preserve
80mm andallgates, no defaultpromotion/training. Placeholder3502498restored.
[Evidence](../log/2026-10-07-m1-height-only-frame.md).

Unload-realization child:21tests, samephasehold butfullXYZpose rejectsUNLOAD15
(FARdr~[-15.75,-20.19,-1.65]mm>25mm). Do notpromote. Baselineverticalonly
heightlag3.4..4.2mm matchesignoredroll/pitch lever3.6..4.5mm.588/596failed
rowframesselectedforce>5N; effortsettled notlateblocker. Next exactworldZ
correction preservingselectedbodyXY andstance9joints; existinggatesunchanged.
No newruntimecode/training;placeholder3429808restored.
[Evidence](../log/2026-10-07-m1-hold-pose-attribution.md).

Wheel phasehandoff child:20tests;100PREPARE+100UNLOAD now execute, noframe
rejection. Command maxdelta.004m/s/20ms. Stoppedunload_timeout,nolift.
Selected contact intermittently>5N; finalstreak[0,3,3,5,3,4,4,23]. Heightreference
only2..3.9mm; inspect actualseparation/gatecomponents/loadready inhibition next,
not relaxed contact persistence. LaterROLL/LAND code not physically verified.
Placeholder3356222restored,no training.
[Evidence](../log/2026-10-07-m1-phase-wheel-hold.md).

Wheel-hold runtime child:18tests,8env100PREPARE completed. Fixed-entry wheel
drift reduced24..39mm→6.68..12.37mm, root-reference3D8.12..17.48mm atlast
pre-action frame. Sampled support>=48.13N,max tilt.005265rad. NoUNLOAD/LIFT;
phasehandoff remains open and must not abruptly zero holding command.
Next selected-wheel braking and continuous support holding/release, fullcycle
then obstacles; no training. Placeholder3276873restored.
[Evidence](../log/2026-10-07-m1-prepare-wheel-hold.md).

Stationary-anchor child: pure bounded wheel-hold primitive added,16CPU tests
pass after5RED failures. Fixed anchor error projected along yaw,2/s gain,
0.04m/s cap,0.2m/s2 slew; no lateral command or anchor relatching.
No runtime integration yet; physical drift remains unresolved. Next diagnostic
PREPARE integration with wheel effort guard and continuous phase handoff,
then matched8env SDF physical comparison. Placeholder3190750 unchanged.
[Evidence](../log/2026-10-07-m1-wheel-hold-primitive.md).

SDF singleleg entry15tests: PREPARE100 then UNLOAD0 frame rejection;noLIFT.
Actual anchors drift24..39mm backward despite zero wheeltarget,root-reference
24..37mmxerror. SDFrolling exposes stationary-anchor control assumption.
New child: bounded wheelholding/coordination inPREPARE/UNLOAD withcontinuous
releaseatROLL/relatchLAND; preserve25mmframe,effort,slew andallphysicalguards.
Targetready isnot actualretention. Placeholder3190750restored,no training.
[Evidence](../log/2026-10-07-m1-sdf-single-leg-entry.md).

SDF contact child14tests: read-only substeps ruleoutstale forces; endpoint0N
has positivegap while originalsurface near/belowground. Invalid1mmrestrequest
wasnative0 dueauto .93mmcontact; explicit2mmcontact now readbackverified.
8/8four-support180steps:112.40..113.15mmforward,minsampled51.87N. Native32wheels
rest1mm,contact2mm; physicalmass/inertia/materialunchanged. Candidateonly,
no crossing/no training. Next fullsingleleg cycle preservingguards,original
envelopeandrealobstacles. Placeholder3162948 restored.
[Evidence](../log/2026-10-07-m1-sdf-contact-margin.md).

Source SDF child8tests: no source point/index changes or remeshing; actual32wheel
triangle shapes, baseline physical arrays exact. Resolution128 rejectsstanding3
(env6RAR0N);256rejects0(multiple0N), before rolling. Not a successful fix.
Next compare native contact geometry/substeps to sensor impulses atzero speed;
no guardrelaxation/resolution sweep. Placeholder3078553 restored, no training.
[Evidence](../log/2026-10-07-m1-source-sdf-comparison.md).

Loaded-contact fidelity child: CPU original-wheel audit finds6nonmanifold edges
with4incident faces on eachwheel, exact and0.1micrometer weld identical. No open
edges/zero-area faces, but valid solid/self-intersection still unverified.
Installed SDF API/test confirmed; not proof of wheel/articulation support at runtime.
Next inspect local overlapping faces/solid interpretation before SDF cooking.
No runtime changes, no GPU use; placeholder2915023 unchanged.
[Evidence](../log/2026-10-07-m1-source-mesh-topology.md).

Explicit effort child54tests: native target3Nm confirmed on3supportwheels,
selected0;20Nm/s maxslope/zeroendpoints, baselinevelocitytarget0/damping5 retained.
8/8settle butprogress-.001532..+.000121m, no traversal. Env3loadedFAR netq
-.000145/RBL+.000935rad, lightFBL+.037391. Next investigate faithful original
mesh contact representation rather than more torque/shape shortcuts. No training;
placeholder2915023restored. [Evidence](../log/2026-10-07-m1-explicit-wheel-effort.md).

Cylinder comparison revealed actual UNLOAD final-postaction omission. Fixed read
of100thaction result, fresh allocation/force/streak, no extraaction/relaxedguard.
49tests; RBL-only8rows reachLIFT/ROLL,15.484cmrise then reject102(FAR29.372N),
root retreats~.69mm. Mass/inertia/materialexact baseline. Cylinder not promoted.
Mixedfourleg cylinder remains unable to finishUNLOAD inbudget; do not count
RBL-only as alllegcoverage. Placeholder2857178restored; no training.
[Evidence](../log/2026-10-07-m1-cylinder-and-unload-boundary.md).

Free-wheel isolation107tests andphysical8/8settle: allfourselectedlegs rotate
.07503.. .07720rad versus~.07503command; selectedforce0N, supporttargets0.
General drive failure no longer fits evidence; loaded contact/constraint behavior
is primary target. Retain physical envelope/mass fidelity in next comparison;
do not replace controller or train on airborne rotation. Placeholder2786123restored.
[Evidence](../log/2026-10-07-m1-free-wheel-drive.md).

Architecture audit: action path writes targets only; current vertical static FF
has no tangential force/acceleration/contact-moment model. This is a known limit,
not proof it causes stall. Atstep100env3 FAR/RBL each retain2positive contacts
30.024mmapart undergain5and20; FBL onepoint0N correlates with largerrotation.
Next lifted-wheel-only drive control isolates free DOF versus ground constraint
before replacing controller. No runtime edits or GPUprobe this turn.
[Evidence](../log/2026-10-07-m1-contact-architecture-audit.md).

Half-timestep child24tests,2.5ms/decimation8/control20msverified; no forward travel
(.596..1.126mmretreat), minrollsupport31.101N, settle_contact_lost_or_missing.
Keep5msdefault. Speed/gain/timestep comparisons do not restore three-support
locomotion: revisit combined contact/body/leg dynamics architecture rather than
another scalar tweak. No long training;placeholder2723800 restored.
[Evidence](../log/2026-10-07-m1-half-timestep.md).

Substep child18tests; read-only scene.update observer collects20x4native states.
Cache matches native exactly; FAR delta .000969rad vs endpoint qd integral .026048,
RBL delta+.001717 vs integral-.014468. Not proof of solver bug; TGS internal
substeps need not equal external endpoint quadrature. Same root/landing result
as no-observer baseline. Next controlled timestep/solver comparison retaining
control duration and physical guards. No training;placeholder2696342 restored.
[Evidence](../log/2026-10-07-m1-native-substeps.md).

Drive-gain child now tested: default-off phase-isolated20vs5,90tests; actual
backend20ROLL/5LAND verified,8/8settle,minsupport33.424N but no effective advance.
Estimated torque now4..10Nm on most loaded wheels, still tiny net angle. Do not
raise gains again: next contact/substep angular-consistency investigation.
Placeholder2662902 restored. No training or production asset changes.
[Evidence](../log/2026-10-07-m1-roll-gain-comparison.md).

Traction child matched higher-drive comparison on7efc037: actualpeak .036m/s,
7.2mm command integral;8/8settle/minsupport34.278N, root retreats .548..1.109mm.
Loaded wheel net angle still tiny(.001154.. .010415rad).14rolling tests pass.
Next separate drive-torque adequacy/contact resistance with bounded comparison;
do not treat cap .1 as achieved speed or fix by merely increasing speed.
Placeholder2623404 restored; no training/runtime code changes this comparison.
[Evidence](../log/2026-10-07-m1-preload-drive-comparison.md).

Leg-aware preload child: 74tests, fixed-physics8env shoulder diagnostic completes
lift/roll-window/land/settle8/8, minimum rolling support34.976N. Front-selected35N,
rear-selected40N with unchanged8cm/actual30N guards. Not production promotion.
Traction child remains OPEN: root negative<1mm, loaded wheel angle .0013.. .0034rad
despite positive commands. Next matched drive/contact investigation on this stable
baseline; original collision geometry and obstacle/PPO/video acceptance outstanding.
Placeholder2567503 verified; no new training. Last Feature/Verified Ref: containing
commit; baseline56c5518; Current Work Ref: codex/m1-contact-crossing.
[Evidence](../log/2026-10-07-m1-rear-preload-cycle.md).

Smooth COM runtime78tests; physical rejection103,weak29.928N. Better than direct97
but not baseline105/no crossing. Failedrow3 entryshift13mm vs row0=76.7mm;
next leg-aware preload feasibility before rolling, not uniform reserve. LAND
velocity continuity still untested. No training;placeholder2523812 restored.
[Evidence](../log/2026-10-07-m1-com-runtime.md).

COM reference primitive added,77tests; not yet runtime-integrated. Existing log
shows PD changes~1.3..1.6Nm on weak hip/knee while feedforward barely changes.
Next continuous acceleration/braking state through LAND/SETTLE and matched smoke;
do not count reference tests as physical stability. Placeholder2471170 unchanged.
[Evidence](../log/2026-10-07-m1-com-trajectory.md).

Measured force branch now honors configured reserve;73tests. Opt-in rolling COM
feedback including support-centroid transport physically rejects97 (28.768N),
earlier than baseline105. Static proposal valid does not mean dynamically safe.
Keep default-off; next acceleration/support-wrench-aware coordination. No training.
[Evidence](../log/2026-10-07-m1-moving-load-feedback.md).

Controlled split-hull comparison:46tests; mass/inertia arrays and material values
match with fixed diagnostic physics. Baseline rejects105,split107,both negative
progress. Original random comparison invalid due shape-count RNG consumption.
Next bounded moving-load compensation; no production geometry promotion/training.
[Evidence](../log/2026-10-07-m1-split-shoulder-comparison.md).

Three-support contact audit: FAR/RBL two contact positions stay exactly fixed,
net wheel angles~.0018rad; instantaneous qdot not sustained rolling.14tests.
Same rejection104. Next contact discretization fidelity before attributing all
failure to absent moving COM feedback. No training;placeholder2363319 restored.
[Evidence](../log/2026-10-07-m1-three-support-contact.md).

Lower rolling cap.02m/s does not fix support: step104,row3FBL29.921N,
all8 negative progress(-.515..-.845mm); only2actions later than baseline.
13tests; diagnostic choice only, production/default unchanged. Next moving
load/traction/reference ownership, not more speed-only guesses. No training.
[Evidence](../log/2026-10-07-m1-low-speed-support.md).

Static reserve40N cannot fit allrows:UNLOADstep11,row0desired80.264mm>80mm,
reason3.58tests;35Ndefault unchanged. Next moving load/speed coordination,
not arbitrary bound increase; no training.
[Evidence](../log/2026-10-07-m1-support-reserve-bound.md).

Shoulder static cycle8/8stablelanding; rolling variant fails supportfloor29.982N
atstep102 after12rollingactions. Lift155.7..157.8mm,pose/marginvalid.53tests.
Next measured moving load/COM redistribution without lowering30N; no training.
[Evidence](../log/2026-10-07-m1-shoulder-lift-cycle.md).

Shoulder hull60vertices/42faces restores8/8forward49.8..62.7mm. Runtime masses,
inertias,materials match source exactly.24tests. Radial underapprox<=4.69mm;
conservative original envelope required for success oracle. Next lift/landing
regression and model fidelity; no training.
[Evidence](../log/2026-10-07-m1-shoulder-wheel-comparison.md).

Collision representation causal comparison:diagnostic prism restores8/8rolling
86.8..94.7mm with unchanged gains/guards vs baseline<0.4mm.23tests.
Not a production tire:verify shoulder geometry and runtime physical invariants,
then redo lift/landing and real crossing. No training/crossing completion.
[Evidence](../log/2026-10-07-m1-wheel-envelope-comparison.md).

Actual cooked FBL hull34vertices/62polygons, sparse uneven tread. Contact
world-Y normal moment~-1.7Nm under drive supports (not proves) faceting hypothesis.
Next controlled collision-fidelity comparison with unchanged physical parameters.
[Evidence](../log/2026-10-07-m1-cooked-wheel-hull.md).

Contact evidence: exact static mesh filter reports two FBL support points44.26mm
apart with shifting loads and stationary points. Next cooked face/moment audit.
Correction: earlier flat-base probes retained48semantic blocks; verified none-stage
scene has onlyground and reproducesfailure exactly. Fix diagnostic flat labeling.
[Evidence](../log/2026-10-07-m1-contact-patch-evidence.md).

PhysX backend confirms intended drive values (not only cached cfg). Opt-in
velocity-iterations4 comparison remains stationary, so not a production fix.
22tests; next inspect actual contact constraints/body locks/cooked shapes.
[Evidence](../log/2026-10-07-m1-physx-drive-solver.md).

Read-only FBL collision-frame audit: identity relative transform, Y thin axis
matches joint Y; no extra-frame cause found. Source drive/limits differ from
verified runtime and cannot establish live locking. Next cooked contact/solver.
[Evidence](../log/2026-10-07-m1-collision-frame-audit.md).

Effective-rolling-progress child: joint-angle telemetry disproves sustained
rotation in row0 despite positive instantaneous qdot. Net wheel angles~0.001rad,
centers<0.003mm. Next substep/contact/solver consistency, not blind gain tuning.
[Evidence](../log/2026-10-07-m1-wheel-angle-response.md).

Effective-rolling-progress: 180-step sustained four-support control completes,
but commanded148mm vs actual below0.4mm. Mid-window measured wheel rates
0.131..0.184 vs target1.042rad/s. Next cumulative wheel angle/contact kinematics.
21 tests; no training. [Evidence](../log/2026-10-07-m1-sustained-rolling.md).

Effective-rolling-progress child: matched zero-support-feedforward control
completes 100 steps but retains negative 0.62–0.69 mm rolling-window progress.
Feedforward not necessary for the symptom. Next inspect contact/angular response
and separate short startup window from sustained rolling. No training.
[Evidence](../log/2026-10-07-m1-rolling-no-feedforward.md).

Upload delta: four-support finite rolling control, isolated gain comparison and
actual PhysX wheel-limit telemetry. 20 focused tests passed; limits effectively
unbounded, but forward traversal unresolved. No training or crossing claim.
Current Work Ref: commit containing this update; baseline e4c0b9a.
[Evidence and improvement summary](../log/2026-10-07-m1-upload-improvements.md).

Wheeltractionaudit:runtimefriction0/stiffness0/damping5;~1..2.6Nmdriveunder50Nm,
no clipping,gravitywheelterm~1e-6Nm. USDconvexHullwheelgeometry;facetingresistance
notproven. Nextboundedfour-supportloadeddrivecontrolvsheldleg;preservegeometry
andgainsuntilcausalcomparison. Flatlandingreproduced;placeholder1964482.
[Evidence](../log/2026-10-07-m1-wheel-traction-audit.md).

Landing-contact-stability improved:172tests,8/8flatcycleallstreak5 after.88s
SETTLE. Frozenheight,final51..67N. Separatecontactpersistence>1Nfromstable
>10N5frames;requirespriorLANDtouchdownandother3>=30N,noextraairtime/descent.
Effective-rolling-progress still<1mm duringroll itself;nexttorque/friction/
trackingaudit.No training;placeholder1934277.
[Evidence](../log/2026-10-07-m1-settle-contact-persistence.md).

Boundedramp54tests:20ROLLactions supportmin35.11N butactualnetprogress<1mm,
NOTeffectiveforwardtraversal. Newchild effective-rolling-progress (tracking/
traction/referenceownership);landing-contact-stability still8..10N atSETTLE
entry. Reviewjittercountervsabortwithoutloweringfinalacceptanceorextendingairtime.
Placeholder1893212,no training. [Evidence](../log/2026-10-07-m1-bounded-rolling-ramp.md).

Rollingaxiscontrolverified:actualsupporttargets1.042rad/s,damping5,positiveYaxes.
Matchedzero-speedholdcompletes20ROLLactions;stepdrivefailsafter9. Nextbounded
acceleration/decelerationnotcommandsignflip. Siblinglanding-contact-stability:
zeroctrlstep200alltouchbutnextSETTLEadmissionlosescontact;weakrow10.15N.
No training/obstacleacceptance. Placeholder1863813.
[Evidence](../log/2026-10-07-m1-rolling-axis-control.md).

Newchild rolling-support-control:46tests;co-movingreference integrated inopt-in
flatrollingprobe. Step99supportfloor rejects29.07..29.54N;rootnegative0.57..3.41mm,
notaxis-signproof. Next logactualwheeltargets/axis/bodyvelocity andtest acceleration
transient hypothesis;preserve30N gate. Placeholder1815158;no training.
[Evidence](../log/2026-10-07-m1-rolling-support-probe.md).

MeasuredTRAVERSEadmission module added,43CPUtests. Actualenvelope bottomclearance
>=5cmtoadvance,rearfar-edge margin>=4cmtoLAND;nostale/collided/unsafeinputs.
Notyetwired:nextactualboxgeometry+rollingreferenceintegration/physicalsmoke.
Worstremainingflatcycle time .38s requiresjointtrajectoryplanning,notfixedwait.
[Evidence](../log/2026-10-07-m1-measured-traverse-gate.md).

Retimed flatcycle:opt-in .12m/s Cartesian proposal andfinebacktracking retain
.5rad/s joint cap.8/8actual15.31..15.77cm rise+stablelanding; highwindowonly
.16...24s. Needobstacle-aware TRAVERSE hold+rolling reference ownership inside
4s;notcrossingacceptance.145focused+23lift tests;placeholder1745580 restored.
[Evidence](../log/2026-10-07-m1-retimed-lift-cycle.md).

Obstacle-cycle child trajectory-budget-feasibility: actual CPU lift_target
needs 4.38 s for nominal 15 cm up/down (110+109 steps), exceeding approved
4 s before forward traverse. Next joint-path timing / rolling-aware references;
do not relax physical clearance or report flatcycle as crossing. No GPU changes.
[Evidence](../log/2026-10-07-m1-crossing-time-budget.md).

Flatcyclepasses139tests/native0:8/8landing_completetrue atstep236;4sLIFT/LAND+
.72sSETTLE,allstreak5,finalselected51..65N,effortgap<.00114Nm,tilt<.00954rad.
NOT obstaclecrossing/policy. Nextactualobstaclecycle+forwardreference ownership/
clearance timing,3seeds/video. Placeholder1640307.
[Evidence](../log/2026-10-07-m1-four-support-settle.md).

Boundedgroundsearch106tests/native0:8/8touchdown by182..184,final27..43N;
weakrowsneeded-2.0/-1.6mm only. Streak0 duefourcontacteffortgap6..14Nm.
Nextfour-support-settle perapproved2sbudget, gatedonallcontactswithin4s;
noextendedairtime/search. Placeholder1598746. [Evidence](../log/2026-10-07-m1-ground-search.md).

Landing timing43tests/native0:90up/110down gives6rowscontact33..43N at182..184,
rows1/5zeroheight but.11/1.40N. Allstreak0,stilltimeout. Need boundedcontactsearch
and approved LAND/SETTLE budget separation; noheight-onlysuccess. Placeholder1547510.
[Evidence](../log/2026-10-07-m1-landing-timing.md).

Controlledland104tests/native0:100up+100down,200actions noaborts butlanding_timeout.
Peak12.72..14.44cm,nearanchoratend butnoselectedLANDforce>10N;finalforce0,
effortgap<.013Nm. Newcontact-seeking-landing: groundreference/remainingbudget and
postactioncontact evidence, notsettleramp. Placeholder1515614.
[Evidence](../log/2026-10-07-m1-controlled-land-cycle.md).

Physical flat singleleglift passes:133tests/native0;8rows(all4legs twice) finish
200LIFTactions,stoppednull,measuredrise17.32..17.82cm. Supportmin36.37N,
tiltabsmax.0128rad,rates.0411rad/s,non-supportcontact0. NOT obstaclecrossing.
Nextcontrolled-land-cycle withshared4sphasebudget then actualobstacle/video.
Placeholder1479138. [Evidence](../log/2026-10-07-m1-lift-handoff.md).

Finitecontact approach132tests/native0: all8UNLOADready within94samples,streak>=5,
force<=2.54N. Nextcontinuous-unload-lift-handoff: firstLIFTpreaction rejectedreason6
all8 dueframe/reference transition; zeroexecutedLIFTactions. Preserveguardlimits.
Placeholder1451314. [Evidence](../log/2026-10-07-m1-finite-unload.md).

Vertical-only130tests/native0:100UNLOADno frameabort,scale1allrows.6instantready
but4sustained5frames;rows2/6still5.79/5.61N. Timeout/0LIFT. Nextfinite-unload-
progress: lateforce/height slopes andflicker, preservingrate/cap/deadline/gates.
Placeholder1427632. [Evidence](../log/2026-10-07-m1-vertical-only-unload.md).

Frame residual audit54tests/native0: row5live-command norm25.03355mm breaches25mm;
Y22.906mm,Z-2.456mm,anglemax.0321rad. Priorframe/IK/limits/slew allvalid.
New child vertical-only-frame comparison with unchanged fullpose guards, testing
3D selected feedback vsCOMownership; no assumedcausality. Placeholder1402415.
[Evidence](../log/2026-10-07-m1-frame-residual.md).

Framebacktrack defect fixed:127tests; priorfullstep .015..032rad >.01 caused.5
plateau. Carryacceptedframe converges, but physicalstep25 row5 safe=false;
allIK/limits/slew true. Newchild frame-divergence: split pose residuals before
changing ownership. NoLIFT. Placeholder1369869. [Evidence](../log/2026-10-07-m1-frame-backtrack-progress.md).

Selected-world opt-in:125tests/native0;6/8 sustainedunloadready,rows2/6 at5.59/5.80N;
100UNLOADtimeout,0LIFT. Stance9unchanged,selected3 fresh-poseIK with slewbacktrack.
Next selected-frame-slew: finalscale.5 reason then consistent LIFT handoff.
Placeholder1310281 restored. [Evidence](../log/2026-10-07-m1-selected-world-unload.md).

Joint attribution audit(code0c2d157): selectederror.003..010rad vsstance.024..033;
last30steps noeffortholds,force stillfalls. Deadline miss, NOT proven steady-state
stall. UNLOADactualrise<=1.34mm. Next explicit stance-pose/contact-effort ownership
review before more controller changes. [Evidence](../log/2026-10-07-m1-unload-joint-attribution.md).

Realized unload audit:48tests/native0; command3.7..6.4mm but actualanchor-relative
wheel rise -3.8..0.1mm; root sag4.6..5.2mm. Effort holds32..43/100 vsload0..5.
New child unloading-realization: vertical pose/effort coordination architecture,
not more load-margin tuning. Still0LIFT. Placeholder1254648 restored.
[Evidence](../log/2026-10-07-m1-unload-response.md). Baseline05dd6fb.

Zero-force target comparison:121tests; native0 but unload_timeout/0LIFT.
Selected9..19N, command3.7..6.4mm. Target alone insufficient; unloading-convergence
open. Next architecture checkpoint: coupled COM/height realized response and
load-reserve gating before more tuning. Placeholder1224540 restored.
[Evidence](../log/2026-10-07-m1-zero-force-target.md). Baseline f71fc1c.

Latest coordinated COM117tests/native0:100UNLOADsteps noallocationabort,
selected12..19N buttimeout/0LIFT. Next unloading-convergence: zero-force tracking
target distinct from5N measured gate, preserve rate/height/support constraints.
Placeholder1161123; [evidence](../log/2026-10-07-m1-coordinated-unload.md).

Latest measured feedback116tests; first trialstep14 fail during effort ramp;
settling gate thenstep68 failrow4 allocation,selected18..31N,0lift. Newchild
coordinated-unload-com: bounded mass-aware body transfer while shortening leg,
retain original anchors/bounds/thresholds. Placeholder1125373 restored.
[Evidence](../log/2026-10-07-m1-unload-feedback.md).

Latest backend audit: actual gains and sent effort match cached values8/8 exactly;
normal-contact sensor excludes friction, so old proxy is not complete balance.
112tests/native0; unload stilltimesout. Close parameter audit, next measured-unload-
control: bounded selected-leg force-feedback reference with stance/pose guards;
no blanketPDcancellation. Placeholder1081679; [evidence](../log/2026-10-07-m1-backend-effort.md).

Latest total-effort audit112tests/native0: finalPD+FF vscontactproxy discrepancy
17..22Nm; cannot attribute full mismatch to PD alone. New child backend-effort-
conventions: read actual gains/sent effort/projected jointforce before changing
controller; contactproxy omits moments/dynamics. Placeholder1046531 restored.
[Evidence](../log/2026-10-07-m1-total-effort-audit.md).

Latest unload phase112tests:100actualsteps timeout,0liftsteps. Effort command gap
<.0006Nm but selectedcontact25..47N; allocations8/8valid. New child total-effort-
contact-consistency: measure PD+feedforward/contact projection before new load
controller. Do not wait longer or lower unloading threshold. Placeholder997933.
[Evidence](../log/2026-10-07-m1-unload-phase.md).

Latest phase effort integration108tests: physicalPREPARE8/8, LIFTstep7 allocation
guardrejectsrows0,1,5,6 before support loss; selected wheel still37..63N, no rise.
New child bounded-unload-handoff: hold height during force transition, verify
measured unloading/support and effort convergence before raising. No threshold
relaxation/training. Placeholder973880; [evidence](../log/2026-10-07-m1-phase-effort.md).

Latest matched standing evidence: leg-only final errors.037..041rad(gain0)
vs.020..022rad(gain1), all8improve~46..48%; contacts maintained, bothnative0 and
clear confirmed.107 tests. Next child feedforward-phase-handoff (fresh PD targets,
rate-limited contact allocation, reset/exit clear) then real single-leg lift.
No crossing/training proof. [Evidence](../log/2026-10-07-m1-standing-comparison.md).

Latest bounded-effort-lifecycle: pure guard107tests, actual flat8x100 standing
feedforward/native0, contact>=79N, tilt<=.00931rad, clear confirmed. Tracking metric
includes velocity-controlled wheel positions; new child leg-only-standing-comparison
must correct telemetry and compare matched baseline before claiming improvement.
No lift/crossing claim. Placeholder933857; [evidence](../log/2026-10-07-m1-standing-effort.md).

Latest physical candidatef3adc98: despite load-feasible PREPARE8/8, lift stops
step38 on nonselected8.49N; actual rise -2.38..2.14mm vs3..4cm command. Root
sag12..16.5mm and joint tracking error~.07..08rad. Next bounded-effort-lifecycle,
standing compensation verification then lift, not more margin changes. Placeholder
906048 restored; [evidence](../log/2026-10-07-m1-load-feasible-lift.md).

Latest load-feasible PREPARE candidate: optional mass-based barycentric30N floor,
unchanged displacement/speed/IK limits.102 tests; flat8 native0 readiness8/8 and
independent post-stage30N allocation8/8 (baseline2/8), weakest30.667N. Next actual
single-leg lift/contact verification; no torque application or crossing claim.
Baselineb33c284; placeholder890689. [Evidence](../log/2026-10-07-m1-load-feasible-prepare.md).

Latest:post-lift-load-readiness child created by actual post-PREPARE audit.
Original readiness8/8 but hypothetical three-contact30N floor only2/8 feasible;
six weakest support25.6..26.4N. Bound20mm geometric readiness alone insufficient.
Next bounded PREPARE load-feasible target, preserve30N lift threshold; then effort
ramp/clear lifecycle.100 tests pass/native0, baselineedce545, placeholder867441.
[Three-support evidence](../log/2026-10-07-m1-three-support-audit.md).

2026-10-07 latest whole-body-load-model child: bounded vertical support solver
added;100 focused tests pass. Actual read-only four-contact allocation8/8,
base residual<=2.274e-13, max computed effort15.531Nm; no torque application.
Next child: three-contact post-PREPARE allocation and safe actuator ramp/clear
ownership (including existing PD contribution), then real lift. Baselinea457f4f;
placeholder848694 restored. No crossing acceptance or training.
[Allocation evidence](../log/2026-10-07-m1-vertical-allocation.md).

2026-10-07 dynamics prerequisite: actual COM Jacobian/gravity convention verified;
new point conversion passes95-test suite and physical helper-linked smoke/native0.
Wheel-origin derivative error<=8.05e-5, mass-weighted gravity error<=3.06e-5.
No extra torque applied and no lift acceptance. New next child under
whole-body-load-model:bounded-force-effort-allocation, validate floating-base
equilibrium, unilateral loads and torque constraints before compensation.
Baseline818c427; branch codex/m1-contact-crossing; placeholder809511 restored.
[Dynamics frame evidence](../log/2026-10-07-m1-dynamics-frames.md).

2026-10-07 optional force-aware transfer conserves supported load while targeting
30N minimum;92 tests pass. Physical8-env fails step43,env3 support7.88N despite
geometric20.85mm. No effective clearance. Position-only family remains unaccepted.
New whole-body-load-model child: inspect dynamics/Jacobian/effort conventions
before bounded whole-body compensation; no more blind planar-gain tuning.
Baselinea71cf2c; branch codex/m1-contact-crossing; placeholder762874 restored.
[Force-transfer negative evidence](../log/2026-10-07-m1-force-transfer.md).

2026-10-07 command-space correction: measured COM error now corrects previous
command under unchanged entry bound. RED reproduced reversed correction;89 tests
pass. Actual PREPARE8/8; LIFT fails step45 on env7 nonselected force0N, millimeter
rise only. New child force-versus-margin-handoff: force-low hold can coexist
with geometric>=20mm transfer no-op. Need load-aware bounded position/attitude
and recovery, not further arbitrary gain/threshold changes. No training.
Baselined4539df; branch codex/m1-contact-crossing; placeholder733255 restored.
[Command/COM evidence](../log/2026-10-07-m1-command-com-feedback.md).

2026-10-07 hard-margin feasibility corrected: optional30mm infeasibility now
falls back to minimum-entry-displacement20mm target, within unchanged bound.
88 tests pass. Physical8x200/native0 maintains nonselected support>=21.02N
but ends4s holding below20mm margin, actualrise millimeters, no lift success.
New child command-to-COM-tracking: inspect commanded versus measured response
before feedback revision. No training. Baseline0fec737; placeholder695745.
[Fallback and plateau evidence](../log/2026-10-07-m1-hard-margin-feasibility.md).

2026-10-07 support-load-distribution: per-row hold and bounded transfer wired
only into opt-in diagnostic.87 tests pass; physicalgate stops atstep8 with
reason103 (soft30mm target beyond8cm), all wheel forces still positive.
New child hard-margin-bound-feasibility: solve hard20mm requirement within
existing bound before considering more displacement. No lift success/training.
Baseline3a97ac2, branch codex/m1-contact-crossing; placeholder660878 restored.
[Support-transfer evidence](../log/2026-10-07-m1-lift-support-transfer.md).

2026-10-07 lift support tracking: torque trace peak61.92Nm<150Nm, no estimated
clipping. Added optional nonintegrating pose feedback,86 tests pass; physical
candidate FAILS atstep24 on nonselected support8.48N, no meaningful clearance.
Default remains off; no training. New child support-load-distribution follows
evidence that posture-only compensation cannot sustain all three supports.
Need measured support-aware unloading/transfer/hold plus recovery; do not relax
contact guard. Baselinefef68bd; branch codex/m1-contact-crossing; placeholder634517.
[Pose-feedback negative evidence](../log/2026-10-07-m1-lift-pose-feedback.md).

2026-10-07 single-lift child: new bounded M1 IK target and opt-in probe;83 CPU
tests pass, but physical8-env gate FAILED atliftstep36 (nonselected support8.79N).
Actual rise remains millimeters at~3cm target. New child under single-lift:
T306.contact-transfer.lift-support-tracking, justified by loaded-joint error and
5..9mm root descent despite frozen target. Next investigate force distribution,
actuator limits and bounded feedback, not increased lift target/looser gates.
Recovery/full crossing/metrics/video/bypass remain open. No training/push.
Baseline6c7d94f; current branch codex/m1-contact-crossing; placeholder598258.
[Lift evidence](../log/2026-10-07-m1-single-lift.md).

2026-10-07 PREPARE candidate: explicit speed.04/bound.08 and stop at measured
hard20mm margin gives actual flat8x100/native0, seed2, finalready8/8 by1.68s.
T306.contact-transfer.front-feasibility has first-seed positive evidence, not
generalized closure. CPU75pass. New next child T306.contact-transfer.single-lift:
lift one wheel after readiness, maintain other support, recover safely on loss.
All crossing/landing/event/bypass/policy requirements remain open; no training.
Baseline8a63752/currentbranch codex/m1-contact-crossing; placeholder538748 restored.
[Readiness evidence](../log/2026-10-07-m1-prepare-ready.md).

2026-10-07 live-feedback correction: projection used frozen anchors while gate
used actual wheel positions; replay quantified ~1cm optimistic margin error.
Now explicit support_w feeds projection separately from fixed IK anchor_w.
CPU69pass and actual flat8x32/native0; rear readiness4/8, fronts not ready.
T306.contact-transfer.front-feasibility remains OPEN; no long training/lift.
Baseline1f26d2a; current branch codex/m1-contact-crossing; placeholder502175.
[Evidence](../log/2026-10-07-m1-live-support-feedback.md).

2026-10-07 physical child OPEN: flat8x100/native0 has rear readiness4/8,
front margins2.6..8.5mm (<20mm). Speed.04 experiment fails bound atstep53;
no lift/training. New child T306.contact-transfer.front-feasibility is blocking
the full controller: reconcile measured COM/support drift and bounded target.
Nearest-point projection and satisfied-margin target-freeze fixes CPU67pass;
target-freeze not physically rerun. GPU7 placeholder restored466385.
[Physical evidence](../log/2026-10-07-m1-prepare-physical.md).

2026-10-07 transfer child: `m1_load_transfer.py` proposes bounded body translation
with fixed stage-entry wheel anchors/root height/RPY, M1 IK and joint slew checks.
64 focused CPU tests pass; actual dynamics remain unverified. Next: coordinator
owns entry capture/reset, observation freshness, contacts and recovery, before
8-env smoke. Baseline `38e17f8`; current branch `codex/m1-contact-crossing`.
[Transfer evidence](../log/2026-10-07-m1-load-transfer.md).

2026-10-07 observer child: `m1_support_observer.py` reads named world-Z wheel
forces, live link masses/COM, selected-leg support triangle and tilt/rate.
54 focused CPU tests pass including observer-to-gate wiring on 8-row fixtures.
Not a real 8-env simulation and not production integration. Next open child:
bounded load transfer with M1 IK, followed by full coordinator and physical gates.
Baseline `24fd181`; Current Work Ref `codex/m1-contact-crossing`.
[Observer evidence](../log/2026-10-07-m1-support-observer.md).

2026-10-07 implementation: written design approved; isolated worktree on
`codex/m1-contact-crossing`, preserved baseline `dacfb46`.
Child T306.contact-transfer.prepare-gate: pure Torch PREPARE gate implemented;
20 new contract tests plus 23 baseline tests pass. No runtime integration yet.
Next child: pre-action named observations and bounded support transfer/M1 IK;
full state machine, event metrics and all physical/PPO gates remain OPEN.
Last Feature/Verified Commit for physical behavior unchanged. Current Work Ref:
`codex/m1-contact-crossing`. Key files: `m1_prepare_gate.py`, its dedicated test.
See [implementation evidence](../log/2026-10-07-m1-prepare-gate.md).

### Earlier design checkpoint (superseded approval status)

2026-10-07: T306.contact-transfer and sibling T306.event-metrics are OPEN.
User approved the contact/COM-driven approach. Current teacher fails physical
crossing: measured stance target drift lowers body; nominal fixed support reduces
collapse but rolls over. Prelift support transfer and per-obstacle evidence are
required, not more knee/reward tuning. See [design](../../docs/superpowers/specs/2026-10-07-m1-contact-crossing-design.md)
and [evidence](../log/2026-10-07-m1-contact-crossing-design.md).
Next: written spec review, then isolated implementation plan/TDD. No long training.
Earlier dates below are historical and do not prove this candidate passes.

2026-10-03 latest: serial teacher foot anchors now capture current articulated
FK only at phase handoff and remain frozen within the phase. Focused regression
is `43 passed, 1 skipped`; physical gate remains open because Isaac Sim reports
CUDA/PhysX foundation `CUDA being in bad state`.

See [foot-anchor regression](../log/2026-10-03-m1-foot-anchor-regression.md).

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

### 2026-10-08 rolling-contact root-cause checkpoint

Focused WBC suite: 157 passed. The 1-env GPU7 handoff still fails its speed
gate (0.08091 m/s at tick 48), while observed loads/tilt remain bounded.
Same-state native-capacity shadow with welded 3-D contacts misses target
forward qdd (+1.417 vs -0.044 m/s^2); normal-only ablation matches forward qdd
but predicts -0.975 m/s^2 vertical acceleration, so it is diagnostic only, not
an accepted controller. The 20/200 Nm/s slew shadows also miss the target; no
rate increase accepted. [Evidence](../log/2026-10-08-m1-wbc-rolling-ablation.md).
Next: implement and finite-difference verify migrating-patch rolling
constraints, then resume single-wheel obstacle crossing. GPU7 placeholder
restored; training remains stopped.

### 2026-10-09 physical crossing priority checkpoint

The user reaffirmed: first achieve actual obstacle crossing and safe far-side
touchdown; only then restore the pre-crossing balance quickly. The bounded
64-step PhysX probe still fails this first gate (`strict_crossing_count=0`,
`strict_failed=true`, peak tilt `0.463 rad`). The 32-step timed obstacle hold
expires before measured far-edge progress; the wheel falls toward the block
and the selected leg changes. The just-added invalid-frame cache fallback did
not trigger because its hold/leg preconditions were already false. This is not
a balance-recovery-only issue: the next fix must use obstacle-relative swing
and landing progress and stabilize the three-wheel support phase through the
approved WBC route. Do not extend a timer or relax strict gates as a substitute.
GPU7 placeholder restored; no training was started. Details:
[instrumented PhysX replay](../log/2026-10-09-m1-teacher-physx-probe-performance.md).

### 2026-10-09 strict event/recovery wiring correction

The runtime wrapper was passing the balance/nominal-pose recovery predicate
into the strict crossing tracker's far-side touchdown argument. This silently
made a crossed-and-landed event wait for recovery, despite the tracker and
specification separating the two. Added a typed gate split so the event counts
on collision-free four-wheel loaded far-side touchdown, while tilt/rate and
nominal-joint pose govern only the subsequent recovery timer. RED/GREEN
regression plus the strict/landing/metrics/teacher suite: **61 passed**;
runtime modules and the probe compile. The probe now records per-step strict
failure state. This fixes gate wiring, not the physical swing: the last PhysX
run remains a failure (zero strict crossings, 0.463 rad peak tilt). A fresh
GPU7 check found another process using 3,194 MiB at 100% utilization in
addition to the placeholder; neither was touched, so the physical smoke was
deferred. Next is obstacle-relative swing progress plus support-WBC integration
and a fresh strict one-obstacle probe; training remains stopped.
