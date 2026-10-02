# GPU7 selection and explicit user hold

## Purpose / Stage / Todo

Reference controller prelaunch resource check, T306.6h.4. User changed the requested physical GPU from4to7, then explicitly chose to preserve the existing reservation process and not start.

## Evidence

2026-09-18 14:42CST read-only nvidia-smi/ps checks:GPU7 UUID GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e,20874MiBused,3208MiBfree,0%utilization. PID2789351 belongs tohexinkun,command`python sleep.py`,started14:40:29. Inspectedscript onlyallocatesCUDAmemorythen sleeps. No signals sent. GPU4/5/6 wereidle,butuserselectedGPU7; noalternativechosen.

Userresponse toexactPID stop request: **保留占位进程，暂不启动**.

14:44:23CST userreportedreservationreducedto15GB. FreshreadonlyGPU7query:15754MiBused,8328MiBfree,0%utilization;currentpythonPID2795762 uses15744MiB. NoIsaaclaunchorsignal. Thisresourceupdatehasnotyetexplicitlyrescindedtheuser'shold; askwhether8-envshouldnowstartwhilepreservingreservation.

## Result / Follow-up / Refs

Superseding update: user explicitly confirmed8env with15GB reservation preserved. Bindingddad702 passed151 CPU tests. Two8×32 runs collected complete samples then failed normal native shutdown139; no1024. Historical hold below remains evidence, not current authorization/status. See [first run](2026-09-18-m1-reference-gpu7-smoke.md),[instrumented reproduction](2026-09-18-m1-reference-gpu7-faulttrace.md).

Pausedbyuser. NoIsaaclaunch,noCPUtestrerun,noGPUbindingcodechange,noautomaticmonitor. Existingf5842d4adapterremainsGPU4-bound; GPU7bindingmustbemodifiedandregression-testedonlywhenresumingimplementation. Futureintentremainsamp/GPU7,8envbefore1024env; donotkillreservationorreleaseGPUwithoutnewauthorization. Source/controller/rewardcontractsunchanged. Related[branch](../todo/T306-m1-ame-long-train-stability.md),[previousresourcecheck](2026-09-18-m1-reference-gpu-resource-blocker.md). BaselineRef4220356;featuref5842d4;physicalverificationnone.
