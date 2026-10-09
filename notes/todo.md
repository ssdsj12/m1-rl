## 2026-10-09 latest: actual lift / WBC handoff diagnosis

- T306/execution-physical: compliant PREPARE200steps/4s is8/8ready, superseding
  older400step/8s acceptance wording. PD unload0/8; most nominal lift is lost
  to body-pose drift and joint tracking. Selected-leg world-height correction
  also fails, so do not repeat gain/height sweeps or start training.
  [Evidence](log/2026-10-09-m1-pd-unload-diagnosis.md).
- WBC same-state snapshot replay corrects prior confounded attribution: native
  effort-capacity counterfactual removes forward runaway whereas zeroing only
  normal RHS does not. Keep slew unchanged; investigate premature22ms handoff.
  [Offline audit](log/2026-10-09-m1-wbc-handoff-counterfactual.md).

## 2026-10-09 previous: M1 mixed terrain density

- T306/mixed-terrain-registry IMPLEMENTING: approved M1 mixed profile now wired into train, reference terrain families unchanged, flat small counts x1.5. Structured layout places165small+3large in20seeds without reducing.45m clearance. Grounded registry replaces fixed-six coordinates only in mixed mode. [Progress](log/2026-10-09-m1-mixed-dense-progress.md), [design](../docs/superpowers/specs/2026-10-09-m1-mixed-dense-terrain-design.md).
- Final CPU suite148passed/1skipped. Independent review4important findings repaired. GPU0 native scene passed:2376records,2280small10cm USD bounds,172semantic-small rays,2neutral steps,1589/1592obs and16actions. Probe ended, no long train; GPU7 placeholder1768831 untouched. Physical crossing remains unproven. [Verification](log/2026-10-09-m1-mixed-terrain-verification.md).

## 2026-10-09 previous: Climb posture source

- Clearance child: strict runtime now consumes oriented authored-mesh wheel bottom, not fixed-radius subtraction.52focusedtests; source-USD/full-mesh oracle agrees, hull reduces194634to2259vertices/wheel. Live PhysX integration and crossing remain unverified. [Evidence](log/2026-10-09-m1-oriented-wheel-bottom.md).

- T306/climb-posture-source OPEN: user wants vendor Climb posture, not extreme extension. SDK Climb/state8 differs from Stair and HighLowStance; inspected files supply no numeric preset. Need vendor parameters or settled named joint/IMU capture. [Evidence](log/2026-10-09-m1-climb-sdk-and-bottom-clearance.md).
- Bottom-clearance/Cartesian/strict tests47passed; physical lift/crossing unproven. No training or probe; GPU7 placeholder unchanged.

## 2026-10-09 previous: measured PREPARE physical gate

- [T306 execution-physical](todo/T306-m1-ame-long-train-stability.md): shared per-row PREPARE controller, acceleration bounds, fresh final verdict and last-executed-reference preservation;92focusedtests passed. [Evidence](log/2026-10-09-m1-batched-prepare-controller.md).
- Production-PD400step GPU0 test completed8/8PREPARE-ready; final support margin31.31--34.40mm, max tilt component0.533deg, non-wheel contact force0. This is NOT lift/crossing. Next measured UNLOAD and lift/roll/landing; no long training, no live probe, GPU7 placeholder untouched.

## 2026-10-09 previous: M1 production contract and support failure

- [T306](todo/T306-m1-ame-long-train-stability.md): M1 mass41.045kg,16actuators, wheel observations and1589/1592 runtime dimensions checked; post-IK corruption,50% teacher attenuation, false10cm geometry and wrong-checkout launches repaired. Latest124passed/1skipped. [Evidence](log/2026-10-09-m1-parameter-and-execution-repair.md).
- Physical crossing FAIL, not training-ready: first post-step COM19.36mm outside remaining support triangle; freeze-other-joints ablation still tips. Next integrate existing measured PREPARE->UNLOAD stages with truthful actuator ownership, then prove lift/roll/landing. Raw invalid reference holds no longer become imitation labels. Save100 retained with separate iteration/checkpoint watchdog. GPU7 placeholder1768831 untouched; no training, no active bounded probe.

## 2026-10-08 previous: corrected obstacles onto measured wheel tracks

- Live USD probe proved the old `y=+/-0.35 m` anchors missed M1 wheel tracks `y=+/-0.215 m` by ~8.7 cm beyond the combined lateral envelopes. Corrected six alternating anchors to `+/-0.215 m`; a fresh GPU7 geometry smoke measured ~48 mm target-track overlap and ~382 mm opposite-track clearance for each obstacle. [Evidence](log/2026-10-08-m1-obstacle-track-alignment.md).
- This proves geometric exposure only, not a crossing. One of the six shapes is 5 cm high while the other five are 10 cm; next use actual bounds in the physical single-wheel swing test. WBC/obstacle focused tests: 173 passed. Training remains stopped.

## 2026-10-08 previous: single-wheel swing task foundation

- Added a time-parameterized single-wheel arc with wheel-envelope top clearance and a QP task that compensates measured acceleration bias. Remote focused suite: **165 passed**. [Evidence](log/2026-10-08-m1-single-wheel-swing-reference.md).
- This is not yet connected to a physical obstacle scene or receding-horizon QP, so crossing remains unproven and training stays stopped. Next: verify actual wheel-center Jacobian and obstacle collision filtering; then apply one-wheel swing with the other three wheels supporting. Acceptance order remains strict crossing first, balance recovery afterwards.

## 2026-10-08 latest: WBC ground-contact observability

- Added a bounded single-env contact probe. GPU7 native PhysX views observe all four wheel contacts by tick 8, but only after transient touchdown (about 102/218/226/218 N); this is not stable support, a lift, or crossing. Contact forces are zero for the first seven ticks. [Evidence](log/2026-10-08-m1-wbc-ground-contact-observability.md).
- Full focused WBC suite: 142 passed, including stale command/clock, fixed slew/residual policy, and native readback checks. CPU oracle fallback now uses an explicit 0.5 s per-tier cap; it is not a real-time backend. [Adapter evidence](log/2026-10-08-m1-wbc-execution-adapter.md).
- Next: achieve a measured same-state transfer from settled PD support to explicit WBC torque, confirm canonical 16-DOF ordering, and verify sustained support/slow roll. Only then run single-leg obstacle crossing. Strict crossing comes first; fast recovery is assessed only afterward. GPU7 placeholder restored; no training.
- PD-oracle samples projected force before/after and cached torque; post-step projected force best matches dynamics. At dt=.001/.0005, base-force max .040314/.034149 N; base moment/joint torque stay <.02 Nm. The .05 N allowance is PD-calibration-only; zero-PD WBC gate remains .02. [Evidence](log/2026-10-08-m1-wbc-pd-oracle.md).
- Focused suite 147 passed, 1 skipped. Native 3/3 samples pass at both dt; this is suspended dynamics calibration, not stance/crossing. GPU7 placeholder1118093 restored; no training.
- Next: grounded support initialization and continuity under explicit sole-owner WBC, then stance/roll. Do not train before grounded single-leg lift/roll/land gates pass.
- User priority: strict crossing success is first and cannot be offset by balance recovery; only after crossing succeeds, measure recovery to four-foot stable support within 2 s as a separate metric (spec updated).

## 2026-10-08 previous: actual WBC sole-owner free execution verified

- 125tests; native8rows x3ticks actually apply QP torque, K/D0/readback verified; maxdynamicsresidual.00571<.02. [Evidence](log/2026-10-08-m1-wbc-execution.md).
- Next grounded support initialization/continuity then stance/roll. Free execution is not support/crossing; CPU not realtime. Placeholder1018794 restored, no training.

## 2026-10-08 previous: explicit speed policy and effort-history guard

- 124tests; live shadow remains feasible under leg.5rad/s diagnosticcap. Native actuation reads0 while PD/projected torque nonzero, so no verified total-effort history exists in warmup. [Evidence](log/2026-10-08-m1-wbc-limits.md).
- Next fresh-environment explicit-total initialization/continuity; do not hot-switch PD or seed history from zero/estimate. Placeholder982669 restored; no physical WBC/training.

## 2026-10-08 previous: derived state bounds expose feasible shadow and missing leg speed limit

- 116tests; correct rearrelease live shadow feasible with state-derived joint bounds, maxeffort12.52Nm/residual7.8e-7; original diagnostic remains negative control. [Evidence](log/2026-10-08-m1-wbc-joint-bounds.md).
- Native leg speedlimit5.94e36 is unset, not motor certification. Next explicit diagnostic speed policy/total torque slew and sole-owner handoff, then physical stance. Placeholder943133 restored; no actuation/training.

## 2026-10-08 previous: live-state contact-step failure localized

- 113tests; measured fullh/pointbias now feed read-only one-step constraints. Native3modes reject. Allattached equalities conflict; rearrelease fails unchanged diagnostic acceleration box even before dynamics. [Evidence](log/2026-10-08-m1-wbc-contact-step.md).
- Next audit diagnostic boxes vs authored state limits/reference limits, implement finite-step convergence/handoff; no arbitrary bound expansion or velocity reset. Placeholder913319 restored; no actuation/training.

## 2026-10-08 previous: live contact velocity exposes transition requirement

- 109tests; native10entries include1zero-force duplicate. FAR rear separates2.374mm/s, front approaches1.652mm/s; maxslip2.682mm/s. [Evidence](log/2026-10-08-m1-wbc-motion.md).
- WBC open child: contact velocity convergence/unilateral impact transition before actuation; do not apply zero-velocity counterfactual to live state. Placeholder889301 restored, no control/training.

## 2026-10-08 previous: native numerical fallback verified

- 105tests; captured allattached inaccurate case solved with guarded active-set fallback, unchanged full constraints residual5.53e-7. Still fails rolling softtarget; correct rearpoint release retains rollingerror2.286e-7. [Evidence](log/2026-10-08-m1-wbc-active-set.md).
- Next moving-state mode validity and actual stance/roll. No WBC actuation/training; GPU7 placeholder867270 restored. Numerical solve is not crossing success.

## 2026-10-08 previous: native rest-mode rolling counterfactual distinguishes release direction

- 100tests; native3candidate modes: FAR rearpointrelease permits targetforward.05/wheelangular.521 with error2.29e-7, releasednormalacc+.02868 and releasedforce4.36e-8N. Opposite release rollingerror.521; allattached rejected solvedinaccurate. [Evidence](log/2026-10-08-m1-wbc-candidates.md).
- Next moving-state mode validity and actual stance/roll execution. Static counterfactual only; no control/training. Placeholder786369 restored.

## 2026-10-08 previous: explicit point release / unilateral acceleration supported

- 95tests; QP now supports hard separation-acceleration lower bounds. Fixed candidate-mode adapter sets released-point force capacity0, retains normal nonpenetration and original moment arms. Synthetic polygon pivot passes only after rearpoint release. [Evidence](log/2026-10-08-m1-wbc-modes.md).
- Next native mode selection/gap-velocity validity, then actual stance. No applied control or training; GPU7 placeholder remains untouched this batch.

## 2026-10-08 previous: contact transport and native static QP verified

- 86tests; moving-evaluation-point acceleration includes migration, rejects missing inputs. Native env0 static QP feasible, maxresidual3.56e-15, maxeffort14.25Nm, wheel loads[101.56,118.92,105.75,86.44]N. [Evidence](log/2026-10-08-m1-wbc-transport.md).
- Next native contact-mode/point-release transition and actual torque stance. Do not lock all polygon contacts or assume smooth circular geometry. No applied WBC/training; placeholder736509 restored.

## 2026-10-08 previous: live wheel friction and schema-default material handling verified

- 77tests; env0 wheel conservative mu [.5992,.5486,.7072,.5856], from native randomized coefficients and installed combine rules. Missing USD physics API no longer confused with missing live friction. [Evidence](log/2026-10-08-m1-wbc-materials.md).
- Next rolling contact-migration constraint and native stance. No training/crossing; GPU7 placeholder706235 restored. Diagnostic exceptions now printed before Kit shutdown; completion markers required.

## 2026-10-08 previous: articulated acceleration bias verified

- 63tests; 8 native M1 rows x3ticks: maximum link linear acceleration error .000743m/s², angular .001352rad/s², both below preset .02. [Evidence](log/2026-10-08-m1-wbc-kinematics.md).
- Next contact-migration rolling constraint/effective friction, then physical stance. No crossing or retraining claim; GPU7 placeholder650836 restored.

## 2026-10-08 previous: native multipoint geometry and wheel-group support verified

- 52tests; env0 actual wheelpoints[2,3,2,2], forceclosure7.63e-6N and pointvelocity9.40e-9. Per-wheel minima no longer multiply by contact count. [Evidence](log/2026-10-08-m1-wbc-contacts.md).
- Next rolling acceleration/material friction, then native stance; no crossing/training. Placeholder532072 restored.

## 2026-10-08 previous: constrained full-body CPU QP implemented

- 45tests pass, including15QP cases: 3Dforces/friction, fullM dynamics, hard contact/effort/acceleration bounds, taskpriority and independent result rejection. [Evidence](log/2026-10-08-m1-wbc-qp.md).
- Next real contact geometry/rolling adapter and native stance. Synthetic only, no training; placeholder354723 untouched.

## 2026-10-08 previous: native torque ownership and velocity bias verified

- 30tests; suspended8rows x3ticks: nativePD0, commandmatch, contacts0, residualmax.00562<.02. Omitting/reversingC raisesRMS~100x/200x. [Evidence](log/2026-10-08-m1-wbc-free.md).
- Next constrained WBC contact-force/effort QP and physical support; no crossing/training claim. Placeholder354723 restored.

## 2026-10-08 previous: full mass/velocity/energy verified, inertia-frame bug fixed

- 28tests; installed inertia actor-frame rotation fixes fullM error0.009→3.81e-6; velocity5.96e-8, energy2.24e-8J. [Evidence](log/2026-10-08-m1-wbc-energy.md).
- Next velocity-bias/actuator ownership, then QP; no crossing/training claim. Placeholder275143 restored.

## 2026-10-08 previous: native full dynamics static consistency passed

- 22CPU tests;8 native rows full M finite/SPD, gravity residual<=3.06e-5, translation mass<=3.82e-6; no PREPARE/lift actions. [Evidence](log/2026-10-08-m1-wbc-native.md).
- Next velocity/frame/energy oracle, then actuator/QP; not crossing success. GPU7 placeholder240899 restored, no training.

## 2026-10-08 previous: WBC written design approved; snapshot implementation

- User confirmed implementation. Full generalized snapshot adapter:21 tests passed after RED; no actuator changes. Next native shape/frame/sign oracle, then WBC integration. [Evidence](log/2026-10-08-m1-wbc-snapshot.md).
- No long training or physical success claim; GPU7 placeholder untouched.

## 2026-10-08 previous: dynamic WBC direction approved, written spec review

- Installed full floating-base dynamics APIs exist; deprecated variants omit root terms. PD torque ownership requires explicit verification. [Read-only audit](log/2026-10-08-m1-wbc-api.md); runtime not yet tested.

- T306 child: dynamic rolling support. New [design](../docs/superpowers/specs/2026-10-08-m1-dynamic-wbc-design.md) defines unified contact forces/total torque and full crossing gates; implementation pending written review.
- GPU7 own placeholder99388 verified untouched; no training. [Evidence](log/2026-10-08-m1-wbc-design.md).

## 2026-10-08 previous: measured lift/roll handoff implemented

-55tests; all8 pass5frame settled gate at96; no budget extension. ROLL5 still rejects row7FBL21.16N; no LAND/crossing.
-Next dynamic rolling wrench/stance control, not more entry waits. Placeholder99388restored,no training.
-[Evidence](log/2026-10-08-m1-lift-handoff.md).

## 2026-10-08 previous: exact internal mesh-pair diagnostic, not promoted

-13tests;10opposite faces/wheel canceled, closededges and sampledouterenvelope unchanged. PhysicalROLL0 blocks on18.72/26.06N support; no crossing fix.
-Next event-gated lift/roll settling withinexistingbudget, no further mesh sweep. Placeholder62471restored,no training.
-[Evidence](log/2026-10-08-m1-mesh-pairs.md).

## 2026-10-08 previous: planner/executor candidate mismatch fixed

-20tests; translation-only runtime filters candidates before selection. Actual2.5msentry8/8valid;5msbaselineplanexactunchanged.
-2.5msphysical passes entry but fails PREPARE62/RBL0N. Timestep change not promoted. Placeholder13723restored,no training.
-[Evidence](log/2026-10-08-m1-entry-capability.md).

## 2026-10-08 previous: contact patch switch, resolution-only fix rejected

-7observer tests; unchanged128trajectory, targetconstant/torquesmooth at normal-load drop. Contact separation min.987→1.182mm.
-Source256comparison fails LIFT5/FBL9.62N, not promoted. Next collision continuity/contact coupling, no gain sweep. Placeholder4171104 restored,no training.
-[Evidence](log/2026-10-08-m1-roll-patches.md).

## 2026-10-08 previous: 5ms rolling transient isolated

- 153tests; physical lift_samples exactly baseline. ROLL6 final5ms force drops46.29→12.21N with COM/rotation impulse; do not average away protection.
- Next contact/stance actuator coupling audit, not low-frequency COM feedforward alone. Placeholder4135886 restored; no training.
- [Evidence](log/2026-10-08-m1-roll-substeps.md).

## 2026-10-08 previous: rolling continuity tested, dynamic support still open

- 149tests pass. Zero-start ramp rejects ROLL3; continuous-start ramp rejects ROLL6 at row7 FBL12.21N despite37.67mm margin. No LAND/crossing/training.
- Next coupled acceleration/support/COM control; no further scalar-profile sweep or threshold relaxation. Placeholder4102845 restored.
- [Evidence](log/2026-10-08-m1-roll-continuous.md).

## 2026-10-08 previous: full flat lift/roll after unload support correction

- Fixed double-limited ramp target in new opt-in UNLOAD feedback;144tests pass.
- GPU7 all8 lift159.36..159.80mm and execute20ROLL steps; LAND11 row5RBL contact8.19N triggersstop. Not crossing/landing success.
- Next T306 child: braking/lowering overlap and contact dynamics. Placeholder4039652 restored; no training.
- [Evidence](log/2026-10-08-m1-unload-support.md).

## 2026-10-08 previous: posture-only hypothesis tested and insufficient

- Default-off bounded RP feedback,103 tests. GPU7 tilt improves but static support stays29.99N; still LIFT36 rejection/no ROLL/LAND.
- Anchor drift alone is not causal: common translation preserves support loads. Open T306 child refined to measured support-relative COM placement, not gain tuning.
- Placeholder3976474 restored; no training. [Evidence](log/2026-10-08-m1-attitude-feedback.md).

## 2026-10-08 previous: anticipatory runtime exposes support-anchor drift

- Default-off entry reference now used continuously through PREPARE/UNLOAD;74 tests pass.
- GPU7 all8 PREPARE ready; LIFT36 allocation rejects row0 at~54mm. Actual static support29.99065N vs nominal36.446N; support-anchor drift18.15mm. No crossing/training claim.
- Open T306 child: measured support geometry/compliance; keep candidate opt-in. Placeholder3872161 restored.
- [Evidence](log/2026-10-08-m1-anticipatory-runtime.md).

## 2026-10-08 previous: PREPARE4s confirmed and implemented

- UserconfirmedPREPAREonly4s. Design+probe200stepcap updated,33tests pass. Allotherphase/safetybounds unchanged; no newphysicalrun or training.
- No budgetapprovalpending. Next opt-in causalentryreference and continuousUNLOADintegration, then GPU7comparison/placeholderrestore.
- [Evidence](log/2026-10-08-m1-prepare-four-seconds.md).

## 2026-10-07 historical: PREPARE deadline conflict required user choice

- Existingramp needs3.44..3.56s for70..75mm;2s rest-to-rest bound48mm. Offline4s eightrowIKpaths pass,maxjointspeed.122943rad/s, NOTphysicalproof.
- Asked extendPREPAREonlyto4s vsretain2s/redesigncontrol; noanswer, contractunchanged. No training/GPUchange. Goalactive.
- [Evidence](log/2026-10-07-m1-transfer-budget.md).

## 2026-10-07 previous: causal entry-only forecast finds all-leg static candidates

- 19tests; actualGPU7entrysnapshot matchesbaseline. 2401poses/row x17heights:8/8eligible, selectedRPdelta0, shifts20..75mm, worstload35.25N.
- Next bounded selectedreference transfer/path/effort and physicaltracking;17staticpoints notdynamicproof. Placeholder656674restored,no training.
- [Evidence](log/2026-10-07-m1-entry-forecast.md).

## 2026-10-07 previous: whole-sampled-lift candidate selector

- 20tests; selector rejects any intermediateunderload/IKfailure and unchangedbounds; allinvalid returns index-1, notsuccess. Prefers minimumshift/tilt amongeligibleposes.
- Next actualentrypose snapshot + causalforecast generation and path/slew checks; historicalPREPARE lacksquat/joints. No runtime/trainingchange.
- [Evidence](log/2026-10-07-m1-anticipatory-selector.md).

## 2026-10-07 previous: early lifted-pose support is feasible in sampled static model

- 1715poses/row: lateFBLanchors0sampled35Nsolutions; entryanchors+160mmlift ALL8rows have35Nsolutions inside79.9mmreferencebound.
- MeasuredFBLroot drift86.95..86.98mm;80mmisreferencebound, notactualrootproof. Next causalentrycandidate/fullpath and driftcontrol, notlatepatch.
- [Evidence](log/2026-10-07-m1-support-pose.md).

## 2026-10-07 previous: named batched mass predictor

- 8tests; puretorch predictor agrees with792nativeposes:float32 whole/bodyCOM<5.74um, float64<4.27um. Reversed name/column order exactlyequivalent.
- Next use candidate liftedpose predictions for bounded anticipatorysupport feasibility/integration. Not wired tocontrol; no training/GPUchange.
- [Evidence](log/2026-10-07-m1-mass-predictor.md).

## 2026-10-07 previous: direct native COM verification

- 3tests; GPU7eightenvobserver run reproduces exact baseline trajectory andROLLrejection. Direct rootquaternion COM error4.27um, individualbody3.67um across792rows.
- Next tested candidate-pose predictor/anticipatorysupport; dynamiccrossing remainsopen. Placeholder424671restored,no training.
- [Evidence](log/2026-10-07-m1-native-com.md).

## 2026-10-07 previous: authored COM replay matches recorded poses

- 792native row-samples:FK fit max3.12micrometers, wholeCOM max4.33micrometers. Uses wheel-fitted attitude, not independent root-quaternion validation.
- Next tested candidate-pose predictor and native root/bodyCOM validation before anticipatory support integration. No GPU/training/control changes.
- [Evidence](log/2026-10-07-m1-com-replay.md).

## 2026-10-07 previous: predictive COM source inventory

- CPU USD audit:17bodies/16movingjoints,41.045319557kg matches native total. Each leg5.19883kg; baseCOM asymmetric and FBL_HIP has nonidentity parent rotation.
- Next named-joint FK/native COM comparison before anticipatory support changes. No GPU/probe/training; placeholder134617 untouched.
- [Evidence](log/2026-10-07-m1-mass-tree.md).

## 2026-10-07 previous: horizontal-only load reference infeasible at current pose

- 12tests; existingROLLfeedback rejects9 on row4entrybound. Proportionaltarget80.76mm; independent minimum-entry halfplane solution80.713mm>80mm for35Ngoal. Not a hardware impossibility proof.
- Liftedleg changesCOM: frontstaticreservefalls~31N. Next anticipatoryPREPARE/LIFT support and boundedposture, not largerhorizontalshift/lowerthreshold. Placeholder134617restored,no training.
- [Evidence](log/2026-10-07-m1-sdf-load-feedback.md).

## 2026-10-07 previous: actual LIFT support-mask wiring fixed

- 29tests; world-frame mode previously logged advance=false butpassedNone toLIFT. Baseline14underloadevents stillraisedtarget; fixed9events allholdtarget (0violations).
- StillROLLoffset13reject row0RAR28.21N, only1.8..3.0mmtravel/noLAND. Next proactive supportredistribution. Priorclaims of LIFTpause corrected. Placeholder65616restored,no training.
- [Evidence](log/2026-10-07-m1-lift-gate.md).

## 2026-10-07 previous: rolling handoff alone does not restore support

- 18tests; single-variable removal of zero-start rollprofile preserves exact UNLOAD/LIFT. Forwardprogress0.8..1.5mm, butROLLoffset10 rejects row5RBL27.72N; no landing.
- Preexisting LIFT dips occur beforeROLL, so next proactive three-support redistribution, not onlywheel handoff. Own placeholder4155417restored,no training or controlcodechange.
- [Evidence](log/2026-10-07-m1-roll-handoff.md).

## 2026-10-07 previous: smooth UNLOAD reaches all-leg 16cm lift

- 49tests; opt-in existing bounded COM ramp fixes abrupt~2m/s2 reference starts.8/8unload gate at64, then wheel-center lift159.6..159.8mm, max tilt.013rad.
- Still notcrossing: LIFT support transient min17.37N, ROLLoffset5 rejects row1RBL29.69N<30N; no landing/travel acceptance. Next LIFT/ROLL support continuity. Own placeholder4054047restored,no training.
- [Evidence](log/2026-10-07-m1-unload-ramp.md).

## 2026-10-07 previous: friction moment explains dynamic load deficit

- 7 tests; exact baseline physical reproduction. Measured friction matches mass*COM acceleration; roll moment4.18..5.12Nm shifts static lowwheel34N prediction to19..21N versus actual23..27N.
- Next acceleration/braking and unloading coordination, not static gravity-only allocation or reduced guards. Own placeholder3932345 restored; no training.
- [Evidence](log/2026-10-07-m1-friction-substeps.md).

