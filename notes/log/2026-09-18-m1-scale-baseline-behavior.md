# 1024 baseline18 behavior negative-case audit

Stage:T306.6h.6a.1a, children.1 crossing geometry and.2 phase reentry. Read-onlyCPU audit,2026-09-18; no newIsaacrun/thresholdchange/sourceedit.

Input is [baseline18](2026-09-18-m1-scale-baseline18.md), singleprocess full1024×1600/native0/commonPASS,originalstrict615/1024. Its409failed environments split into four disjoint groups, verified both by independent agent and main fresh data reads:

| Group | Count | Evidence / boundary |
| --- | ---: | --- |
| First ordered crossing missing | 18 | FAR overbar6,RAR17,union18; cannot be repaired by a controller that only activates after both ordered touchdown events |
| Crossing complete, no5-sample activation qualification | 21 | phase11→-1→0 reentry before collecting5consecutive valid samples |
| Potential qualification precedes tilt failure | 31 | qualificationprepare243..254; hardfailure occurs later, actualcandidate outcome still must be measured |
| Only whole-first-episode wheel-mean spread fails | 339 | original>.08 gate, not replaced by a postactivation slice |

Main explicitly asserted disjoint union409 equals every originalfailed env. Reporthas53terminated/reset,54tilt failures,timeout0; overlappinggates must not be added asdistinctenvironmentcounts.

## First crossing geometry

Frozen overbarwindow:x[.82,.88],y[-.3759,-.0241],z>=.1609,force<=1N,strictlyafterprelift. All thresholds unchanged. Main reloaded first7chunks and independently confirmed eachwindow/height/lateral/contact value.

FARmissIDs471,563,768,824,972,990. Eachhasprelift andxywindow/contacteligible, but maximumz respectively .158027902,.159397349,.155101255,.157637119,.152884305,.149521530m,allbelow.1609. Windows141–146. Allwindowcontactforce0.

RARmissIDs40,140,228,294,447,471,563,577,592,619,633,711,768,972,977,990,997. Windows197–202,allwindowy<-0.3759 evenatmaximumy. Nearestmaxy-.376155853(env294),furthestmaxy-.394078255(env563);allforce0. Env563alsoallwindowheightlow;768hasoneheight-eligible samplebutstilllateraloutside. Notabsenceofaxsampleorcontactthreshold. Missingpassed/touchdownisdownstreamofmissingorderedoverbar,notanadditionalindependentcause.

Union18:`40,140,228,294,447,471,563,577,592,619,633,711,768,824,972,977,990,997`.

## Activation qualification and premature wave reentry

Main freshNumPy replay via frozen`sync_verdict._observer_replay` onall50chunks,RunBudget1024×1600:985envhavepotentialready_count>=5,firstprepare243..254;39nevereligible. NoTorch/Isaacmodulesimported. Thisisqualificationonbaseline,notactualcandidateactivation.

The39areunion18plus21:`3,24,81,99,122,129,139,181,221,341,389,441,450,451,481,483,621,699,737,805,1021`.

These21alreadyhavebothorderedtouchdown. Independentfulltracefoundphase11afterwhichFARcontactbrieflyzero;thenonly1–4qualifying samplesbeforewave=True/nonzerolegsresetready_count. Firstwave reentry244..248. Main independentlyverifiedenv24:sample243phase11/wavefalse/legs0/FARforce0;244–245qualified;246phase0/wavetrue/legmax.266602874,readyreset0. Its laterfirsttilt285/termination297cannotbeconfusedwiththeearlierreentry.

54tiltfailuresdivide23nevereligible(21aboveplus563/972)and31qualifiedbeforetilt. Independenttracefirsthardfail280..610,notfirstcrosswindow;thisdoesnotpromiseasynchronizationfixcuresall31. Finalwhole-episodegate remainsunchanged.

## Relation to actual candidate failure

[Candidate19](2026-09-18-m1-scale-candidate19.md) independentlyencounteredenv523freshwave reentry atprepare247 and intentionally failed its applicabilityguard. Thatcasehadready5available atthenextprepare,unlikethe21whosecounterneverreaches5. Bothroutespointtophase-completion/reentry coordination; donotremoveguardorlowerdwellthreshold.

Noformalpromotion/newphysicalattempt authorizedbythisaudit. PreservefullN,source/reference/SDKandallnegativeartifacts. Next:traceoriginalsemanticgate/state-transitioninputs,designexplicitcompletion/reentrycontractinisolatedcandidatewithTDDandreviews;firstcrossgeometryremainsaseparatechild,notresolvedbyphasefix.

Refs:formal646f486;isolatedscaletask3_accepted;repoHEAD5553e84;verifier3930483e477e0a1c6faa15c3a66dea97a20289d8e78cec9d9f4e6ca708dc79c5. See[T306](../todo/T306-m1-ame-long-train-stability.md).
