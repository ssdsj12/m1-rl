# IK Active Tangent Implementation Plan

> Use superpowers:executing-plans inline; one fresh final reviewer after implementation. User direct execution overrides repetitive handoff/approval prompts.

**Goal:** Remove constrained-direction stagnation without relaxing actual10cm crossing/recovery.
**Architecture:** Preserve projected fullDLS candidate and add reducedABAD/HIP candidate only when finite raw knee crosses its existing bound. Pick strictly better legal actualFKresidual within same32iterations.
**Tech Stack:** PyTorch CPU regressions, independent execution audit, isolated Isaac4env.

## Task1 — provenance and RED

Files: tests/fixtures/m1_v26_tangent.json; tests/test_m1_teacher_ik_tangent.py; .superpowers/sdd/2026-10-15-m1-ik-active-tangent/progress.md.
- [ ] Finishv26terminalaudit, preserve fullraw4episode/video/source before replacing remote runtime. Verify stopped child andGPUempty.
- [ ] Extract frames118/122/133/134/137 q=feedback_context.last_applied_q, branch_q, execution_body_step_{j}_{axis} from finalenv1JSONL; storetraceSHA. Baselinecopies of currentIK/teacher.
- [ ] Parameterize frame133/134/137 × float32/64, call solve_constrained_ik(q,target,branch,tolerance_m=q.new_full((1,4),.0001)); assertvalid, allresidual<=.0001, samebranch, knee>=.1, jointlimits, maxdelta<=.05, iterations<=32. Run oldv26 and observe residualfailure, not importerror.
- [ ] Preserve normal118/122 output comparison; add configured.1/.3 fourleg boundarytests, existinginvalidseed/unreachable/outerratecoverage, candidate-infinity regressions. Add forced reducedstepNaN with legalnormalcandidate and assert fallbackcannot replace it. Use monkeypatch only for numericalfailure injection, not coretarget tests.

## Task2 — minimal implementation and GREEN

Files: ame_baseline/m1_teacher_ik.py; ame_baseline/m1_reference_teacher.py fingerprintonly.
- [ ] Save jacobian before fulldls. Keep rawfinite and knee_sign. After existingprojection build:

```python
hit = knee_sign * raw_proposal[:, 2::3] < cfg.min_knee_abs_rad
delta_knee = proposal[:, 2::3] - q[:, 2::3]
remaining = error - jacobian[..., 2] * delta_knee[..., None]
tangent = q.reshape(batch, 4, 3).clone()
tangent[..., :2] += dls_step(jacobian[..., :2], remaining,
                           cfg.damping, cfg.dq_component_limit_rad)
tangent[..., 2] = proposal[:, 2::3]
```

- [ ] Evaluate both through identical finite/limits/branch/configuredminimum checks and realFK. Fornormal use existinglegal; tangenteligible=active & hit & rawfinite & tangentlegal. Pick tangent only when itsresidual<currentresidual and (normalillegal or tangentresidual<normalresidual). Then unchanged finalaccept/currentqheldonfailure. Keep originalfinite guardingbothpaths. Inactive legs neverupdate; tie retainsnormal.
- [ ] Change fingerprint v26-ik-boundary-step to v27-ik-active-tangent. PublicAPI unchanged.
- [ ] Run `CUDA_VISIBLE_DEVICES= PYTHONPATH=.:tests:rsl_rl /opt/conda/envs/env_issacsim/bin/python -m pytest -q tests/test_m1_teacher_ik_tangent.py tests/test_m1_teacher_ik_boundary.py tests/test_m1_teacher_ik.py`. Expected0failed. SaveRED/GREENandSHA.
- [ ] Full prior759 plusnewtests. Freshfinalreviewfocus: preprojectionnonfinite, negativebranch/configmin, perlegisolation, same32/component/outerrate, geometryaudit. OneC/I RED/GREENfixpass, no repeatreview. No Gitidentitychange; manualsourceledger.

## Task3 — actual crossing

- [ ] Verify candidateSHA localremote, previousnativeabsent/GPUempty, no train/play. Unique evidence-first-obstacle-ik-tangent-v1 and logfileguard/flock; same4env/10cm/slowrolling/loadfeedback1000diagnosticsteps. Never restart on observerdisconnect.
- [ ] Observe activewheelbottom/rawforces/passage/restore and completeall4audits/videos. Nativeexit0 or mathematicalvalidity never successalone. Archive localremoteSHA; update notes/index/T306. No productiontraining or evidencecleanup.

Self-review: scope confined to candidate direction and version; tests cover domainandnonfinite, no target/threshold changes. Allphysical requirements remainopen untilactualevidence. No implementation whilev26finalaudit consumes live source.