## 2026-10-07 previous: COM motion distinguishes dynamic support from static allocation

- 3 observer tests; physical UNLOAD samples exactly match baseline. Mass-weighted COM has lateral acceleration ~0.16..0.18m/s2 during load loss. Normal-contact API does not measure friction; no traction root cause claim yet.
- Next dynamic support / friction-inclusive momentum evidence, not another threshold change. Own placeholder3835014 restored; no training.
- [Evidence](log/2026-10-07-m1-com-substeps.md).

## 2026-10-07 previous: named substep audit confirms real load decline

- Correct planner labels toFBL,FAR,RBL,RAR; runtime namesresolved. LowwheelPD only-.4..+.6Nm, not prior misindexed~-18Nm hypothesis.
- 2observer tests; native5msforces decline across5controlsteps, finalmeans22.65..26.55N. Exactbaseline outcome; notendpointnoise. Next dynamicload/COM/moment coordination. Placeholder3692792restored,no training.
- [Evidence](log/2026-10-07-m1-support-substeps.md).

## 2026-10-07 previous: settled activation exposes support-load deficit

- 39tests; per-rowheight activation at31..41 aftereffort/loadready. AtUNLOAD52 allselectedforce0N, but frontcases another support26..29N<30N; shift80.275mm rejects53.
- Next target-versus-actual three-support load/stance coordination, not more height/bound tuning. NoLIFT/training;placeholder3579350restored.
- [Evidence](log/2026-10-07-m1-height-settled.md).

## 2026-10-07 previous: exact height candidate blocked by transfer transient

- 46tests; default-off height-only mode preserves bodyXY/stance9 and corrects worldZ. Physical8env rejectsUNLOAD12: FARdesiredshift80.61mm>80mm, beforeLIFT.
- Next inspect early COM/support/effort/correction coordination, not boundincrease. Candidate not promoted, no training;placeholder3502498restored.
- [Evidence](log/2026-10-07-m1-height-only-frame.md).

## 2026-10-07 previous: unload height error attributed to ignored attitude

- 21tests;588/596failedrowframes have selectedforce>5N. Actualheight lags reference3.4..4.2mm, matching first-order roll/pitch effect3.6..4.5mm.
- FullXYZ compensation comparison rejectsUNLOAD15 on25mmframe bound/lateral drift. Next worldZ-only correction retaining bodyXY, not fullXYZ or ignored tilt. Placeholder3429808restored,no training.
- [Evidence](log/2026-10-07-m1-hold-pose-attribution.md).

## 2026-10-07 previous: continuous wheel holding reaches UNLOAD

- 20tests;100PREPARE+100UNLOAD execute without prior frame rejection, command slew<=.004m/s per20ms. Still unload_timeout; selected contact intermittently exceeds5N, fresh streaks insufficient.
- Next decompose unload gate and actual contact separation/height inhibition; preserve5N/5frames. Later phases not physically reached. Placeholder3356222 restored,no training.
- [Evidence](log/2026-10-07-m1-phase-wheel-hold.md).

## 2026-10-07 previous: wheel holding reduces physical PREPARE drift

- 18 tests;8env100PREPARE completes. Backward wheel drift reduced from24..39mm to6.68..12.37mm; last root-reference errors8.12..17.48mm, sampled support>=48.13N.
- NoUNLOAD/LIFT executed. Next continuous phase handoff and fullcycle validation, not relaxed guards/training. Placeholder3276873 restored.
- [Evidence](log/2026-10-07-m1-prepare-wheel-hold.md).

## 2026-10-07 previous: bounded wheel-hold command primitive

- 16 CPU tests pass after five RED failures. Added longitudinal anchor feedback, 0.04m/s speed and 0.2m/s2 slew bounds, heading projection and invalid-state rejection.
- Not runtime-integrated or physically validated. Next opt-in PREPARE comparison plus safe phase handoff; no relaxed gates or long training. Placeholder3190750 untouched.
- [Evidence](log/2026-10-07-m1-wheel-hold-primitive.md).

## 2026-10-07 previous: single-leg entry exposes wheel-anchor drift

-15tests; sourceSDF fullcycle stops atUNLOAD0 beforeLIFT: actualwheelanchors drift24..39mm duringPREPARE, exceeding25mm actual/reference framebound. Targetready is not actualanchorretention.
- Next bounded wheelholding duringPREPARE/UNLOAD and smooth release toROLL, not frame-limit relaxation. Placeholder3190750 restored; no training.
- [Evidence](log/2026-10-07-m1-sdf-single-leg-entry.md).

## 2026-10-07 previous: effective SDF contact margin restores four-support rolling

-14tests; original mesh retained, explicit1mmrest/2mmcontact verified on32wheels.8/8complete180steps,forward112.40..113.15mm,minimumsampledforce51.87N. Mass/inertia/materialexact baseline.
- Fixed invalid diagnostic offset pair (authored1mm previouslynative0). This is four-support rolling only, not crossing; next full single-leg cycle with unchangedguards, then obstacle acceptance. Placeholder3162948 restored, no training.
- [Evidence](log/2026-10-07-m1-sdf-contact-margin.md).

## 2026-10-07 previous: source SDF cooks but standing contact rejects

-8tests; original points retained, no remeshing,32 wheel triangle shapes confirmed. Resolutions128/256 reject before rolling on zero/low wheel support force; no useful-travel conclusion.
- Physical arrays exactly match fixed baseline. Keep default collision/guards; next contact geometry/substep audit distinguishes actual loss versus sampled impulse. Placeholder3078553 restored, no training.
- [Evidence](log/2026-10-07-m1-source-sdf-comparison.md).

## 2026-10-07 previous: original wheel topology prerequisite

- CPU audit of all four source wheels finds six four-face nonmanifold edges per wheel after exact/tolerance welding; no boundary or zero-area faces. Installed SDF API exists, but solid validity/cooking is unverified.
- New loaded-contact child: inspect local overlap/solid interpretation before bounded SDF comparison; no asset/controller change or training. Placeholder2915023 left running.
- [Evidence](log/2026-10-07-m1-source-mesh-topology.md).

## 2026-10-07 previous: explicit wheel effort arrives but loaded wheels still stall

-54tests; native PhysX confirms3Nm supportwheel torque,20Nm/s ramp/zeroendpoints;8/8settle but negligible translation. Not a drive-delivery failure.
- Retain defaults/no training; next source-mesh-faithful collision representation investigation, not torque escalation. Placeholder2915023 restored.
- [Evidence](log/2026-10-07-m1-explicit-wheel-effort.md).

## 2026-10-07 previous: unload final-frame bug fixed; cylinder also stalls under load

-49tests. Consume fresh result of100thUNLOADaction without adding action; RBL8/8 gate now passes. Cylinder reachesROLL but rejects102(minsupport29.372N), negative~.69mmprogress.
- Identical masses/inertias/materials confirmed; cylinder is not a fix. Keep source assets/defaults; next loaded-contact/dynamic coordination, no more geometry substitution on faith. Placeholder2857178 restored; no training.
- [Evidence](log/2026-10-07-m1-cylinder-and-unload-boundary.md).

## 2026-10-07 previous: all four lifted wheels track drive, loaded contact remains blocker

-107tests;8/8free-wheel cycles settle, selected angle .07503.. .07720rad vs .07503radcommand, selected contact0N; groundedwheel targets0 verified.
- Drive can rotate free wheels. Next isolate loaded contact representation/constraints before controller rewrite; not crossing acceptance. Placeholder2786123 restored; no training.
- [Evidence](log/2026-10-07-m1-free-wheel-drive.md).

## 2026-10-07 previous: architecture audit identifies persistent loaded contact pairs

- No runtime changes. Main loaded FAR/RBL retain two~30mm-spaced positive contacts even atgain20; light FBL unloads one point and rotates more. This is correlation, not solved rootcause.
- Normal-only static allocation cannot prove dynamic feasibility; do not jump to WBC without isolation. Next bounded lifted-wheel-only drive comparison before changing contact/control architecture. Placeholder2723800 remains reserved; no training.
- [Evidence](log/2026-10-07-m1-contact-architecture-audit.md).

## 2026-10-07 previous: half timestep rejected, no rolling improvement

-24tests; actual2.5ms x8 retains20mscontrol; minimum rolling support31.101N, negative .596..1.126mm travel; settle_contact_lost_or_missing, not accepted.
- Keep5msdefault. Stop speed/gain/timestep-only tuning; revisit three-support contact and coordinated body/leg dynamics before further runtime changes. Placeholder2723800 restored; no training.
- [Evidence](log/2026-10-07-m1-half-timestep.md).

## 2026-10-07 previous: native substep data rules out stale wheel cache

-18tests;20actions x4physics samples, native/cache exact equal. Env3FAR net angle .000969rad versus endpoint-velocity integral .026048rad. This is not by itself a solver bug: TGS internal integration uses intermediate velocities.
- Same physical outcome as no-observer baseline; next controlled timestep/internal solver investigation, no gain escalation/training. Placeholder2696342 restored.
- [Evidence](log/2026-10-07-m1-native-substeps.md).

## 2026-10-07 previous: phase-isolated wheel gain does not restore motion

-90tests; gain20 only duringROLL, backend restored5 atLAND;8/8settle, min support33.424N. Estimated loaded drive4..10Nm still gives no effective advance.
- Stop gain/speed-only tuning; investigate contact constraints and substep velocity/angle consistency. No training;placeholder2662902 restored.
- [Evidence](log/2026-10-07-m1-roll-gain-comparison.md).

## 2026-10-07 previous: stable preload higher-drive comparison still cannot advance

- 14 rolling tests pass; matched physical cap .1 produces actual .036m/s peak, 7.2mm command integral. 8/8 settle complete, minimum support34.278N, but root retreats .548..1.109mm.
- Next drive torque/contact resistance comparison, not further speed increase or long training. Placeholder2623404 restored.
- [Evidence](log/2026-10-07-m1-preload-drive-comparison.md).

## 2026-10-07 previous: leg-aware preload completes short cycle, traction remains open

- 74 focused tests pass. Front-selected reserve35N/rear-selected40N: 8/8 lift/roll-window/land/settle completed; minimum rolling support34.976N.
- No crossing: root progress remains negative submillimeter and loaded wheel net angles are only .0013.. .0034rad. Next matched traction comparison on stable preload baseline; no long training.
- [Evidence](log/2026-10-07-m1-rear-preload-cycle.md). Placeholder2567503 verified restored.

## 2026-10-07 previous: smooth COM integration still fails moving support

-78tests; physical rejection103 vs direct97, still29.928N and no traversal. LAND continuity not reached.
- Full shift failedrow3=13mm vs row0=76.7mm: next per-leg preload feasibility, not uniform reserve or reactive gain. No training;placeholder2523812.
- [Evidence](log/2026-10-07-m1-com-runtime.md).

## 2026-10-07 previous: bounded COM reference primitive

-77tests; PD torque changes materially while static allocation stays similar. Added isolated acceleration/braking-limited reference, not runtime-enabled.
- Next continuous ROLL/LAND/SETTLE integration and matched smoke; preserve complete entry bound and actual joint guards. No training;placeholder2471170 unchanged.
- [Evidence](log/2026-10-07-m1-com-trajectory.md).

## 2026-10-07 previous: static moving-load feedback worsens transient unloading

-73tests; measured reserve now honors35N; opt-in moving-frame COM feedback implemented. Physical rejection97 vs baseline105, weak load28.768N.
- Feedback stays default-off. Next acceleration/wrench-aware redistribution, not static correction gain. No training;placeholder2471170.
- [Evidence](log/2026-10-07-m1-moving-load-feedback.md).

## 2026-10-07 previous: controlled finer-hull comparison insufficient

-46tests; paired fixed-physics shapes have identical masses/inertias/material values. Original rejects105, split rejects107; both negative progress.
- Split is diagnostic only, not a fix. Next bounded moving-load compensation; no more shape/speed-only sweeps. No training;placeholder2420282.
- [Evidence](log/2026-10-07-m1-split-shoulder-comparison.md).

## 2026-10-07 previous: loaded shoulder wheels retain stationary contacts

- Read-only lifted rolling audit: FAR/RBL contacts fixed, net wheel angles~.0018rad while qdot suggests motion;14tests. Same support rejection104.
- Next contact discretization fidelity under three-support loads; COM feedback gap also open. No training;placeholder2363319.
- [Evidence](log/2026-10-07-m1-three-support-contact.md).

## 2026-10-07 previous: lower speed alone does not restore moving support

- Diagnostic .02m/s cap still rejects row3 FBL29.921N atstep104 (only2actions later); all8 forward progress remains negative.13tests.
- Next measured moving support/traction/reference control; no threshold relaxation or long training. Placeholder2339056 restored.
- [Evidence](log/2026-10-07-m1-low-speed-support.md).

## 2026-10-07 previous: reserve-only approach hits COM bound

-58tests;40Nplanning reserve fails UNLOADstep11:required80.264mm exceeds80mm bound. Default35N and all hard protections unchanged.
- Next measured moving-load/speed coordination within COM space, not more static reserve or relaxed limits. No training;placeholder2299107.
- [Evidence](log/2026-10-07-m1-support-reserve-bound.md).

## 2026-10-07 previous: shoulder static cycle passes, moving support needs control

- 53tests;8/8lift155.7..157.8mm. Rolling aborts atstep102 on29.982N support<30N, not pose/clearance.
- Matchedzero-speed hold completes8/8stablelanding,allstreak5. Next moving support-load/COM control; preserve30Nfloor. No training;placeholder2265953.
- [Evidence](log/2026-10-07-m1-shoulder-lift-cycle.md).

## 2026-10-07 previous: shoulder profile and physical invariants

- Shoulder-preserving regular hull restores8/8rolling49.8..62.7mm; masses/inertias/materials exactly match baseline.24tests.
- Radial underapprox bound4.69mm; keep original conservative envelope for crossing oracle. Next lift/landing regression and model-fidelity assessment. No training;placeholder2221235.
- [Evidence](log/2026-10-07-m1-shoulder-wheel-comparison.md).

## 2026-10-07 previous: collision-envelope comparison restores rolling

- Opt-in32-sided envelope:8/8advance86.8..94.7mm vs baseline<0.4mm;180steps/no guard rejection.23tests. Strong causal evidence against source collision representation.
- Diagnostic cylinder preserves gross envelope, not tire shoulders; audit physical invariants/fidelity before production and redo lift/landing/obstacle acceptance. No training;placeholder2193711.
- [Evidence](log/2026-10-07-m1-wheel-envelope-comparison.md).

## 2026-10-07 previous: actual cooked hull read

- Runtime FBL wheel hull34vertices/62polygons; sparse uneven tread samples. Normal contact world-Y moment opposes drive (~-1.7Nm), but dynamics balance not established.
- Next controlled geometry-fidelity comparison preserving mass/inertia/friction, not gain tuning. No training; placeholder2174114.
- [Evidence](log/2026-10-07-m1-cooked-wheel-hull.md).

## 2026-10-07 previous: direct contact evidence / flat label corrected

- Prior flat-base probes retained48semantic obstacles. Verified none-stage scene contains only ground and reproduces failure exactly, excluding those obstacles as necessary cause.
- Exact mesh filter yields two stationary FBL contacts spanning44.26mm with load transfer; next cooked support-face/drive moment audit. No training; placeholder2154675.
- [Evidence and correction](log/2026-10-07-m1-contact-patch-evidence.md).

## 2026-10-07 previous: actual drive and solver comparison

- PhysX confirms wheel stiffness0/damping5/maxspeed20.84rad/s. Standing-only velocity iterations4 read back but no rolling recovery (<0.4mm progress).
- 22tests; next inspect actual contact constraints, not further parameter guesses. No training; placeholder2112963.
- [Evidence](log/2026-10-07-m1-physx-drive-solver.md).

## 2026-10-07 previous: collision frame checked read-only

- Inspected FBL collision-to-body transform is identity, thin axis Y agrees with joint axis. No frame mismatch found; source drive values must not replace runtime telemetry.
- Next actual cooked contact/solver response. No GPU use or config changes.
- [Evidence](log/2026-10-07-m1-collision-frame-audit.md).

## 2026-10-07 previous: wheel angle is not sustained rotation

- Same180-step control: row0 wheel net angles only0.00086..0.00110rad, wheel centers move<0.003mm despite positive instantaneous wheel-speed readings.
- Next inspect substep/contact/solver consistency; do not interpret instantaneous speed as rolling. No training; placeholder2076869.
- [Evidence](log/2026-10-07-m1-wheel-angle-response.md).

## 2026-10-07 previous: sustained rolling still blocked

- 21 focused tests; bounded 180-step flat diagnostic completes. Two-second rolling command integrates to 148 mm but actual progress stays below 0.4 mm.
- Next measure cumulative wheel rotation/contact-point motion; short startup duration alone does not explain failure. No training; placeholder 2060766.
- [Evidence](log/2026-10-07-m1-sustained-rolling.md).

## 2026-10-07 previous: rolling without support feedforward

- Matched gain-0 probe completes 100 steps; all eight rows still move backward 0.62–0.69 mm during the rolling window. Feedforward is not a necessary cause.
- Next inspect contact/angular response and distinguish short startup transient from sustained rolling. No training; placeholder 2043200 restored.
- [Evidence](log/2026-10-07-m1-rolling-no-feedforward.md).

## 2026-10-07 previous: upload delta and rolling diagnostic

- 20 focused tests passed. Four-support rolling comparison and actual wheel-limit telemetry added; PhysX limits are effectively unbounded.
- Effective forward traversal remains open; no crossing acceptance or training. Placeholder restored (2011308).
- [Changes and evidence](log/2026-10-07-m1-upload-improvements.md).

## 2026-10-07 previous: wheel drive limits/friction ruled out

- Runtimefriction0,stiffness0,damping5;drive~1..2.6Nm vs50Nmlimit,no clipping.
- USDwheelusesconvexHull;facetingresistanceishypothesisnotproven. Nextloaded
  four-supportdrivecontrolvsheldleg;no blindgain/geometrychanges.
- Flatlandingreproduced;placeholder1964482,no training.
  [Evidence](log/2026-10-07-m1-wheel-traction-audit.md).

## 2026-10-07 previous: contact-persistent SETTLE passes

-172tests;8/8flatcyclelandsstably after .88sSETTLE;51..67Nfinalselectedload.
  HeightfrozenduringSETTLE;5frames>10Nacceptanceunchanged.
- Effectiveforwardmotionstill<1mm;nextwheeltraction/torque/trackingaudit,
  NOTcrossingacceptance. Placeholder1934277,no training.
  [Evidence](log/2026-10-07-m1-settle-contact-persistence.md).

## 2026-10-07 previous: bounded acceleration passes support but not traversal

-54tests;20ROLLactions withsupportmin35.11N,no30Nfloorviolation.
- Actualprogress<1mm despite7.2mmcommanded:NOTeffectiveforwardtraversal.
  LANDstillrejects8..10N contactjitter. Nexttracking/traction andsettlecontract.
- Placeholder1893212 restored;no training. [Evidence](log/2026-10-07-m1-bounded-rolling-ramp.md).

## 2026-10-07 previous: rolling direction chain verified / transient isolated

- Actualtargets1.042rad/s,damping5,positiveYaxes:donotflipsign.
- Matchedzero-speed highhold passes20frames;stepdrive failsafter9actions.
  Nextacceleration/decelerationcontrolwithunchanged30Nfloor.
- ZerocontrolalsoexposesmarginalLAND/SETTLEcontact;noacceptance/training.
  Placeholder1863813. [Evidence](log/2026-10-07-m1-rolling-axis-control.md).

## 2026-10-07 previous: held-leg rolling support rejection

-46tests;optional rolling reference transported bymeasuredforwardprogress.
- Physicalroll stopsafter9actions:weak support29.07..29.54N below30N;
  negative transient displacement,axis signnotyetproven. No training.
- Next runtimewheel-target/axis andacceleration/load-transferaudit.
  Placeholder1815158 restored. [Evidence](log/2026-10-07-m1-rolling-support-probe.md).

## 2026-10-07 previous: measured traverse admission module

-43CPUtests: measured5cmclearance requiredtoadvance; wheel rear mustpass far
  edge+4cm beforeLAND. Notyetwiredtophysicalobstacles;no crossingclaim.
- Actualflatcycle worstremainingtime .38s;nextactualbox+rollingreference
  integrationandsmoke. [Evidence](log/2026-10-07-m1-measured-traverse-gate.md).

## 2026-10-07 previous: retimed physical flat lift/landing

- Opt-in Cartesian retiming preserves .5rad/s joint limit;8/8measuredrise
  15.31..15.77cm andstablelanding. High window only .16...24s,NOT crossing.
- Next obstacle-aware TRAVERSE hold + rolling references under4s;no training.
  Placeholder1745580 restored. [Evidence](log/2026-10-07-m1-retimed-lift-cycle.md).

## 2026-10-07 previous: obstacle-cycle timing is infeasible in current vertical probe

- CPU actual lift_target: 15 cm up/down takes 110+109 steps = 4.38 s,
  already over 4 s before traverse. No physical crossing claim or long training.
- Next trajectory-budget-feasibility plus rolling support references; preserve
  clearance/slew limits. [Evidence](log/2026-10-07-m1-crossing-time-budget.md).

## 2026-10-07 previous: flat lift/land/settle cycle passes

-139tests;8/8stablelanding,allstreak5,SETTLE.72s after4saction,final51..65N.
- Nextactualobstacle/forwardtraverse/clearance timing+3seeds/video; no fullcrossing
  ortrainedpolicyclaim. No longtraining.
- Placeholder1640307 restored; [evidence](log/2026-10-07-m1-four-support-settle.md).

## 2026-10-07 previous: all8 ground contacts established

-106tests; bounded5mmsearch bringsall8touchdownwithin4s; weakrowsneed1.6..2mm.
- Stillnotsettled:fourcontacteffortgap6..14Nm. Nextapproved2sSETTLEaftercontact,
  noextendedsinglelegsearch orobstacle-successclaim. No training.
- Placeholder1598746 restored; [evidence](log/2026-10-07-m1-ground-search.md).

## 2026-10-07 previous: landing timing separates two causes

-43tests;90up/110down:6contact33..43N,2zeroheight butweak.11/1.40N;stilltimeout.
- Next boundedcontactsearch and LAND/SETTLE budgetreview;notobstacleacceptance.
- Placeholder1547510 restored; [evidence](log/2026-10-07-m1-landing-timing.md).

## 2026-10-07 previous: controlled lowering not yet touchdown

-104tests;100up+100down completes butlanding_timeout. NoLANDselectedforce>10N,
  finalforce0;effortgap<.013Nm. Peak12.72..14.44cm,not10cmobstacleclearanceproof.
- Next contact-seeking-landing geometry/budget/postactioncontact investigation.
- Placeholder1515614 restored; [evidence](log/2026-10-07-m1-controlled-land-cycle.md).

## 2026-10-07 previous: physical flat single-leg lift passes

-133tests;8/8finish200LIFTactions,actualrise17.32..17.82cm;supportmin36.37N,
  tiltabsmax.0128rad,non-supportcontact0. No obstaclecrossingclaim/training.
- Next controlledland/settle withtotal4sphasebudget, then actualobstacle/video.
- Placeholder1479138 restored; [evidence](log/2026-10-07-m1-lift-handoff.md).

## 2026-10-07 previous: all8 measured unloading passes

-132tests; all8UNLOADready within94samples,force<=2.54N,streak>=5.
- FirstLIFTpreaction rejectedreason6all8, noexecutedlift. Nextcontinuousframe
  handoff; do not loosen slew or claimcrossing. No longtraining.
- Placeholder1451314 restored; [evidence](log/2026-10-07-m1-finite-unload.md).

## 2026-10-07 previous: vertical compensation avoids lateral abort

-130tests;100UNLOADcompleted buttimeout/0LIFT.6instantready,only4sustained5frames;
  remaining5.79/5.61N. Allcorrection scales1, no oldframeabort.
- Next finite-unload-progress withinunchangedphysical/timegates.
- Placeholder1427632 restored; [evidence](log/2026-10-07-m1-vertical-only-unload.md).

## 2026-10-07 previous: frame divergence is predominantly lateral

-54tests/native0; row5translation25.034mm exceeds25mm,mainlyY22.91mm;
  Zsag2.46mm,otherguardsvalid. NoLIFT/training.
- Next vertical-only-frame matchedcomparison, retaining fullpose safety guards.
- Placeholder1402415 restored; [evidence](log/2026-10-07-m1-frame-residual.md).

## 2026-10-07 previous: frame progress fixed, physical bound rejection

-127tests; full correction nowreachable underjoint slew, but physicalstep25
  row5 frame-safe check rejects (IK/limits/slew pass).0LIFT.
- Next frame-divergence residual attribution, no bound relaxation/training.
- Placeholder1369869 restored; [evidence](log/2026-10-07-m1-frame-backtrack-progress.md).

## 2026-10-07 previous: selected world pose improves unloading

-125tests;6/8 sustained measuredunloadready, remaining5.59/5.80N. Stilltimeout/0LIFT.
- Next selected-frame-slew reason(finalscale.5), then consistent LIFT handoff.
- Placeholder1310281 restored; [evidence](log/2026-10-07-m1-selected-world-unload.md).

## 2026-10-07 previous: stance tracking attribution

- Offline trace analysis: stancejoint error.024..033rad exceedsselected.003..010;
  force stillfalls and last30steps noeffortholds. Not proven steady-state stall.
