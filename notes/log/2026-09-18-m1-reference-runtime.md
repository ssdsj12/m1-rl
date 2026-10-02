# M1 reference runtime adapter verification

## Purpose / Stage / Todo

Independent controller-oracle runtime adapter, [T306.6h.2](../todo/T306-m1-ame-long-train-stability.md). Reference code stays read-only; no production AME/controller/reward changes. This log separates CPU interface verification from actual Isaac execution.

## Inputs / Procedure

- Baseline code:9672385. New standalone files: `tools/m1_reference_validation/run.py`, `runtime.py`, `run.sh`, `tests/test_runtime_contract.py`.
- Python: amp; physical GPU4. Allowed simulation sizes8/1024 and budgets32/1600. No1env, checkpoint, PPO runner, automatic restart or installation.
- Read-only installed API audit: recorder post-step is before auto-reset; EXPORT_NONE prevents dataset export; forced sensor updates support each physics substep; terrain1row×Ncols assigns separate columns; AppLauncher accepts fast_shutdown=False.
- Native PhysX contact sensor/filter path properties must be validated separately from the requested source path list. Reference filter list is lexical, so own-bar mapping uses parsed numeric column identifiers.

## Evidence

- 2026-09-18 13:33:39 CST GPU/process precheck: GPU4 idle5MiB, no M1 training/reference validation process. No action on unrelated processes.
- Reference CPU rerun: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/home/hexinkun/m1/Go2Pvcnn /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q -p no:cacheprovider /home/hexinkun/m1/Go2Pvcnn/tests/test_m1_curriculum.py`:88passed in1.97s,exit0.
- AdapterTDD:initial21missing-implementation failures; additional zero-sample-finalization regression failed before correction. Firstcompletecontracts26passed, mainindependent rerun26passed1.70s.
- Spec review foundtwo omissions: actualinterpreter provenance andreport-write failure skippingcleanup. Addedactualsys.executable/sys.version guard andindependentattempts forreport/status/env.close/restore/app.close, withfault-injectiontests. Mainindependent rerun30passed1.80s,exit0;bash-npassed. LF-only shell confirmed;missing-output shell refuses launch beforeIsaac.
- Spec re-reviewPASS. Deployedhashesmatchreviewedfiles; mainindependentdeployedunion142passed21.13s,exit0. Qualityreviewpending. NoIsaacrunhasstartedforthisadapter.
- Qualityreview foundtwo measurement blockersbeforeIsaac: entiregroundBBox includesunusedborderbottomvertices, whileactualreferencedfacesremainplanar; fixed20um scannerownership tolerance failsfar-worldfloat32 quantization. MainverifiedTerrainGenerator._add_terrain_border onlyfiltersfaces andcreate_prim_from_mesh writesallvertices; independentlyreproducedownbarloweredge4091.72->4091.719970703125 classifiedasforeign1/own0. Bothareadaptermeasurementbugs, notcontrollerfailures. MinimalTDDfixinprogress:used-faceworldgeometry anddocumentedfloat32ownershipboundary; nochangephysical1N/clearancethresholds orsourcegeometry.
- Bothmeasurementfixes:8focusedRED→38runtimeGREEN; maindeployedunion150passed21.68s,exit0. Testsusebundledpxr memoryUSD(noIsaac): addamp's `isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310` toPYTHONPATH andits`bin` toLD_LIBRARY_PATH. Groundnowusesreferencedtriangleworldvertices,ignoresunusedpointsforplanarity,bboxdiagnosticonly. ScannerownershipboundisinclusiveunionofUSDandfloat32-quantizedworldboundsplusoriginal20umgeometricchecktolerance; measuredshift/boundsreported,neighborobstaclestillrejected. Finalqualityre-reviewpending.

## Result / Follow-up

FinalspecandqualityreviewsPASS. Standaloneadaptercommittedatf5842d4; maindeployedunion150passed21.68s. Runtime andbehaviorremainunverified: launchprecheckat14:22CSTfoundGPU4occupiedbyanotheruser,soNOIsaacprocesswasstarted. See[GPUresourceblocker](2026-09-18-m1-reference-gpu-resource-blocker.md). Needresourcecoordinationbefore8×32. Recordactualexposedobstacleheight(sourceembeds15mm)withoutchangingcontrollerorrelaxingthresholds. Onlythreestrict8×1600passespermit1024execution.

## Git Refs

Baseline Ref:9672385. Candidate/LastFeature/LastCPUVerifiedRef:f5842d4; noPhysicalVerifiedRef. Related [plan](../../docs/superpowers/plans/2026-09-18-m1-reference-runtime.md), [metrics](2026-09-18-m1-reference-metrics.md), [provenance](2026-09-18-m1-reference-preflight.md).
