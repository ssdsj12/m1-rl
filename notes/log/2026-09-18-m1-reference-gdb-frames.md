# M1 native teardown: retained-frame diagnosis

## Purpose / Stage / Todo

T306.6h.5a, continuation of [native capture 06](2026-09-18-m1-reference-gdb-capture.md). Native139 occurs after full8×32 and normal appclose markers; the first stack identifies PhysX tensor destruction underneath repeated CPython frame_dealloc calls. Need identify retained frame files/functions before selecting another fix.

## Procedure / Conditions

Only isolated debug tools changed. Capture reads CPython3.10 frame/code/compact-ASCII structures with GDB read_memory, without executing target functions or inspecting arbitrary local values. Limit200 native frames,4096 bytes/string; retain native tail20 and GC/finalization callers. Unreadable/non-ASCII fields report errors rather than fake names. f_lineno0 is explicitly invalid; co_firstlineno is not a reconstructed execution line. Original native-exit accounting is unchanged.

RED2 failures for missing helpers/metadata -> GREEN6 tests15.891s. Main independent rerun6PASS15.853s. New real amp CPU process keeps its own frame and is observed at frame_dealloc; filename/name/firstline/GC callers verified, non-ASCII filename rejected fieldwise. Original exit0/7, SIGSEGV139, ABRT134 and SIGSTOP-incomplete checks remain. Read-only review APPROVE. Capture SHA2565c4dea10eda8356497bc9854a281d735d58c7df75a1924d84d383dd392af79ad; test0831213263ba5721a6af914728a869361a95d4f948faf57312344a1395571639.

## Independent CPU mechanism evidence

Installed `omni/kernel/py/omni/ext/_impl/stat_cache.py` SHA256d09905d34ad52577c95f997d1f69fa152b3b3d71dc7e8570e777842ef064cd6b caches Exception objects and reraises them without dropping traceback. A CPU-only probe loads that real file with stub extension settings/Kit modules, not Isaac/torch. After a caught missing-path exception, deleting a weakref-able owner and collecting GC leaves owner alive; real reset_stat_cache plus GC releases it and cache size1->0. Main independent rerun confirms all assertions. This is a candidate mechanism, not yet actual-crash attribution.

Reproduce: `/home/hexinkun/miniconda3/envs/amp/bin/python -B /home/hexinkun/m1_debug_tools/gdb-jammy/probe_stat_cache_retention.py`. Script SHA2562e52a4931d6c3827ad63133ace084ee7d99adafbb020e36932f48ab87d823877. No SDK files/bytecode changed. reset_stat_cache lives in private `_impl`, not a public cleanup API. Installed ext_settings.py34–36 reads startup setting `/app/extensions/pathStatCacheEnabled` with lru_cache; disabling midway cannot reliably undo an installed hook. No runtime setting changed yet.

## Real run / Result

Fresh output `run_logs/m1_reference_validation/20260918_gpu7_8x32_07_gdb_frames`, same amp/GPU7/8×32 and production adapter b60ca0f. Reservation2795762 still15744MiB; GPU7 precheck15754MiB used/8328MiB free. PID3073066, runID7c6946b3-4bb4-47fe-bbb7-bf6c0aa2da2b. Full32steps/32prepare+IK in44.0597s, all close markers, then native139. GDB exit0 separately (exec2897), no automatic retry or acceptance finalizer. Own child ended.

First fatal metadata is complete:97native frames,13Python frame_dealloc records,0read errors. Python chain: adapter step_once -> reference wrapper step -> instrumented _prepare_actions -> reference _prepare_actions -> torch.functional.einsum -> importlib find/load/spec -> _path_isfile -> _path_is_mode_type. Native bottom OSError_clear -> delete_garbage -> gc_collect_main -> Py_FinalizeEx. Installed torch/functional.py368 lazy-imports torch.backends.opt_einsum in einsum; importlib/_bootstrap_external.py153 calls _path_stat and154 catches OSError.

This matches the stat-cache mechanism closely. Remaining attribution limit: the actual OSError was not directly matched to a _stat_cache entry; _os_stat_cached itself is not in the frame_dealloc list (GC order is a possible explanation, not proof). Independent read-only audit approves exactly one variable cache-off test. Add only launch setting pathStatCacheEnabled=false plus fail-closed verification/evidence of effective setting and real importlib hook identity. Do not call private reset API, change torch/controller/SDK, or relax thresholds. This is the third source-backed lifecycle hypothesis; if verified-cache-off stillcrashes, stop adding speculative fixes and revisit architecture.

## Follow-up / Git refs

Baseline and production candidate b60ca0f unchanged. Only new isolated debug scripts. After stack matching, choose a minimal source-backed lifecycle correction or report remaining evidence gap. No1600/1024/10000 runs before the startup gate. [Branch](../todo/T306-m1-ame-long-train-stability.md), [plan](../../docs/superpowers/plans/2026-09-18-m1-reference-runtime.md).