- Review stance-pose/contact-effort ownership; no blind gain/timeout changes.
- [Evidence](log/2026-10-07-m1-unload-joint-attribution.md). No new GPU job.

## 2026-10-07 previous: realized unloading mismatch

-48tests/native0; actual wheel deltaZ -3.8..0.1mm despite3.7..6.4mm command;
  root sag4.6..5.2mm, effort waiting32..43steps. No LIFT, no training.
- Child unloading-realization: review vertical pose/effort coupling before gains.
- Placeholder1254648 restored; [evidence](log/2026-10-07-m1-unload-response.md).

## 2026-10-07 previous: zero target insufficient

-121tests;100UNLOADsteps stilltimeout, selected9..19N,0LIFT; no training.
- Next unloading-convergence architecture checkpoint: actual vs commanded height,
  force slope and load-reserve gating; do not continue blind gain/timeout tuning.
- Placeholder1224540 restored; [evidence](log/2026-10-07-m1-zero-force-target.md).

## 2026-10-07 previous: coordinated unloading preserves load feasibility

-117tests; flat8 runs100UNLOADsteps without allocation abort, selected12..19N,
  but timeout before5N; no LIFT. Coordinated COM resolves earlierstep68failure.
- Next unloading-convergence: separate zero-force target from5N measured gate,
  retain.01m/s/2cm bounds. Placeholder1161123 restored.
- [Evidence](log/2026-10-07-m1-coordinated-unload.md).

## 2026-10-07 previous: settled force feedback reduces contact, not yet unloaded

-116tests; feedback after effort settling reaches selected18..31N then row4
  allocation failsstep68,0liftsteps. Fixed prepared root does not track unloading.
- Next coordinated-unload-com using existing bounded mass-aware transfer with
  fixed stance anchors; do not lower30N/5N gates. Placeholder1125373 restored.
- [Evidence](log/2026-10-07-m1-unload-feedback.md).

## 2026-10-07 previous: backend parameters verified; contact proxy corrected

- net_forces_w excludes tangential friction; prior17..22Nm is not full balance.
- Actual backend gains and sent efforts match exactly8/8;112tests/native0.
- Next measured-unload-control with bounded selected-leg reference feedback;
  stop repeating closed parameter audit, no blanket PD cancellation.
- Placeholder1081679 restored; [evidence](log/2026-10-07-m1-backend-effort.md).

## 2026-10-07 previous: total effort/contact proxy mismatch

-112tests; unchanged unload audit shows PD+FF vscontactproxy discrepancy17..22Nm.
- Not enough to blame/cancel PD. Next backend-effort-conventions: actual drive
  parameters, sent effort and projected joint force, including proxy limitations.
- Placeholder1046531 restored; [evidence](log/2026-10-07-m1-total-effort-audit.md).

## 2026-10-07 previous: unloading timeout despite converged effort

-112tests; actual100-step UNLOAD times out,0liftsteps. Effort target gap<.0006Nm
  but selected contacts still25..47N; allocation8/8valid. Ramp time not sufficient explanation.
- Next total-effort-contact-consistency: audit PD+feedforward vs measured contact
  loads before changing policy. No blind gain changes; placeholder997933 restored.
- [Evidence](log/2026-10-07-m1-unload-phase.md).

## 2026-10-07 previous: phase effort handoff needs unloading stage

-108tests; actual PREPARE8/8, LIFTstep7 allocation guard rejects4rows; actual
  supports remain loaded, effort is still transitioning. No successful wheel rise.
- Next bounded UNLOAD/settle holding height, measured contact and effort readiness
  before lift. Preserve thresholds; placeholder973880 restored/clear confirmed.
- [Evidence](log/2026-10-07-m1-phase-effort.md).

## 2026-10-07 previous: matched standing compensation improves tracking

- Named12-leg error falls~46..48%: final.037..041rad baseline vs.020..022rad
  compensation. Both flat8x100 native0/contact maintained/effort cleared.
-107 tests pass; next feedforward-phase-handoff into PREPARE/LIFT with fresh
  PD targets and guarded contact allocation. No actual lift success yet.
- [Evidence](log/2026-10-07-m1-standing-comparison.md).

## 2026-10-07 previous: guarded standing effort smoke

-107 tests pass; flat8x100 standing feedforward native0, contacts>=79N,
  maxaxis tilt.00931rad, effort buffer cleared on exit. No lift claim.
- Next leg-only-standing-comparison: current error includes velocity-controlled
  wheels and cannot prove leg tracking improvement; fix telemetry and matched baseline.
- Placeholder933857 restored; [evidence](log/2026-10-07-m1-standing-effort.md).

## 2026-10-07 previous: actual lift still fails after feasible PREPARE

- f3adc98 physical lift stops step38, nonselected force8.49N; actual rise only
  millimeters vs3..4cm targets. Root sag12..16.5mm, joint tracking error~.07..08rad.
- Next whole-body-load-model bounded-effort-lifecycle and standing compensation
  trial; do not keep increasing geometric margins or start training.
- Placeholder906048 restored; [evidence](log/2026-10-07-m1-load-feasible-lift.md).

## 2026-10-07 previous: load-feasible PREPARE8/8

- Optional barycentric30N load floor preserves bounds;102 tests pass.
- Actual flat8 PREPARE and independent post-stage30N allocation8/8 (was2/8).
- Next actual single-leg lift with live contact gates; no lift/crossing claim.
- Placeholder890689 restored; [evidence](log/2026-10-07-m1-load-feasible-prepare.md).

## 2026-10-07 previous: post-lift load readiness mismatch

- Physical PREPARE8/8 but static three-support30N floor only2/8 feasible; others
  have weakest support25.6..26.4N. Geometric20mm readiness is insufficient.
- Next whole-body-load-model:post-lift-load-readiness; align bounded PREPARE
  target with LIFT30N without lowering thresholds, then effort lifecycle.
-100 tests pass, native0; placeholder867441 restored.
- [Evidence](log/2026-10-07-m1-three-support-audit.md).

## 2026-10-07 previous: bounded static support allocation

- 100 focused tests pass; read-only flat8 dynamics smoke native0, allocations8/8.
- No extra torque applied or lift success. Next three-contact PREPARE audit and
  effort ramp/reset ownership before bounded physical compensation.
- Placeholder848694 restored; [evidence](log/2026-10-07-m1-vertical-allocation.md).

## 2026-10-07 previous: dynamics frame prerequisite verified

- Actual floating-base Jacobian8x17x6x22 and gravity8x22 verified. Jacobian is
  COM-based; wheel-origin conversion reduces FK derivative error to8.05e-5.
-95 tests pass; helper-linked smoke native0. No extra torque applied or lift acceptance.
- Next whole-body-load-model child: bounded force/effort allocation with base
  equilibrium and torque limits before physical compensation. Placeholder809511 restored.
- [Evidence](log/2026-10-07-m1-dynamics-frames.md).

## 2026-10-07 previous: force-aware position candidate remains unaccepted

-92 focused tests pass. Optional load-conserving correction still loses a
  support atstep43 (7.88N) despite20.85mm geometric margin; actualrise millimeters.
- New whole-body-load-model child: examine posture/effort support rather than
  continuing planar gain changes. Runtime dynamics API conventions still unverified.
- Placeholder762874 restored. [Evidence](log/2026-10-07-m1-force-transfer.md).

## 2026-10-07 previous: command-space feedback corrected; load gate still fails

-89 tests pass; trace confirms centimeter-scale command/measured offset.
- Physical PREPARE8/8, LIFT fails atstep45 on nonselected force0N, no clearance.
- New force-versus-margin-handoff child: geometric20mm can stop transfer while
  low support force blocks lifting; need actual load-aware position/attitude planning.
- Placeholder733255 restored. [Evidence](log/2026-10-07-m1-command-com-feedback.md).

## 2026-10-07 previous: hard-margin fallback removes false bound rejection

-88 tests pass; actual8x200 lift trace finishes4s without early rejection,
  nonselected support min21.02N, but measured rise remains millimeters.
- Final margins below20mm; all rows hold. This is timeout/incomplete lifting,
  not success. Next command-to-COM-tracking child diagnoses steady response error.
- Placeholder695745 restored. [Evidence](log/2026-10-07-m1-hard-margin-feasibility.md).

## 2026-10-07 previous: support-aware hold hits target bound

- Per-row lift hold + bounded support transfer added;87 focused tests pass.
- Physical8-env stops atstep8 on8cm target bound before support loss; no lift success.
- New child support-load-distribution.hard-margin-bound-feasibility: check whether
  hard20mm margin fits when optional30mm target does not; do not expand bounds blindly.
- Placeholder660878 restored. [Evidence](log/2026-10-07-m1-lift-support-transfer.md).

## 2026-10-07 previous: pose-only feedback is insufficient

- Torque audit: estimated peak61.92Nm vs150Nm limit; no estimated clipping.
- Opt-in bounded pose feedback added,86 CPU tests pass. Actual lift still fails:
  nonselected support8.48N atstep24; selected wheels unload but clearance inadequate.
- Next T306.contact-transfer.lift-support-tracking.support-load-distribution:
  support-aware transfer/hold and recovery; no long training or success claim.
- Placeholder634517 restored. [Evidence](log/2026-10-07-m1-lift-pose-feedback.md).

## 2026-10-07 previous: single-lift physical gate remains open

- Added bounded single-wheel lift, real IK/slew and fresh PREPARE handoff;83 CPU tests pass.
- Actual8-env lift guard stops atstep36: nonselected support8.79N, actual wheel
  rise only millimeters despite ~3cm target. No crossing success or new training.
- New child T306.contact-transfer.lift-support-tracking: diagnose compliant root
  drift and load redistribution before feedback compensation; recovery still open.
- Placeholder598258 restored. [Evidence](log/2026-10-07-m1-single-lift.md).

## 2026-10-07 previous: first PREPARE 8/8 result

- Explicit probe candidate speed.04/bound.08 + hold-at-hard-margin completed
  flat8x100/native0, seed2: readiness8/8 by1.68s; margins21.5..27.8mm.
- CPU75pass. Only PREPARE evidence; no lift/crossing/PPO acceptance or training.
- Next: bounded single-leg lift and support-loss handling; then three-seed and
  full obstacle/video/event/bypass gates. Placeholder538748 restored.
- [Readiness evidence](log/2026-10-07-m1-prepare-ready.md).

## 2026-10-07 previous: live support / fixed anchor separation

- Corrected projection to measured wheel positions, retaining frozen IK anchors.
- CPU69pass; actual flat8x32/native0, rear readiness4/8, fronts remain unready.
- Offline trace shows ~1cm support-margin overestimate from stale geometry;
  front displacement/time feasibility still OPEN. Placeholder502175 restored.
- [Live-feedback evidence](log/2026-10-07-m1-live-support-feedback.md).

## 2026-10-07 previous: physical PREPARE gate remains open

- Actual GPU7 flat8x32 and8x100 diagnostics ran/native0; readiness4/8 (rear only).
- Fronts fail hard.02m support margin within2s; explicit speed.04 trial stops
  on displacement bound. No lift or training. Placeholder restored PID466385.
- Fixed avoidable incenter detour and recapture of measured-root drift; latest
  freeze fix has CPU verification only (67 passed), not a physical pass.
- [Physical evidence and next root-cause checks](log/2026-10-07-m1-prepare-physical.md).

## 2026-10-07 previous: bounded load transfer

- T306.contact-transfer.proposal: frozen anchors/height, limited root translation,
  real M1 IK/limits/slew and explicit infeasibility reasons implemented.
- 64 focused CPU tests pass; no physical acceptance, no training started.
- Next: connect observer/gate/proposal under phase and reset ownership, then
  actual 8-env smoke; retain full crossing/avoidance/event-metric requirements.
- [Transfer evidence](log/2026-10-07-m1-load-transfer.md).

## 2026-10-07 previous: support observations

- T306.contact-transfer.observer: named wheel forces, mass-weighted COM,
  three-support margin and tilt rates implemented in isolated branch.
- Observer-to-gate CPU integration and regression: 54 passed; no Isaac smoke yet.
- Next: bounded load-transfer/M1 IK and complete coordinator before runtime enable.
- [Observer evidence](log/2026-10-07-m1-support-observer.md).

## 2026-10-07 previous: isolated PREPARE gate

- Written design approved; isolated branch `codex/m1-contact-crossing`.
- Existing dirty baseline preserved separately as `dacfb46` and byte-compared.
- T306.contact-transfer.prepare-gate: CPU contract implemented, 43 focused tests passed.
- Not wired into teacher; no physical crossing or training claim. Next: pre-action
  observation contract and bounded support transfer, then full coordinator.
- [Gate evidence](log/2026-10-07-m1-prepare-gate.md).

## 2026-10-07 historical: contact-driven crossing design

- T306.contact-transfer / T306.event-metrics OPEN: user approved contact/COM-driven
  load transfer before single-leg swing and honest per-obstacle metrics.
- Current teacher still fails physical acceptance; no long training active.
- [Design](../docs/superpowers/specs/2026-10-07-m1-contact-crossing-design.md),
  [evidence](log/2026-10-07-m1-contact-crossing-design.md).
- Written spec review precedes implementation; no new GPU experiment this update.

## 2026-10-03 latest: serial foot-anchor regression

- Current articulated FK is captured only at serial phase handoff and frozen
  as `hold_foot_pos_w`; regression suite is `43 passed, 1 skipped`.
- Physical gate remains open due Isaac CUDA/PhysX foundation failure; no
  training is running.
- [Evidence](log/2026-10-03-m1-foot-anchor-regression.md).

## 2026-10-01 latest: stance encoding / auto-reset

- T306 auto-reset latch defect fixed after RED test; 45 focused tests pass.
- Stance action now encodes measured support pose; physical crossing remains unproven.
- Ineffective warmup stopped. Bounded LR0 reset probe is the only new experiment.
- [Evidence, failed trials and next gate](log/2026-10-01-m1-reset-stance-evidence.md).

## 2026-10-01 M1 approach-gate audit (historical)

- T306.approach-gate OPEN: CPU replay of the actual wrapper method confirms
  premature leg commands on calls 1 and 2 while the near trigger stays false.
- GPU7 has only the user's placeholder PID 2138492; no new training launched.
- Previous phase/replan explanations are not established physical root causes.
  Read the [audit](log/2026-10-01-m1-approach-gate-audit.md) before further tuning.

## 2026-09-29 M1 active conversion checkpoint

- M1 runtime conversion is implemented in the AME scene: M1 asset/body/joint
  names, M1 planner backend, 16-D mixed action, single-leg teacher, 10 cm
  semantic obstacles, and explicit collision penalty.
- The true cross-success path now requires prior candidate, visible lift,
  local wheel-bottom clearance, age/touchdown completion, no collision, and
  obstacle disappearance; cross-rate and conditional success-rate are separate.
- Code gate: 65 focused tests + 1 skipped (including the 10 cm planner test);
  no training was launched.
- Physical gate remains open: a short PhysX probe showed single-leg commands
  and no collision, but not a repeatable >=5 cm wheel-bottom clearance under a
  deterministic obstacle/foot alignment. Do not promote a checkpoint or start
  long training until that probe passes.

# Investigation Dashboard

- 2026-09-23 当前长训：已通过在线 MPC teacher 挂载与 12 腿关节/足端命名修复，GPU7 上 PID 3793266 正在从 `model_16900.pt` 继续训练（`--num_envs 256 --max_iterations 10000`），当前约 16927/26901，未见 OOM、Vulkan 或 traceback。占位程序生命周期包装器已接入：长训启动时停止当前用户的 `sleep.py`，训练退出后恢复；本轮未发现占位进程，因此尚无恢复动作。`small_obstacle_climb` 与 `Crossing success proxy` 目前仍为 0，需继续观察后续迭代及真实轨迹，不能据此宣称跨越已验收。详见 [在线 teacher 与生命周期记录](log/2026-09-23-m1-online-teacher-mount-and-lifecycle.md)。

This page is the fast-start dashboard for agent work. Detailed memory lives in [todo/](todo/); evidence lives in [log/](log/).

## Start Here

- T306最新（2026-09-20）：registry `394ea67`、encounter core `d27e26c` 均SPEC→QUALITY通过；最新全套2317passed/252.31s/0skip/exit0，最终聚焦184passed。CPU 1024单hit/row判定12.51s→0.36s，保留全owner/all-ray精确语义；不是Isaac容量验收。下一步明确为pre-helper vendor hook、行级缓存重置、sync release/begin及原始sidecar/独立replay；不得重做已完成的geometry审计。未接runtime/启动训练，GPU7占位3919095未动。新G1三次/1024/G2/AME/policy/10000仍未完成。[本轮证据](log/2026-09-20-m1-encounter-registry-coordinator.md)。下方旧“当前”段为历史。

- T306最新：ACTIVE，9dc0dc7已接全17body/collider向外姿态投影；主代理2128full/237.61s/0skip、SPEC→QUALITY PASS。唯一amp/GPU7 `pose-projection-live-20260919`完整8×32/native0/wrapper0；4352 colliderstep精确独立回放、原28非计时字段及rawpose逐位一致，rawfailed40保留，原占位351307未动。测试oracle中点Minor已以RED→GREEN64修复，生产不变。下一步直接registry/coordinator/reference hook和遇障交接，不重复基础投影审计；三次新G1/1024/G2/AME/policy/10000尚未完成。[本轮证据](log/2026-09-19-m1-pose-projection.md)。下方旧“当前”段为历史。

- T306最新：ACTIVE，live source owner＋17body逐步raw pose已实现47167e8；主代理2026full/226.43s/0skip、SPEC→QUALITY通过。唯一amp/GPU7实测live-provider-20260919-1830完整8×32/native0/wrapper0、正常先关lease后关env，23raw守卫逐位相同，32×8×17完整姿态；与旧startup28非计时字段逐位一致。原rawfailed40保留，GPU7原占位351307未动。下一步显式向外pose投影→registry/coordinator，不能把本次raw采集称CLEAR/G1/PPO或10000通过；长训尚未启动。[在线实施与实测](log/2026-09-19-m1-live-provider.md)。下列旧“当前”段为历史。

- T306当前：ACTIVE，root944G/495G可用。保守局部geometry已实现3d97e9b，focused222/main1929full/0skip/exit0，SPEC→QUALITY复审通过。主代理对既有现场负例独立回放：136colliders、104Mesh/3664vertices和32native Cylinder全覆盖，原rawfailed40与JSON SHA不变。新模块不改collector/SDK/阈值，不将关闭的probe伪作live provider；下一步open lease＋同一步17body raw poses＋保守world/frame投影接线。GPU7仅原占位351307，无新训练。coordinator/新G1/1024/G2/AME/policy/10000仍未完成。[实现与真实数据回放](log/2026-09-19-m1-conservative-geometry.md)。

- T306当前：BLOCKED，等待精确pip缓存迁移授权或根盘空间恢复；同一条件已连续3个目标轮。fresh root533224KiB，低于1GiB启动门槛；b16168b clean，GPU7仅原占位351307。代码92278b7 CPU门槛已完成（main1687full/169.98s/0skip、SPEC→QUALITY PASS），真实query/G1/G2/AME/policy/10000均未验收。未迁移/删除/启Kit，不再重复CPU基础审计。恢复后fresh资源检查→单次8×32实际query，完整目标不变。[本轮记录](log/2026-09-19-m1-collision-query-initialization.md)。

- T306当前：B2b2b source watch/query lease完成，代码8a3746f；主代理1565full/152.72s/exit0/0skip、实际Carb＋8个M1内存实例CPU probe通过，SPEC→QUALITY PASS。修复真实USD callback保活、finalize失败锁存及构造清理异常公开retry owner。下一步直接8-env实际PhysX query初始化/无额外physics-step诊断，不重复旧基础审计。未启Kit/GPU训练，旧run/SDK/参考/占位不变；完整G1/G2/AME/policy/10000仍未完成。[本轮记录](log/2026-09-19-m1-collision-scene-lease-implementation.md)。

- T306当前：B2b2a静态scene binding与显式CollisionPathScope完成，c608945，main1452full/146.49s/0skip、SPEC→QUALITY PASS。修复真实proxy ID借用引用导致的延后解码SIGSEGV；两次正式scope真实8内存实例136collider/104proxy解码、运动hash不变、只读及关闭拒绝通过。下一步watch/lease与8-env初始化真实query无额外physics-step验证；不重复旧基础审计，不把CPU当物理验收。coordinator/G1/G2/AME/policy/10000仍未完成，占位/SDK/旧run不变。[本轮证据](log/2026-09-19-m1-collision-scene-binding-implementation.md)。下方query完成为历史阶段。

- T306当前：用户已批准“按规格实施”。隔离A1/B1/B2a＋B2b1非阻塞query协议完成，代码f85c7ea，主代理1338full（145.24s/0skip）、SPEC→QUALITY PASS。17408请求CPU协议27.19→2.34s，未接真实SDK/启GPU。现继续薄USD/SDK stage/path/settings/source绑定、geometry失效监控与8-env初始化无额外physics-step诊断；source bounds不能假充PhysX cooked包络。coordinator/sync/replay/G1/G2/AME/learned/10000仍未完成。见[实施记录](log/2026-09-19-m1-collision-query-batch-implementation.md)。下方BLOCKED/待书面审阅为已解除的历史。

- T306当前2026-09-19 11:05：目标BLOCKED，等待具体规格e25e805的用户审阅；方向同意已保留，自动续行不是书面审阅。三轮同条件核验及相关安全审计已完成，停止重复审计。GPU7仅原占位351307，无本任务训练；未改代码或验收目标。确认规格后计划/TDD继续。[等待记录](log/2026-09-19-m1-written-spec-review-blocked.md)。

- T306资源核验2026-09-19 11:02：raw scanner为22801rays/env；全ray xyz单步1024已267.199MiB，超旧NPZ未压256MiB上限，旧verifier非流式。新增.6h.6a.1a.2b证据容量子项；不要求密集全ray编码、不删证据/改精度。根盘仅约3.51GiB，后续本任务大输出需/data预检。原规格仍待书面审阅；未改控制/开仿真，占位保留。见[证据容量](log/2026-09-19-m1-encounter-evidence-capacity.md)。

- T306最新2026-09-19：用户同意修正版A，已写具体规格e25e805并通过自审/两项只读边界复审，待书面审阅后计划/TDD。语义为每次遇障，不永久锁同物体；新增owner交接、frame/identity、G2真实再遇障依赖。未改代码/开仿真，GPU7占位351307保留。旧A/B阻塞解除；10000/learned仍未验收。[规格](../docs/superpowers/specs/2026-09-19-m1-encounter-lifecycle-design.md)、[审阅记录](log/2026-09-19-m1-encounter-design-review.md)。

- T306最新23:36：持续目标 BLOCKED，等待 phase 重入方案 A/B 的用户选择；同一待选条件已跨三轮，安全只读审计已完成。未启动新仿真/训练，GPU7仅占位351307，未改代码/阈值/SDK。完整10000及learned跨越/绕行目标保留但未完成，收到选择后续行。[阻塞核验与恢复条件](log/2026-09-18-m1-design-choice-blocked.md)。

- T306最新23:32：CPU复算定位首次跨越链：FAR失败者的world抬升目标本身偏低（IK回放差<7e-7），RAR横向越界包含root/yaw影响；质量关联不等于单因。记录完整，未改源码/阈值/随机化，未启动新仿真。phase重入方案A/B仍待用户确认；GPU7原占位351307保留。见[几何审计](log/2026-09-18-m1-scale-first-cross-geometry.md)。10000更新及learned跨越/绕行仍未验收。

- T306最新23:07：baseline18完整1600/native0/commonPASS；candidate19完成247步后在prepare247因env523重新wave/非零legs触发保护，native1/wrapper2/verifier3，非旧Isaac原生崩溃。未重启；占位已恢复351307/15744MiB。新子项：18初次跨越几何失败、phase11后重入与接管时序冲突；转CPU定位/设计，不删保护、不改阈值。formal646f486不动，10000/learned仍未验收。见[run19](log/2026-09-18-m1-scale-candidate19.md)、[行为分组](log/2026-09-18-m1-scale-baseline-behavior.md)。下列旧进度为历史。

- T306.6h.6a.1 持续执行中：用户要求直至验收；同一冻结候选run14/15/16三次amp/GPU7完整8×1600均strict8/8、native/wrapper/verdict0、零reset。每个重复2700非计时数组与run14逐位一致。正式接入/回归正在执行；新.6a.1a处理1024紧凑布局、唯一origin和全量验收预算，未启动1024/10000。15GiB占位保留。见[repeat15](log/2026-09-18-m1-sync-repeat15.md)、[repeat16](log/2026-09-18-m1-sync-repeat16.md)、[1024审计](log/2026-09-18-m1-1024-readiness-audit.md)。下列单次run14状态为历史。

- T306.6h.6a 隔离实现与单次物理验证PASS：373CPUtests/spec/quality通过；run14 amp/GPU7单进程完整8×1600，native/wrapper/verdict0，strict8/8（基线4/8），0reset/0重启。接管action245..253，原跨障前缀逐位一致；全首回合轮均速差降到.01966..03224<.08。15GB占位一直保留。未推广正式adapter、未扩1024/10000、非learned policy或大绕行完成；待候选接入与严格重复。见[实现与实测](log/2026-09-18-m1-post-cross-sync-implementation.md)、[设计](../docs/superpowers/specs/2026-09-18-m1-post-cross-wheel-sync-design.md)。

