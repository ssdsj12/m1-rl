# M1 native exit-owner diagnosis — approved route A

## Scope and decision

User approved route A on 2026-09-18: identify the native exit callback in one isolated amp/GPU7 diagnostic before selecting a minimal repair. This is a diagnostic design, not approval for a speculative SDK patch, package upgrade, Kit-host rewrite, or long training.

Preserve `/home/hexinkun/m1` read-only, the production adapter at `b60ca0f`, all existing run artifacts, and GPU7 reservation PID 2795762 (`python sleep.py`). Never attach to, signal, or change that reservation. Use only `/home/hexinkun/miniconda3/envs/amp/bin/python` and physical GPU7 UUID `GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e`.

## Evidence and alternatives

Baseline captures 06/07 fault during late Python GC of PhysX tensor owners. Cache-off diagnostic 09 instead reaches `Py_Exit(0)`, then libc `exit` calls a native callback which releases a Python list with a NULL thread state. It exits 134, not successfully. Both manifestations remain failures.

The matching host libc Build-ID is `490fef8403240c91833978d494d39e537409b92e`. The recorded return PC is libc base + `0x45495`, immediately after the `ef_cxa` callback instruction at +`0x45493`. Existing fatal-time registers cannot recover that callback. No specific registering library has been proven.

Bounded integrity checks found 22 selected installed files matching their RECORD SHA-256 and size. This does not establish full environment or ABI correctness, but does not support reinstalling on the assumption that these files were overwritten.

Alternatives considered: (A) capture callback registration/invocation and target the actual owner; (B) independent Kit-host extension runner, requiring new initialization and sampling equivalence; (C) a vendor-supported backport or a complete compatible stack in a separate prefix. A is selected because it changes no SDK or production behavior and supplies evidence needed to choose B/C if required.

## Components and data flow

1. A separate opt-in GDB helper records `__cxa_atexit` registration triples `(callback, arg, dso_handle)` and caller PCs using read-only register/memory access. Records are bounded and overflow is explicit, never silently called complete.
2. Derive libc load base from the current inferior, validate the exact Build-ID and expected call bytes, and install invocation/return breakpoints at offsets `0x45493`/`0x45495`. Never reuse the previous ASLR address. On invocation record callback, argument, status, thread, owning shared object, and recent registration matches. Track nested invocations per thread, not just a global last callback.
3. On native fatal signal preserve the current capture harness's backtrace, mappings, true inferior exit status, and the unreturned invocation(s). Do not call target Python/C functions, mutate target values, suppress signals, skip callbacks, or force process success. Instrumentation can alter timing and is diagnostic only.
4. Use the archived cache-off candidate in a separate complete diagnostic directory to reproduce 09 without replacing any production adapter file. Preserve its existing verified source/settings and copied support modules; record checksums and any diagnostic-only path differences. Do not change physical parameters, rewards, controller, thresholds, or finalization semantics.

## Tests and one-run protocol

Before Isaac: failing CPU tests then implementation for registration matching, nested/threaded callbacks, callback return, bounded overflow, unmatched records, mismatch refusal, and native signal/exit accounting. Include a minimal compiled native fixture whose registered callback has a known owner and aborts; no GPU is needed for fixture tests. Keep existing diagnostic exit/frame tests passing.

Perform fresh resource/process and source hash checks. Launch one own child in amp, physical GPU7, 8 environments × 32 steps, using existing isolated GDB. No resume, supervisor, retries, or parallel Isaac process. Record GDB shell status separately from inferior status. On instrumentation error mark incomplete; if a diagnostic child remains alive, report and handle only that positively identified child, never the reservation.

The diagnostic succeeds only if it proves which invoked callback did not return and either matches registration caller/DSO or explicitly explains why ownership remains unresolved. A debugger exit code of 0 is not simulation success. If this capture is incomplete, stop and inspect evidence before any further run.

## Repair selection and acceptance

After capture, describe the actual owner, causal evidence, and the smallest supported, reversible repair. No implementation-specific patch is pre-approved by this diagnostic spec. Any required ABI/package/environment migration is a separate design decision; do not swap a single `libcarb` or upgrade in place.

Normal clean exit remains mandatory: exact requested steps, close markers, native exit 0, and external finalizer acceptance, without `os._exit`, fast shutdown, signal masking, or automatic restart. Then three independent 8×1600 strict runs must all pass before 1024×32 capacity and 1024×1600 validation. These are reference-controller tests, not learned-policy success or a completed 10000-iteration training run.

## Rollback and recordkeeping

Production/SDK files are untouched, so rollback is to stop using the isolated diagnostic directory. Preserve its logs as evidence. Update T306.6h.5c, dashboard and per-verification log with actual results; retain baseline `b60ca0f` as the last accepted adapter feature ref.
