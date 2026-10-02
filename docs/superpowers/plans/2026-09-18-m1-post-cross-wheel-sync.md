# M1 Post-Cross Wheel Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development for implementation and independent spec then quality review. User approved the written design and explicitly requested implementation; continue through the authorized single physical test without asking again.

**Goal:** Build and test one isolated post-cross-only wheel synchronization candidate against frozen strict metrics.

**Architecture:** Preserve original reference preparation once per step; independently observe pre-reset samples and override only eligible wheel columns after ordered crossing and stable touchdown. A pure CPU-testable tensor state machine, thin simulator bridge, and separate fail-closed offline verdict keep controller state, physics lifecycle, and acceptance separated.

**Tech Stack:** amp Python3.10, PyTorch/NumPy/pytest, installed IsaacLab45, physicalGPU7.

## Workspace / immutable boundaries

- Approved spec: `docs/superpowers/specs/2026-09-18-m1-post-cross-wheel-sync-design.md`, designcommit6c53e32.
- Frozen baseline: `/home/hexinkun/m1_rl/tools/m1_reference_validation`, clean againsta86cbf5.
- Local isolated copy: `C:/Users/xk/Documents/project/m1_reference_validation_stage/post_cross_sync/adapter`.
- Remote isolated copy: `/home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter`.
- Output: `/home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_14_post_cross_sync` and sameprefix.log.
- Do not change reference/SDK/formalAME/formaladapter/metrics.py/provenance.py/clone_evidence.py/run.sh or cfg gain. No automatic retry or second parameter choice. User approved an isolated copy, not a promotion.

## Task 1: isolated candidate, TDD and CPU evidence

Files created: `post_cross_sync.py` (tensor state/observer), `sync_bridge.py` (live contract/wrapper/data writing), `sync_verdict.py` (offline CLI), `tests/test_post_cross_sync.py`, `tests/test_sync_bridge.py`, `tests/test_sync_verdict.py`. Modify only candidate `run.py` and `runtime.py` for optional wiring. Existing tests remain.

- [x] Confirm copied baseline fullsuite212passes. Freeze file manifest; no dependency installation.
- [x] Write core tests before core implementation; capture failing output. Include independent ordered events, root==1.15rejection, five-sample debounce, initialphase-1, phase11transient, terminationpriority, stale/duplicatepacket, partialreset, cloneparity, outputhold/rate/bias/filter.

Core API fixed for independent implementation:

```python
sync = PostCrossSync(num_envs=8)  # CPU torch state; no Isaac imports
final, diagnostic = sync.prepare(step, original_actions, current)
# current: wheel_velocity[n,4], root_pos[n,3], wave_gate[n],
# drive_allowed[n], episode_length[n]; actions are raw-scaled reference outputs.
packet = {**sample, 'episode_id': sync.episode_id.clone(),
          'env_id': torch.arange(8), 'applied_actions': actual_actions}
sync.observe(step, packet)  # pre-reset, deep copies; does not read metrics
sync.reset(env_ids)        # one explicit notification per actual reset
```

The state machine exposes `episode_id`, `active`, `activation_step`, `events`, `last_observed_step`. `prepare` requires contiguous global calls and previous-step observation except first/reset; it checks episode_length decrease without reset. `observe` requires global contiguous steps and env/episode identity; reset invalidates pending/previous applied and only clears named environments. `original_actions` is n×16; inactive rows bitwise unchanged and all leg columns unchanged. `current` is cloned before use. Packet has root_pos/gravity/wheel_pos/wheel_contact_force/wheel_bar_force_peak/nonwheel_bar_force_peak/reference_collision/wave_gate/phase/prepared_actions/terminated/timeout/wheel_velocity/applied_actions.

Every diagnostic is a CPU tensor snapshot with env-major dimensions: `episode_id`, `active`, `activation_step`, `events[n,2,4]`, `ready_count`, `gate_reasons` bitmask, `support_ok`, `original_actions[n,16]`, `final_actions[n,16]`, `velocity[n,4]`, `filtered_velocity[n,4]`, `error[n,4]`, `bias[n,4]`, `slew_limited[n,4]`, `bias_limited[n]`, `physical_limited[n,4]`, `hold[n]`, `integral_paused[n]`. Bridge adds `step`, `episode_length`, currentroot/wave/drive flags, actual and processed wheel targets.

Approved math (unchanged):

```python
alpha = 1.0 - math.exp(-0.02 / 0.20)
vf = vf + alpha * (v - vf)
error = vf.mean(-1, keepdim=True) - vf
raw_bias = bias + 0.5 * 0.02 * error
centered = raw_bias - raw_bias.mean(-1, keepdim=True)
projected = centered / centered.abs().amax(-1, keepdim=True).clamp_min(1.0)
desired = torch.tensor([1.0, 1.0, 1.4, 1.4]) + projected
output = previous_output + (desired - previous_output).clamp(-0.02, 0.02)
```

