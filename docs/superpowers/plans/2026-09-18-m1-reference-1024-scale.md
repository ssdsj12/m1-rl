# M1 Reference1024 Scale Implementation Plan

> **For agentic workers:** Use subagent-driven-development with fresh bounded implementer and separate spec then quality review per task. User requested continuous execution; no repeated execution-choice question. TDD applies to all behavior changes. No physical task until CPU/review gates pass.

**Goal:** Verify the unchanged post-cross controller at1024environments with correct compact layout and independent full-denominator evidence.

**Architecture:** Branch from byte-identically promoted8-env adapter into an isolated filesystem candidate, leaving formal and frozen8-env copy untouched. Add construction-time deterministic terrain mapping and explicit runtime modes; generalize offline verifier budgets without importing control implementation. Preserve core/bridge/metrics/native finalizer and SDK.

**Tech Stack:** ampPython3.10,NumPy,pytest,Torch/IsaacLab45 runtime,SSH4090.

Design:[1024scale](../specs/2026-09-18-m1-reference-1024-scale-design.md), independent design reviewPASS. Known memory/geometry audit:[readiness](../../../notes/log/2026-09-18-m1-1024-readiness-audit.md).

## Paths and boundaries

- Local frozen `C:/Users/xk/Documents/project/m1_reference_validation_stage/post_cross_sync/adapter`.
- New local scale `C:/Users/xk/Documents/project/m1_reference_validation_stage/scale1024/adapter`.
- New remote scale `/home/hexinkun/m1_debug_tools/scale1024_20260918/adapter`.
- Formal `/home/hexinkun/m1_rl/tools/m1_reference_validation` remains at the reviewed promotion until1024 acceptance.
- Never alter the reference `/home/hexinkun/m1`, SDK, old artifacts or unrelated dirty work. No new Git branch needed for the already approved isolated-copy workflow. Useapply_patch for local edits andSCP for synchronization.
- Fixed immutable sources:post_cross_sync.py18aeb0c7, sync_bridge.py817ed035, metrics.py a9487322, clone_evidence.py eb35f3e, provenance.py e065452f, run.sh9588480e. No mutations to cleanup_run/finalize/controller math.

## Task0: complete prior promotion and create isolation

- [x] Require373formalCPUtests plus spec andqualityPASS; main agent commitonly8approvedpaths with clean index precheck. Record exactcommit646f486.
- [x] Check new local/remote scale directories do not exist. Copy all16acceptedfiles preserving contents, no overwrite. Remote diff-qr0; both16-fileinventoriesmatch. Frozen8-env source remains available for old hash-bound verdicts.
- [x] Capture baseline git status/diff and scale file hashes. CPUtesting uses no bytecode/cache/plugins.

## Task1: deterministic layout and live ownership

Files:create `scale_layout.py`, `tests/test_scale_layout.py`; modify `runtime.py` layout/own-bar/scene/sink guards, `run.py` layout metadata wiring. Do not touchcore,bridge,verdict,oldtests,run.sh orSDK.

- [x] RED tests for pure `tile_indices(num_envs)` and factory/liveguard contracts. Interface:

```python
def tile_indices(num_envs):
    if type(num_envs) is not int or num_envs <= 0:
        raise ValueError('invalid environment count')
    ids = np.arange(num_envs, dtype=np.int64)
    if num_envs == 1024:
        return ids % 32, ids // 32
    return np.zeros(num_envs, dtype=np.int64), ids

def test_1024_bijection():
    rows, cols = tile_indices(1024)
    assert len(set(zip(rows, cols))) == 1024
    assert (rows[31], cols[31]) == (31, 0)
    assert (rows[32], cols[32]) == (0, 1)
    assert (rows[-1], cols[-1]) == (31, 31)
```

Preserve104-column legacy helper test. Additional real arithmetic test builds origins `(row-15.5)*8,(col-15.5)*8`, computes float32bar centers, asserts all local center errors<=2e-5;1×1024 control case proves768failures. Shuffled actual path list mapsenv0..1023correctly; duplicate/missing/row32/col32/nonzero slot rejected.

- [x] Run focusedtests, record expectedmissingimplementationRED. Implement minimal pure mapping plus `make_scale_terrain_type(parent_type)` factory. Its subclass `_compute_env_origins_curriculum(self,num_envs,origins)` must reject othercount/shape, callparentonce, assign torchlong levels/types from mapping onorigins.device, setmax_terrain_level32 and returnorigins[levels,types]. Factory imports noSDK and Torch only when invoked; no moduleglobalpatch. Fakeparent testrecords1call, preserves random draw, checks assignment happens before parentconstructor returns/spawn callback. Record original parentmodule/class and actual subclassidentity.

