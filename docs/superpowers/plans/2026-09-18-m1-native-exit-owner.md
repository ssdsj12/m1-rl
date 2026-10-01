# M1 Native Exit Owner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Identify the actual native exit callback and registering library behind diagnostic09's post-completion SIGABRT without modifying the SDK or production adapter.

**Architecture:** Preserve the existing capture harness and add opt-in callback tracing in an isolated directory. Registration and invocation metadata is bounded, read-only and matched per thread; actual inferior status remains independent of debugger status. A copied diagnostic candidate reproduces09, while production stays atb60ca0f.

**Tech Stack:** Python3.10, GDB12.1PythonAPI, ELF/glibc x86_64, ampIsaac4.5/Kit106.5, CPU C fixture.

Spec: [approved routeA](../specs/2026-09-18-m1-native-exit-owner-design.md). User's latest“那继续修改”continuesapprovedrouteA. Existing isolateddebugroot/localstage selected explicitly; no newgitworktreeorpackageinstall. Do not touch reservation2795762.

## Task1: Opt-in exit-callback capture (one implementer)

Files in `m1_reference_validation_stage/debug_tools/`: create `exit_callbacks.py`, `test_exit_callbacks.py`, `exit_owner_fixture.c`, `test_exit_owner_gdb.py`; modify `capture_gdb.py` only to call opt-in tracing hooks. Deploy under `/home/hexinkun/m1_debug_tools/gdb-jammy/exit_owner_20260918/`, never overwrite originalcapture.

- [x] Write failing pureCPUtests and demonstrateRED for boundedregistration, matching callback+arg, per-threadnestedenter/return, unmatchedcallback, overflowandinvalidlibcguard.
- [x] Implement a small `ExitCallbackLedger` with `register`, `enter`, `returned`, `snapshot`. A callbackentry stores matchingregistration(s), notjustlatestcallback. Returnedstacks areperthread. Boundtotalrecords; trackoverflow explicitly.
- [x] Add GDBintegration: pending__cxa_atexitbreakpoint atstarti, registerrdi/rsi/rdx plusreturnPCat*RSP andDSOpaths; onlibcload use `info proc mappings` currentbase andELFBuild-ID,requireexpectedBuild-ID490fef8403240c91833978d494d39e537409b92e andbytesat+0x45493=`ff d0`. Verifyreturnbytesaswell. Capturecallbackrax,arg rdi,statusesi oncall; popsame-threadstack at+0x45495. Breakpointstop returnsFalse; onerrorflagdiagnosticincompletewithouttargetmutation.
- [x] Opt-in through `M1_GDB_TRACE_EXIT=1`; defaultcapturemustremainidentical. Installafterstarti,beforenormalcontinue. Snapshotintofatalreportandfinalreport. No calls toinferiorfunctions; no signal suppression or programcounter manipulation.
- [x] Testnativefixturecompiledwith`cc -g -O0 -fno-omit-frame-pointer exit_owner_fixture.c -o exit_owner_fixture`. Fixture calls__cxa_atexit forknownnamedcallbacks; lastinvocationaborts. Assertknowncallbacksymbol+registeringcaller,unreturnedstack,native134,debugger0distinct. Normalmodechecksreturnedcallbacksandnative0. RejectmismatchedBuild-IDbeforehardwarediagnosis.

Examplefixturecontract:
```c
#include <stdlib.h>
extern int __cxa_atexit(void (*)(void *), void *, void *);
static int token;
void fixture_abort(void *p) { if (p == &token) abort(); }
int main(void) { return __cxa_atexit(fixture_abort, &token, 0); }
```

Verificationcommand(withisolatedGDBconfiguredbytesthelper):
```bash
cd /home/hexinkun/m1_debug_tools/gdb-jammy/exit_owner_20260918
PYTHONDONTWRITEBYTECODE=1 /home/hexinkun/miniconda3/envs/amp/bin/python -m unittest -v test_exit_callbacks test_exit_owner_gdb
```
- [x] Existing`test_capture_gdb.py` sixcontractsremainpassing.
- [x] Speccompliance review,thenqualityreview; fixmust-fixissuesbeforeIsaac. Mainindependentlyrerunstests.

## Task2: Isolatedreproductionpackaging(main,inparallelwithTask1)

- [x] Readrun.py/runtime.pyforpath-relativeassumptions. Createfresh`exit_owner_20260918/adapter/`bycopyofproductionadapter,thenoverlayonlyfourarchivedcache-offcandidatefiles. Compareallfilessha256toexpectedbaseline/candidate, noalteredcontroller/rewards/thresholds. Copyisolationisnotdeploymentofrejectedcandidate.
- [x] Create`run_exit_owner_gdb.sh`fromtheexistinglauncherwithTARGETpointingisolatedadapter,DEBUG_CAPTUREpointingnewcaptureandtraceoptenabled. Keepamp,physicalcuda7,8env,32steps,rendererflags,existingVulkanICD and environment unchanged. Reserveoutputandreportpaths; noacceptancefinalizer; logdiagnostic-only.
- [x] `bash -n` thenreadcompletewrapper. Verifytargethasallmodulesandpathresolutionisportablebeforelaunch.

## Task3: One8×32diagnostic(main)

- [x] BeforelaunchcheckGPU7UUID/freeVRAMandreservationcommand,user,PID. ChecknootherownIsaactraining/debugchild. Ensurebaselineproductiondiff0versusb60ca0f.
- [x] LaunchoneforegrounddiagnosticviaSSH withuniqueoutput`20260918_gpu7_8x32_10_exit_owner`,persistouterlogandGDBshellstatus. Pollownlog/process bounded; nouserprocesssignals,noautomaticrerun.
- [x] Readfullreportnormal/nativeexitcode,all32samples,loadedlibraries,unreturnedcallbackandmatchingregistration. IndependentlyreadcallbackDSOmachinecode/sourcewhereavailable.
- [ ] Ifincomplete,stopanddescribeevidencegap. Ifownerproven,formonesource-backedminimalrepairandfailingregressiontest; donotinventaSDKpatchbeforeevidence. Anyenvironment/ABIupgradeorKit-hostrewriteismaterialdesignchange.

## Task4: Evidencehandoff(main)

- [x] UpdateT306.6h.5c/.5c.1,notesdashboardandper-testlog. Recordchecksums/tests/nativecodes separately.
- [x] Ensureallown diagnosticchildrenexited,reservationuntouched,productionunchangedunlessseparatelyverifiedrepairaccepted.
- [x] Stateactualoutcome: diagnosticidentificationisnotclean-exitrepair; 32stepsisnot1600behaviorgateor10000training.

## Self-review

2026-09-18 outcome: run10 identified the PhysX replicator attach callback's function-static Python list as the post-close abort owner. CPU diagnostics: 22 tests passed; copied adapter: 170 passed. Spec and quality reviews approved. Native status remains 134, so this is not a clean-exit repair. The unchecked item above is transferred to T306.6h.5c.2: a supported replicate_physics=False workaround and its regression test await the user's design choice. See [run10 evidence](../../../notes/log/2026-09-18-m1-physx-exit-owner-capture.md).

Allspecboundariescovered:sourceandSDKunchanged,ASLR/Build-IDguard,bounded/threadedtracking,realnativefixture,trueexitstatus,oneownGPU7child,preservedreservation,noautomaticrestart. Stopbeforeanyunprovenrepair; rollbackisonlyceasinguseofisolateddiagnostictools.