- T306.6h.6 隔离A/B完成、候选拒绝：225CPUtests/spec/quality通过；run13 amp/GPU7完整8×1600、native0、strict1/8（基线4/8）。gain0消除七个完整首回合平地尾段的目标振荡，但env1触发参考终止判据、env2/5后轮横向错过跨杆范围。正式adapter未动、不追加仿真、不扩1024/10000；新.6a需解耦轮同步与跨障速度/轨迹。15GB占位一直保留。见[对照证据](log/2026-09-18-m1-wheel-equalizer-ab.md)。下列状态为历史。

- T306.6h.5c.3 接入完成、严格门槛未全过：正式adapter a86cbf5、212CPUtests通过；run12 amp/GPU7单进程完整8×1600、native0、无重启。8/8完成FAR/RAR窄横杆跨越与落地，4/8仅轮均速差>.08失败。新.6定位到外层轮速反馈饱和交替，等待单变量隔离A/B确认；未启动1024/10000。用户坚持GPU7，已允许必要时停本人15GB占位并在无计算任务后恢复，本次未动。见[严格首测与诊断](log/2026-09-18-m1-reference-strict-run12.md)。下列状态为历史。

- T306.6h.5c.2 STARTUP VERIFIED：amp/GPU7隔离run11完整8×32，native/wrapper均0、startup_passed=true、无重启。212CPUtests与规格/质量审查通过；相比run10新增配置仅replicate_physics=False，场景/初始状态及28个非计时采样字段完全相同。正式入口/SDK/参考/15GB占位不变；未验证1600/1024/10000。新.5c.3待接入与严格行为门槛。见[普通复制A/B](log/2026-09-18-m1-normal-clone-ab.md)。

- T306.6h.5c.1 定位完成：隔离run10完整8×32后native134；53562注册/294调用、零溢出，唯一未返回回调确认为`_physx`中replicator attach返回列表的静态析构。22诊断CPUtests/170副本tests及两轮审查通过。未改SDK/正式入口/占位。新.5c.2拟在隔离副本以replicate_physics=False做8×32对照，等待选择；未启动长训。见[原生责任库证据](log/2026-09-18-m1-physx-exit-owner-capture.md)。

- T306.6h.5c ROUTE A APPROVED：用户允许SDK退出范围调查，并选择先隔离定位native回调注册者。只读审计22关键文件均匹配RECORD；09栈定位libc ef_cxa回调，但注册库仍未知。设计6addb50已记录，未实施新诊断/修复，未启动训练。撤回仅指无效cache-off候选，不是模型/训练进度回退。既往120/1000轮正常结束不等于10000已保证；当前故障在8×32全部完成后关闭阶段，不应当成中途截止的同一根因。见[调查与边界](log/2026-09-18-m1-native-exit-owner-audit.md)。

- T306.6h.5c WAITING DESIGN/SCOPE：三处入口生命周期修补均未得到正常退出。缓存关闭确实生效，但8×32完整执行后native134，原生栈为Py_Exit(0)→C退出回调→list_dealloc→失效threadstate。本轮候选归档并撤回；停止追加局部补丁，需讨论SDK关闭生命周期范围，未改amp/SDK/驱动/占位。1600/1024/10000仍未启动。见[失败与原生证据](log/2026-09-18-m1-reference-stat-cache-gate.md)。

- T306.6h.5a：隔离gdb已安装，5项CPU退出语义测试通过。8×32诊断06完整采样后native139，原生栈定位PhysX tensor对象随Python残留frame析构；正在补充frame文件/函数信息，不改amp/Isaac/驱动/占位进程。未启动1600/1024。见[原生诊断](log/2026-09-18-m1-reference-gdb-capture.md)。

- 2026-09-18 T306.6h.5：amp/GPU7的8×32均完整采样，但正常退出时发生native139，fataltrace定位到解释器GC。两处生命周期风险修补/164CPUtests通过仍未消除原生故障。T306.6h.5a等待用户批准独立gdb获取C/C++栈；保留15GB占位、全部现场，不安装依赖、不启动1600/1024/10000。横杆实测露出45mm。见[首测](log/2026-09-18-m1-reference-gpu7-smoke.md)、[有效栈](log/2026-09-18-m1-reference-fatal-diagnostics.md)、[最新验证](log/2026-09-18-m1-reference-launcher-cleanup.md)。

- 2026-09-18 14:42 T306.6h 用户改选GPU7，随后明确“保留占位进程，暂不启动”。保留本人sleep.py PID2789351，未启动Isaac、未改设备绑定；后续先适配GPU7再8env→1024env。见[GPU7暂停决定](log/2026-09-18-m1-reference-gpu7-hold.md)。

- 2026-09-18 14:22 T306.6h：独立参考验证入口已提交f5842d4，150项CPU回归/spec/quality均通过；还未启动Isaac。新T306.6h.4：GPU4被其他用户liuxx占用21710MiB、100%利用率，需先协调资源，未终止对方任务。8-env/1024-env均未验收。见[实现证据](log/2026-09-18-m1-reference-runtime.md)、[资源阻碍](log/2026-09-18-m1-reference-gpu-resource-blocker.md)。

- T306.6h execution update: independentmetrics now77focused/112unionCPUtestsPASS, bothreviewsapproved;80-step×8envCPUparity matches reference clearance flags. Runtimeadapter inprogress; noIsaacsimulationyet. Originalbar sourceembedding15mm isnewT306.6h.3 physicalaudit, mustmeasureactualabovegroundheight before60mmclaims. See[metrics](log/2026-09-18-m1-reference-metrics.md).

- 2026-09-18 T306.6h IMPLEMENTING：用户已确认独立控制器规格。参考CPU基线88passed；新来源guard35passed且spec/quality审查通过；只读USD检查3layers/1MDL/0unresolved，17刚体/16关节/浮动根/4圆柱轮确认。新增入口尚在实施，未启动8-env仿真。新增全身子步接触诊断，避免四轮sensor的netforce被误当纯横杆力；8×1600三次全通过才准1024。见[预检证据](log/2026-09-18-m1-reference-preflight.md)。

- 2026-09-18 T306.6h：用户同意参考 M1 控制器“先复现小跨越、再适配大绕行”的方向，并指定先8env后1024env。[第一阶段详细设计](../docs/superpowers/specs/2026-09-18-m1-reference-controller-validation-design.md)已取消1-env仿真：8×32启动、三次8×1600严格通过后，才进行1024×32容量检查和1024×1600控制器验证。仅修改设计与记录，尚未启动仿真。参考accepted权重缺失，不冒充已学会越障；入口/资产问题仍待适配。现有AME、10000长训与旧监控均不变，profiling路线保持停止。见[参考调查及规模修订](log/2026-09-18-m1-reference-controller-design.md)。

- 2026-09-18 T306.6g：新轮式奖励fresh1024×120已单进程完整结束，exact0..119、complete+exit0，138checkpoint tensors/35TB tags finite。固定评测flat8/8、small/large0/8，均无碰撞/失败终止；机器人仍在障碍前停止。正式10000未启动。T306.6g.1a的profile采集路线三次实测未产出有效诊断，已停止；拟改显式诊断接口，待确认，监控暂停。见 [pilot](log/2026-09-18-m1-wheel-reward-1024-pilot.md)、[行为汇总](log/2026-09-18-m1-wheelreward-tail-audit.md)、[诊断限制](log/2026-09-18-m1-reward-hook-bootstrap-probe.md)。

- 2026-09-18 T306.6f CLOSED：逐事件记录证明72/4800膝部几何事件发生在自身障碍通过后，scanner读到2.5m间距的相邻环境障碍，而PhysX过滤跨环境碰撞。仅将probe间距改为8m（与已有评测一致），同配置8env×600步实测0.05m四轮通过8/8、前进3.10m、0reset、几何事件72→0、complete+exit0；本轮重新回归97 passed,1 skipped。未放宽膝部碰撞惩罚；source hull保守性不是这72事件的已证根因。见 [事件追踪和隔离对照](log/2026-09-18-m1-probe-neighbor-contamination-fix.md)。

- 历史记录（2026-09-17，非当前待确认状态）：semantic1轮接触修复后的fresh1024×120完整结束（exact0..119，exit0，138 tensors/35 tags finite）。修正版评测平地8/8、小跨越/大绕行0；失败终止漏洞已修。600步固定姿态物理对照：0.05m四轮完整通过8/8，0.10m为0/8，均无reset。此后轮式奖励已确认实施，最新结果见上。见 [当前状态](todo/T306-m1-ame-long-train-stability.md)、[训练对照](log/2026-09-17-m1-semantic1-wheel-120-training.md)、[评测修正](log/2026-09-17-m1-evaluation-terminal-failure.md)、[高度匹配探测](log/2026-09-17-m1-step-height-matched-probe.md)。

- 2026-09-17 T306 当前要求已改为 `amp`、GPU4、1024 env、单进程完成，不再使用自动重启监督器。真实 M1 浮动底座、腿位置/轮速度混合控制、平衡站姿与轮轴无限转动已接入。8-env 平地驱动对照：旧增益前进 0.0025m，新增益 1.6044m，均 300 步；新版本 AME 和 AME-AMP 各完成 2 次更新。1024 x 120 单进程验证已完成；10000 长训及越障/绕障行为尚未验收。见 [T306](todo/T306-m1-ame-long-train-stability.md)、[驱动对照](log/2026-09-17-m1-floating-drive-gate.md)、[1024 验证](log/2026-09-17-m1-floating-1024-stability.md)。

- 历史记录（2026-09-16，非当前任务状态）：当时存在服务器 Vulkan ICD 与默认 renderer multi-GPU 路径问题，并使用恢复监督器。该路线已被单进程验收要求取代，不得将历史model_1100或tmux会话名当作当前训练。详见 [T306 branch page](todo/T306-m1-ame-long-train-stability.md) 和 [历史修复日志](log/2026-09-16-m1-ame-long-train-vulkan-watchdog-fix.md)。

- 2026-09-11 T305 统一策略评测新增 SemLoco：复用默认 adapter，最新 `model_19999.pt` 通过真实 1024 env x 48 transitions smoke，得到 `27 valid_windows` 与 `5224.88 env-steps/s`，详见 [SemLoco integration smoke](log/2026-09-11-policy-benchmark-semloco-integration-smoke.md)。

- 2026-09-11 T305 统一策略评测新增 AME 与 AME-AMP：专用 adapter 与六类 launcher 已提交，两个最新最长 checkpoint 均通过真实 1024 env x 48 transitions smoke，分别得到 `27` 个 valid windows，详见 [integration smoke](log/2026-09-11-policy-benchmark-ame-integration-smoke.md)。

- 2026-09-03 T305 统一策略评测已实现并完成真实 AMP 验收：1024 env x 48 transitions，`5683.82 env-steps/s`、`6 episodes`、`27 valid_windows`，无 NaN/Inf/OOM/Traceback。四模型、三套 suite、固定 manifest、24/23 timing、valid-only MSE 和正式汇总入口均已落地，见 [T305 branch page](todo/T305-policy-benchmark.md)。
- 2026-09-06 T305 真实 `small_runway` 已验收：AMP 与修复后的 Distillation 均通过 1024 env x 48 steps；此前缺失源于 suite 从未启动，Distillation 无结果源于 wrapper 漏传 critic/context，详见 [debug log](log/2026-09-06-policy-benchmark-small-runway-distillation-debug.md)。

- 2026-08-31 最新 AMP 长跑 `2026-08-28_18-54-54/4161d7b` 已完成到 iteration `3499`，但行为在训练中后期崩溃：`Policy/mean_noise_std` 峰值 `13.66`，末尾仍为 `4.99`；`valid_bad_orientation` 末尾约 `0.963`；`AMP/value_loss` 峰值 `1.13e6` 实为基础 critic，真正 `AMP/amp_value_loss` 峰值约 `167.7`。根因跟踪转入“AMP PPO std/KL 控制与判别器饱和”开放节点，见 [长跑诊断](log/2026-08-31-parallelism-amp-long-run-diagnosis.md)。

- 2026-08-28 Parallelism AMP actor guidance now warms up after the existing AMP Critic/discriminator path: actor AMP weight is `0` through iteration `500`, ramps to `0.1` by `600`, and then stays fixed. The real `1024 env x 4 iteration` resume smoke and focused `24`-test suite pass without NaN/Inf/Traceback/OOM. See [warm-up verification](log/2026-08-28-parallelism-amp-warmup-real-smoke.md), [AMP smoke evidence](log/2026-08-27-parallelism-amp-batched-transition-and-1024-smoke.md), and the [Chinese HTML design](../docs/superpowers/specs/2026-08-27-parallelism-joint-amp-design-zh.html).

  Branch details: [T304 Parallelism AMP](todo/T304-parallelism-amp.md).

- 2026-07-27 Parallelism branch checkpoint: `extension/parallelism` now has a self-contained flat Go2 foot planner with 24-frame trot rollout, 50 candidates per foot, torch single-pass filters/scores, RL reference adapter, and `go2_foostep_planner.py --planner-backend parallelism` wiring. Focused verification is `14 passed`; real Isaac viewer smoke remains the next check. See [Parallelism planner implementation](log/2026-07-27-parallelism-flat-foot-planner-implementation.md).

- 2026-07-25 viewer CUDA Graph OOM fallback is local: the real H30 livestream command now catches graph capture OOM, disables graph for that manager, and continues eager RTI instead of exiting at `capture_end()`. Runtime regression is `12 passed`; viewer smoke reached fallback and continued. A later phase-6 `kkt=(nan,nan)` / `clearance=-inf` is separate and remains open. See [viewer OOM fallback](log/2026-07-25-joint-mpc-viewer-cuda-graph-oom-fallback.md).

- 2026-07-24 common-metric regression: small/cross explicitly verifies all applicable flat metrics, including map-backed stance grounding and forbidden semantics. See [common metric regression](log/2026-07-24-joint-mpc-cross-common-metric-regression.md). The preview liftoff geometry blocker remains open.

- 2026-07-24 metric/stance follow-up: the small gate already consumes every flat/common metric. A forced stance-z map projection was rejected because it collapsed publication/validity to `2.7%`; retain the numeric stance-ground gate and redesign published IK/anchor z ownership before changing nominal again. See [follow-up](log/2026-07-24-joint-mpc-cross-flat-metrics-stance-follow-up.md).

- 2026-07-24 Task 17 latest: controlled small passes the complete flat/common
  gate, including world-map stance grounding and semantics, but strict crossing
  is still `0` because no swing foot enters the obstacle footprint. The next
  correction must unify selector and published discrete sweep geometry. See
  [cross stance/common follow-up](log/2026-07-24-joint-mpc-cross-stance-common-and-sdf-follow-up.md).
- 2026-07-24 follow-up: stance gap/penetration has a direct numeric regression and joint-linear selector components are present; focused selector/nominal is `84 passed`, but controlled crossing remains red at refresh 59. A preview warm-path experiment was reverted after early publication collapse. See [follow-up](log/2026-07-24-joint-mpc-cross-joint-linear-selector-follow-up.md).

- 2026-07-24 Task 17 preview liftoff root cause: cross inherits the complete flat/stance-ground gate, and selector/nominal focused tests are `84 passed`, but controlled refresh 59 remains invalid because selector checks a continuous IK swing while publication checks joint-linear swept geometry. Edge 25 alone penetrates foot `13.92mm` and calf `9.92mm`; candidate/weight tuning is no longer the correct owner. See [preview liftoff contract](log/2026-07-24-joint-mpc-cross-preview-liftoff-contract.md).

- 2026-07-24 Task 17 cross common gate is wired and tested: controlled cuboid strict crossing plus collision and world-map stance/touchdown semantics are green, but the complete report remains red on joint step `0.3563rad`, publish/valid `0.5655`, and stop `0.4345`. A separate CUDA/CPU scan parity failure is also open. See [controlled result](log/2026-07-24-joint-mpc-cross-flat-metrics-controlled-result.md).

- 2026-07-23 final Task 16 flat closure: real same-refresh KKT is wired into acceptance, focused tests are `115 passed`, the full package is `284 passed`, and formal CUDA flat v13 passes `19/19` cells with primal/dual maxima `5.133e-5/9.014e-5`. Task 17 small-obstacle crossing is next; large/viewer/performance remain blocked. See [final flat closure](log/2026-07-23-joint-mpc-rti-final-flat-gate-closure.md).

- 2026-07-23 final Task 16 first flat diagnosis: future-swing/preview/swept issues and a severe CUDA SPD stride bug are fixed and guarded. Current-map B3 rolling validity is `[24,24,24]`, but the formal 19-cell flat gate remains `19/19` red on alpha-zero fallback, cold joint step, root/foot ordering, tracking, and several publish ratios. Small/large/viewer/performance remain blocked. See [final flat gate first diagnosis](log/2026-07-23-joint-mpc-rti-final-flat-gate-first-diagnosis.md).

- 2026-07-23 final Task 15: superseded seven-loss, Gaussian-map, control-rollout, adaptive-contact, duplicate solver, and old probe paths are deleted. The final import graph and full package pass (`247 passed`); Task 16 flat behavior is next. See [final legacy deletion](log/2026-07-23-joint-mpc-rti-final-legacy-deletion.md).

- 2026-07-23 final Task 14: the acceptance layer now uses 72 frozen P/A/M metrics and strict foot-event crossing; focused verification is `57 passed`. This closes schema correctness, not flat/small behavior. See [final actual-world metrics schema](log/2026-07-23-joint-mpc-rti-final-actual-world-metrics-schema.md).

- 2026-07-23 final Task 13: fixed same-refresh diagnostics, eight-stage profiler, and viewer overlays now share one production refresh. Diagnostics/pipeline/rolling/viewer regression is `61 passed`; actual visual behavior and performance are not claimed. See [final diagnostics/viewer/profiler](log/2026-07-23-joint-mpc-rti-final-diagnostics-viewer-profiler.md).

- 2026-07-23 final Task 10: the temporary sequential block solve is removed. New full-horizon constraints are folded into fixed-band augmented systems, then solved through 36D separator factors, H30->H32 neutral padding, five explicit combine levels, and boundary recovery. Dense parity and CUDA Graph pass, but B=40 is `122.67ms/refresh`; Task 19 performance remains red. See [final associative scan](log/2026-07-23-joint-mpc-rti-final-associative-scan.md).

- 2026-07-23 final perceptive-kinematic continuation: the new `LqProblem` production path no longer enters the eager dense QP. A fixed-shape batched block-pentadiagonal solve with two active-mask refinements matches the dense reference within `2e-5`; real CUDA Graph capture/replay, preview-tail copy-back, and the Task 1-12 focused union pass (`128 passed`). True five-level H30/32 associative recovery is still open before performance acceptance. See [final RTI pipeline checkpoint](log/2026-07-23-joint-mpc-rti-final-pipeline-cuda-checkpoint.md).

- The local pure-kinematic viewer CUDA Graph startup blocker is fixed without changing RTI formulas or weights. Graph-unsafe constants now use the cache, fixed general CUDA systems use the partial-pivot Triton solve with contiguous inputs, and alpha zero is an exact nominal copy under non-finite directions. CPU runtime/line-search is `26 passed`; real GPU scan compile plus graph capture/replay is `2 passed`. Task 14E behavior remains separate and red. See [CUDA Graph capture fix](log/2026-07-22-joint-mpc-rti-cuda-graph-capture-fix.md).

- Task 14E方案 A is implemented and solver-valid but behavior-red. Focused verification is `124 passed` plus contract/IK/gait/terrain `47 passed`; the real viewer closes all invalid cycles, validity `1.0`, root velocity `0.10739m/s`, joint step `0.34683rad`, stance XY slip `0.338mm` and clearance `+9.276um`. Preserving shifted foot z leaves stance gap `84.63mm`, airborne touchdown `0.020408`, and carry ratio `29.72`, so Task 14F/ranked/formal/Stage B remain blocked pending a new z/onset manifold decision. See [Task 14E implementation](log/2026-07-22-joint-mpc-rti-warm-x1-manifold-implementation.md).

- Task 14D published-root XY priority is implemented and solver-correct but behavior-rejected. The initial affine seed was built outside fixed boxes; a free-subspace seed closes the defect, with focused `93 passed`, contract/terrain `37 passed`, and viewer full/selected x1 root-XY violations `0/0`. Root velocity is green at `0.12535m/s`, but phases `13..23` all fail exact-FK publication, leaving validity `0.77551` and joint step `0.37823rad`. Ranked/formal/Stage B remain blocked pending a new architecture decision. See [published root XY priority](log/2026-07-22-joint-mpc-rti-published-root-xy-priority.md).

- Task 14C mixed published-kinematics KKT is implemented: four stance-XY rows plus two swing-Z floor rows, with one exact-FK `published_kinematics` filter. Focused union is `93 passed`. The real S4 sphere viewer makes clearance green at `+6.219um`; nominal/full/selected floor deficits are `+2.473mm/-5.271um/-5.294um`, and validity, joint, stance, crossing, collision, penetration, and cold-once/warm-only are green. Only root velocity remains red at `0.22393m/s > 0.2m/s`; ranked/formal remain blocked pending read-only layer diagnosis. See [mixed swing-floor viewer](log/2026-07-22-joint-mpc-rti-mixed-swing-floor-viewer.md).

- Task 14 root-layer diagnosis reproduces the viewer exactly and localizes the remaining failure to the constrained QP direction: overall nominal/full/selected root errors are `0.09045/0.23343/0.22393m/s`; warm-only selected is `0.19634m/s`, while the cold first edge is `1.54806m/s`. Full QP worsens nominal in `41/49` cycles and trust saturates only four times. Do not increase trust, alter the metric, or sweep scalars; a root/foot priority contract needs explicit approval before behavior changes. See [root-layer diagnosis](log/2026-07-22-joint-mpc-rti-root-tracking-layer-diagnosis.md).

- Task 14 now has an implemented affine published-x1 support KKT: six complete FK rows, nonzero anchor target, fixed-rank scan Schur correction, affine-feasible active-set seed, and exact-FK continuing-stance line filter. Focused regression is `63 passed`. The real viewer proves strong improvement in stance XY, but the grounded final variant remains red on validity `0.98`, root velocity `0.21931m/s`, and clearance `-3.296mm`; ranked/formal remain blocked and support-anchor variants stop here. See [affine support KKT](log/2026-07-22-joint-mpc-rti-affine-support-kkt.md).

- Task 14 exhausted and rejected trajectory-relative, fixed-world, and body-relative final-swing Step shaping. Compact one-env PhysX buffers unblocked the real viewer; all three candidates close joint continuity to about `0.321-0.323rad` but regress stance to about `1.295mm`, root velocity to about `0.221m/s`, and clearance to about `-2.05mm`. Production is restored to phase-11-only Step and focused regression is `82 passed`. The next move requires an explicit architecture decision; ranked/formal runs remain blocked. See [Step architecture closure](log/2026-07-22-joint-mpc-rti-step-architecture-closure.md).

- Task 14 accepted the current persistent-anchor Contact normalization but rejected every attempted touchdown-boundary shortcut. Moving Step from phase 11 to phase 12 and changing `tau` to `phase/12` passed focused tests yet regressed ranked small to `6/7` and worsened the real viewer phase `11->12` joint step from `0.41972` to `0.44678rad`, with `-3.83mm` swing clearance. Production semantics are restored; next design work is a continuous final-swing approach residual inside the existing Step family. Full `29,640` remains blocked. See [phase-12 rejection](log/2026-07-21-joint-mpc-rti-touchdown-phase12-rejected.md).

- Task 14 sharding now has real CLI write/merge evidence, and viewer small mode now uses an actual S4 sphere, real 0.01m scanner field, published x1, actual root/joint/foot, and shared JointMetrics. The 49-cycle event passes strict crossing and all collision/semantic/map/validity/lifecycle metrics, but real post-crossing stance is red (`5.120mm` slip, `5.225mm` anchor residual) despite only `1.924e-6m` actual/planned foot readback error. Full regression is `207 passed`; diagnose Contact/Terrain pressure before full formal or other viewer cases. See [CLI sharding and viewer blocker](log/2026-07-21-joint-mpc-rti-cli-sharding-real-viewer-small-blocker.md).

- Task 14 current production candidate is green on ranked small `7/7`, ranked flat `7/7`, late-phase formal representative cells `12/12`, and the full CPU package `205 passed`. The pure-yaw blocker was a per-node warm yaw wrap that created a false `2*pi` horizon edge; the small fixture also now recenters its local field while preserving a fixed world obstacle. Strong continuing Contact uses `contact_anchor_xy=400`, while future onset remains weak at `1.0`. Complete `29,640`-cell formal small acceptance and real viewer crossing remain open. See [yaw continuity and formal subset](log/2026-07-21-joint-mpc-rti-yaw-continuity-formal-subset.md).

- Task 13 flat behavior is green under the user-approved 19-command axis-isolated matrix: formal planner `19/19` and the real eight-case viewer smoke both pass. Small-obstacle Task 14 may start. CUDA Graph capture still has loss-scalar construction work and remains a Stage B performance item. See [flat axis-19 and viewer gate](log/2026-07-21-joint-mpc-rti-flat-axis19-viewer-gate.md).

- The approved lifecycle is now cold-once/warm-only per environment: cold may run only after creation or explicit reset; every later cycle must use warm start, including alpha-zero/no-improvement cycles. Pause Task 13 tuning until solver state uses an explicit `initialized` lifecycle, invalid candidates cannot overwrite the last finite cache, and lifecycle regressions pass. See [plan amendment](log/2026-07-21-joint-mpc-rti-cold-once-warm-only-plan-amendment.md).