- [x] In `adapt_cfg`, whenN1024: requiredisabled terrain_levels curriculum, setgenerator32×32,replace only terrain.class_type withfactory class;N8keepsold1×8. Keepmax_init0,size8m andonlyaddterrain.class_type toallowlist. Rejectwrongreference importer or unexpected generator/currentcurriculum. Add tests fakeconfigN1024 while originalN8tests stay unchanged. SPEC-found actualSDKconfigclass issue fixed with realdecorator/declarations regression.

- [x] Changeown_bar_indices tokeyparsed(row,col) and usepuretilemapping; preserveall count/path/slot guards. Do notchange PhysX sensor shapes, norms, peak reductions orforeign coverage.

- [x] Add `layout_evidence(env)` that verifiesexactN1024,expectedlevels/types,terrainorigins32×32×3,unique8mspaced origins,sceneoriginsbitwiseequaltilegather,robot envpathorder. Record namedlayout `m1_grid32x32_v1`,tile_size8,fullrow/col/actualorigins/class/hash. Geometrystillvalidatedbyexisting validate_scene unchangedthresholds. Write `scale_layout.json` and scene field onlyN1024.

- [x] Add runtime sinkguard forN1024 eachsample usingcurrentterrainlevels/types/origins/sceneorigins, comparetoexpectedfreshgather andstartupfrozenorigins. Reject drift beforeaccepting sample. Test individualfielddriftandduplicateorigin; failure mustraise into existing cleanup/reportpath. N8path performs no newscene accesses.

- [x] Run fullsuite withaddedtests,bashsyntax; spec reviewthenqualityreview. Fixissues withRED beforeGREEN. Save individual log,freezeTask1 hashes; noGPU yet. Implementer431passed78.20s, main431passed77.79s, independentSPEC/qualityPASS; exactsnapshot `scale1024_20260918/task1_accepted/adapter` pluslocalsnapshot preserved. Nonblockingrunmetadata-test concern will get executablecoverage inTask2.

## Task2: explicit baseline mode and versioned metadata

Files:create `scale_identity.py`, `tests/test_scale_modes.py`; modify `runtime.py` argumentvalidation, `run.py` orchestration. Nochanges to frozenbridge/core.

- [x] TDD parse `--controller-mode` choicespost-cross-sync/reference,defaultpost-cross-sync. Rejectreference unlessN1024/steps1600. Argumentparser rejects before simulator start. N8defaults andexistingCLIunchanged.
- [x] Introduce pure metadata builder withversion `m1_reference_scale_v1`,N1024,layoutname,fixedcontroller parameters,allsourceSHA256s(run,runtime,scale_layout,scale_identity,sync_verdict,core,bridge), separatetop-level `controller_mode`. Bothconfig/provenanceget samecommonidentity. Verifybuilderhashesactualfiles; baseline absentdiagnostic_candidate,candidateexistingcandidate_metadata intact. Eight path retains originalmetadataexceptverifiernewhash.
- [x] Runtimecontroller branch:

```python
wrapper_type, restore_ik = instrument_reference_wrapper(M1RslRlEnvWrapper, wrapper_module, counters)
if args.controller_mode == 'post-cross-sync':
    wrapper_type = make_sync_wrapper(wrapper_type)
wrapped = wrapper_type(env.unwrapped, clip_actions=1)
# validate_scene, RuntimeSink and holder setup remain in their original order
if args.controller_mode == 'post-cross-sync':
    wrapped.bind_post_cross(output, sink)
else:
    write_json(output / 'sync_live_contract.json', validate_live_contract(env.unwrapped, sink))
```

Reference usesoriginalprepare/IK andzeros,doesnotcreateSyncBridge orsidecarchunks. Makebranchtest executable withstubwrapperfactory/calls,not onlystringmatching. Cleanupowners unchanged; reporterexplicitmodeandbaselinepurpose; neverfabricateacceptedbaseline.
- [x] FullCPU,codehashguard,independentSPECthenquality. FreezeTask2,recordlog. NoGPU. Implementer445passed78.13s; main14focused2.47s; independentSPEC/qualityPASS(14tests2.79/3.08s), snapshot task2_accepted/adapter preserved. Fullreference1600CPUmain normalreturn andreal writtenlayout coverage included, nophysicalclaim.

## Task3: budget-aware independent verifier

