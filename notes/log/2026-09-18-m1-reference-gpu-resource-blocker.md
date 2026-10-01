# Reference validation GPU4 resource blocker

## Purpose / Stage / Todo

Prelaunch resource safety check for independent M1 controller validation. New childT306.6h.4 blocks physicalTask5, not CPU adapter correctness. Related [T306](../todo/T306-m1-ame-long-train-stability.md), [runtime verification](2026-09-18-m1-reference-runtime.md).

## Procedure / Inputs / Evidence

At2026-09-18 14:22CST, read-only `nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader`, GPU4memory/utilizationquery, and`ps -p 2600089,2600090,2600091,2600092 -o user,pid,ppid,lstart,args`.

- PhysicalGPU4 UUID `GPU-930f9e84-5ed8-b68c-21b7-3c6759aeb7df`:24564MiBtotal,21710MiBused,2372MiBfree,100%utilization.
- GPU4primaryallocation:PID2600089,20514MiB; threeothercontexts390MiBeach. Allbelongto`liuxx`, started13:41:34, runninganotherproject's`train_pytorch_recon_img.py`, notM1orourvalidation.
- OtherGPUsalsooccupiedaround21.7GB. Earlier13:33GPU4idlecheckwasvalidthenbutnotpermissiontoignorefreshstate.
- Standaloneadapterf5842d4, bothreviewsPASS,150CPUtestsPASS. NoIsaacsimulationortrainingstartedthisturn; no8/1024behaviorresult.

## Result / Follow-up

Stoppedbeforelaunch. Didnotkill,signal,modify,orinspecttrainingdataofotheruser'sjob;didnotchooseanotherGPUorrestartoldsupervisor. NeedusercoordinationofGPU4availability. Noautomaticmonitorcreatedunderthiscontroller-onlydesign. Whenavailable,recheckownership/resources,thenstartfresh8×32withindependentoutputdirectory; do notskipstrict8-envgates.

## Git Refs

Baseline/CandidatefeatureRef:f5842d4. PhysicalverificationRef:none. ProductionAMEandreferencecodeunchanged.
