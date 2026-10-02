# M1 wheel equalizer isolated A/B

## Purpose / Stage / Todo

T306.6h.6, following the [strict run12 failure](2026-09-18-m1-reference-strict-run12.md). User explicitly confirmed the [single-variable design](../../docs/superpowers/specs/2026-09-18-m1-wheel-equalizer-ab-design.md). Goal is causal diagnosis of the gain3 wheel equalizer, not policy training or automatic promotion.

## Candidate scope

Formal reference adapter a86cbf5 remains unchanged. Isolated remote copy: `/home/hexinkun/m1_debug_tools/equalizer_off_20260918/adapter`. Only runtime.py and run.py behavior/metadata edits: exact source gain3 guard, gain0 override, exact3→0 diff guard, and diagnostic metadata in configuration/provenance. Tests changed in test_runtime_contract.py plus new test_equalizer_ab.py. run.sh/metrics/provenance/clone evidence unchanged. Source `/home/hexinkun/m1`, installed SDK, AME and all safety/acceptance limits untouched.

## CPU evidence

- Copied baseline:212passed24.43s.
- Initial RED had11fail/6pass, including3over-specific error-regex failures. Regex corrected before implementation.
- Corrected RED:8failed/9passed/54deselected0.51s; gain still3, wrong source gain not rejected, candidate provenance absent.
- GREEN:17passed/54deselected0.37s.
- Full regression:225passed24.49s; bash syntax passes.
- CPU logs at candidate parent:cpu-red.log,cpu-green.log,cpu-suite.log.

Candidate hashes before review:

```text
runtime.py d13cc7967c2a55b63aacbbcfc0e9d6b0e3479360157201c0830800ffcb1027b7
run.py b742687f1b5f1e0af287bbd649ac5edc374e54cc76b433e17fb6d4583a1f3cb8
```

## Independent baseline audit

The50raw chunks cover exactsteps0..1599. Tail800usessteps800..1599,799adjacent differences; it is diagnostic only and cannot replace the1600sample strict gate. Baseline pooled target difference RMS.83998303rad/s, speed difference RMS.77451815rad/s. FAR target lag1 is-1 in6/8, approximately-.9902 in2/8; allFAR/FBL zero-target fraction.5. Env3/5have occasional FAR targets above1 from negative measured speeds, so do not claim every target is strictly0/1. Previous-speed control-law replay error≤8.05e-8rad/s.

## Review and physical result

Independent spec and quality reviews both PASS with no must-fix. Exactly the approved run13 was executed on amp/physicalGPU7, retaining15GiB reservation PID2795762. No restart, signal, GDB, SDK change or second candidate. Final CPU rerun:225passed24.77s; bash syntax passed. Formal adapter remains byte-clean against a86cbf5.

Command: `ulimit -c 0` then `bash /home/hexinkun/m1_debug_tools/equalizer_off_20260918/adapter/run.sh --num-envs 8 --steps 1600 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_13_equalizer_off`, stdout/stderr at output-prefix.log. PID3589897; runIDfd00757c-d88e-4bd7-b7d3-d86ed52c1ccf. Received exact1600steps/1600prepare+IKcalls/6400physical sensor updates. Sampling103.925117s excludes shutdown. ENV_CLOSED, RUNTIME_REFS_RELEASED, APP_CLOSED and POST_CLEANUP precede native0. Final completed=true, passed=false, strict1/8, wrapper3; wrapper3 is behavioral rejection, not an Isaac crash. Measurement/finalization errors are empty.

### Frozen parity

Baseline and candidate before-config and source-wave/acceptance snapshots exactly equal; after-config differs only gain3→0. Provenance is equal after removing the explicit candidate label. Before/after binding snapshots match within and across runs. Scene manifest, measured geometry, randomization JSON and runtime metadata exactly equal. All six initial NPZ arrays match exactly:root_state_w,joint_pos,joint_vel,masses,material_properties,env_origins. This checks bound sources, not every file in the reference/SDK tree.