- Task 13 pure-kinematic flat gate remains red after root-trust and cold-first-edge alignment. The current ranked CUDA candidate is resource-safe and moving tracking, stance, lead, jump, joint validity, and zero-command behavior are green; only phase-11 swing/touchdown clearance remains at `-21/-29mm`. Do not start small or Stage B. See [diagnostic](log/2026-07-21-joint-mpc-rti-root-trust-cold-first-edge-and-flat-tuning.md).

- The active-KKT blocker is closed by a fixed-two-refinement feasible blocking solver; dense/scan final difference is `9.64e-8`, and the current focused QP/nominal/loss/RTI union is `32 passed`. The approved grouped-convolution/propagated-height/Scharr/bilinear semantic path is already differentiable with respect to trajectory XY. Ranked tracing now proves an early-command objective conflict: a swing-boundary kink moves through internal edges `11..0` into published `x1`; `command_early=0.1` fixes jump but breaks foot lead/leak, while `smooth_first=0.2` does not fix jump. Stop scalar sweeping and write a minimal design amendment before changing frozen loss semantics. See [solver/phase diagnostic](log/2026-07-21-joint-mpc-rti-feasible-kkt-and-phase12-warm-kink.md).

- Pure-kinematic Tasks 1-11 are committed; Task 12's shared metrics/report/watchdog foundation is green (`20 passed` focused; `11 passed` selector/watchdog regression). Flat execution is the next active front. See [Task 12 verification](log/2026-07-20-joint-mpc-rti-kinematic-task12-runner-watchdog-verification.md).
- Task 13 flat trace wiring now exists; a CPU ranked run was explicitly stopped after no progress for roughly 45 seconds, so no flat acceptance claim is made. Use monitored CUDA for the formal gate. See [CPU watchdog stop](log/2026-07-20-joint-mpc-rti-kinematic-flat-ranked-cpu-watchdog-stop.md).
- The first monitored CUDA ranked flat run is resource-safe but behavior-failing: stance slip, zero-command drift, alpha-zero fallback, and root/swing tracking remain open. Small testing is not authorized yet. See [CUDA flat gate](log/2026-07-20-joint-mpc-rti-kinematic-flat-ranked-cuda.md).
- Nominal phase-anchor and body-frame metric corrections reduced the main stance slip from `0.134m` to below `1mm`; zero drift, swing event/clearance, and backward joint/line-search failures remain. Small testing is still not authorized. See [nominal anchor fix](log/2026-07-20-joint-mpc-rti-kinematic-nominal-anchor-fix.md).
- Latest Task 13 diagnosis confirms the grouped-convolution semantic field is already differentiable (`5` focused metric tests pass and terrain gradient coverage exists). The mixed command `(1.0,0.5,1.0)` instead reports invalid nominal reachability; its first swing foot jumps about `0.134m` in the published x1 while root moves about `0.022m`, so lead metrics are currently masked/inconclusive. See [foot-lead validity diagnostic](log/2026-07-20-joint-mpc-rti-kinematic-foot-lead-valid-diagnostic.md).
- Task 13 now separates cold nominal reachability from the accepted RTI result: a finite non-nominal candidate with solver status zero can be valid, while alpha-zero fallback still requires a valid nominal. The flat fixture also uses the configured `0.34m` root clearance. Focused regression is `50 passed`; ranked CUDA behavior remains open. See [validity/fixture fix](log/2026-07-21-joint-mpc-rti-kinematic-validity-and-fixture-fix.md).
- The post-fix ranked CUDA run completes safely and exposes the next real blocker: forward stance remains stable but has `21.4%` alpha-zero plus immediate root onset; backward reaches zero joint margin, an 8-frame nominal fallback run, and `50.9mm` stance slip. Zero-command drift is `1.24e-4m`. See [post-validity flat diagnostic](log/2026-07-21-joint-mpc-rti-kinematic-flat-after-validity.md).
- Backward rolling behavior is batch-size sensitive: B=1 and ranked B=3 first choose different alpha at frame 10 from tiny preceding numeric differences, then their warm starts diverge into different validity/joint outcomes. Candidate-loss/filter/scan parity at that frame must be resolved before ranked tuning can represent formal B275. See [rolling batch sensitivity](log/2026-07-21-joint-mpc-rti-rolling-batch-sensitivity.md).
- A principled line-search status bug is fixed by TDD: when all five candidates fail the existing finite/joint-position/joint-velocity filters, alpha-zero still returns the nominal state but now receives nonzero solver status and cannot be published valid. RED `2 failed`; scoped GREEN `14 passed`; no candidate/filter/loss/recovery was added. See [infeasible fallback fix](log/2026-07-21-joint-mpc-rti-infeasible-fallback-status-fix.md).
- The shared gate now requires `trajectory_valid_ratio=1.0`; previously forward `13/25` and backward `15/25` valid traces could mask failed frames from other metrics. TDD is RED `1 failed` then GREEN `10 passed`; this is a metrics-only correction inherited by flat and small. See [validity metric](log/2026-07-21-joint-mpc-rti-trajectory-validity-metric.md).
- Two nominal phase errors are fixed by TDD: exact phase-zero lift now starts at measured foot, and future liftoff reuses the preceding stance/touchdown placement. This removes `0.12m/0.356m` reference jumps without changing nominal architecture; nominal suite is `11 passed`. See [liftoff phase fixes](log/2026-07-21-joint-mpc-rti-liftoff-reference-phase-fixes.md).
- Stronger `contact=200` is rejected because it regresses both signed ranked cells to `22/25`. A proved warm-terminal defect is TDD-fixed: terminal joints hold old accepted `q30` instead of copying unconstrained old `q7`; nominal is `12 passed`, focused regression `63 passed`, and all three ranked cells are now `25/25` valid. Forward joint margin remains only `5e-5rad`, so joint tuning still precedes stance/lead work. See [terminal hold fix](log/2026-07-21-joint-mpc-rti-contact200-terminal-hold-fix.md).
- Approved command/swing early-phase subweights remain inside the existing loss families. The former add-only active-KKT failure is closed by feasible blocking with the same two refinements; do not reopen that stale blocker. Current behavior work starts at the phase-12 shifted-warm discontinuity and separate zero-command/swing-endpoint residuals. See [solver/phase diagnostic](log/2026-07-21-joint-mpc-rti-feasible-kkt-and-phase12-warm-kink.md).
- The phase-12 touchdown-conflict hypothesis is now rejected: phase-11/12 targets are identical and nominal FK/stance anchors agree. The 48-step failure instead isolates to forward command geometry: pure `vx=1` reaches the calf bound while pure `vy` and pure yaw retain margin; step scale/weight, joint trust, and posture probes did not close the gate. Validity ratios now use exact boolean counts. See [touchdown/vx diagnostic](log/2026-07-21-joint-mpc-rti-touchdown-vx-geometry-diagnostic.md).
- Real rolling evidence refined that conclusion: future shifted-warm FK and regenerated touchdown could differ by `0.29m`, so Step and Contact were conflicting despite static cold/warm parity. Future stance anchors now use touchdown references, and Step now targets phase-11 `tau=1`; focused regression is `43 passed`. The best 48-step candidate has positive signed joint margins and passing stance/lead/validity, but joint-step, signed clearance, and root tracking remain open. See [touchdown/vx diagnostic](log/2026-07-21-joint-mpc-rti-touchdown-vx-geometry-diagnostic.md).
- Current focus: **T302v joint MPC RTI GPU**.
- The approved 2026-07-20 replacement design now has a 16-task implementation plan. Execution order is contract -> fixed gait/IK/nominal/field -> seven losses/direct-Z QP/H30 scan/five-alpha search -> new RTI and old-code deletion -> monitored metrics -> flat -> small -> joint rerun -> Stage B -> final same-candidate rerun. See [plan log](log/2026-07-20-joint-mpc-rti-kinematic-flat-small-plan.md).
- The 2026-07-20 replacement design is approved: pure-kinematic H30, gait `24/12+12`, vectorized nominal, seven frozen losses, joint-bound/trust KKT, H30/32 associative scan, five-alpha loss-only line search, flat then small-obstacle behavior gates, and unchanged Stage B `1024 x H30 x 1000 <=5s`. The old 15+15 adaptive-contact/recovery architecture and its implementation plan are no longer the production direction. See [design log](log/2026-07-20-joint-mpc-rti-kinematic-flat-small-design.md).
- Active branch page: [T302v](todo/T302v-joint-mpc-rti-gpu.md).
- Active implementation plan: [Joint MPC RTI small-obstacle crossing plan](../docs/superpowers/plans/2026-07-16-joint-mpc-rti-small-obstacle-crossing-implementation-plan.md).
- Background reward implementation plan: [T302r Go2 geometry clearance reward plan](todo/T302r-go2-geometry-clearance-reward-plan.md).
- Active code surface:
  - [Go2Pvcnn/extension/batch_mpc_planner/participation.py](../Go2Pvcnn/extension/batch_mpc_planner/participation.py)
  - [Go2Pvcnn/extension/batch_mpc_planner/manager.py](../Go2Pvcnn/extension/batch_mpc_planner/manager.py)
  - [Go2Pvcnn/extension/reference/cache.py](../Go2Pvcnn/extension/reference/cache.py)
  - [Go2Pvcnn/extension/mdp/rewards_reference.py](../Go2Pvcnn/extension/mdp/rewards_reference.py)
  - [Go2Pvcnn/extension/mdp/semantic_body_part_clearance.py](../Go2Pvcnn/extension/mdp/semantic_body_part_clearance.py)
  - [Go2Pvcnn/extension/mdp/semantic_contact_rewards.py](../Go2Pvcnn/extension/mdp/semantic_contact_rewards.py)
  - [Go2Pvcnn/extension/semantic_curriculum.py](../Go2Pvcnn/extension/semantic_curriculum.py)
  - [Go2Pvcnn/go2_pvcnn/sensor/semantic_contacter/](../Go2Pvcnn/go2_pvcnn/sensor/semantic_contacter/)
  - [Go2Pvcnn/go2_pvcnn/tasks/teacher_elevation_trajectory_mpc_semantic_env_cfg.py](../Go2Pvcnn/go2_pvcnn/tasks/teacher_elevation_trajectory_mpc_semantic_env_cfg.py)
  - [Go2Pvcnn/scripts/play.py](../Go2Pvcnn/scripts/play.py)
  - [Go2Pvcnn/scripts/mpc_policy_eval.py](../Go2Pvcnn/scripts/mpc_policy_eval.py)
  - [Go2Pvcnn/extension/viz/go2_foostep_planner.py](../Go2Pvcnn/extension/viz/go2_foostep_planner.py)
  - [Go2Pvcnn/extension/batch_mpc_planner/semantic_policy.py](../Go2Pvcnn/extension/batch_mpc_planner/semantic_policy.py)
  - [Go2Pvcnn/extension/batch_mpc_planner/parametric.py](../Go2Pvcnn/extension/batch_mpc_planner/parametric.py)
  - [Go2Pvcnn/extension/batch_mpc_planner/planner.py](../Go2Pvcnn/extension/batch_mpc_planner/planner.py)
  - [Go2Pvcnn/extension/batch_mpc_planner/losses/terrain_clearance.py](../Go2Pvcnn/extension/batch_mpc_planner/losses/terrain_clearance.py)
  - [Go2Pvcnn/tests/test_batch_mpc_parametric.py](../Go2Pvcnn/tests/test_batch_mpc_parametric.py)
  - [Go2Pvcnn/tests/test_batch_mpc_backend.py](../Go2Pvcnn/tests/test_batch_mpc_backend.py)
  - [Go2Pvcnn/tests/test_viewer_reset.py](../Go2Pvcnn/tests/test_viewer_reset.py)
  - [Go2Pvcnn/tests/test_mpc_policy_eval_script_static.py](../Go2Pvcnn/tests/test_mpc_policy_eval_script_static.py)
- Current contract:
  - T302v.8 original implementation plan is amended in place: execute fixed-H30 Tasks 8A-9A and close the complete Stage A behavior/safety/JointMetrics gate first; only then execute H30 Stage B `1024 x 1000 <=5s`; completion still requires a fresh same-candidate Stage A+Stage B rerun. See [log/2026-07-18-joint-mpc-h30-implementation-plan-amendment.md](log/2026-07-18-joint-mpc-h30-implementation-plan-amendment.md).
  - T302v.8 Chinese HTML design fixes the production planner to H30 with 15-frame stance/swing, a full 275-combination signed `(vx,vy,yaw)` command matrix, per-leg touchdown confirmation and up to 10 extension frames, full foot/knee/calf/thigh/base safe-anchor checks, continuous root lateral/RPY assistance with double clamps, four parallel line-search alphas, and a complete JointMetrics extension including root roll/pitch deviation. Stage A remains open; Stage B remains paused and is now formally `1024 x H30 x 1000 <=5s`; Stage C still requires a fresh same-candidate rerun. See [log/2026-07-18-joint-mpc-h30-adaptive-contact-root-assist-design.md](log/2026-07-18-joint-mpc-h30-adaptive-contact-root-assist-design.md).
  - T302v.7 implementation plan is amended and active: 14 TDD tasks cover Stage A coupled gait/JointMetrics/H16-H50 exploration, Stage B frozen-`H_selected` MPX-referenced performance, and Stage C same-candidate joint rerun. Inline execution is authorized until both fresh gates pass. See [log/2026-07-17-joint-mpc-root-joint-coupled-gait-plan.md](log/2026-07-17-joint-mpc-root-joint-coupled-gait-plan.md).
  - T302v.7 Chinese HTML design is approved and amended: complete root-joint FK/GGN coupling, stance equality, command-conditioned touchdown, foot-leading-root startup, arrowhead/Schur solve, and one JointMetrics contract across every scenario. Stage A explores H16-H50 fixed full-cycle horizons together with the original solver/loss directions and selects `H_selected`; Stage B freezes it and uses MPX-referenced temporal/state GPU parallelism to keep the unchanged `1024 x H_selected x 1000 <=5s` gate; Stage C reruns both gates on one final candidate. See [log/2026-07-17-joint-mpc-root-joint-coupled-gait-design.md](log/2026-07-17-joint-mpc-root-joint-coupled-gait-design.md).
  - T302v.7 gait-quality diagnosis is open: eight flat rolling commands confirm root-carried feet. Mean signed consecutive-stance displacement is `1.040x` the root step, only `4.02%` of stance samples stay within `1mm/frame`, and swing motion relative to root contributes only `7.0%` of root progress. Performance work is deferred while the support-driven gait contract is designed. See [log/2026-07-17-joint-mpc-root-foot-propulsion-order-quantification.md](log/2026-07-17-joint-mpc-root-foot-propulsion-order-quantification.md).
  - T302v functional acceptance is green: stop `65/65`, strict cross `100%`, zero per-part collision/penetration, joint `119`, legacy `213`, and real viewer pass. The earlier single-cell `4768ms` performance result was rejected after a realistic multi-cell audit; `11x11` small plus `41x41` large signed exact fields remain above the `5s` full-refresh gate. See [log/2026-07-17-joint-mpc-rti-full-design-revalidation.md](log/2026-07-17-joint-mpc-rti-full-design-revalidation.md).
  - T302u MPC semantic avoidance memory fix is implemented locally: existing `parametric_semantic_avoidance` now builds a soft proximity field and queries root/foot/touchdown risk with differentiable `grid_sample` instead of materializing dense `[B,H,4,22500,2]` pairwise tensors. No MPC loss key or config loss term was added. `env_isaacsim` verification includes focused `225 passed`, pycompile/diff check exit `0`, and a real `TeacherElevationTrajectoryMpcSemanticEnvCfg` probe with `1024` RL envs and `1024` MPC envs for `30` steps: `max_sampled_plan_count_seen=1024`, CUDA max allocated `7.43GB`, reserved `9.27GB`, no OOM. See [log/2026-06-16-mpc-proximity-field-semantic-avoidance.md](log/2026-06-16-mpc-proximity-field-semantic-avoidance.md).
  - T302t is implemented locally: flat-small training now uses `GoalAnchoredVelocityCommand` for `base_velocity`, preserving body-frame `[vx_body, vy_body, yaw_rate]` command semantics for old checkpoint compatibility while anchoring world movement direction to reset-time distant goals. Focused tests `6 passed`, viewer regression `33 passed`, pycompile and diff check exit `0`, and real 8-env `env_isaacsim` train smoke exits `0` with Command Manager `GoalAnchoredVelocityCommand`, policy_state `(45,)`, action `12`, and saved cfg parameters `goal_distance=10.0`, `vx_abs_range=(0.6,1.0)`, `vy_abs_range=(0.6,1.0)`, `yaw_range=(-0.8,0.8)`. See [log/2026-06-13-2323-t302t-goal-anchored-flat-small-command.md](log/2026-06-13-2323-t302t-goal-anchored-flat-small-command.md).
  - T302q is implemented locally in [todo/T302q-flat-small-avoidance-reward-plan.md](todo/T302q-flat-small-avoidance-reward-plan.md): added `teacher_elevation_trajectory_mpc_semantic_flat_small_avoidance`, kept observation/action shape checkpoint-compatible, added `semantic_body_part_clearance_reward` using current IsaacLab foot/calf/thigh body poses against the current IsaacLab scanner semantic/elevation maps through the same MPC terrain query helper, and changed the existing row-based semantic curriculum to episode-level true small-contact success.
  - T302q focused verification and real smoke pass after adding the new experiment to the trajectory-manager allowlist: focused `31 passed`, pycompile exit `0`, fresh 16-env/1-iteration IsaacLab train smoke exit `0`, and resume from `2026-06-04_18-16-07/model_14000.pt` exit `0`.
  - T302q flat-small 1024-env slowdown root cause is fixed locally in `SemanticGridRayCaster`: the hot path was repeated late semantic mesh refresh polling when optional large-obstacle geometry is intentionally absent, not `raycast_mesh` or semantic id lookup. After the fix, scanner `refresh` dropped from `1684-1877ms/chunk` to `0.01-0.02ms`, steady `observation.compute` is `21-22ms`, and normal resumed collection is back in the `3.768-6.857s` range after startup. See [log/2026-06-10-2317-t302q-semantic-raycaster-refresh-fix.md](log/2026-06-10-2317-t302q-semantic-raycaster-refresh-fix.md).
  - T302q flat-small curriculum flat-mask bookkeeping is fixed locally: when the terrain generator exposes one flat sub-terrain but IsaacLab `terrain_types` span multiple column ids, all columns are now treated as flat. Focused `21 passed`, pycompile exit `0`, and real 64-env IsaacLab probe reports `plane_mask_count=64` / `plane_env_count=64`. See [log/2026-06-11-1428-t302q-flat-small-plane-mask-fix.md](log/2026-06-11-1428-t302q-flat-small-plane-mask-fix.md).
  - T302r Go2 geometry clearance reward is implemented locally in [todo/T302r-go2-geometry-clearance-reward-plan.md](todo/T302r-go2-geometry-clearance-reward-plan.md): point-only clearance is upgraded into foot sphere, calf/thigh capsule, and base footprint fixed-shape GPU scanner-map queries; local focused tests pass and a 16-env real IsaacLab smoke exits `0`. Radius/margin probe shows radius alone is insufficient (`0.50m` hit small cells but `positive_deficit=0` with original margins); signal-first params now use `0.50m` query radius and enlarged margins (`foot/base=0.20m`, `calf/thigh=0.40m`) and produced nonzero reward in `1/64` envs. See [log/2026-06-11-1810-t302r-clearance-radius-margin-probe.md](log/2026-06-11-1810-t302r-clearance-radius-margin-probe.md).
  - T302q flat-small velocity curriculum is disabled only for `TeacherElevationTrajectoryMpcSemanticFlatSmallAvoidanceEnvCfg`: `lin_vel_cmd_levels=None`, base cfg still has the velocity curriculum, and real 8-env smoke shows Curriculum Manager has only `terrain_levels`.
  - Latest flat-small TensorBoard readout for `2026-06-11_18-31-19` shows signal-first clearance is now technically nonzero (`484/825`, last-20 mean `-2.355e-07`) but too small to drive behavior, while curriculum remains closed (`semantic_gate_pass=0`, `flat_move_up_count=0`, `mean_terrain_level -> 0`). Do not continue this exact run for a long time before curriculum metric/gate redesign. See [log/2026-06-11-1955-t302q-flat-small-1831-tensorboard-readout.md](log/2026-06-11-1955-t302q-flat-small-1831-tensorboard-readout.md).
  - T302q/T302r env-level collision curriculum redesign is written as Chinese HTML at [../docs/superpowers/specs/2026-06-11-flat-small-env-level-collision-curriculum-design.html](../docs/superpowers/specs/2026-06-11-flat-small-env-level-collision-curriculum-design.html): each env decides upgrade/downgrade at episode end, global semantic gate is removed from flat move-up, curriculum TensorBoard keeps only `mean_terrain_level`, and clearance reward gets an explicit `clearance_scale` recommendation. See [log/2026-06-11-2156-flat-small-env-level-collision-curriculum-html-design.md](log/2026-06-11-2156-flat-small-env-level-collision-curriculum-html-design.md).
  - T302s is implemented locally: flat-small curriculum now uses env-level episode-end `move_up`/`move_down`, removes active global semantic gate parameters and noisy curriculum return metrics, keeps only `mean_terrain_level`, and wires `clearance_scale=1000.0`. Focused tests `184 passed, 1 warning`, pycompile exit `0`, diff check exit `0`, and real 8-env `env_isaacsim` smoke exit `0`. See [log/2026-06-11-2211-t302s-env-level-collision-curriculum-implementation.md](log/2026-06-11-2211-t302s-env-level-collision-curriculum-implementation.md).
  - T302s TensorBoard readout for `2026-06-11_22-15-56` shows the curriculum cleanup and clearance scale are active, but terrain level falls to zero because flat-small training still uses tiny command ranges (`lin_vel_x/y=(-0.1,0.1)`) after disabling velocity curriculum. With terrain size `8m`, the move-up distance threshold is `4m`, so low-speed episodes rarely satisfy the upgrade condition. See [log/2026-06-12-1039-t302s-flat-small-2215-tensorboard-readout.md](log/2026-06-12-1039-t302s-flat-small-2215-tensorboard-readout.md).
  - T302s fixed the flat-small command range mismatch locally: training cfg now uses `lin_vel_x=(0.6,1.0)`, `lin_vel_y=(-0.2,0.2)`, `ang_vel_z=(-0.3,0.3)` while velocity curriculum remains disabled. Focused tests `180 passed, 1 warning`, pycompile exit `0`, and real 8-env smoke exit `0`; saved cfg confirms the new ranges. See [log/2026-06-12-1054-t302s-flat-small-fixed-command-ranges.md](log/2026-06-12-1054-t302s-flat-small-fixed-command-ranges.md).
  - T302s TensorBoard readout for `2026-06-12_10-53-23` shows fixed command ranges opened terrain curriculum: `mean_terrain_level` max `7.475`, last-100 mean `5.97`, episode length last-100 `991.64`. Semantic clearance/contact are now dense at high levels, so continue briefly and watch whether contact trends down. See [log/2026-06-12-1355-t302s-flat-small-1053-tensorboard-readout.md](log/2026-06-12-1355-t302s-flat-small-1053-tensorboard-readout.md).
  - Later T302s readout at step `22868` still supports brief continuation: `mean_terrain_level` last-100 `5.805`, contact last-100 `-0.000684`, clearance last-100 `-0.002979`, episode length last-100 `980.84`, reward last-100 `26.12`. Next decision around `model_23500-24000`; stop and retune if episode length drops below about `950` or contact stops improving. See [log/2026-06-12-1548-t302s-flat-small-1053-tensorboard-readout.md](log/2026-06-12-1548-t302s-flat-small-1053-tensorboard-readout.md).
  - T302s readout at step `23389` reaches `model_23300`: terrain stays open and stability recovers (`episode_length` last-100 `991.84`, reward last-100 `28.15`), but semantic contact/clearance are noisy rather than cleanly improving (`contact` last-100 `-0.000858`, `clearance` last-100 `-0.003496`). Continue only to about `model_24000`, then checkpoint-eval or retune. See [log/2026-06-12-1642-t302s-flat-small-1053-tensorboard-readout.md](log/2026-06-12-1642-t302s-flat-small-1053-tensorboard-readout.md).
  - First-layer eval for `model_23600.pt` gives mixed evidence: strict flat-small training scene short sample has `0/8` small-collision envs over `200` steps, but existing dense small-collision eval has `8/16` collided envs over `300` steps, mostly feet/calves. No true path-obstacle foot-over metric exists yet, so reliable overpass is not proven. See [log/2026-06-12-1722-t302s-model23600-first-layer-eval.md](log/2026-06-12-1722-t302s-model23600-first-layer-eval.md).
  - 1000-step crossing probe for `model_23600.pt` on the flat-small training scene used 16 envs and a fixed forward command: only `1/16` envs produced a path-obstacle opportunity, root crossed that obstacle, true small contact stayed `0`, but foot-over success was `0` and overpass success was `0`. Opportunity coverage is too low for a stable rate, but enough to reject a success claim. See [log/2026-06-12-1740-t302s-model23600-crossing-1000step-probe.md](log/2026-06-12-1740-t302s-model23600-crossing-1000step-probe.md).
  - Formal controlled crossing eval for `model_23600.pt` now has sufficient opportunities and rejects the overpass claim: `15/16` envs saw a path-small obstacle, `14` root-crossed, `foot_over_count=0`, true small contact hit `11/16`, and overpass success was `0/15`. Continuing this exact line without retuning is unlikely to solve the behavior. See [log/2026-06-12-1815-t302s-model23600-controlled-crossing-eval.md](log/2026-06-12-1815-t302s-model23600-controlled-crossing-eval.md).
  - Flat-small cfg is now retuned with an explicit `semantic_foot_over_clearance` reward, stronger small-contact penalty, and smaller low-row center safety holes to create more path teaching opportunities. Focused `18 passed`, pycompile exit `0`, and real 8-env smoke exit `0`; next check is whether a short warm-start makes foot-over reward nonzero and improves controlled crossing `foot_over_count`. See [log/2026-06-12-1833-flat-small-foot-over-training-signal.md](log/2026-06-12-1833-flat-small-foot-over-training-signal.md).
  - Latest controlled crossing eval for `2026-06-12_19-05-27/model_28900.pt` still fails the core behavior despite longer training and the explicit foot-over reward: `15/16` opportunities, `14` root crossed, `foot_over_count=0`, real small contact `7/16`, and overpass success `0/15`. Contact is lower than `model_23600.pt`, but the policy still does not lift over small obstacles. See [log/2026-06-13-1505-t302s-model28900-controlled-crossing-eval.md](log/2026-06-13-1505-t302s-model28900-controlled-crossing-eval.md).
  - Run `2026-06-13_11-20-40` after increasing `semantic_foot_over_clearance` scale confirms magnitude is larger but event frequency remains sparse: nonzero `9/2167`, max `0.1018`, last-100 `0`, while contact last-100 is `-0.00210`. See [log/2026-06-13-1510-t302s-flat-small-1120-tensorboard-readout.md](log/2026-06-13-1510-t302s-flat-small-1120-tensorboard-readout.md).
  - Training livestream visualization is fixed locally for the user’s one-env command: [../Go2Pvcnn/scripts/train.py](../Go2Pvcnn/scripts/train.py) preserves requested `--livestream` before `AppLauncher` mutation and installs an env0 follow camera only when `rank==0`, `num_envs==1`, and livestream is `1/2`. Static `2 passed`, pycompile exit `0`, and real `env_isaacsim` smoke exit `0`. See [log/2026-06-13-1651-train-single-env-livestream-follow-camera.md](log/2026-06-13-1651-train-single-env-livestream-follow-camera.md).
  - Play keyboard visualization is implemented locally and documented in [human-12](human/human-12-batched-planner-train-viewer-commands.md): [../Go2Pvcnn/scripts/play.py](../Go2Pvcnn/scripts/play.py) adds `--keyboard-control`, terminal-thread hold-to-move `W/S/A/D/Q/E`, `+/-` speed stepping, and `--terrain-row/--terrain-col` env0 sub-terrain selection; flat-small PLAY disables training curriculum because contact sensors are absent, and both PLAY cfgs now disable timeout termination so visualization does not auto-refresh on episode timeout. The `pynput` route is removed; livestream control now reads from the SSH terminal when stdin is a TTY. Full viewer reset `33 passed`, pycompile exit `0`, and real play smoke exit `0`. See [log/2026-06-13-1839-play-terminal-keyboard-backend.md](log/2026-06-13-1839-play-terminal-keyboard-backend.md) and [log/2026-06-13-2022-play-disable-timeout-refresh.md](log/2026-06-13-2022-play-disable-timeout-refresh.md).
  - Flat-small static semantic course column generation is fixed locally: `terrain_name_for_col()` now repeats the only terrain name across all generated terrain columns, so `TeacherElevationTrajectoryMpcSemanticFlatSmallAvoidanceEnvCfg` no longer spawns small objects only in column 0. Focused tests pass and a real 4-env train cfg probe reports `row00_col_count=20`, `row09_col_count=20`, `row00_first_last=[8,8]`, `row09_first_last=[80,80]`, `total_small=8000`. See [log/2026-06-13-2207-flat-small-semantic-course-column-fix.md](log/2026-06-13-2207-flat-small-semantic-course-column-fix.md).
  - T302q constraints: do not modify MPC planner loss/reference/command shaping, do not use SemLoco foothold search, do not duplicate MPC FK in the reward, do not create another curriculum route, and use `semantic_contact_small.data.force_matrix_w` as the curriculum collision source.
  - T302p plan is created in [todo/T302p-mpc-command-frame-alignment-plan.md](todo/T302p-mpc-command-frame-alignment-plan.md): external commands remain root-yaw/body-frame `[vx_body, vy_body, yaw_rate]`; MPC world geometry must rotate command XY by current root yaw; viewer must stop pre-rotating before MPC; eval must record command-source equality and flat all-direction direction metrics.
  - T302p implementation is in the local working tree and focused verification passed: `command_frame_axes()` rotates body command XY by root yaw; MPC world-geometry heading paths in planner/semantic/terrain-clearance helpers use root-yaw world axes; viewer no longer pre-rotates before MPC; eval records command-source equality and planned direction diagnostics. Focused suite `184 passed, 1 warning`, pycompile exit `0`, diff check exit `0`, and a GPU0/env_isaacsim 5-step fixed-forward smoke exited `0`.
  - T302p real acceptance continuation ran and failed behavior gates: eight-direction tracking all exited `0` and command-source error stayed `0.0`, but root direction failed `forward`, `left`, and `right`; moving-leg direction failed all eight commands. Low-small GPU3 regression exited `0` but failed hard metrics: `max_fk_semantic_collision_count=21`, `max_fk_semantic_collision_rate=0.0175`, and `max planned_vs_fk_foot_error_crossing_leg_max_m=0.13923m`.
  - T302p low-small regression is now fixed locally without adding a new loss: existing `ik_fk_residual.weight` and `kinematics.weight/joint_limit_margin_rad` are wired into the sampled path, and existing FK collision aggregation now keeps sparse collisions salient. GPU0/env_isaacsim default `parametric_v1` low-small regression passed with `max_fk_semantic_collision_count=0` and max crossing FK error `0.04201m`.
  - T302p direction-loss wiring continuation fixed flat-left root direction while preserving low-small compatibility: existing `progress.weight/min_progress_m` and existing `swing_direction_loss()` are now wired into the sampled path, tracking eval synchronizes zero semantic obstacles to the terrain cfg, flat-left final root lateral ratio is `0.0200`, and low-small GPU0 remains `max_fk_semantic_collision_count=0`. T302p remains active because the strict per-leg whole-cache endpoint metric still fails for two middle legs; current evidence points to metric/gait-phase mismatch rather than command-frame mismatch.
  - T302p hard constraint after latest user override: do not add new losses or optimize metrics with new loss terms; fixing existing loss/weight coordinate or wiring issues is allowed. Do not add hard projection or postprocess snapping.
  - T302m cleanup is implemented locally: production train/play/register/factory/viewer are narrowed to `teacher_elevation_trajectory_mpc_semantic + mpc`; old `batched_planner`, `batched_together_planner`, old teacher cfgs, old script entrypoints, and production debug variants are deleted from the working tree.
  - T302m MPC tuning entry is unified locally: `TeacherElevationTrajectoryMpcSemanticEnvCfg` now tunes planner runtime/diagnostics/participation through `mpc_planner_cfg: MpcPlannerCfg`; production task cfg no longer exposes duplicated top-level MPC aliases.
  - T302m MPC participation config is now blacklist-only: `include_terrain_cols`, `include_terrain_names`, and `include_terrain_rows` were removed; use `exclude_pairs` to remove envs from MPC reference participation.
  - T302m local/static verification passed: cleanup guards `3 passed`, viewer tests `16 passed`, current focused suite `43 passed`, backend suite `128 passed`, production pycompile pass, and production old-route scan has no matches.
  - T302m real IsaacLab acceptance passed on card1 after fixing train/play local `rsl_rl` imports, the RSL-RL wrapper observation contract, and the active PPO config: contact drop probe pass, 1024-env 1-iteration train smoke pass, 1024/64/25-step performance `epoch_seconds=5.8828s`.
  - T302l design approved in [../docs/superpowers/specs/2026-05-30-mpc-rl-participation-and-runtime-design.html](../docs/superpowers/specs/2026-05-30-mpc-rl-participation-and-runtime-design.html).
  - T302l implementation plan lives in [todo/T302l-mpc-rl-participation-and-reward-plan.md](todo/T302l-mpc-rl-participation-and-reward-plan.md).
  - T302l PLAY/VIEWER split is verified locally and in `env_isaacsim`: `TeacherElevationTrajectoryMpcSemanticEnvCfg_PLAY` is no-MPC for `scripts/play.py`; `TeacherElevationTrajectoryMpcSemanticEnvCfg_VIEWER` preserves MPC viewer behavior; `model_14000.pt` headless play ran 5 steps with no planner attach.
  - MPC RL runtime must align `reference_trajectory_horizon = reference_replan_interval_steps = 25`.
  - Only selected envs participate in MPC reference reward; selection filters by terrain/difficulty and excludes only AND-matching terrain+difficulty pairs.
  - `reference_foot_pos_reward()` must compare IsaacLab and MPC feet in world frame.
  - RL semantic collision reward must use IsaacLab real contact, not semantic height-map collision approximation.
  - Current T302l semantic contact route uses 2 custom global semantic sensors, `semantic_contact_small` and `semantic_contact_large`, each covering all selected robot bodies and all `row_*/col_*/slot_*` semantic objects.
  - Final semantic contact acceptance on card1 passed with `num_envs=1024`, `force_matrix_w` shapes `[1024, 13, 640, 3]` and `[1024, 13, 100, 3]`, and `epoch_seconds=5.6489s` for 1024 env / 64 MPC env / 25 steps.
  - Robot-drop semantic contact probe on card1 passed: small and large obstacle contacts are detectable with no NaN/Inf and no empty-env cross-talk; small-obstacle contact is much sparser than large-obstacle contact in the controlled drop setup.
  - Design approved in [../docs/superpowers/specs/2026-05-28-parametric-low-small-loss-redesign.html](../docs/superpowers/specs/2026-05-28-parametric-low-small-loss-redesign.html).
  - Implementation plan lives in [todo/T302k-low-small-loss-redesign-plan.md](todo/T302k-low-small-loss-redesign-plan.md).
  - Task 1 restored the nominal extraction contract locally: `semantic_policy.py` builds `ParametricTrajectoryNominal`, `planner.py` builds nominal before optimization, and decode consumes `nominal + variables`.
  - Task 2 added optional `is_plane_terrain` metadata through scanner terrain construction, subset, planner normalization, and MPC manager IsaacLab terrain type inference.
  - Task 3 added GPU low-small component circle approximation in `semantic_geometry.py`.
  - Task 4 replaced sampled `parametric_low_small_crossing` with `parametric_touchdown_keepout`.
  - Task 5 added sampled `parametric_swing_foot_clearance`.
  - Task 6 added FK realized `parametric_fk_body_leg_collision` and it now participates in the sampled Adam loss path.
  - Task 7 added `parametric_trajectory_fk_consistency` and it now participates in the sampled Adam loss path.
  - Task 8 added sampled `parametric_plane_root_z_target` gated by `is_plane_terrain`.
  - Task 9 added plane-only low-small FK semantic collision probe metrics and JSONL GPU/run metadata. The diagnostic now runs after optimization, uses rolling segment terrain snapshots, and counts FK semantic collision only on crossing-triggered legs.
  - Full matrix on GPU0 passed hard acceptance for covered crossing rows: `20` cycle rows, `12` covered rows, `0` FK semantic collisions, max crossing FK error `0.0634m`; four rows exceed preferred `0.05m` but stay within accepted `0.08m`.
  - New low-small direction: no hard projection, no touchdown snapping, no hard foot separation; debug by tuning confirmed loss weights/parameters only.
