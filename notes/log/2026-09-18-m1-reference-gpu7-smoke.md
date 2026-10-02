# M1 reference GPU7 validation

## Purpose / Stage / Todo

Resume T306.6h.2 physical validation after user chooses GPU7 and explicitly approves keeping the15GB reservation while trying8env. Reference/controller/reward unchanged; amp runtime. Related[hold](2026-09-18-m1-reference-gpu7-hold.md),[branch](../todo/T306-m1-ame-long-train-stability.md).

## Conditions / Procedure

Read-only GPU7 check14:45:46:15754MiBused/8328MiBfree,0%utilization. Reservationwasnotstopped. ExplicitphysicalGPU7 UUID GPU-46a1bc7e-093f-ab76-2bf1-35b0ae1fd66e; noCUDAremapping. SourceAppLauncher mapsdevice7tobothphysics_gpu7andactive_gpu7. NoalternativeGPUorfallback/restart.

Minimalbindingchange: sharedPHYSICAL_GPU=7/DEVICE forCLI,cfg,CUDAcontext,tensors,peakmemoryandmetadata; shell7. Nochangefour-wheelorfour-substepconstants.

## CPU Evidence

TDD GPU binding 4 fail/4 pass/31 deselected →39 pass in2.05s; bash-n pass. Main deployed union151 passed in21.51s. Independent binding review APPROVE. Scope only standalone adapter files.

## Runtime Evidence / Result

First real amp/GPU7 attempt: output `run_logs/m1_reference_validation/20260918_gpu7_8x32_01`, sibling `.log`; PID2818778, run_id `b659aa09-5bda-4ea9-aa7d-4a964fc5bb08`. Command form: `bash tools/m1_reference_validation/run.sh --num-envs 8 --steps 32 --output /home/hexinkun/m1_rl/run_logs/m1_reference_validation/20260918_gpu7_8x32_01` from target root. No automatic retry.

All8 environments have32 first-episode samples, zero resets, no first failure; prepare/IK calls32/32 and128 physical contact updates. Candidate measurement issues empty and module bindings stable. Actual physical GPU UUID ends35b0ae1fd66e, amp Python3.10.21. Full stepping/report collection took72.176s with first-launch cache work.

Then ENV_CLOSED→APP_CLOSED→POST_CLEANUP→native SIGSEGV139. External wrapper reports2 and completed/startup_passed/passed are allfalse. Thus startup is NOT accepted despite full samples. No OOM evidence. Reservation PID2795762 remains untouched. New shutdown child T306.6h.5; diagnostic reproduction is recorded separately in [faulttrace](2026-09-18-m1-reference-gpu7-faulttrace.md). No1600/1024 run.

Physical geometry confirms T306.6h.3: actual exposed bar height0.044999999–0.045000476m, due to source15mm embedding, not60mm aboveground. Preserve source baseline; strict wheel-center clearance remains0.1609m. No scanner own-bar hits or active wave gate in this short pre-obstacle window, so this is not crossing evidence.

## Git Refs

Baseline4220356, runtime featuref5842d4, tested GPU7 bindingddad702. Main independently checked report.json for both runs. Key files: standalone run.py/runtime.py/run.sh; reference and production AME unchanged.
