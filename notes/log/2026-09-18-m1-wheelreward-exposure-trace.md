# M1 wheel reward fixed-small exposure trace

## Purpose / Stage / Related Todo

Diagnose why the final pilot policy stops before the0.10m box despite nonzero new training rewards. This is an observational diagnostic under[T306.6g.1](../todo/T306-m1-ame-long-train-stability.md),not a new reward design or another training run.

## Method / Contract

One-off[trace script](../../run_logs/m1_reward_exposure_trace.py) executes the unchanged fixedsmall evaluator withrunpy. sys.setprofile observes actualhelperRETURN beforeauto-reset and only theprogress wrapper call chain; theclimb wrapper is excluded. It copies small tensors,never frame/terrain/env references. EpisodeMetrics oldalive includes theterminal reward,then itscloned nextalive excludesreset episodes. Everymetricsupdate must correspond toexactlyone capture. Exception-unwindreturnevents are excluded by normalRETURN opcode in thefixedampCPython3.10runtime; originalexceptions propagate andhook iscleared.

Reportfirst-episodeenvironmentstepsN_alive,four-wheel denominator4N_alive,andconditionalwheel opportunitiesalive&enabled&active_wheel&needs_lift separately. Capture semantic1/validpatch/semantic2veto,actual root/wheel forward andworld/relativeup motion,rawhelperreward beforeweight/dt,plus100-step windows. Rawlabels at invalidpoints are not trustedterrain observations. Rootx isworldx,not relative environmentprogress. Fixedsmall exposure cannot establish training-distribution opportunityfrequency; profiling overhead invalidates performance comparisons.

## Test / Review Evidence

Initial missing-scriptRED8fail;helper/metrics exception-propagation boundaryRED2fail. Final main-agent ampCPU command: `env -u PYTHONPATH /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q run_logs/test_m1_reward_exposure_trace.py Go2Pvcnn/tests/test_m1_obstacle_rewards.py Go2Pvcnn/tests/test_m1_evaluation_metrics.py` yields44passed in3.28s (12new,32existing). Implementerpy_compilepasses. Independent spec andqualityreviewsPASS. ScriptSHA256`47a914c60e89e0e5c9c23d19c8cc631be3b7db9308ebfce648515515da86d4fd`,local/remote identical. No production filechanged.

## Actual Runtime

amp/physicalGPU4,8env×500steps,seed42,small0.10m box,samefinal[model119](../../logs/rsl_rl/m1_cross_large_complex_ame/2026-09-18_10-52-23/740f07e/model_119.pt),sameevalconfig. OnlyTRAIN_ENTRYPOINTpoints tothetrace. One tmuxm1wheel_exposure_small,unique[log](../../run_logs/m1_wheel_reward_exposure_small120.log),launchedafterallotherIsaacprocessesexit.

```bash
env EVAL_SCENARIO=small NUM_ENVS=8 MAX_ITERATIONS=500 DEVICE=cuda:4 TRAIN_ENTRYPOINT=run_logs/m1_reward_exposure_trace.py CHECKPOINT=/home/hexinkun/m1_rl/logs/rsl_rl/m1_cross_large_complex_ame/2026-09-18_10-52-23/740f07e/model_119.pt VALIDATION_LOG=run_logs/m1_wheel_reward_exposure_small120.log bash Go2Pvcnn/scripts/run_m1_validation.sh
```

## Result / Conclusion / Follow-up

Attempt1PID2182605 completedtheunderlying500stepevaluation andexited0. ItsM1_EVALUATIONdictionary exactlymatches theunprofiledsmallbaseline:crossing0/8,forward1.0745615959m,lateral0.0764395893m,allcollision/failure/invalidrates0. HoweverM1_REWARD_EXPOSUREanditsCOMPLETEareabsent,so thetraceacceptanceFAILS despitewrapperexit0. Noexposureconclusioncanbedrawnfromthisattempt.

Theprintafterrunpy didnotexecuteaftertheevaluator'sfinallyenv.close()/launcher.app.close(). InstalledSimulationApp.close lines561..617includesnativeapp.shutdown/pluginunloadanddisablesloggingbeforethatshutdown. Thisisafterall500evaluationsteps,notprematuretrainingexit. Movingone-timeflushintotheactualEpisodeMetrics.summarynormalRETURNhook was a minimaldiagnostic-onlyfixwithSystemExit-after-summaryregression. ItpassesCPUtests,butisNOTsufficienttoexplainorfixeliminatedruntimecapture:thev2resultbelowalsolacksthetrace.

## Second Attempt / Remaining Evidence Gap

[v2runtime](../../run_logs/m1_wheel_reward_exposure_small120_v2.log),PID2195941observedlivewith`amp/bin/python run_logs/m1_reward_exposure_trace.py --num_envs8 --max_iterations500`,againcompletedtheevaluationwithanexactbaseline-matchdictionaryandexit0,butnotraceJSON/traceCOMPLETE. ThissecondtraceacceptancealsoFAILS. TheflushrevisionisSHA256`8f3e5b653f20921416dfb00e4798abf8c0ed415d7065ad78de5e236827c96e19`;main-agentregression47passed in3.31s;independentreviewPASS. Do notmisrepresenttheseCPUtestsasevidenceofruntimehookcapture.

Read-onlychecksconfirmcorrectscriptversionbeforelaunch,nosymlink,absolutehelper/wrapper/metricsco_filenamesmatchingexpectedpaths,normalpycache,andnoTRAIN_ENTRYPOINToverride. SearchinstalledPythonstartupsourcefoundnoguaranteedhookclearingcall;native/Isaacprofile-overwriteisatestablehypothesis,notaprovenrootcause. Beforeanother500steptrace,addatemporarytransparentmetrics-constructorprobeinthisone-offrunner,reportlivehookstateafterbootstrap,thenperformonly1step. Productionreward/evaluator/configremainsunchanged. Both500steprunsfinishednormally;their missingdiagnosticdoesnotshowprematuretrainingexit.

## Git Refs

Baseline4b5251f+priorwork,candidate740f07e+uncommittedapprovedrewardimplementation. Onlytwoone-offrun_logsPythonfiles wereaddedforthistrace;productionreward/config/evaluator/scannerhasheswererecordedbeforelaunchforunchangedchecks.