- Old dense residual MPC (`nominal.py`, `optimizer.py`, `variables.py`, `losses/registry.py`) is retired. Do not reopen V9/V10/V11/V12 scalar-loss branches unless explicitly requested.
- T302o design is approved enough for implementation planning: [../docs/superpowers/specs/2026-06-05-mpc-policy-eval-design.html](../docs/superpowers/specs/2026-06-05-mpc-policy-eval-design.html). It adds one Python entry under `Go2Pvcnn/scripts/`, not a shell script, and keeps `scripts/play.py` no-MPC behavior unchanged.
  - T302o Task 4 tracking runtime metrics are implemented and real-smoke verified: per-step `metrics.jsonl`, per-round `rounds.jsonl`, and top-level `summary.json` include tracking aggregates; reference feet use `_trajectory_manager.current_reference()["foot_pos_w"]` with `_trajectory_reference_cache` + `current_frame_ids()` fallback; card0/env_isaacsim tracking smoke exit `0`, 3 valid steps, `reference_valid_ratio=1.0`.
  - T302o implementation is smoke-verified on card0/env_isaacsim: local/static regression `16 passed`, pycompile exit `0`, tracking smoke `20` valid steps with `reference_valid_ratio=1.0`, small_collision smoke uses env-count denominator with `total_env_rounds=4`, and livestream startup reached `Streaming server started`.
  - T302o livestream follow-up fixed the marker semantics and follow-camera gating: eval now visualizes full MPC foot trajectories per leg from `_trajectory_reference_cache.foot_pos_w`; a reproduced real livestream run showed the previous follow-camera branch produced `0` debug rows, then the fix snapshots `livestream_enabled` before `AppLauncher(args)` and updates env-one camera every step; card0/env_isaacsim post-fix debug produced `10` follow-camera rows with active camera `/OmniverseKit_Persp` matching requested pose.
  - T302o foot-trajectory lag is reproduced but not fixed: headless shift probes show actual feet match earlier MPC cache frames better than `current_frame_ids()`; wide probe had best cache frame `0` in `28/51` warmed samples and frame `2` in `14/51`, suggesting policy/reference tracking lag rather than a simple marker one-frame delay.
  - T302o timebase probe shows current eval is not async MPC-vs-policy execution: `refresh_from_env()` is called during post-step reward computation, then `mpc_policy_eval.py` metrics/markers read the same cache/phase after `wrapped_env.step()` returns. The remaining timing detail is a synchronous post-step phase-advance convention: non-replan refresh entry uses the previous phase, refresh exit/after-step uses the advanced phase. See [log/2026-06-06-1616-t302o-foot-trajectory-timebase-probe.md](log/2026-06-06-1616-t302o-foot-trajectory-timebase-probe.md).
  - T302o flat-forward lateral bias is reproduced as a command-frame mismatch: on flat terrain with semantic map all zero and command shaping disabled, robot yaw `16deg` plus unrotated nominal forward `[1,0]` produced about `9.4cm` body-frame side drift; manually yaw-rotating the command reduced side drift to about `4.4mm`. See [log/2026-06-06-1633-t302o-flat-forward-mpc-left-bias-reproduction.md](log/2026-06-06-1633-t302o-flat-forward-mpc-left-bias-reproduction.md).
  - T302o remaining follow-up: `--terrain-rows/--terrain-cols` currently resize terrain grid rather than selecting original terrain row/col IDs, so true multi-terrain comparison semantics need a separate fix before reporting final terrain-sweep results.

## Status Legend

- `active`: current execution front.
- `verify`: implemented/evidenced, keep as regression guard.
- `context`: useful background, not current work.
- `done`: closed history.
- `closed`: unfinished historical route closed by the current T302k direction.

## Active Fronts

- [T306 M1 AME long-train stability](todo/T306-m1-ame-long-train-stability.md): amp/GPU7 encounter接入；7b6ddd7已构造实际完整局部保守包络，原query负例保持不变。下一步live lease/provider与同一步body-pose投影，再coordinator；保留15GB占位，无训练进程，不使用重启supervisor。新G1/1024/G2及policy跨绕/10000仍未验收。

- [T305 统一策略评测 Benchmark](todo/T305-policy-benchmark.md): 六类模型 harness 和真实接线 smoke 已完成；下一步运行六个正式 checkpoint 的三套 suite 并生成论文统计。

- [T303 Parallelism flat foot planner](todo/T303-parallelism-flat-foot-planner.md): verify state. Self-contained flat/highmap batched planner, RL adapter, and viewer backend route are implemented on branch `Parallelism`; real Isaac viewer smoke is the next follow-up.

- [T302v joint MPC RTI GPU](todo/T302v-joint-mpc-rti-gpu.md): final Task 16 flat is closed (`19/19`, real KKT, full package `284 passed`). Task 17 small-obstacle crossing is the active behavior gate; Tasks 18-19 large/viewer/RL-batch/performance remain blocked behind it.

| Front | State | Why It Matters Now | Next Step |
| --- | --- | --- | --- |
| T306 | continuous implementation | 3d97e9b/main1929full；实际136collider局部保守包络回放全覆盖，原rawfailed40不变。 | live owner/17body poses/保守投影→coordinator→新G1/1024/G2；AME/policy跨绕/10000仍未验收。 |
| T305 | verification | AMP/Distillation/PPO/Teacher/AME/AME-AMP need a reproducible paired simulation benchmark for complex mixed terrain, large-obstacle avoidance, small-obstacle crossing, and valid planner tracking MSE. | six-model harness and AME variants smoke verified; formal paper sweep remains open. |
| T302q | active | Flat-small run `2026-06-11_18-31-19` has stable locomotion and signal-first clearance is nonzero, but curriculum never opens and the semantic signal is tiny. | Redesign curriculum metrics/gate aggregation before another long run; optionally eval `model_20700.pt` only as behavior sanity. |
| T302s | active | Fixed command ranges opened terrain curriculum, and controlled crossing eval now has sufficient path-obstacle opportunities. `model_28900.pt` still has `foot_over_count=0` and overpass success `0/15`, so the current training signal is not teaching clean low-small overpass. | Redesign training to provide staged/dense path-aligned crossing signal instead of continuing this run blindly. |
| T302r | active | Geometry clearance is implemented and confirmed nonzero in training logs, but its magnitude is tiny (`~1e-7` mean), so it is not yet a strong learning signal. | Decide whether to rescale clearance reward and/or add part-level diagnostics after curriculum metric cleanup. |
| T302p | active | Command-frame implementation is local and guarded, command-source equality is real-verified, low-small FK semantic hard gates pass, and flat-left root direction is now fixed after existing progress/swing-direction wiring. Strict per-leg whole-cache endpoint direction still fails and appears to be a metric/gait-phase boundary issue. | Decide/implement the per-leg direction metric contract before further planner tuning; keep low-small regression as guard. |
| T302n | verify | Semantic obstacle curriculum is now row-gated: static row-based obstacle generation, flat-only semantic gate for terrain row upgrades, and no runtime semantic-course rebuild. | Keep as regression guard; rerun row probe if changing terrain curriculum, semantic counts, or contact sensor wiring. |
| T302o | verify | Python-only evaluation route loads policy checkpoints with MPC reference/cache, reports policy-vs-MPC tracking metrics, measures flat small-obstacle collision by collided envs per round, and supports livestream MPC foot markers plus env-one follow camera; foot-trajectory mismatch is reproduced and timebase-probed as sync post-step refresh plus phase-advance convention, not async MPC execution. | Keep as regression guard; analyze policy/reference gait mismatch and fix terrain row/col selection semantics before claiming true multi-terrain comparison results. |
| T302m | verify | Current working tree has been cleaned to the single semantic MPC route; MPC tuning is unified under `mpc_planner_cfg`; participation filtering is blacklist-only; local/static tests pass and card1 IsaacLab acceptance passes. | Keep as regression guard; run train smoke only if changing task cfg/runtime wiring again. |
| T302l | verify | MPC participation/contact route and PLAY/VIEWER split are verified; PLAY no longer attaches MPC, viewer uses VIEWER cfg, and low-small hard metrics remain clean. | Keep as regression guard; rerun PLAY smoke only if changing play wrapper, policy observation shape, or task cfg. |
| T302k | active | Current parametric MPC path; low-small loss redesign implementation is verified on covered rows, with only parameter tuning left unless user approves a new loss. | Inspect loss breakdown and tune confirmed parameters only if continuing soft FK-error reduction. |

## Root Map