Files:modify `sync_verdict.py`; create `tests/test_scale_verdict.py`. Existing `tests/test_sync_verdict.py` unchanged andmustallpass.

- [x] RED addimmutablebudgetinterface/defaultcompat:

```python
@dataclass(frozen=True)
class RunBudget:
    num_envs: int = 8
    steps: int = 1600
    def __post_init__(self):
        if (type(self.num_envs) is not int or type(self.steps) is not int
                or (self.num_envs,self.steps) not in ((8,1600),(1024,32),(1024,1600))):
            raise ValueError('unsupported verdict budget')
```

Avoid dataclass dynamicimport issues byregisteringmoduleintestloadorusingimmutableNamedTuplewithvalidatedconstructor; no mutableN/STEPSglobalrewrite. Public `evaluate(output,baseline=None,*,num_envs=8,steps=1600)` keepsoldpositionalbehavior. Default `_chunks/_completion/_prefix/_observer_replay/_replay/_analyze` helpers acceptbudgetdefault8×1600; usebudgetN/Tforallallocations/loops/shapes. Tailwindowonlystrictremains800..1599.

- [x] Add CLIexplicit `--num-envs`/`--steps` default8/1600 andoptionalbaseline; strictrequiresbaseline,startuprejectsunexpectedbaseline. Errorverdictfailclosed; reportdistinctstartup/strict andnooriginalstrictpassfor32. Keepexistingexit0iffacceptanceforitsdeclaredkind,else3.
- [x] Generalize onlydimension/bookkeeping variables,notindependent equations. Original8testsvalidateidenticalresultsemantics. `_chunks` scalechecks1or50chunks,each32rows,fullJacobian[1024,17,6,22],allenvIDsrequired; NPZ256MiBboundunchanged.
- [x] Newscalemetadata validator verifiesactualcodehashes,modevalues,cfg/provconsistency,layoutsourceevidence andactual1024arrays. Baselinecomparison removesonlyvalidatedtop-levelcontroller_modeandcandidate-onlydiagnostic_candidate,thenremainingJSONbyte-equivalentobjects/NPZbitwise. Bothliveunitscontractsidentical. Test forgedN,lastenvmissing,cfg/provmismatch,baselinecandidateidentity,sourcehashchangeandnestedmodechangesmustfail.
- [x] Refactorcompletion into commonfullrun andfirst-episode checks. Bothnative0/exactbudget/cleanuphash/source/scanner/measurement/fullchunksrequired. Candidateallfirstepisodesfulllengthandzeroreset. Old8baselinefulllengthrequired. Scale1024baselineallowwrapper3onlybehaviorandrecordnegativeperenv, notcommonfailures; exactstepsrequiredthroughallresets. Per-envbaselineprefixhasnotermination/timeout/reset throughstepactivation-1; comparealloldnon-timingfields bitwise. Test endatlastprefixreject,endatactivationorlatersafelydoesnotinvalidateprefix,baselinecommonerrorreject.
- [x] Startupanalyze requiresnoactive/hold,fulloriginal/final/actual16parity,actualprocessedwheelparity,allsubsteps4,sameindependentobserver/controlstatereplay; skiponlycrossing/activation/tailrequirementswhichcannotexistat32. Resultstrictbehaviorfalse,startupacceptedtrueonlywithoriginalstartuptrue. Testforgedsidecar/replay/nativefails.
- [x] TestscaleCPUusingactual1024shape:one32-stepvalidfixtureandlastenvcorruption;onefull1024×1600syntheticartifact/replay(in50chunks)withknownorderedcrossing/activation,targetandactualdata. Use/tmpuniqueevidencedirectory,expectedseveralGiB,RAMavailable; donotmassduplicatefixturesacrossparametrizedtests. RecordRSS/time/disk,noGPU. Purefocusedtests coverindividualmutations withoutrebuilding3.47GiBfor each.
- [x] Runall373+newtests,bashsyntax; reviewSPECthenqualityafterfixes. Ensurecore/bridge/metrics/nativefinalizer/run.shfrozen,oldisolatedverifierstillreverifiesrun14. Freezeallcandidatefilesandindividualtestlog.

Task3 final:506CPU146.22s, mainpostfix102new+oldverifier78.81s includingfull1024×1600fixture, SPEC/qualityPASSafterexact-metadata-schemaP2RED→GREEN. Bothlocal/remote task3_accepted/adapter snapshotscreated,diff-qr0. NoGPUbeforethisgate.

## Task4: capacity and strict physical evidence

Physicaltasksownedbymainagent,notimplementation/reviewsubagents.

