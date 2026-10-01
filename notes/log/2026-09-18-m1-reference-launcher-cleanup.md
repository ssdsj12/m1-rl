# Reference AppLauncher owner detach verification

## Purpose / Stage / Todo

Second lifecycle hypothesis for T306.6h.5, after [fatal diagnostics](2026-09-18-m1-reference-fatal-diagnostics.md) localizednative139 to post-close interpreterGC. Installed AppLauncher holds itself via two timeline subscriptions and SIGTERM boundmethod. This remains a hypothesis, not native rootcause proof.

## Method / Conditions / CPU Evidence

Standalone adapter only: saveprelaunchSIGTERM; afterenvclose/restore, unsubscribeSTOP/PLAY individually usinginstalledsupported API, clearattributes; restoreSIGTERM onlyifcurrenthandler.__self__ isthislauncher. Main release callbackfinally clears otherownerrefs evenifdetachfails. Errorsremainnonzero/noPOST_CLEANUP; nofatalhandler/SDKprivateinterface/control/thresholdchanges.

RED4failed48deselected→GREEN52passed3.71s. Actualmain fakewithCcallbackregistry doubles+realsignalidentity/weakrefs testsnormalandindividualunsubscribe failures; thirdpartyhandlerspreserved. Maindeployedunion164passed23.55s, diffcheckpass, spec+qualityAPPROVE. Baseline8b0605c. SHA256 run.py42c06b27fc656645c57105b3101f7cf484c9e8df0d1f07b7bf41df1d73dfb922; runtime.py315a15eb48f6bc67678f7fe305ef556037ac51368f554ceaee582577a2b1c4a3.

## Real8×32 / Result

PrecheckGPU7free8328MiB, reservationPID2795762unchanged. Freshamp/GPU7run output `run_logs/m1_reference_validation/20260918_gpu7_8x32_05_launcher_detach`, PID2921452, runid de7879c1-606d-4943-b600-d719106fbfe8. Commandform `PYTHONFAULTHANDLER=1 bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_05_launcher_detach`. Full32steps15.0275s,32prepare/IKcalls. ENV_CLOSED→LAUNCHER_OWNERS_DETACHED→RUNTIME_REFS_RELEASED→APP_CLOSED→POST_CLEANUP thenSIGSEGV139. Trace again says interpreter `Garbage-collecting`, `<no Python frame>`; wrapper2 and no startupacceptance. Configuration/source hashes forbaseline01/fix03/diagnostic04identical; sourcecontroller/physicsunchanged.

## Follow-up / Git Refs

Second lifecycle hypothesis is insufficient to resolve native139. Unit-verified ownercleanup retained, but no nativefix claim. Five real8×32runs comprise baseline, initialdiagnostics, ownerfix1, rearmeddiagnostics, launcherfix2; do not call thisfivefailedfixes or automaticrestart. No more identicalruns/unknowninterface-release guesses.

Next dependency T306.6h.5a: need nativeC/C++stack. No gdb/lldb/eu-stack/libSegFault found in /usr/bin,/usr/local/bin, miniconda3bin orenvbinpaths; no accessiblecore orprivilegedapport/dmesg. Asked user for permission to install anisolatedgdbtoolchain, leavingamp/Isaac/driver/reservationunchanged. Do notinstalluntilapproval. No8×1600/1024. Baseline8b0605c, candidatefeatureb60ca0f (onlyownedthreefiles). ReferenceandproductionAMEuntouched.