| Root | Status | Stage | Branch | Current | Refs |
| --- | --- | --- | --- | --- | --- |
| T306 | active | M1 AME long training and obstacle behavior | `m1_rl` + isolated encounter | 3d97e9b局部保守geometry/main1929CPU；live provider/新G1/1024/G2及全目标未验收 | [branch](todo/T306-m1-ame-long-train-stability.md); [latest](log/2026-09-19-m1-conservative-geometry.md) |
| T305 | verify | unified policy benchmark | `parallelism-amp` | six-model harness and AME/AME-AMP 1024-env smoke passed; formal sweep pending | design [2026-09-03](../docs/superpowers/specs/2026-09-03-policy-benchmark-design-zh.html); latest [2026-09-11](log/2026-09-11-policy-benchmark-ame-integration-smoke.md) |
| T303 | verify | Parallelism flat foot planner | `Parallelism` | Self-contained 24-frame trot foot planner, 50 candidates per foot, torch single-pass filter/score, RL adapter, and viewer backend route; real viewer smoke remains open. | design [2026-07-27](../docs/superpowers/specs/2026-07-27-parallelism-flat-foot-planner-design.html); latest log [2026-07-27](log/2026-07-27-parallelism-flat-foot-planner-implementation.md) |
| T302q | active | flat small-obstacle avoidance RL reward | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | Local implementation complete; focused regression, pycompile, fresh IsaacLab train smoke, and old-checkpoint resume smoke pass; small-collision eval smoke remains open. | design [2026-06-10](../docs/superpowers/specs/2026-06-10-flat-small-obstacle-avoidance-reward-design.html); latest log [2026-06-10 20:35](log/2026-06-10-2035-t302q-flat-small-local-implementation-and-smoke.md) |
| T302r | active | Go2 geometry clearance reward | [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | Local implementation, smoke, and radius/margin probe pass; signal-first params can produce nonzero reward, but TensorBoard sanity is still open. | design [2026-06-11](../docs/superpowers/specs/2026-06-11-go2-body-geometry-clearance-reward-design.html); latest log [2026-06-11 18:10](log/2026-06-11-1810-t302r-clearance-radius-margin-probe.md) |
| T302p | active | MPC command-frame alignment | [T302p](todo/T302p-mpc-command-frame-alignment-plan.md) | Implementation local; command-source equality verified; low-small hard gates pass; flat-left root direction fixed (`root lateral 0.0200`), but strict per-leg whole-cache endpoint metric remains open. | design [2026-06-06](../docs/superpowers/specs/2026-06-06-mpc-command-frame-alignment-design.html); latest log [2026-06-07 12:11](log/2026-06-07-1211-t302p-direction-loss-wiring-and-metric-boundary.md) |
| T302n | verify | semantic obstacle curriculum | [T302n](todo/T302n-semantic-obstacle-curriculum-plan.md) | Row-based static semantic objects and flat-only terrain row gate implemented; local focused tests and card1 IsaacLab row probe pass | design [2026-06-03](../docs/superpowers/specs/2026-06-03-semantic-obstacle-curriculum-design.html) |
| T302o | verify | MPC policy evaluation script | [T302o](todo/T302o-mpc-policy-eval-plan.md) | `mpc_policy_eval.py` implemented and smoke-verified: tracking compares policy feet to MPC reference feet, small_collision counts collided envs per round on dense-small flat terrain, and livestream overlays MPC foot markers. | design [2026-06-05](../docs/superpowers/specs/2026-06-05-mpc-policy-eval-design.html); verified `996ce1f` |
| T302m | verify | teacher elevation MPC semantic cleanup | [T302m](todo/T302m-teacher-elevation-mpc-semantic-cleanup-plan.md) | Single-route cleanup implemented locally; card1 IsaacLab acceptance and 1024/64/25 performance pass | design [2026-05-31](../docs/superpowers/specs/2026-05-31-teacher-elevation-mpc-semantic-cleanup-design.html) |
| T302l | verify | MPC RL participation and reward integration | [T302l](todo/T302l-mpc-rl-participation-and-reward-plan.md) | Selector/world-foot/global contact work and PLAY/VIEWER split verified; prior card1 1024 quantity/perf acceptance retained | design [2026-05-30](../docs/superpowers/specs/2026-05-30-mpc-rl-participation-and-runtime-design.html) |
| T302k | active | parametric MPC trajectory contract | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | Low-small loss redesign and plane-only FK semantic collision testing | design commit `97c5b60` |
| T302h | closed | semantic obstacle jitter/crossing evidence | [T302h](todo/T302h-semantic-obstacle-jitter-reproduction.md) | Closed as implementation route; retained as reproduction/evidence for T302k | rolling25 low-small production evidence |
| T302i | closed | viewer realized-foot mismatch evidence | [T302i](todo/T302i-viewer-realized-foot-mismatch.md) | Closed as loss-sweep route; IK/FK mismatch evidence retained for T302k reachability | clamp trace and reachable probes |
| T302j | closed | touchdown endpoint consistency evidence | [T302j](todo/T302j-touchdown-endpoint-consistency.md) | Closed as dense/default-MPC endpoint route; endpoint lessons folded into T302k | structured touchdown logs |
| T302g | context | MPC semantic RL config | [T302g](todo/T302g-mpc-semantic-rl-training-config.md) | Deferred until parametric planner behavior stabilizes | global-sync sampled MPC evidence |
| T302 | context | MPC collision/semantic baseline | [T302](todo/T302-mpc-body-leg-height-field-collision-safety.md) | Baseline metric history only | strict JSONL history |
| T300 | context | old dense MPC backend | [T300](todo/T300-unified-dense-mpc-backend.md) | Superseded by T302k | dense path retired |
| T100 | context | batched together planner | [T100](todo/T100-batched-together-planner-gpu-migration.md) | Historical non-MPC planner path | keep for rollback/context |
| T301 | context | viewer reset/step mode | [T301](todo/T301-viewer-r-key-grounded-reset.md) | Viewer controls background | use only for viewer regressions |
| T200 | done | semantic static course | [T200](todo/T200-semantic-static-course-viewer.md) | Course/runtime support complete enough for current planner work | feature `130c635` |
| T002 | done | compact-todo workflow | [T002](todo/T002-compact-todo-interactive-memory-and-test-grooming.md) | Skill implemented; this session used it for cleanup | compact session logs |
| T000 | done | notes workflow | [T000](todo/T000-notes-workflow.md) | memory system bootstrapped | feature `7cf6c11` |

## Open Leaves

- T306.6h.6a.1a（1024扩容）: Task1/2/3、run17startup、baseline18公共门槛完成；candidate19在prepare247保护失败，native1/wrapper2/verifier3，不重跑/推广。[run19](log/2026-09-18-m1-scale-candidate19.md)。
  - .1 初次跨越几何：18env missing ordered事件（FAR高度6/RAR横向17并集）；源函数CPU回放验证FAR的world目标偏低，RAR需计入root/yaw而非只改腿横移。质量仅关联，动力学隔离因果仍缺证据；跨后同步不能补救。[几何复算](log/2026-09-18-m1-scale-first-cross-geometry.md)。
  - .2 phase完成后重入：用户已批准具体规格实施，A1几何基础f8ce0af已829full/双审查PASS，继续.2c完整provider/状态机/交接接入；不能只reset解锁或将rootmask套legs。子项.2a方向/轮侧/多物体接触/真实路线与G2物理再遇障，不能由CPU或G1替代。[实施记录](log/2026-09-19-m1-encounter-geometry-implementation.md)。
    - .2c.1 已完成：live owner及同一步17body-pose向外投影9dc0dc7/8e60686，真实8×32/native0、4352colliderstep独立回放；原rawfailed40保留，不改clearance。[投影证据](log/2026-09-19-m1-pose-projection.md)。
    - .2c.2 当前：registry394ea67/core d27e26c均双审、2317全回归；.2c.2a CPU核心CLOSED，.2c.2b仍OPEN为reference/sync动作交接和新证据接线，随后才新G1/G2验收。[当前实现](log/2026-09-20-m1-encounter-registry-coordinator.md)。
  - 22:46资源风险缓解但未查明来源：本次完成CPU fixture完整归档/data、旧路径保留链接，仅移除校验重复副本，root约14.29GiB。run18同PID1408步；未来新产物用/data，baseline/源码不搬，保留所有原验收/容量门槛。[存储核验](log/2026-09-18-m1-scale-fixture-storage.md)。
- T306.6g.1a（暂停，阻塞T306.6g.1）: profile采集路线停止，显式奖励诊断方案未实施；当前优先T306.6h独立参考验证。正式10000未开始，T306.6f串扰已关闭。见[T306](todo/T306-m1-ame-long-train-stability.md)。

- T306.1 host Vulkan repair: 历史host ICD曾返回 `VK_ERROR_INCOMPATIBLE_DRIVER`；该历史故障不能直接当作当前launcher故障。主机级驱动仍需独立管理员验收；本轮仅复核测试/日志，未改系统驱动。

- T305.3 formal paper evaluation: run paired conditions for all six weights and generate confidence intervals and paired statistics; [branch page](todo/T305-policy-benchmark.md), [latest smoke](log/2026-09-11-policy-benchmark-ame-integration-smoke.md).

- T302v Task 17 small-obstacle gate: start with one controlled cuboid at `vx=0.2m/s`, require safe behind touchdown, convex region, nominal and whole-leg sweep safety, strict crossing, and zero world-map collision before expanding phases/shapes/speeds; [branch page](todo/T302v-joint-mpc-rti-gpu.md), [flat prerequisite](log/2026-07-23-joint-mpc-rti-final-flat-gate-closure.md).
- T302v.7 support-driven gait quality: current root command integration carries both stance and swing feet; define stance-slip, swing touchdown-lead, and root/support phase metrics before behavior changes; [branch page](todo/T302v-joint-mpc-rti-gpu.md), [quantification](log/2026-07-17-joint-mpc-root-foot-propulsion-order-quantification.md).
- T302v realistic signed performance: single-cell acceptance was rejected; `11x11` small plus `41x41` large footprints remain above `5s` despite compiled MPC and multiple exact-EDT experiments. Requires a new batched exact EDT architecture or explicit contract change; [branch page](todo/T302v-joint-mpc-rti-gpu.md), [revalidation](log/2026-07-17-joint-mpc-rti-full-design-revalidation.md).
- T302v real-1024 boundary: separately measure Isaac physics and RayCaster ray generation after the planner-side performance contract is resolved; [branch page](todo/T302v-joint-mpc-rti-gpu.md).

| Leaf | Parent | Status | Priority | Why Active | Next Read |
| --- | --- | --- | --- | --- | --- |
| T302w.11 | T302w | verify | P0 | Root forward correction is still smooth and zero-preserving, but now limits the unchanged `0.25m` nominal endpoint to approximately `0.05-0.50m`; CPU parametric tests pass, runtime behavior unverified. | [bound-change log](log/2026-07-15-mpc-root-forward-bound-005-050.md) |
| T302w.10 | T302w | verify | P0 | Identically-zero `parametric_reachability` computation and breakdown key removed; CPU contract explicitly asserts absence; separate FK consistency loss remains. | [removal log](log/2026-07-15-remove-zero-parametric-reachability-loss.md) |
| T302w.8 | T302w | open | P0 | Row8/col12 at optimize step 16 reproduces `0.244m` planned-foot/analytic-FK error, `0.205m` root-Z step, joint saturation, and heightfield penetration while Isaac playback readback stays micron-close; current-runtime 16-vs-24/25 A/B is next. | [opt16 reproduction log](log/2026-07-15-mpc-row8-col12-opt16-position-repro.md) |
| T302w.6 | T302w | verify | P0 | Deterministic S4 cylinder/cone `optimize_steps=0..25` sweep identifies step `16` as the smallest conservative candidate; broader placements/seeds and multi-replan playback remain open before any default change. | [optimizer-step sweep log](log/2026-07-15-mpc-low-small-optimize-steps-sweep.md) |
| T302q.1 | T302q | verify | P0 | New flat-small avoidance RL config, body-part clearance reward, and episode-level curriculum gate are implemented and smoke-verified; keep as regression guard. | [implementation log](log/2026-06-10-2035-t302q-flat-small-local-implementation-and-smoke.md) |
| T302q.2 | T302q | active | P0 | Final behavior evidence is still open: run small-collision eval smoke against a useful flat-small run/checkpoint and inspect episode-level collision summaries. | [T302q Task 9](todo/T302q-flat-small-avoidance-reward-plan.md#task-9-small-collision-evaluation-and-notes-alignment) |
| T302r.1 | T302r | verify | P0 | Geometry clearance implementation is local: RED tests caught missing helpers, focused `158 passed`, curriculum subset `34 passed`, pycompile exit `0`, and 16-env real smoke exit `0`. | [implementation log](log/2026-06-11-1551-t302r-go2-geometry-clearance-implementation.md) |
| T302r.2 | T302r | active | P0 | Signal-first params produced real nonzero clearance reward in a 64-env probe, but short TensorBoard sanity is still needed to confirm training logs become nonzero. | [latest radius/margin log](log/2026-06-11-1810-t302r-clearance-radius-margin-probe.md) |
| T302p.1 | T302p | verify | P0 | Code path alignment implemented locally: body/root-yaw command is preserved at viewer/eval/MPC boundary, MPC world geometry rotates by root yaw, and command-source diagnostics are recorded. | [implementation log](log/2026-06-06-1858-t302p-command-frame-implementation.md) |
| T302p.2 | T302p | active | P0 | Full acceptance is still open: low-small FK semantic hard gates pass and flat-left root direction is fixed, but the strict per-leg whole-cache endpoint direction metric still fails for two middle legs; decide whether the metric should be swing-window based before tuning more. | [latest log](log/2026-06-07-1211-t302p-direction-loss-wiring-and-metric-boundary.md) |
| T302n.1 | T302n | verify | P0 | Row-gated semantic curriculum implemented: 10-row `plane_counts`/`non_plane_counts`, flat-only semantic gate, no runtime rebuild; focused `24 passed` and IsaacLab row probe pass. | [T302n plan](todo/T302n-semantic-obstacle-curriculum-plan.md) |
| T302o.1 | T302o | verify | P0 | Eval CLI, cfg contracts, tracking metrics, small-collision env-rate metric, livestream command sync, and MPC foot markers are implemented and smoke-verified; foot-trajectory timebase is diagnosed as sync post-step refresh with phase advance, while gait mismatch and terrain row/col selection remain follow-ups. | [T302o plan](todo/T302o-mpc-policy-eval-plan.md#task-7-real-isaaclab-smoke-tests-and-notes) |
| T302m.1 | T302m | verify | P0 | Route cleanup, local regression, card1 contact/drop, 1024-env train smoke, and 1024/64/25-step perf pass. | [T302m cleanup plan](todo/T302m-teacher-elevation-mpc-semantic-cleanup-plan.md) |
| T302l.1 | T302l | verify | P0 | Two global semantic contact sensors are implemented; exact-path body resolution fixes 1024-env `gym.make` stall; card1 quantity and 25-step performance pass. | [T302l implementation plan](todo/T302l-mpc-rl-participation-and-reward-plan.md) |
| T302l.2 | T302l | verify | P0 | PLAY/VIEWER split verified: PLAY no planner attach with `model_14000.pt`, VIEWER cfg static contract covered, low-small regression FK semantic collisions `0`. | [Task 20](todo/T302l-mpc-rl-participation-and-reward-plan.md#task-20-play--viewer-cfg-split) |
| T302k.12 | T302k | active | P0 | Replan touchdown/current-foot and touchdown IK/FK mismatch remain the main trajectory/reachability issue. | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md#open-children) |
| T302k.18 | T302k | verify | P0 | Low-small loss redesign is implemented and hard acceptance passes on covered full-matrix rows; remaining work is parameter tuning only unless user approves new loss. | [T302k low-small loss redesign plan](todo/T302k-low-small-loss-redesign-plan.md) |
| T302k.17 | T302k | verify | P0 | Nominal extraction Task 1 is implemented, committed, and covered by local regression tests. | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md#open-children) |

## Branch Pages

- [T306-m1-ame-long-train-stability.md](todo/T306-m1-ame-long-train-stability.md)

- [T305-policy-benchmark.md](todo/T305-policy-benchmark.md)

- [T302v joint MPC RTI GPU](todo/T302v-joint-mpc-rti-gpu.md)

- [todo/README.md](todo/README.md)
- [T302s-env-level-collision-curriculum-plan.md](todo/T302s-env-level-collision-curriculum-plan.md)
- [T302q-flat-small-avoidance-reward-plan.md](todo/T302q-flat-small-avoidance-reward-plan.md)
- [T302r-go2-geometry-clearance-reward-plan.md](todo/T302r-go2-geometry-clearance-reward-plan.md)
- [T302p-mpc-command-frame-alignment-plan.md](todo/T302p-mpc-command-frame-alignment-plan.md)
- [T302n-semantic-obstacle-curriculum-plan.md](todo/T302n-semantic-obstacle-curriculum-plan.md)
- [T302o-mpc-policy-eval-plan.md](todo/T302o-mpc-policy-eval-plan.md)
- [T302m-teacher-elevation-mpc-semantic-cleanup-plan.md](todo/T302m-teacher-elevation-mpc-semantic-cleanup-plan.md)
- [T302l-mpc-rl-participation-and-reward-plan.md](todo/T302l-mpc-rl-participation-and-reward-plan.md)
- [T302k-parametric-mpc-trajectory-contract.md](todo/T302k-parametric-mpc-trajectory-contract.md)
- [T302k-low-small-loss-redesign-plan.md](todo/T302k-low-small-loss-redesign-plan.md)
- [T302h-semantic-obstacle-jitter-reproduction.md](todo/T302h-semantic-obstacle-jitter-reproduction.md)
- [T302i-viewer-realized-foot-mismatch.md](todo/T302i-viewer-realized-foot-mismatch.md)
- [T302j-touchdown-endpoint-consistency.md](todo/T302j-touchdown-endpoint-consistency.md)
- [T302g-mpc-semantic-rl-training-config.md](todo/T302g-mpc-semantic-rl-training-config.md)
- [T302-mpc-body-leg-height-field-collision-safety.md](todo/T302-mpc-body-leg-height-field-collision-safety.md)
- [T300-unified-dense-mpc-backend.md](todo/T300-unified-dense-mpc-backend.md)
- [T100-batched-together-planner-gpu-migration.md](todo/T100-batched-together-planner-gpu-migration.md)
- [T301-viewer-r-key-grounded-reset.md](todo/T301-viewer-r-key-grounded-reset.md)
- [T200-semantic-static-course-viewer.md](todo/T200-semantic-static-course-viewer.md)

## Recent Logs

| 2026-09-19 | M1 conservative local geometry | 3d97e9b；focused222/main1929CPU；实际136collider回放 | 全3664vertices/32nativeCylinder覆盖、原rawfailed40保持；live provider待接 | [T306.6h.6a.1a.2c.1](todo/T306-m1-ame-long-train-stability.md) | [verification](log/2026-09-19-m1-conservative-geometry.md) |

| 2026-09-18 | M1 post-cross sync design | 源码/reset边界审计＋run12离线gate | 接管action245..253；仅设计，无新仿真/实现 | [T306.6h.6a](todo/T306-m1-ame-long-train-stability.md) | [audit](log/2026-09-18-m1-post-cross-sync-design-audit.md) |

| 2026-09-18 | M1 wheel equalizer A/B | 225CPUtests; oneamp/GPU7 8×1600 | native0/completedtrue，strict1/8；gain0候选拒绝，无推广/重启 | [T306.6h.6a](todo/T306-m1-ame-long-train-stability.md) | [verification](log/2026-09-18-m1-wheel-equalizer-ab.md) |

| 2026-09-16 | M1 AME long-train Vulkan/watchdog fix | root cause + launcher + supervisor + real resume smoke | focused `29 passed`; launcher `3` updates exit `0`; supervisor `4` updates reaches `model_1037.pt` and exits `0`; host Vulkan ICD remains broken | [T306](todo/T306-m1-ame-long-train-stability.md) | [verification](log/2026-09-16-m1-ame-long-train-vulkan-watchdog-fix.md) |

| 2026-07-22 | Joint MPC RTI published root XY priority | free-subspace seed closes fixed-bound violations; representative behavior still red | focused `93 passed`; contract/terrain `37 passed`; root XY violations `0/0`; root `0.12535m/s`; validity `0.77551`; joint `0.37823rad` | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [verification](log/2026-07-22-joint-mpc-rti-published-root-xy-priority.md) |

| 2026-07-22 | Joint MPC RTI Step approach midpoint | CPU contract green; representative viewer blocked by PhysX CUDA OOM; ranked/formal remain blocked | `3` approach tests and `25` trajectory-loss tests pass; no viewer behavior claim | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [verification](log/2026-07-22-joint-mpc-rti-step-approach-midpoint.md) |

| 2026-07-21 | Joint MPC RTI native-shape parity + viewer stance diagnosis | five-shape parity; small/flat `7/7`; grounding offset fixed; worst FL stance slip `3.173mm`; joint+viewer `248 passed` | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [verification](log/2026-07-21-joint-mpc-rti-native-shape-parity-ranked-retune.md) |
| 2026-07-21 | Joint MPC RTI CLI sharding + real viewer / fixture blocker | exact two-shard merge passes; `0.01m` ranked is `5/7`; formal native-shape parity open; actual sphere crossing collision-safe but stance slip is `5.120mm` | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [verification](log/2026-07-21-joint-mpc-rti-cli-sharding-real-viewer-small-blocker.md) |
| 2026-07-21 | Joint MPC RTI yaw continuity + formal subset | ranked small/flat `7/7`; late-phase subset `12/12`; CPU `205 passed`; complete formal/viewer open | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [verification](log/2026-07-21-joint-mpc-rti-yaw-continuity-formal-subset.md) |
| 2026-07-17 | Joint MPC root-joint coupled gait implementation plan | amended to 14 TDD tasks: Stage A selects `H_selected`; Stage B uses MPX-referenced parallelism for unchanged `<=5s`; Stage C final joint rerun | [T302v.7](todo/T302v-joint-mpc-rti-gpu.md) | [plan](log/2026-07-17-joint-mpc-root-joint-coupled-gait-plan.md) |
| 2026-07-17 | Joint MPC root-joint coupled gait design | amended: Stage A explores H16-H50 plus existing solver/loss directions; Stage B freezes `H_selected` and uses MPX-style parallelism for unchanged `<=5s/1000` | [T302v.7](todo/T302v-joint-mpc-rti-gpu.md) | [design](log/2026-07-17-joint-mpc-root-joint-coupled-gait-design.md) |
| 2026-07-17 08:57 | Joint MPC root/foot propulsion order quantification | reproduced: stance displacement/root `1.040x`, stance `<=1mm` only `4.02%`, swing-relative/root `7.0%`; no planner change | [T302v.7](todo/T302v-joint-mpc-rti-gpu.md) | [root/foot quantification](log/2026-07-17-joint-mpc-root-foot-propulsion-order-quantification.md) |
| 2026-07-17 00:45 | Joint MPC RTI full design revalidation | functional pass; realistic multi-cell exact signed performance remains above `5s`; single-cell pass rejected | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [full revalidation](log/2026-07-17-joint-mpc-rti-full-design-revalidation.md) |
| 2026-07-16 20:19 | Joint MPC RTI stop-on-small floating reproduction | reproduced: semantic foot-over conflicts with support recovery after command stops; no code change | [T302v.5](todo/T302v-joint-mpc-rti-gpu.md) | [floating reproduction](log/2026-07-16-joint-mpc-rti-stop-on-small-floating-reproduction.md) |
| 2026-07-16 | Joint MPC RTI small-obstacle crossing implementation plan | six tasks / 25 TDD steps; inline execution authorized and active | [T302v.4](todo/T302v-joint-mpc-rti-gpu.md) | [implementation plan](log/2026-07-16-joint-mpc-rti-small-obstacle-crossing-plan.md) |
| 2026-07-16 19:58 | Joint MPC RTI small-obstacle crossing implementation | functional pass; idle-GPU performance gate remains open | [T302v.4](todo/T302v-joint-mpc-rti-gpu.md) | [implementation verification](log/2026-07-16-joint-mpc-rti-small-obstacle-crossing-implementation.md) |
| 2026-07-16 16:05 | Joint MPC RTI small-obstacle crossing design | under review: adds signed-distance construction and separate foot/calf/thigh/base collision-frame rate `0%` acceptance overall and per shape-speed cell; strict cross remains required; code unchanged | [T302v.4](todo/T302v-joint-mpc-rti-gpu.md) | [crossing design](log/2026-07-16-joint-mpc-rti-small-obstacle-crossing-design.md) |
| 2026-07-16 15:20 | Joint MPC small-obstacle collision quantification | reproduced: strict cross success `1/223`; calf collision dominates; no planner code changed | [T302v.4](todo/T302v-joint-mpc-rti-gpu.md) | [collision quantification](log/2026-07-16-joint-mpc-small-obstacle-collision-quantification.md) |
| 2026-07-16 14:50 | Joint MPC viewer foot-name fix | undefined viewer normalization helper fixed; `133 passed`; real Isaac actual-state read finite | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [foot-name fix](log/2026-07-16-joint-mpc-viewer-foot-name-fix.md) |
| 2026-07-16 13:35 | Joint MPC RTI speed and swing verification | planner root velocity tracks all nine commands; real viewer swing peak lift `0.034..0.064m`; direct playback velocity boundary documented | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [speed/swing verification](log/2026-07-16-joint-mpc-rti-speed-swing-verification.md) |
| 2026-07-16 13:06 | Joint MPC RTI viewer grounding fix | functional pass: real nine-case order error `0`, stance surface gap max `0.010303m`, joint step max `0.183284rad`, zero root drift; performance recheck open | [T302v.3](todo/T302v-joint-mpc-rti-gpu.md) | [grounding fix](log/2026-07-16-joint-mpc-rti-viewer-grounding-fix.md) |
| 2026-07-16 11:44 | Joint MPC RTI viewer foot-flying reproduction | reproduced: adapter order error mean `2.465rad`, joint step `2.479rad`, foot step `0.590m`; viewer playback matches planner | [T302v.3](todo/T302v-joint-mpc-rti-gpu.md) | [reproduction](log/2026-07-16-joint-mpc-rti-viewer-foot-flying-reproduction.md) |
| 2026-07-16 10:40 | Joint MPC RTI synchronous exact EDT | pass: 1024×H16×1000 full refresh `4469.05ms`, version `+1000`, nonfinite `0` | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [exact EDT acceptance](log/2026-07-16-joint-mpc-rti-synchronous-exact-edt.md) |
| 2026-07-16 10:35 | Joint MPC RTI exact EDT regression | pass: joint `93`, old MPC `193`, public batches `1/40/512/1024`, pycompile/diff clean | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [regression](log/2026-07-16-joint-mpc-rti-exact-edt-regression.md) |
| 2026-07-16 00:38 | Joint MPC RTI multi-step Isaac fix | partial pass: 1/16-env three-step stable; real 1024 startup still open | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [multi-step fix](log/2026-07-16-joint-mpc-rti-multistep-isaac-fix.md) |
| 2026-07-15 23:50 | Joint MPC RTI performance acceptance | pass: 1024×H16×1000 `2885.63ms`, nonfinite `0`, peak `282.58MiB` | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [performance](log/2026-07-15-joint-mpc-rti-performance.md) |
| 2026-07-15 23:49 | Joint MPC RTI regression | pass: latest joint `72`, old MPC `193`, pycompile/diff clean | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [regression](log/2026-07-15-joint-mpc-rti-regression.md) |
| 2026-07-15 23:48 | Joint MPC RTI Isaac smoke | partial: 1-step boundary pass; 2-step process exit remains open | [T302v](todo/T302v-joint-mpc-rti-gpu.md) | [Isaac smoke](log/2026-07-15-joint-mpc-rti-isaac-smoke.md) |

| Time | Topic | Result | Todo | File |
| --- | --- | --- | --- | --- |
| 2026-07-15 14:38 | MPC root forward smooth bound `0.05-0.50m` | pass: correction bounds are now `[-0.20,+0.25]m` around the unchanged `0.25m` nominal; parametric `22 passed`, no IsaacLab started | [T302w.11](todo/T302w-mpc-row8-col12-loss-tuning.md#t302w11-root-forward-smooth-bound-005-050m) | [2026-07-15-mpc-root-forward-bound-005-050.md](log/2026-07-15-mpc-root-forward-bound-005-050.md) |
| 2026-07-15 14:10 | Remove zero parametric reachability loss | pass: dead loss and output key removed; no dedicated config weight existed; CPU backend + parametric `170 passed`, no IsaacLab started | [T302w.10](todo/T302w-mpc-row8-col12-loss-tuning.md#t302w10-remove-zero-parametric-reachability-loss) | [2026-07-15-remove-zero-parametric-reachability-loss.md](log/2026-07-15-remove-zero-parametric-reachability-loss.md) |
| 2026-07-15 03:49 | MPC row8/col12 optimize-16 position repro | reproduced: root/foot Isaac readback is micron-close, but planned-foot/analytic-FK error reaches `0.244m`, root Z step `0.205m`, and rough-terrain penetration is severe; no code changed | [T302w.7/T302w.8](todo/T302w-mpc-row8-col12-loss-tuning.md#t302w7-row8col12-optimize-16-position-reproduction) | [2026-07-15-mpc-row8-col12-opt16-position-repro.md](log/2026-07-15-mpc-row8-col12-opt16-position-repro.md) |
| 2026-07-15 03:18 | MPC low-small optimize-step sweep | partial pass: all `0..25` counts crossed covered cylinder/cone anchors; step `16` is the first conservative reachability candidate and observed `20-34%` lower plan time than step `25`; single-anchor limitation remains | [T302w.6](todo/T302w-mpc-row8-col12-loss-tuning.md#t302w6-low-small-optimizer-step-ablation) | [2026-07-15-mpc-low-small-optimize-steps-sweep.md](log/2026-07-15-mpc-low-small-optimize-steps-sweep.md) |
| 2026-06-16 17:30 | MPC touchdown keepout runtime cache | pass: 1024/1024 MPC long-tail root cause was repeated low-small component circle extraction inside sampled loss; final 60-step real probe `epoch_seconds=15.26`, max allocated `7.55GB`, no 35s `mixed_zero_split` tail | [T302u](todo/T302u-semantic-map-contact-collision-plan.md) | [2026-06-16-mpc-touchdown-keepout-runtime-cache.md](log/2026-06-16-mpc-touchdown-keepout-runtime-cache.md) |
| 2026-06-16 16:32 | MPC proximity field semantic avoidance | pass: existing `parametric_semantic_avoidance` now uses proximity field + `grid_sample`; real 1024 RL / 1024 MPC / 30-step probe exits `0`, max allocated `7.43GB`, no OOM | [T302u](todo/T302u-semantic-map-contact-collision-plan.md) | [2026-06-16-mpc-proximity-field-semantic-avoidance.md](log/2026-06-16-mpc-proximity-field-semantic-avoidance.md) |
| 2026-06-13 20:22 | Play disable timeout refresh | pass: PLAY cfgs set `terminations.time_out=None`; real smoke Termination Manager only has `base_contact`/`bad_orientation` | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) | [2026-06-13-2022-play-disable-timeout-refresh.md](log/2026-06-13-2022-play-disable-timeout-refresh.md) |
| 2026-06-13 18:39 | Play terminal keyboard backend | pass: `--keyboard-control` now uses terminal reader thread, removes `pynput`, static `32 passed`, real smoke exits `0` with non-TTY warning in tool runner | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) | [2026-06-13-1839-play-terminal-keyboard-backend.md](log/2026-06-13-1839-play-terminal-keyboard-backend.md) |
| 2026-06-13 18:10 | Human 12 play keyboard command update | pass: command guide now documents flat-small `--terrain-row/--terrain-col`, `--keyboard-control`, key map, `pynput` install state, and X/DISPLAY limitation | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) | [2026-06-13-1810-human-12-play-keyboard-command-update.md](log/2026-06-13-1810-human-12-play-keyboard-command-update.md) |
| 2026-06-13 17:56 | Play pynput install headless smoke | pass: `pynput 1.8.2` installed; static `31 passed`; real `--keyboard-control` smoke exits `0`, but current shell lacks X/DISPLAY so keyboard backend is disabled with warning | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) | [2026-06-13-1756-play-pynput-install-headless-smoke.md](log/2026-06-13-1756-play-pynput-install-headless-smoke.md) |
| 2026-06-12 17:40 | T302s model23600 crossing 1000-step probe | diagnostic pass: 16 envs x 1000 steps, no small contact, but overpass success `0/1` opportunity | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-12-1740-t302s-model23600-crossing-1000step-probe.md](log/2026-06-12-1740-t302s-model23600-crossing-1000step-probe.md) |
| 2026-06-13 15:05 | T302s model28900 controlled crossing eval | diagnostic pass: 16 envs x 1000 steps, opportunity `15/16`, root crossed `14`, foot-over `0`, real small contact `7/16`, overpass success `0/15` | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-13-1505-t302s-model28900-controlled-crossing-eval.md](log/2026-06-13-1505-t302s-model28900-controlled-crossing-eval.md) |
| 2026-06-12 17:22 | T302s model23600 first-layer eval | partial diagnostic: strict training scene `0/8` collision, dense eval `8/16` collision; reliable overpass not proven | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-12-1722-t302s-model23600-first-layer-eval.md](log/2026-06-12-1722-t302s-model23600-first-layer-eval.md) |
| 2026-06-12 16:42 | T302s flat-small 10:53 TensorBoard readout at 23.3k | diagnostic pass: stability recovered, but semantic trend is noisy; continue only to about `model_24000` before eval/retune | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-12-1642-t302s-flat-small-1053-tensorboard-readout.md](log/2026-06-12-1642-t302s-flat-small-1053-tensorboard-readout.md) |
| 2026-06-12 15:48 | T302s flat-small 10:53 TensorBoard readout at 22.8k | diagnostic pass: still worth continuing briefly; next decision around `model_23500-24000` | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-12-1548-t302s-flat-small-1053-tensorboard-readout.md](log/2026-06-12-1548-t302s-flat-small-1053-tensorboard-readout.md) |
| 2026-06-12 13:55 | T302s flat-small 10:53 TensorBoard readout | diagnostic pass: terrain curriculum now reaches high levels; continue while monitoring semantic contact trend | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-12-1355-t302s-flat-small-1053-tensorboard-readout.md](log/2026-06-12-1355-t302s-flat-small-1053-tensorboard-readout.md) |
| 2026-06-12 10:54 | T302s flat-small fixed command ranges | pass: flat-small training ranges now match requested forward-biased values; focused tests and real smoke passed | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) | [2026-06-12-1054-t302s-flat-small-fixed-command-ranges.md](log/2026-06-12-1054-t302s-flat-small-fixed-command-ranges.md) |
| 2026-06-12 10:39 | T302s flat-small 22:15 TensorBoard readout | diagnostic pass: curriculum scalar cleanup worked and clearance is visible, but terrain level drops to zero due to tiny command ranges after velocity curriculum removal | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-12-1039-t302s-flat-small-2215-tensorboard-readout.md](log/2026-06-12-1039-t302s-flat-small-2215-tensorboard-readout.md) |
| 2026-06-11 22:11 | T302s env-level collision curriculum implementation | pass: RED/GREEN focused tests, pycompile, diff check, and real 8-env smoke passed; active curriculum returns only `mean_terrain_level` | [T302s](todo/T302s-env-level-collision-curriculum-plan.md) | [2026-06-11-2211-t302s-env-level-collision-curriculum-implementation.md](log/2026-06-11-2211-t302s-env-level-collision-curriculum-implementation.md) |
| 2026-06-11 21:56 | Flat-small env-level collision curriculum HTML design | pass: Chinese HTML design written and parser-checked; ready for user review before implementation planning | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-11-2156-flat-small-env-level-collision-curriculum-html-design.md](log/2026-06-11-2156-flat-small-env-level-collision-curriculum-html-design.md) |
| 2026-06-11 19:55 | T302q flat-small 18:31 TensorBoard readout | diagnostic pass: clearance no longer all zero but remains tiny; curriculum still closed; do not continue exact run long | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-11-1955-t302q-flat-small-1831-tensorboard-readout.md](log/2026-06-11-1955-t302q-flat-small-1831-tensorboard-readout.md) |
| 2026-06-11 18:10 | T302r clearance radius/margin probe | diagnostic pass: radius alone hit semantic cells but no positive deficit; radius `0.50m` plus enlarged margins produced nonzero reward `1/64` | [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) / [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-11-1810-t302r-clearance-radius-margin-probe.md](log/2026-06-11-1810-t302r-clearance-radius-margin-probe.md) |
| 2026-06-11 17:24 | T302q flat-small TensorBoard readout | diagnostic pass: stable training and fixed bookkeeping, but geometry clearance still all zero and semantic gate closed | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) / [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-11-1724-t302q-flat-small-tensorboard-readout.md](log/2026-06-11-1724-t302q-flat-small-tensorboard-readout.md) |
| 2026-06-11 16:21 | T302q flat-small remove velocity curriculum | pass: flat-small cfg no longer mounts `lin_vel_cmd_levels`; real 8-env smoke shows only `terrain_levels` active | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-11-1621-t302q-flat-small-remove-velocity-curriculum.md](log/2026-06-11-1621-t302q-flat-small-remove-velocity-curriculum.md) |
| 2026-06-11 15:51 | T302r Go2 geometry clearance implementation | pass: geometry reward implemented with focused tests, pycompile, curriculum subset, and 16-env real IsaacLab smoke | [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-11-1551-t302r-go2-geometry-clearance-implementation.md](log/2026-06-11-1551-t302r-go2-geometry-clearance-implementation.md) |
| 2026-06-11 15:19 | T302r Go2 geometry clearance reward plan | pass: standalone todo/plan created for foot sphere, calf/thigh capsule, base footprint GPU scanner-map clearance implementation | [T302r](todo/T302r-go2-geometry-clearance-reward-plan.md) | [2026-06-11-1519-t302r-go2-geometry-clearance-plan.md](log/2026-06-11-1519-t302r-go2-geometry-clearance-plan.md) |
| 2026-06-11 15:13 | Go2 body geometry clearance HTML design | pass: Chinese HTML design created for USD-derived foot/calf/thigh/base geometry, fixed-shape GPU map queries, reward aggregation, and validation plan | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-11-1513-go2-body-geometry-clearance-html-design.md](log/2026-06-11-1513-go2-body-geometry-clearance-html-design.md) |
| 2026-06-11 14:28 | T302q flat-small plane mask fix | pass: single flat sub-terrain with 20 generated columns now counts all columns as flat; focused `21 passed`, pycompile exit `0`, real 64-env probe `plane_env_count=64` | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-11-1428-t302q-flat-small-plane-mask-fix.md](log/2026-06-11-1428-t302q-flat-small-plane-mask-fix.md) |
| 2026-06-11 14:20 | T302q flat-small curriculum and clearance root cause probe | diagnostic pass: flat mask recognizes only column 0 as flat, so `plane_env_count=52/1024`; real env scanner has small pixels but body-part clearance samples no small semantic cells and stays zero | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-11-1420-t302q-flat-small-curriculum-clearance-root-cause-probe.md](log/2026-06-11-1420-t302q-flat-small-curriculum-clearance-root-cause-probe.md) |
| 2026-06-11 11:20 | T302q flat-small TensorBoard semantic/curriculum readout | diagnostic pass: semantic contact sparse, `semantic_body_part_clearance` always `0`, episode-level semantic gate never passes, and flat-only bookkeeping shows suspicious non-flat move-ups | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-11-1120-t302q-flat-small-tensorboard-semantic-curriculum-readout.md](log/2026-06-11-1120-t302q-flat-small-tensorboard-semantic-curriculum-readout.md) |
| 2026-06-10 20:43 | Human 12 flat-small command update | command guide updated with new flat-small experiment/Gym ids, warm-start train commands, play commands, and eval caveat | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-10-2043-human-12-flat-small-command-update.md](log/2026-06-10-2043-human-12-flat-small-command-update.md) |
| 2026-06-10 20:35 | T302q flat small local implementation and smoke | pass after one runtime wiring fix: focused `31 passed`, pycompile exit `0`, fresh train smoke exit `0`, resume from `model_14000.pt` exit `0` | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-10-2035-t302q-flat-small-local-implementation-and-smoke.md](log/2026-06-10-2035-t302q-flat-small-local-implementation-and-smoke.md) |
| 2026-06-10 19:45 | T302q flat small avoidance reward plan | plan recorded; dashboard switched to T302q; no runtime code implementation yet | [T302q](todo/T302q-flat-small-avoidance-reward-plan.md) | [2026-06-10-1945-t302q-flat-small-avoidance-plan.md](log/2026-06-10-1945-t302q-flat-small-avoidance-plan.md) |
| 2026-06-09 20:26 | Current MPC/PPO HTML overview | documentation pass: Chinese framework-style static HTML overview created at [../docs/current-mpc-ppo-overview.html](../docs/current-mpc-ppo-overview.html); HTML parser check passed | [T302p](todo/T302p-mpc-command-frame-alignment-plan.md) / [T302l](todo/T302l-mpc-rl-participation-and-reward-plan.md) | [2026-06-09-2026-current-mpc-ppo-html-overview.md](log/2026-06-09-2026-current-mpc-ppo-html-overview.md) |
| 2026-06-07 12:11 | T302p direction loss wiring and metric boundary | partial pass: root direction fixed and low-small compatibility passes; per-leg endpoint metric still open | [T302p](todo/T302p-mpc-command-frame-alignment-plan.md) | [2026-06-07-1211-t302p-direction-loss-wiring-and-metric-boundary.md](log/2026-06-07-1211-t302p-direction-loss-wiring-and-metric-boundary.md) |
| 2026-06-07 11:04 | T302p low-small FK loss wiring and regression | low-small hard gates pass after existing loss wiring; flat-left still fails direction preference | [T302p](todo/T302p-mpc-command-frame-alignment-plan.md) | [2026-06-07-1104-t302p-low-small-fk-loss-wiring.md](log/2026-06-07-1104-t302p-low-small-fk-loss-wiring.md) |
| 2026-06-06 23:17 | T302p real acceptance failures | real tests completed but acceptance failed: eight-direction command sync passes, direction metrics fail; low-small hard metrics fail | [T302p](todo/T302p-mpc-command-frame-alignment-plan.md) | [2026-06-06-2317-t302p-real-acceptance-failures.md](log/2026-06-06-2317-t302p-real-acceptance-failures.md) |
| 2026-06-06 18:58 | T302p command-frame implementation | implementation and focused verification pass; full eight-command and low-small semantic regression still open | [T302p](todo/T302p-mpc-command-frame-alignment-plan.md) | [2026-06-06-1858-t302p-command-frame-implementation.md](log/2026-06-06-1858-t302p-command-frame-implementation.md) |
| 2026-06-06 18:34 | T302p MPC command-frame alignment plan | plan recorded; dashboard switched to T302p; no runtime code implementation yet | [T302p](todo/T302p-mpc-command-frame-alignment-plan.md) | [2026-06-06-1834-t302p-mpc-command-frame-alignment-plan.md](log/2026-06-06-1834-t302p-mpc-command-frame-alignment-plan.md) |
| 2026-06-06 16:33 | T302o flat forward MPC lateral bias reproduction | reproduced; flat semantic-free run shows default planner uses unrotated world `[1,0]` as nominal forward while robot yaw is `16deg`; default body-left drift `-0.0937m`, yaw-rotated command body-left drift `-0.0044m` | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-06-1633-t302o-flat-forward-mpc-left-bias-reproduction.md](log/2026-06-06-1633-t302o-flat-forward-mpc-left-bias-reproduction.md) |
| 2026-06-06 16:16 | T302o foot trajectory timebase probe | diagnostic pass; real IsaacLab one-off probe confirms `refresh_from_env()` happens during post-step reward, metrics/markers read the same post-step cache/phase, and mismatch is not async MPC execution; phase advance slightly increases along-current mismatch | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-06-1616-t302o-foot-trajectory-timebase-probe.md](log/2026-06-06-1616-t302o-foot-trajectory-timebase-probe.md) |
| 2026-06-06 14:13 | T302o livestream foot trajectory marker and follow camera | pass for runtime path; RED missing full trajectory marker helper, GREEN targeted `1 passed`, static+metric `16 passed`, real livestream smoke exit `0` with `Streaming server started`, `total_steps=2`, reference valid `1.0` | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-06-1413-t302o-livestream-marker-follow-camera.md](log/2026-06-06-1413-t302o-livestream-marker-follow-camera.md) |
| 2026-06-05 17:45 | T302o final MPC policy eval smoke | pass; local/static `16 passed`, pycompile exit `0`, tracking smoke exit `0` with 20 valid steps and `reference_valid_ratio=1.0`, small_collision smoke exit `0` with `total_env_rounds=4`, livestream startup exit `0` and `Streaming server started` | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-05-1745-t302o-mpc-policy-eval-smoke.md](log/2026-06-05-1745-t302o-mpc-policy-eval-smoke.md) |
| 2026-06-05 | T302o Task 5 small_collision runtime metrics | pass locally; metric `7 passed in 1.61s`, static `7 passed in 0.03s`, pycompile exit `0`, diff check exit `0`; final card0/env_isaacsim smoke later verified env-count denominator | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-05-t302o-task5-small-collision-runtime-metrics.md](log/2026-06-05-t302o-task5-small-collision-runtime-metrics.md) |
| 2026-06-05 | T302o Task 4 tracking runtime metrics | pass locally and real smoke; RED missing `TrackingRoundAccumulator`; GREEN metric `6 passed`, static `6 passed`, pycompile exit `0`; card0/env_isaacsim smoke exit `0`, 3 valid tracking steps, reference valid ratio `1.0` | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-05-t302o-task4-tracking-runtime-metrics.md](log/2026-06-05-t302o-task4-tracking-runtime-metrics.md) |
| 2026-06-05 | T302o Task 3 rollout skeleton | pass; RED static `3 failed, 2 passed in 0.04s`, GREEN static `5 passed in 0.02s`, pycompile exit `0`, diff check exit `0`, real IsaacLab smoke exit `0`; output dir `logs/mpc_policy_eval/task3_smoke/2026-06-05_17-00-41`; Task 4 tracking metrics next | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-05-t302o-task3-rollout-skeleton.md](log/2026-06-05-t302o-task3-rollout-skeleton.md) |
| 2026-06-05 | T302o Task 2 metric helpers | pass after import isolation correction; invalid original RED recorded; corrected RED missing helper; GREEN `3 passed in 1.48s`, pycompile exit `0`, diff check exit `0`; Task 3 rollout skeleton next | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-05-t302o-task2-metric-helpers.md](log/2026-06-05-t302o-task2-metric-helpers.md) |
| 2026-06-05 | T302o Task 1 static contracts | pass; RED `4 failed`, GREEN `4 passed in 2.10s`, pycompile exit `0`, staged diff check exit `0`; Task 2 metric helpers next | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-05-t302o-task1-static-contracts.md](log/2026-06-05-t302o-task1-static-contracts.md) |
| 2026-06-05 | T302o MPC policy eval plan | plan recorded; dashboard switched to T302o; implementation not started | [T302o](todo/T302o-mpc-policy-eval-plan.md) | [2026-06-05-t302o-mpc-policy-eval-plan.md](log/2026-06-05-t302o-mpc-policy-eval-plan.md) |
| 2026-06-03 20:52 | T302n row-gated semantic curriculum | pass; static row-based semantic objects, flat-only semantic gate, no runtime semantic level; focused `24 passed`, pycompile exit `0`, IsaacLab card1 row9 probe flat `8/2`, non-flat `4/1`, force shapes `[8,13,416,3]` / `[8,13,82,3]` | [T302n](todo/T302n-semantic-obstacle-curriculum-plan.md) | [2026-06-03-2052-t302n-row-gated-semantic-curriculum.md](log/2026-06-03-2052-t302n-row-gated-semantic-curriculum.md) |
| 2026-06-03 19:58 | T302n viewer reference foot pos cfg fix | pass; `VIEWER` cfg builds, `reference_foot_pos` / `semantic_contact_collision` are enabled, and the user viewer command reaches env setup plus MPC manager attach | [T302n](todo/T302n-semantic-obstacle-curriculum-plan.md) | [2026-06-03-1958-t302n-viewer-reference-foot-pos-cfg-fix.md](log/2026-06-03-1958-t302n-viewer-reference-foot-pos-cfg-fix.md) |
| 2026-06-02 00:06 | T302l PLAY / VIEWER cfg split | pass; local focused tests pass, headless PLAY with `model_14000.pt` completes 5 steps with no planner attach, low-small covered rows `2` with FK semantic collisions `0` and max crossing FK error `0.0416m` | [T302l](todo/T302l-mpc-rl-participation-and-reward-plan.md) | [2026-06-02-0006-t302l-play-viewer-cfg-split.md](log/2026-06-02-0006-t302l-play-viewer-cfg-split.md) |
| 2026-05-31 23:06 | T302m card1 IsaacLab acceptance | pass; contact drop probe, 1024-env 1-iteration train smoke, and 1024/64/25-step perf pass; `epoch_seconds=5.8828s` | [T302m](todo/T302m-teacher-elevation-mpc-semantic-cleanup-plan.md) | [2026-05-31-2306-t302m-card1-isaaclab-acceptance.md](log/2026-05-31-2306-t302m-card1-isaaclab-acceptance.md) |
| 2026-05-31 22:49 | T302m teacher elevation MPC semantic cleanup | local pass; cleanup guards `3 passed`, viewer `16 passed`, focused `43 passed`, backend `128 passed`; IsaacLab card3 smoke blocked by existing 20.6GB 1024-env train process causing OOM | [T302m](todo/T302m-teacher-elevation-mpc-semantic-cleanup-plan.md) | [2026-05-31-2249-t302m-teacher-mpc-semantic-cleanup.md](log/2026-05-31-2249-t302m-teacher-mpc-semantic-cleanup.md) |
| 2026-05-31 10:49 | T302l semantic contact robot drop probe | pass; real robot drop detects small and large semantic contacts; empty envs stay zero; no NaN/Inf; small active frames `5` vs large active frames `150` | [T302l](todo/T302l-mpc-rl-participation-and-reward-plan.md) | [2026-05-31-1049-t302l-semantic-contact-robot-drop-probe.md](log/2026-05-31-1049-t302l-semantic-contact-robot-drop-probe.md) |
| 2026-05-30 23:13 | T302l semantic global contact card1 performance | pass after exact-path body resolution fix; card1 quantity alignment PASS, shapes `[1024,13,640,3]` and `[1024,13,100,3]`, 1024/64 probe `5.6489s` | [T302l](todo/T302l-mpc-rl-participation-and-reward-plan.md) | [2026-05-30-2313-t302l-semantic-global-contact-card1-perf.md](log/2026-05-30-2313-t302l-semantic-global-contact-card1-perf.md) |
| 2026-05-30 21:23 | T302l MPC RL final verification | pass; focused `7 passed`, backend `140 passed`, contact smoke PASS, 1024/64 probe `5.256s`, train entry PASS, low-small covered rows `0` FK semantic collisions and max crossing FK error `0.0634m`; PhysX global-filter warning recorded | [T302l](todo/T302l-mpc-rl-participation-and-reward-plan.md) | [2026-05-30-2123-t302l-final-verification.md](log/2026-05-30-2123-t302l-final-verification.md) |
| 2026-05-30 21:14 | T302l 1024/64 performance | pass; probe `5.256s <= 10s`, train entry exits `0` with `--planner-backend mpc` | [T302l](todo/T302l-mpc-rl-participation-and-reward-plan.md) | [2026-05-30-2114-t302l-rl-1024-64-performance.md](log/2026-05-30-2114-t302l-rl-1024-64-performance.md) |
| 2026-05-30 21:03 | T302l semantic contact smoke | pass in `env_isaacsim`; 26 per-body filtered contact sensors expose force matrices `[4,1,filter_count,3]` | [T302l](todo/T302l-mpc-rl-participation-and-reward-plan.md) | [2026-05-30-2103-t302l-semantic-contact-smoke.md](log/2026-05-30-2103-t302l-semantic-contact-smoke.md) |
| 2026-05-28 22:59 | T302k low-small full matrix and FK inner-loop losses | pass for hard acceptance on crossing-covered rows; max FK semantic collision `0`, max crossing FK error `0.0634m`; four rows remain soft tuning risk over `0.05m` | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2259-t302k-low-small-full-matrix-and-fk-inner-loop.md](log/2026-05-28-2259-t302k-low-small-full-matrix-and-fk-inner-loop.md) |
| 2026-05-28 21:06 | T302k plane low-small FK semantic collision probe | pass for metric/logging smoke; plane rows and required FK semantic keys present; crossing legs not covered in smoke | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2106-t302k-plane-low-small-fk-collision-probe.md](log/2026-05-28-2106-t302k-plane-low-small-fk-collision-probe.md) |
| 2026-05-28 21:25 | T302k plane root-z target | pass locally; plane-only root-z target sampled key added | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2125-t302k-plane-root-z-target.md](log/2026-05-28-2125-t302k-plane-root-z-target.md) |
| 2026-05-28 21:17 | T302k FK trajectory consistency | pass locally; final optimized-target vs FK-realized consistency key added | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2117-t302k-fk-trajectory-consistency.md](log/2026-05-28-2117-t302k-fk-trajectory-consistency.md) |
| 2026-05-28 21:10 | T302k FK body leg collision | pass locally; final loss key added for realized FK body/leg terrain collision, with post-optimization limitation recorded | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2110-t302k-fk-body-leg-collision.md](log/2026-05-28-2110-t302k-fk-body-leg-collision.md) |
| 2026-05-28 20:57 | T302k swing target clearance | pass locally; sampled loss key `parametric_swing_foot_clearance` added | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2057-t302k-swing-target-clearance.md](log/2026-05-28-2057-t302k-swing-target-clearance.md) |
| 2026-05-28 20:48 | T302k touchdown circle keepout | pass locally; sampled loss key is now `parametric_touchdown_keepout` | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2048-t302k-touchdown-circle-keepout.md](log/2026-05-28-2048-t302k-touchdown-circle-keepout.md) |
| 2026-05-28 20:34 | T302k low-small GPU circles | pass locally; fixed-shape component circles stay on input device | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2034-t302k-low-small-gpu-circles.md](log/2026-05-28-2034-t302k-low-small-gpu-circles.md) |
| 2026-05-28 20:25 | T302k plane terrain metadata | pass locally; `is_plane_terrain` flows through MPC terrain and manager infers `flat/plane` from IsaacLab terrain names | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2025-t302k-plane-terrain-metadata.md](log/2026-05-28-2025-t302k-plane-terrain-metadata.md) |
| 2026-05-28 20:14 | T302k nominal extraction contract | pass locally; decode consumes `nominal + variables`; pure-yaw high/large semantic candidate restored | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-28-2014-t302k-nominal-extraction-contract.md](log/2026-05-28-2014-t302k-nominal-extraction-contract.md) |
| 2026-05-28 | T302k low-small loss redesign design/plan | design committed and implementation plan created under todo; no code implementation yet | [T302k plan](todo/T302k-low-small-loss-redesign-plan.md) | [HTML design](../docs/superpowers/specs/2026-05-28-parametric-low-small-loss-redesign.html) |
| 2026-05-26 21:33 | T302k body-relative foot anchor fix | pass for major accumulated foot drift; residual yaw body-x drift remains background | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-26-2133-t302k-body-relative-foot-anchor-fix.md](log/2026-05-26-2133-t302k-body-relative-foot-anchor-fix.md) |
| 2026-05-26 20:21 | T302k support-plane root roll/pitch | pass locally and in `env_isaacsim`; root roll/pitch follows support plane after frame0 | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-26-2021-t302k-support-plane-root-roll-pitch.md](log/2026-05-26-2021-t302k-support-plane-root-roll-pitch.md) |
| 2026-05-26 17:57 | T302k dense path retirement | pass locally; old dense residual modules/config switch removed | [T302k](todo/T302k-parametric-mpc-trajectory-contract.md) | [2026-05-26-1757-t302k-dense-path-retirement.md](log/2026-05-26-1757-t302k-dense-path-retirement.md) |

## Maintenance

- Keep this page as a dashboard, not a changelog.
- Put detailed background in branch pages and evidence in logs.
- Old unfinished T302h/T302i/T302j leaves are closed as routes and preserved as context, not deleted.

- 2026-09-24: crossing-state hardening added: require pre-front clearance and exclude collision frames from success rate; focused tests pass. Full episode physical validation remains open.

| 2026-10-03 | M1 serial PhysX follow-up | partial/fail | headless runtime recovered; 128-step four-leg physical gate still fails (tilt/net-clearance) | T306 | [2026-10-03-m1-serial-physx-followup.md](log/2026-10-03-m1-serial-physx-followup.md) |
