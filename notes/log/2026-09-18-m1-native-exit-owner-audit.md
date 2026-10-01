# M1 SDK integrity and native exit-owner audit

## Purpose / Stage / Todo

T306.6h.5c and child .5c.1: after user permits SDK shutdown repair scope, identify a reversible next diagnostic rather than a fourth speculative cleanup patch. User selected route A: isolated native callback registration/invocation capture before selecting a repair. [Design](../../docs/superpowers/specs/2026-09-18-m1-native-exit-owner-design.md), commit6addb50. Written-spec review and implementation remain pending at this checkpoint.

## Input / Procedure / Evidence

Three read-only parallel audits, no SDK/torch imports, no simulation, no package writes:

1. RECORD ownership/hash audit:22 selectedinstalledfiles,20,855,864bytes allmatchdeclaredSHA256and size;190dist-info normalizednames unique,allhaveRECORD.36sharednonpycpathsunderomni/isaacsimhaveconsistentRECORDhashes;5sharedPythonfiles also实算match. Key16files eachsingleowner. Mainandtelemetry-private libcarb differbutbothmatchtheirownpackageRECORD; notoverwriteevidence. This isbounded,notproofallfiles/ABI/runtimepathsarecorrect.
2. Existing09nativeevidence:libcbase0x7ff14a5dc000,callbackreturnPC0x7ff14a621495,offset0x45495. ActualhostlibcBuild-ID490fef8403240c91833978d494d39e537409b92e; objdump shows flavor4branchandcall*rax at0x45493. Atthatinstruction raxiscallback,rdiarg,esistatus. Fatalregistersareafterabortandcannotidentifyoriginalcallback. OrdinaryC atexitcanwrap__cxa_atexit; notproofspecificC++/torch/carbowner. MainindependentlyrecheckedBuild-ID/disassembly.
3. InstalledIsaac4.5closealreadydoesstageclose/app.shutdown/framework.unload_all_plugins; nopublicgeneralrelease-allPythonownerAPI found. Official4.5KnownIssuesCrash#3 discusseslatephysics.tensorsGC. Carbonite210.1.11OMPE-72296 addresseslateLinuxstatic-owneratexitpluginteardown; installed180.6cannotbeassumedidenticalbugorbackportable. Noindividualsharedlibraryreplacementproposed.

Primarysources: [Isaac4.5knownissues](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/overview/known_issues.html#crash), [Carbonitechangelog](https://docs.omniverse.nvidia.com/kit/docs/carbonite/latest/CHANGES.html), [Carboniteshutdownexplanation](https://docs.omniverse.nvidia.com/kit/docs/carbonite/205.0/docs/Kernel/ShutdownDebugging.html).

Mainfreshchecks:`git diff --exit-code b60ca0f -- tools/m1_reference_validation` exit0; reservation2795762Sl+ python sleep.py; GPU7UUID46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e,15754MiBused/8328free/0%. No diagnostic child launched thisturn.

## Result / Communication correction

No repair claimed. Prior cache-off candidate was archived/reverted because nativeexit134remained; this did not discardtrainingprogress,models,logs,oracceptedM1features. Existing120/1000updatesingle-processcompletionsdonotguarantee10000. Currentreference8×32capturescompletedallrequestedstepsandthencrashedduringshutdown; thisdoesnotestablishthesamecauseasoldmid-trainingtermination. Userobjectedtorollback/early-stopwording; bothfaultclassesmustremainseparateinallfutureclaims.

RouteA adds boundedread-only__cxa_atexitregistrationandmatchinglibccallbackentry/returnevidence inisolateddebugtooling,notproductioncleanupchanges. ExactBuild-ID/bytesmustguardASLR-relativebreakpoints. CPUfixturesandexistingexitaccountingmustpassbeforeoneamp/GPU7 8×32diagnostic. Noautoreruns/fastshutdown/os._exit. Normalcleannative0gatesremainbeforethree8×1600andlater1024. No10000trainingstarted.

## Git refs / Follow-up

Baseline/lastacceptedadapter:b60ca0f. Newdesignonly:6addb50. Noacceptedfixcandidate. Keyfiles:archived09.log/.gdb.json;installedlibc;selectedSDKRECORDs;isolateddebug_tools;newdesign. [Dashboard](../todo.md),[branch](../todo/T306-m1-ame-long-train-stability.md).
