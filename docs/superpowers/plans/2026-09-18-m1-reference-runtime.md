# M1 reference controller runtime implementation plan

> Execute with subagent-driven-development and test-driven-development; spec review then quality review per task. Approved scope: [design](../specs/2026-09-18-m1-reference-controller-validation-design.md).

## Boundaries

Only new `tools/m1_reference_validation/` files in m1_rl. Reference `/home/hexinkun/m1` stays read-only. Runtime amp, physical GPU4, explicit ContactFreePlay configuration + reference M1RslRlEnvWrapper, zero16column residuals, no runner/checkpoint/restart. No production reward or controller tuning. Provenance guard must pass before simulation. Main owns deployment/notes.

## Task 3: Pure first-episode diagnostic accumulator

Files: `metrics.py`, `tests/test_metrics.py`; numpy dependency, no Isaac imports. Inputs are copied pre-reset arrays for ALL environments, never defaults for missing attributes. Consecutive step indices start at zero.

- [ ] RED: missing/nonfinite/wrong-shaped data rejected; firstfailure survives later good samples; goal followed by fall fails; timeout fails; missing overbar/touchdown/recovery samples fail; partial steps incomplete; all environments required; strict clearance uses0.0959radius; rearwheelpass uses rear edge+radius; no JSON NaN/Inf.
- [ ] Frozen thresholds: barcenter(0.85,-0.20),size(0.06,0.16,0.06),radius0.0959,margin0.005,force1N,phase11,rootx1.5,tilt0.45,heighttarget0.57/recoverystart1.1/tolerance0.04,actiondelta2.0,wheelspeedspread0.08. Preserve reference-radius0.095 clearance separately.
- [ ] Accumulate perenv firstepisode; continue aftergoal untilbudget/firsttermination. Required wheelorder FAR,FBL,RAR,RBL; crossing FAR/RAR. Require prelift before frontedge-radius, overbar sample withz>=0.1609+genericcontact<=1N, rear edge+radius pass, subsequentgroundcontact+heightnearwheelradius. Retain originalhelper clearance flags independently.
- [ ] Track initial/max/finalroot,phase,maxtilt,finite state,wheelheights,prelift/overbar/passed/touchdown,ownbarforce,nonwheelcollision evidence,failure/reset/timeoutstep,samplecounts,recoverymeanerror+lastactiveerror,waveactiondelta/activity,nonwavezero check, signedwheelvelocitycount/min/max/mean. Perenv front/rear requiredlift0.13/0.14, never cross-env aggregation.
- [ ] completed requiresfullconsecutivebudget+normalprocessfinalization; passed additionallyallperenvcriteria.32stepsmokecompletion isnotbehaviorpass. No missingcontactzero-fill.
- [ ] GREEN; spec review; quality review; mainrerun.

## Task 4: Source-bound adapter, configuration, recorder, process

Files: `run.py`, `runtime.py`, `run.sh`, `tests/test_runtime_contract.py`. LazyIsaacimports enableCPUtests.

- [ ] RED: rejectnumenvsoutside8/1024,stepsoutside32/1600,mixedsourcemodules,missingcompletion; fakecfgallowlistedchangesonly; fakerecorderpre-resetforwarding/noexport.
- [ ] Source binding: reference Go2Pvcnn anditsrsl_rl beforeeditablepaths. Directcfg/wrapperimports afterAppLauncher. Assertactual modulefiles forgo2_pvcnn,extension,agent,rsl_rl belongreference. Hashsources+assets; savemanifestinterpreter/config/seed/diffbeforesteps.
- [ ] Config changesonly:8/1024envs,terrain1row×Ncols,size8×8,flat,maxlevel0,cuda:4,verifiedportableoverlay,crossing_success=None,episodelength>=(steps+1)*dt,recorderEXPORT_NONE. Retain source startupmass/friction,commands,gains/controlflags. Record sampledPhysXmasses/materials,origins,initialpose.
- [ ] RecorderTerm.record_post_step afterphysics/termination/reward BEFOREreset; return(None,None),RecorderManagerBaseCfg subclass,DatasetExportMode.EXPORT_NONE,export_in_record_pre_resetFalse. Bindsinkafterwrapperconstructorreset. Resolveexactnamedwheel/body/joints. Capture raw/prepared/gate/phase/IK; missingfailclosed. Persistperstep+summary.
- [ ] Preserve generic wheel net force and original crossbar failure independently from actual filtered bar force. semantic_contact_small is a four-wheel sensor with matrix[N,4,Nbars,3]. Map own bar by semantic_filter_paths row/column, not sorted index==env (>99 sorting issue).
- [ ] Add diagnostic-only M1SemanticGlobalContactSensor subclass overriding CONTACT_BODY_NAMES to the17 verified bodies; independent scene field, no source/controller/termination changes. Force its update(dt,force_recompute=True) each physics substep; override _update_buffers_impl to retain perbody own-bar peak, because last-frame-only sampling misses transient collisions. Recorder pre-step clears peak; post-step consumes it before reset. No track_pose/air_time/contact_points/history. Tests cover lexicographic filter order, perenv ownership, nonwheel contacts and transient peak retention. Verify actual17body view/contact-report API before sampling.1024 densematrix alone is204MiB, and four samples/controlstep adds cost.
- [ ] Scene assertions:Nuniqueorigins,minspacing8m,Nmatchingbarprims+geometry,correctcontactfilters,scannerownbar/noneighborpatchcontamination. Verify spawnedstageZ/meters1 andinitialheight. Missingproofblocksbehavioracceptance.
- [ ] Fresh exclusiveoutputdirectory; startedmanifest; exception-safecloseenv/app; completiononlyafterfullsteps+reports+cleanup; externalexitcheckrequiresmarker+summary. No restarts. Progress32steps; thresholds frozenbeforefirststep. JSONstrict.
- [ ] run.sh mirrorsverifiedampGPU4environment: referencePYTHONPATH+IsaacLab45,PYTHONDONTWRITEBYTECODE1,existingNVIDIAEGLICD,renderer multiGpuenabled/autoEnablefalse,unsetCUDA_VISIBLE_DEVICES,cuda:4. Do notsource traininglauncher. No installations.
- [ ] GREENCPUtests; specreviewthenqualityreview; allnewtests+88referencebaseline.

## Task 5: Sequential physical validation

- [ ] Real8×32startup: correctsources,wrapper/IKcalled,8isolated,validcontacts,completebudget+cleanclose. Notbehaviorpass.
- [ ] Onfailure collectexactfirstexception/stall; minimaladapterfix withRED/GREEN/review thenexplicitnewrunID. No silentrepeats/parametersweeps.
- [ ] Threeindependent8×1600runs seed20260711,strict8/8each. Stoponfirstfailure; retainfirstfailuretrace anddiagnosebeforecontrollerchanges. Neverrelaxthresholds.
- [ ] Onlyafterthreepasses1024×32capacitythen1024×1600strictall1024. RecordGPU4peakmemory,PID,steps,timing,randomization. No otherGPU/scale/restart.
- [ ] Syncdesignstatus,tododashboard,T306.6h,perverificationlogs/index; onlyexactownedfilescommitted. Finaldistinguishescode/runtime/behavior andstates1024notrunifgatered.
