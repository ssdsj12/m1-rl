# M1 scale1024 post-cross-sync candidate19

Task T306.6h.6a.1a / approved Task4. FAILED atprepare247 after247completedsteps; no1024strict acceptance. Noautomaticrestart.

## Final failure and preserved evidence

22:53:57→23:03:29,onePID309168,wall9:31.29. Completedsteps0..246 (247total),thenprepare247raised:

```text
ValueError: Post-cross applicability failure before action override:
{'wave_gate': [523], 'nonzero_legs': [523]}
```

Stack:run.py139→runtime.py420→sync_bridge.py171→referencewrapper1372→sync_bridge.py166/110→post_cross_sync.py267. ThisisPythoncontractrejectionbeforeactionoverride,nottheoldnativePhysXshutdownfault. envclose/launcherownersdetached/runtime refsreleased/appclose/POST_CLEANUPallprinted. Actualnative1,wrapper2;reportcompleted=false,passed=false. finalizationerrorsincludeexited1/candidatebudgetmismatch/cleanupPID-budgetmismatchbecauseactualsteps247not1600. Do notreinterpret asnormalfullcompletion.

8sample+8syncchunks retained:7×32andone23stepchunk224..246. No`bindings_after.json`becauseworkfailedbeforeend-of-runbindingcapture. FrozenindependentCLIwithoriginal1024×1600budgetandbaseline18returnedactual3,accepted=false,firsterrorFileNotFoundErrorforbindings_after. Noartifactforgeryorcopiedbindingstoobtainapass. report/exception/partialchunksallpreserved.

ExternalwholeGPU677samplespeak11140MiB;compute562samplespeak11096MiB;GNUmaxRSS10,031,164KiB,swap0. Afterchildgone/GPU7free,mainreverifiedandstoppedonlym1scale19_monitor(PID309156)andm1scale19_process_monitor(PID309159).

23:05:14 restoredoriginal15GiBreservation underpriorauthority,onlyafterGPU7UUID/emptycompute/scriptSHA8a487ab7...freshchecks. tmux`m1_gpu7_reserve_20260918_after_scale19`,PID351307,actualcmd`python sleep.py`,cwd/home/hexinkun,exe/home/hexinkun/miniconda3/envs/m1/bin/python3.10,CUDA_VISIBLE_DEVICES7,CONDA_PREFIXm1,CONDA_DEFAULT_ENVm1. FreshGPUqueryshows351307/15744MiB. Thism1runtimeissolelytheoriginalreservation;simulationusedamp. Nootherjobsstopped.

## Main fresh timing witness

Initialrandomization6arraysandfirst32sample28non-timingfieldsbitwiseequalbaseline18. Mainalsoverifiedall28non-timingfieldsforenv523steps224..246exactlyequalbaseline. Atstep240phase10/wavetrue;241..245phase11/wavefalse/legs0;246phase-1/wavefalse/legs0. prepare243..246ready_count1,2,3,4;sample242..246qualifies5times,soattempt247wouldnewlyactivate. Baseline247thenhasphase0/wavetrue/legs.266336799,rootx1.4687233;actualcandidateerrornamescurrentwave/legs523. Env523wasinactiveatlastcompletedstep246;226otherenvsactivebythen. Thisisnotanongoing-syncwheelinstabilityat523.

Nochangehasbeenmadetofrozencore/replay/thresholds. Newchild.2willtracephase11→-1→0semanticreentryandfreshpreparevspriorobserveownership;newchild.1keeps18firstcrossingfailuresseparate.[Fullbaselineaudit](2026-09-18-m1-scale-baseline-behavior.md). CurrenttaskmovesbacktoCPUdiagnosis/design,notautoretry.

Belowishistoricallaunch/monitoringrecord,notcurrentRUNNINGstatus.

## Preconditions and identity

2026-09-18 22:53:57 +08:00, one launch after [baseline18](2026-09-18-m1-scale-baseline18.md) completed full1600/native0 and independent baseline-common audit passed. Baseline behavior615/1024 and53episode terminations remain negative evidence; not waived. No automatic restart or repeated attempt.

- Python `/home/hexinkun/miniconda3/envs/amp/bin/python`; physicalGPU7 UUID `GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e`.
- PID309168;run-ID `f665c6c2-423e-4420-ba0c-2fcedd626292`;tmux `m1scale19`, timewrapper panePID309162.
- Frozen source/CWD `/home/hexinkun/m1_debug_tools/scale1024_20260918/adapter`; freshdiff-qr0 againsttask3_accepted, no source changes.
- Newoutput `/data/hexinkun-m1-acceptance-20260918/20260918_gpu7_1024x1600_19_scale_sync`.
- Sidecars atsameprefix `.launch.log`,`.gpu.csv`,`.process.csv`; both1-second externalmonitors started before candidate. Sessions `m1scale19_monitor`, `m1scale19_process_monitor`.
- Root free14.182GiB,targetfree6673.63GiB;targetparentownedhexinkun0700;newoutput+allsidecars absent beforelaunch. GPU7noothercomputeprocess,4MiBbeforelaunch. No olddata moved by this launch.
- The original15GiBreservation remains paused for this task. Restore only after taskcompute is absent andGPU7 has no otherjob; no duplicate reservation during simulation.

```bash
ulimit -c 0
/usr/bin/time -v bash /home/hexinkun/m1_debug_tools/scale1024_20260918/adapter/run.sh \
  --num-envs 1024 --steps 1600 \
  --output /data/hexinkun-m1-acceptance-20260918/20260918_gpu7_1024x1600_19_scale_sync
```

Defaultcontroller-mode post-cross-sync; noresume. Fixedamp/cuda7/headless/multiGPUfalse/cacheoff/nativeaudit inherited from unmodifiedrun.sh. Shellwrapper has no retryloop. This is referencecontroller validation steps, not AME training iterations orpolicy-onlysuccess.

22:54:24 actual/procPID309168existswithfullampcommand,statuscreating_environment,0samples,582MiB. This is initialization, not completed physical verification. Never infer completion fromtmuxname orstatus alone.

## Completion gate

Wait for actual nativeexit and report without restarting. Require full1600 and normalcleanup, preserveall1024per-env failures, then independentpairedverifier:

```bash
/home/hexinkun/miniconda3/envs/amp/bin/python -B /home/hexinkun/m1_debug_tools/scale1024_20260918/adapter/sync_verdict.py \
  --num-envs 1024 --steps 1600 \
  --output /data/hexinkun-m1-acceptance-20260918/20260918_gpu7_1024x1600_19_scale_sync \
  --baseline /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_1024x1600_18_scale_baseline
```

CLIargumentnamesverifiedagainstfrozenparser;commandwasexecutedandreturned3forincompleteevidenceasdocumentedabove. Allsource/scene/randomization/activation-prefix/controlobserverreplay/tail799/full1024strictgatesunchanged. Noformalpromotion ifnegative; diagnosefirstfailurewithoutthresholdrelaxation ornewblindrun.

BaselineRef formal646f486;CurrentWorkRef isolatedscale task3_accepted atrepoHEAD5553e84,verifierSHA3930483e477e0a1c6faa15c3a66dea97a20289d8e78cec9d9f4e6ca708dc79c5. NoAMEruntime/action/rewardorSDKchange inthisrun. NextremainactualAME10000+learnedcross/avoidance.