Apply projected update only for active support-valid environments without previous hold/anywheel-limit; otherwise bias unchanged. New activation initializes vf from currentv and holds previous actualpacket wheelaction exactly; no integration firststep. Active originalwave/leg/non-drive/root≤1.15 invalidates run. Finite checks fail closed. Implementation retains nativeclose, does not generate process signals.

- [x] Run core RED, implement only provenmissing behavior, run GREEN; unitplantzero/one-sampledelay withfixed disturbance must converge before anyIsaac. Do not claim real stability from it.
- [x] Write bridge tests against real purecore with fake environment boundary only; RED before wiring. Verify scale/defaultoffset/jointorder/20limit/damping30, sourcecfg values, oneoriginalprepare, exact inactive/legparity, onepre-resetrecord, callbackreset and donefallback idempotence. Partialconstruction must release newowners viaexistingholder.
- [x] Implement bridge with `make_sync_wrapper(measured_type)` returning subclass; instantiate normally then `bind_post_cross(output,sink)` after livecontract validated. Modify RuntimeSink with `sync_observer=None` callback invoked on compactpre-reset sample beforeflush; recorder postreset calls observer reset when bound. DefaultNone preserves212tests. Existing cleanup clears holder/wrapper; no newglobalowners.
- [x] Wire run.py only afterAppLauncher import path: newmetadata/filehashes, newwrappertype, binding, sink observer; flush sidecar afterloop. Retain originalcounters/metrics/config/nativefinalizer. Mirror candidate name/config inprovenance andconfiguration; do notmutatecfg.
- [x] Write offlineverdictnegative tests first: missingchunks/fields, duplicate/outoforderstep, wrongshape/episode, wrongactualvsfinal, changedlegs/inactiverows, neveractiveenv, jump>0.02, tailRMSfail, originalstrictfalse, source/randomization/prefix mismatch allreject.
- [x] Implement `evaluate(output, baseline)` returningaccepted/errors/per_env; CLIwritesnew sync_verdict.json andexit0onlyacceptedotherwise3. Load exactly1600samples and sidecarsteps; noIsaacimports. Preserve report/nativeexit. Checkoriginalstrict8/8, runtime/config/source/initialrandomizationparity excludingexplicitnewlabel, all preactivation fields compared to run12 with maxabsdiff summaries; unexplainedprefixdifference rejects. Validate per-env tail799 differences and ratebound, biasbounds/zero-sum, eventactivation and units. Invalidinput returnsstructuredfailure, nevertraceback-onlysuccess.

CPU command for all phases:

```bash
cd /home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 \
LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin \
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests
```

- [x] Run12/run13offlinegate replay: run12 firstactions249,253,248,251,245,248,248,247; run13firstepisodeenv1/2/5neverready. Keepdataread-only. Fullsuiteandbashsyntaxpass.
- [x] Independent spec review of fullcandidate, fix/reviewloop; onlythenindependentqualityreview, fix/reviewloop. Snapshot candidatefilehashes. Noformalfeaturecommit/promotion; hashes providecandidateidentity.

## Task 2: single physical test and complete evidence

- [x] RecheckGPU7UUID/resource/PID. Originalreservation canstayifmemoryfits; onlystopverifiedauthorizedreservationifneeded, restoreaftercomputeends. Nootherprocesssignals.
- [x] Launch exactlyonce, then inspectprogresswithboundednonblockingpolls:

```bash
ulimit -c 0
bash /home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter/run.sh \
  --num-envs 8 --steps 1600 \
  --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_14_post_cross_sync \
  > /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_14_post_cross_sync.log 2>&1
```

- [x] Verifyrealprocessnativeexit, all1600/6400sensorupdates, cleanupmarkers, report and sidecars; execute separateverdict:

```bash
/home/hexinkun/miniconda3/envs/amp/bin/python /home/hexinkun/m1_debug_tools/post_cross_sync_20260918/adapter/sync_verdict.py \
  --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_14_post_cross_sync \
  --baseline /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x1600_12_normal_clone
```

- [x] Reportactualstrict8/8orfailedgates, activationsteps, target/actualRMS, wheelmeans,bias/saturation, prefixparity; iffailedretainandstop,noKi/τrerun. Do notpromisephysicalsuccessbeforeevidence.
- [x] Updateplancheckboxes/specstatus, notes/todo.md, notes/todo/T306-m1-ame-long-train-stability.md, notes/log/index.md and oneimplementation/physicaltestlog. Confirmformaladapterunchanged; artifactshashesretained. No1024/10000/policy-onlyclaim.

## Execution outcome

All373 CPU tests passed (74.64s); SPEC and code-quality reviews passed after independent verifier replay and strict float rounding corrections. Unique run14 completed8×1600,6400physical updates, strict8/8, native/wrapper/verdict0, zero resets/restarts. Preactivation physical/action prefixes match baseline bitwise. Each full-episode four-wheel mean-speed spread .01966..03224rad/s is below.08; all per-env tail target delta RMS below.00046. The 15GiB reservation stayed alive throughout. Formaladapter/SDK/AME unchanged. See [complete evidence and residual limits](../../../notes/log/2026-09-18-m1-post-cross-sync-implementation.md).