| Env | First-episode samples | Root progress m | Wheel mean spread rad/s | Strict rejection |
| --- | ---: | ---: | ---: | --- |
| 0 | 1600 | 4.72449 | .0961583 | wheel speed |
| 1 | 135 | 1.09757 | .2229535 | phase/progress/rear height/reference collision/termination/recovery/wheel speed/all RAR events |
| 2 | 1600 | 4.71704 | .0884832 | wheel speed, RAR overbar/passed/touchdown |
| 3 | 1600 | 4.75487 | .0833507 | wheel speed |
| 4 | 1600 | 4.74510 | .0985131 | wheel speed |
| 5 | 1600 | 4.69464 | .1148624 | wheel speed, RAR overbar/passed/touchdown |
| 6 | 1600 | 4.72937 | .1060030 | wheel speed |
| 7 | 1600 | 4.69680 | .0746270 | none |

### First-episode-aware oscillation comparison

Offline script at candidate parent `analyze_equalizer_ab.py`, output `analysis.json`. It asserts contiguous1600steps, initial/metadata parity and recomputed first-episode means against the report. Diagnostic tail800 is steps800..1599 and799within-window differences; it never replaces the strict denominator.

For paired environments0,2,3,4,5,6,7, all having complete first episodes in both runs, target difference RMS falls .848488407→0rad/s and actual-speed difference RMS .784206293→.237259572rad/s. Candidate targets are constant[1,1,1.4,1.4], zero-target fractions0; baseline front zero-target fractions.5. Actual speed fluctuations and mean mismatch remain. Env1 has no first-episode tail800 and is explicitly excluded from this diagnostic comparison, not from strict1/8 acceptance. Raw pooled8-env tail would mix repeated failures and is not a valid paired-flat result.

Candidate first wave begins53 in all8 vs baseline95..97; seven finish wave181..182 vs237..246. The control removal also changes approach/crossing timing and trajectory. Evidence establishes outer feedback contribution to target alternation, not that a gain0 controller is safe or that velocity increase uniquely explains every failure.

### Failed crossing events

Independent audit replayed frozen metrics against both full raw datasets; both metrics reports match exactly. Main independently checked the decisive samples.

- Env1 terminates first atstep134; report includes0..134=135samples and reset_count1. Raw1600contains11terminations at134+135k, not11first-episode resets. Atstep131 phase6 begins with RARx=.693928; at134 RAR=(.728470,-.358503,.097001)m and generic netforce95.423N. It triggers the unchanged reference geometric/load collision predicate. Own-bar wheel and nonwheel substep peaks remain0N, so do not call this measured bar impact. RARneverprelifts. Rootdx1.097567 is below recovery start1.1, so recoverymean has zero samples. Baselineenv1 entersphase6atRARx=.616235 and completes allfourRAR events.
- Env2/5 RAR reaches x∈[.82,.88] atsteps147/148, with z=.194..201m and force0, but y=-.392546..-.395944 exceeds strictlowerbound-.3759 by16.65..20.04mm. Thus overbar is not recorded; ordered passed/touchdown cannot be recorded later even though actual landing geometry occurs. This is lateral crossing-corridor failure, not evidence of insufficient lift or measured bar impact. Baseline RAR overbar y=-.363728/-.354445 passes. Their first_failure_step=null is correct for aggregate/missing-event gates, not success.

## Conclusion / current state

DIAGNOSTIC COMPLETE, CANDIDATE REJECTED. Strict result worsened4/8→1/8. No promotion, threshold relaxation, further simulator run or1024expansion. Original baseline remains available unchanged; isolated candidate and raw evidence retained. At final process check3589897 had exited naturally; GPU7 showed15754MiBused/8328free/0%, only original reservation computePID2795762.

New child T306.6h.6a: separate synchronization from crossing speed/trajectory scheduling. Next design must preserve the proven crossing-stage timing/clearance while addressing flat-tail feedback oscillation; identify actuator/load response and transition/reset state before choosing filtered synchronization or feedforward changes. A phase-only tail change is a bounded diagnostic alternative but not yet a full-controller repair. No further candidate is authorized by this one-run design. AME lifecycle, namedphysicaltargetbridge, learned crossing and large avoidance remain separate open stages.

## Git / Follow-up

Baseline Ref:a86cbf5; approved design initially7c9dac9; Candidate Ref:isolated hashes above. Key Files:isolated runtime.py/run.py and tests; frozen report and offline analysis. No candidate feature commit or physical acceptance. See [implementation plan](../../docs/superpowers/plans/2026-09-18-m1-wheel-equalizer-ab.md). Dashboard/branch/index aligned. No1024/10000 or learned crossing/avoidance conclusion; no human/AI mainline contract edit because formal behavior was unchanged.
