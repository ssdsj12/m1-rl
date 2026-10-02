# Reference adapter native-owner cleanup verification

## Purpose / Stage / Todo

T306.6h.5 normal-shutdown investigation. Test the source-backed hypothesis that adapter caller/closure references retain native owners after plugin unload. [Previous reproduction](2026-09-18-m1-reference-gpu7-faulttrace.md).

## Conditions / Change / CPU Verification

Only standalone run.py/runtime.py/tests change. Main initializes/clears its sink/env/sensor/wrapper/GPU/config refs and recorder holder. Cleanup persists CPU candidate, closes env, restoresIK, clears caller refs plus a consumable owner dictionary, clears helper locals, gc.collect while app alive, then app.close. Direct env/sink call arguments were found to retain objects on the CPython evaluation stack until cleanup returned; weakref/cycle tests required the consumable dict. No changes to finalizer/source/controller/GPU7/fast_shutdown=False.

TDD initial6failed; first callback version still5failed dueargument-stack owners; final45runtime tests pass2.34s. Main deployed union157passed21.83s, bash-n/gitdiffcheck pass, independent spec+quality APPROVE. SHA256 run.py a51fd0716a942d99a65157f86f7cf9b69c345f17eff22fa351bbfaecb693eecb; runtime.py e31f9a44869142b44326832c6887ec3c88805258ae1f7b3b18af8230b0ca2d03. Tests exercise cyclic weakrefs, partial init and report/envclose/restore failures; marker remains failclosed.

## Real8×32 Verification

`PYTHONFAULTHANDLER=1 bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_03_owner_release`.

Amp/GPU7, same source/seed/geometry/thresholds,15GB reservationPID2795762 untouched; precheck8328MiB free. PID2874242, runid bef85013-b41e-4977-b441-4bef6ab20bbc. Full32steps16.24s;32prepare/IKcalls. ENV_CLOSED→RUNTIME_REFS_RELEASED→APP_CLOSED→POST_CLEANUP→native139/wrapper2. Startup remainsfailed. No1024/1600.

## Conclusion / Follow-up

Adapter owner release is unit-verified but did NOT eliminate native crash; no claim this fixesIsaac. This is the first lifecycle-fix hypothesis tested, not three failedfixes (earlier runs were baseline+instrumentation). Source audit additionally finds AppLauncher retains itself via STOP/PLAY subscriptions and SIGTERM/SIGABRT/SIGSEGV handlers. Its SIGSEGV replacement interferes with initialPYTHONFAULTHANDLER. Next step is re-arm fatal diagnostics afterAppLauncher and collect a usable stack before another lifecycle change. Avoid private/shared PhysX interface releases (SDK already manages those), forcedexit, upgrades or repeated autonomousrestarts.

## Git Refs

Baseline ddad702; candidate owned three-file diff above. Reference and productionAME unchanged. Last verified scopeCPU157only; no clean native physical exit.