2026-09-18 operational storage amendment:root free space fell25GiB→12.058GiB fromwritesnotexplainedbytaskartifacts; useraskedtofree/identifyalloweddata. Do notmove livebaseline18 or anysource. Read-onlyauditconfirmed--outputnotpartofmetadata/sourcepaircomparison. Futurecandidate19 NEW output may use `/data/hexinkun-m1-acceptance-20260918/20260918_gpu7_1024x1600_19_scale_sync`, withsidecarlaunch/GPU/processlogsintheprivate0700parent(createdand878bytewriteverified). Preservebaselineoriginalpath; noexistingfilesmoved,noequations/gates/budgetchange. Recheckrootandtargetcapacitybeforeanynextlaunch;datapathdoesnotcureunknownrootgrowthorwaivebaselinecommongates. Thisadapterisnot10000-updateAMEtraining.

- [x] RecheckGPU7UUID,allGPU7processes,filesystemfree>=12GiB,hostRAM,candidatehashes. CaptureverifiedownreservationPID2795762 exactowner/start/cwd/interpreter/cmd/script/environmentbeforestop;neverrelyonstalePIDalone. Stoponlythisverifiedsleep.pywithTERMunderexistinguserauthority,waititsremoval,ensureGPU7otherwisefree. Preserveitsrestorableinvocation. NoSDK/driverchanges. Completed22:02:05,25GiBdisk/885GiBRAM.
- [x] Runonce candidate1024×32 newoutput `20260918_gpu7_1024x32_17_scale_startup` withulimit-c0. Independentobserverrecordsnvidia-smipeak/progress; noauto-restart. Useexternalreturn/nativefinalizerandnewverifier `--num-envs 1024 --steps 32 --output <dir>`. Allstartupgatesrequired. Failure stopsnextlaunchandstartsdiagnosis. PASSall1024/32/128sensor,native/wrapper/verifier0;normalclose,peak11148MiB,wall4:38.75. Explicitstrictfalse.
- [x] Onlyafterpass,runreferencebaseline1024×1600 with`--controller-mode reference` newoutput `20260918_gpu7_1024x1600_18_scale_baseline`. Requirecomplete1600/native0/no commonmeasurementfailure;behaviornegativeisretainednotrewritten. Completed41:32.16,native0/full50chunks/6400sensor/normalcleanup;mainindependentcommonexit0. Originalbehavior615/1024,53episodeendsretained;notstrictPASS. PeakwholeGPU11338MiB. Candidate19launchedonce22:53:57toapprovednew/dataoutputafterfreshresource/sourcechecks.
- [ ] Thenrun candidate1024×1600 defaultpost-cross-sync newoutput `20260918_gpu7_1024x1600_19_scale_sync`; runverifierwithsame-scalebaselineandexplicitbudget. Reportall1024denominator/per-envfirstfailure. Nosweep/retry/thresholdrelaxation. Attempt19FAILEDafter247completedsteps:prepare247env523wave/legsreentryviolatedapplicability,native1/wrapper2/independentverifier3. Full1600/1024strictremainunmet;noautoretry. NewCPUchildinvestigatesphasecompletion/reentrycontract,separatefrom18firstcrossgeometrymisses.
- [x] Whennotaskcomputeprocessremains,restoreverifiedreservationusingitsoriginalscript/runtime/environmentandconfirmonlyintendedGPU7memoryallocation. Ifcapacityfails,donotstartreservationwhilefailedtaskstillalive. Restored23:05:14onlyaftercandidate309168gone/GPU7free/sameUUID/scriptSHAverified;PID351307actualpython sleep.py/originalm1placeholderenv/cwd,15744MiB. Nootherjobsstopped.
- [ ] Writeper-runlogs/dashboard/T306/index/sourcehashes/reviewresults. Only1024strict+verifierpasspermitsformalpromotion; failurepreservesactiveproblemnode. OverallgoalcontinueslaterthroughAMElifecycle/actiontransferandactuallearnedcross/avoidance10000acceptance.

## Main-agent self-review

Layoutstageisconstruct-timeandliveguarded;modebranchpreservesoriginalwrapper/reset/cleanup;verifierbudgetsareexplicitandnoequationschanged;native/source/measurementguardsseparatedfrombaselinebehavior;full1024coverageandtail799remain. Oldhash-boundevidencearchived,15GiBreservationcontrolledonlywithspecificexistingauthority,physicallaunchesgatedbypassingreviews. Noautomaticrestartsorfalsepolicyclaim.
