# Reference post-launch fatal diagnostics verification

## Purpose / Stage / Todo

T306.6h.5, diagnostic-only follow-up to [owner cleanup](2026-09-18-m1-reference-owner-cleanup.md). Installed AppLauncher.py156–159 installs Python SIGABRT/SIGSEGV callbacks after interpreter-startPYTHONFAULTHANDLER, interfering with native fataltrace. No control/physics/finalizer changes.

## Method / Verification

Immediately after successfulAppLauncher, disablefaulthandler, select SIG_DFL forSEGV/ABRT, thenenable(file=sys.stderr,all_threads=True). This ordering matters: CPython3.10 disable restores savedhandlers; enable alreadyenabled is a no-op. SIGTERM remainsunchanged. Marker `M1_REFERENCE_FATAL_DIAGNOSTICS_ENABLED` proveswiring.

RED5failed44deselected; GREEN49runtimepassed4.53s. FourcontrolledCPUchildren coverABRT/SEGV andhandlerinstallationorder, RLIMIT_CORE=0; actual-6/-11 exits, main/backgroundthreadstack, noSDKcallback, unchangedSIGTERM. Maindeployedunion161passed23.52s; independent spec+qualityAPPROVE; diffcheckpass.

Realdiagnostic run04 output `run_logs/m1_reference_validation/20260918_gpu7_8x32_04_rearmed_trace`, PID2896901, runid48eb6ec3-c575-464d-8606-373e24d6c9d6. Sameamp/GPU7/8×32/source/seed/thresholds, sleep.py2795762preserved. Commandform `PYTHONFAULTHANDLER=1 bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_04_rearmed_trace`.32steps17.936s; ENV_CLOSED→RUNTIME_REFS_RELEASED→APP_CLOSED→POST_CLEANUP→native139. This time validtrace: `Fatal Python error: Segmentation fault`, currentthread `Garbage-collecting`, `<no Python frame>`. Finalizer stillrejectscompletion/wrapper2. This localizes failure to interpreterGC, not the simulationstepbudget.

## Result / Follow-up / Refs

Instrumentationpass is notnativecrashfix. Baselinecc5fae3; candidate run.py04ab63ee5facb87cb7eddea11a76935eedb6bfacc0883556629f359c8fb8c387; runtime.py4010de570b57b14b5ca36bce906a9a9d9ec5bdd0db3eda9057c2b0faec86d024. Next second lifecycle hypothesis: detach AppLauncher STOP/PLAY subscriptions using supportedunsubscribe, restore only handler registrations stillownedbythatlauncher, preservefataldiagnostics, collectbeforepluginunload. No1600/1024; requiresnormalexit0 beforestartupacceptance.
