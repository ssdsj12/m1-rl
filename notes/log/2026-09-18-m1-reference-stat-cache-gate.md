# M1 reference startup: Kit stat-cache lifetime gate

## Purpose / Stage / Todo

T306.6h.5b, child of native shutdown failure .5; depends on completed [native frame diagnosis .5a](2026-09-18-m1-reference-gdb-frames.md). Test one source-backed hypothesis: Kit's cached path-stat exceptions retain importlib/control frames and their PhysX owners beyond app/plugin shutdown.

This is the third lifecycle hypothesis, following adapter owner release and AppLauncher callback detach. The preceding diagnostic runs were not additional fix attempts. No fourth speculative fix if this fails.

## Method / Conditions

Only independent `tools/m1_reference_validation/` adapter: add startup `--/app/extensions/pathStatCacheEnabled=false`, leaving both renderer multi-GPU flags unchanged. Immediately after AppLauncher/fatal diagnostics, require actual carb setting false, loaded effective cache setting false, and actual importlib `_path_stat` not the SDK cached hook. Record hook module/qualname/codefilename and nonphysical configuration reason. Fail closed on inconsistency. Never reset private SDK cache, monkeypatch its hook, change installed SDK/amp packages, or alter controller/physics/rewards/thresholds.

CPU RED9failed49deselected0.41s: defaultflag missing, guard missing, main wiring missing. GREEN58passed3.95s, main independent deployed suite170passed23.78s; bash-n and diffcheck pass. Independent spec+quality APPROVE. Fresh real test amp/GPU7,8×32, same reference/version/configuration, preserving reservation2795762. Native0 plus external finalization required. No debugger in this acceptance run.

Candidate hashes: run.py d81b598f74d940b76f64ca5d77390c25c99ad3d8b46d3bdf8515949c8f36771a; runtime.py2cebcfaebb938043d2af1dbe4e3d403564acf49319d9a2ca9a51df1e2b56406c; run.sh9588480e6ad56ac1503026935318450303ffe341c065d9e8b9e0466cfe4d5700; tests65e2d6e895b347a77257b255ac4f70c2ced7ae6a3d592f39eec1a4b141024f12.

Run08 launched with `PYTHONFAULTHANDLER=1 bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_08_cacheoff`, log sibling.log. Precheck GPU7free8328MiB; reservation unchanged. PID3103166, runID513a9443-5330-4a9e-8bee-5d95c24abcf2. Full32steps/32prepare+IK in15.0904s. Actual setting=false, loaded effective setting=false, hook=_frozen_importlib_external._path_stat, SDKcachedhook=false. Thus the single-variable intervention actually applied.

After ENV_CLOSED/LAUNCHER_OWNERS_DETACHED/RUNTIME_REFS_RELEASED/APP_CLOSED/POST_CLEANUP, Python aborted with `PyThreadState_Get: the function must be called with the GIL held ... current Python thread state is NULL`, runtime state finalizing. Native134, wrapper2; finalreport correctly rejects completed/startup_passed/passed. This is not a native-exit fix:139->134 is only a changed failure manifestation.

Last diagnostic09 preserved exactly this candidate (no further fix), output `run_logs/m1_reference_validation/20260918_gpu7_8x32_09_cacheoff_gdb`, PID3112135, GDB shell0/nativeSIGABRT6=134 confirmed. C++stack: `Py_Exit(sts=0)` -> libc `exit`/exit handler -> CPython `list_dealloc` -> `PyThreadState_Get` with NULL threadstate -> fatal_error/abort. The callback's registering owner is not identified by this stack; do not invent a specific SDK module or claim every historical early training exit shares this cause. No live diagnostic child remains; reservation2795762 survives, GPU7returns15754used/8328free.

Read-only version check: amp Python3.10.21, isaacsim/isaacsim-kernel/isaacsim-app4.5.0.0, omniverse-kit106.5.0.162521. Installed kernel metadata explicitly requires that exact Kit version, so no established Kit version mismatch. IsaacLab45 clean v2.2.1 at0f00ca2b4, editable isaaclab0.45.9. No package/driver/SDK files changed.

## Result / Follow-up / Git refs

Hypothesis fails the required clean-exit gate. Three local lifecycle hypotheses have not solved shutdown; stop local patch accumulation and discuss lifecycle/SDK scope before another fix. Four-file cache-off candidate and hashes archived locally under isolated debug_tools/cacheoff_candidate and remotely under `/home/hexinkun/m1_debug_tools/gdb-jammy/cacheoff_candidate_20260918`; checksum check4/4OK. apply_patch reverted only this candidate back to b60ca0f. Original ownercleanup/fataldiagnostics/launcher-detach and external finalizer remain. Main independently confirmed remote exactdiff0 against b60ca0f, fourlocalhashesmatch, bash-n pass, and full restoredCPU suite164passed23.65s. No new accepted feature commit and no furtherIsaacrun afterrestoration. Source configurations for05 and07 have identical SHA2562badbdd3d2639470fb2e8ed35086f9fd67ba63154e99911bf7ddccae0a8aac55 and07sourcebinding37e6a965058e8187ab4bfa235981fab58ae23de256096f9b7cf16c4db639dd3c.

Only after startup cleanly passes may three8×1600 strict runs proceed, stopping at first failure. No1024 or10000 yet. [Branch](../todo/T306-m1-ame-long-train-stability.md),[plan](../../docs/superpowers/plans/2026-09-18-m1-reference-runtime.md).
