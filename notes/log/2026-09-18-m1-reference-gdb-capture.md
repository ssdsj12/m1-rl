# M1 reference native crash capture with isolated GDB

## Purpose / Stage / Todo

T306.6h.5a, childofshutdownfault. User explicitly allowed isolatedgdb installation after [launcher cleanup](2026-09-18-m1-reference-launcher-cleanup.md) stillendednative139 duringinterpreterGC. This supersedes priorWAITINGUSER state. Noauthoritytochangeamp/Isaac/driver/reference/controller/reservation.

## Method / Conditions

Server4090 Ubuntu22.04amd64, systemgdbabsent. Download official UbuntuJammy gdb12.1-0ubuntu1~22.04.2 andmissingruntime debs usingapt-get download, extractwithdpkg-deb into `/home/hexinkun/m1_debug_tools/gdb-jammy/root`; noaptinstall/sudo/environment packagechanges. Runtimeunderdebug mustretainexistingamp/GPU7environment and8×32 budget, no1env orPPOtraining. Preserve sleep.py2795762 (15744MiB); freshprecheckGPU7used15754/free8328MiB.

Debuggerexitstatusmustnotbeconfusedwithnativechildsuccess. FirstexercisecontrolledCPUchildren beforeIsaac; savecrashstack andtrueexitsignal/nativecode. No falsefinalreport when debugger merely stops/returns0. Noautomaticretry.

## Evidence / Result

Isolatedtoolready: GNUgdb12.1, embeddedhostPython3.10.12; ampremainsPython3.10.21. Extractedroot16MB, packages4.7MB. Packageversions: gdb12.1-0ubuntu1~22.04.2, libbabeltrace1 1.5.8-2build1, libboost-regex1.74.0 1.74.0-14ubuntu3, libdebuginfod1 0.186-1ubuntu0.1, libipt2 2.0.5-1, libsource-highlight4v5 3.1.9-4.1build2. Gdbdeb SHA256 b69807229a85ceef0c889fce0e0a630afc1183cade729731988fd1378e9243c1. Systemdpkgstillhasnogdbinstallation; onlyunpackedtoolrootexists.

One-off run_reference_gdb.sh mirrorsbaselineampPYTHONPATH/LD_LIBRARY_PATH, device7/8env/32steps andrendererflags. GDBprivateLD/PYTHONPATH areseparate andinferiorenvrestoredbycapturehelper. PreserveASLR (`set disable-randomization off`), noautoload/debuginfod, livebacktraceinsteadofOScore(ulimit-c0). Shellsyntaxpass, finalSHA256 e5f0bc011aa06fa8be4b7cde6f6517d5dbea07c5723843f8aa09f010077e6a40. Omitexplicitspace-containingkit_argsbecauseGDBstartup-with-shelloffcanalterquotedargv; runtime.pydefaultisidentical. Disableautoloadwith-iexbeforeexecutableload. Productionadapterunchangedatb60ca0f.

CPUcapturetestsRED5missingimplementation thenGREEN5in3.889s; mainindependentrerun5PASS3.839s. Testsrealexit0/7,ctypesSIGSEGV139,abort134,andSIGSTOPincomplete; verifyrestoredinferiorLD/PYTHONPATH+ASLRpersonality. DetachalsoemitsExitedEvent, explicitlyignoredwhile detaching. ReviewAPPROVE. CaptureSHA2565bc9d1ef0cd52354dd5fc2a1ee30ab109a44d4de7c9d7d28b751a9f71a95f77e, testc982e6c572611d2a6b6c52c1343f70304d1aa3067fb22068929c614da982e051. Unknownstop/4fatalstopswithoutconfirmedexitfailsclosedanddetachesownchild; operatorchecksPID. GDBstatusneverpassedtofinalizer.

Native capture 06: output `run_logs/m1_reference_validation/20260918_gpu7_8x32_06_gdb`, actual amp child PID3035708, run ID9807a23e-0fbf-414a-a28f-26f66870e8e5. Command `bash /home/hexinkun/m1_debug_tools/gdb-jammy/run_reference_gdb.sh /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_06_gdb` with tee to sibling.log. All32 steps/32 prepare+IK calls completed in43.4248s under debugger. All close markers emitted.

Native exit confirmed SIGSEGV11 / code139; GDB shell exit separately0 (exec session44806), never accepted as childsuccess. `.gdb.json` isdiagnostic-only, no finalizer invoked and no startup acceptance. Two fatal stops are original fault then Python faulthandler reraising, not two independent faults/restarts. Diagnostic errors0. Ownchild ended; reservation2795762 unchanged and GPU7 returned to15754MiB used/8328MiB free.

First fault stack (log lines288–354): `libomni.physx.tensors.plugin.so` -> `_physicsTensors.cpython-310...so` -> `carb/_carb...so` -> Python `dict_dealloc`/`subtype_dealloc` layers -> `frame_dealloc` (line591, then repeated line600). Confirms native tensor object destruction during retained Python frame destruction after plugin/app shutdown. This narrows the failure but does not yet identify the frame's retaining owner or prove all earlier training exits share this cause. Existing bt60 lacked Python code-name/filename metadata; isolated debugger will add read-only frame metadata before deciding an adapter fix. No SDK patch or speculative release. No1600/1024.

## Follow-up / Refs

Usecapturednativeframes toselectminimalrootcausefix; no more speculativeglobalinterface releases. Onlycleannormal8×32exit permitsstrict1600series then1024capacity. Related[branch](../todo/T306-m1-ame-long-train-stability.md),[plan](../../docs/superpowers/plans/2026-09-18-m1-reference-runtime.md).
