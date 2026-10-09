# 2026-10-08 native M1 rest-mode rolling counterfactual

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), rolling contact child.
Baseline Ref:8a145fb. Candidate Ref:this rest-mode enumeration commit.
Key files: [enumeration](../../Go2Pvcnn/ame_baseline/m1_wbc_candidates.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-candidates.md).

## Contract and tests

Enumerate every nonempty subset of distinct measured point locations per wheel;
coincident slots share attachedmode but retain individual forcevariables/moments.
Cartesian product cap32; excessive count or missing supportgroup rejects, never
silently truncates. This is geometry enumeration, NOT movingstate validity.
RED4helper +1native wiring tests, then GREEN100WBC regression tests.
Initial native attempt revealed missing M1_WHEEL_RADIUS_M import. Added explicit
AST dependency RED test and importfix; final100passed in2.33s. No CUDA repair.

## Native input and limits

Existing bounded --wbc_snapshot, env0 nativeM/gravity/J/9points, measuredmu,
backend/configured torque limits, groupmin35N, counterfactualv=0. Three masks:
allattached; FARlower-xpointreleased; FARhigher-xcoincidentpairreleased.
Attached materialaccel0; released normalaccel>=0, force0. No smoothcircle migration
assumption. Goalwheelangularaccel uses nominal M1radius only as softtask speed
scale; hard geometry/momentarms remain actualpoints.
QPpriority rootlateral/angular0, then forward.05m/s² and4wheelworldYalpha
.5210612976510557rad/s², then legacceleration minimization. Diagnosticbounds
roottranslation±.05, angular±.2, joint±1rad/s², not productionlimit changes.

## Results

Allattached firsttier status solvedinaccurate after10000iterations (~.032s),
strictly rejected, no force/effort used. This is a numerical limitation, NOT
proof of physical infeasibility. Open conditioning/degeneracy audit required.

FARrearpointrelease (originalslot2,x.27874 vsfrontx.33378):
- valid solved all4tiers, forwardaccel.04999985015m/s²;
- wheelworldY angularaccels [.5210612114,.5210612017,.5210612185,.5210612147];
- combined rollingtask residual2.28598e-7 (mixed task units, not physical tolerance);
- rootlateral/angularmaxerror1.05003e-7;
- releasednormalaccel+.02868155527m/s², releasedforcemax4.35371e-8N;
- independent hardviolation4.28904e-8;
- maxeffort12.12777Nm; rootverticalaccel+.00911213m/s².

Opposite release valid but FAR angularaccel~1.36e-5, targeterror.52104767;
releasednormalaccel~-4.46e-7 within numerical1e-5 check; releasedforce1.27e-6N.
This candidate sacrifices rollingsofttask while respecting hard constraints.
Do not rank modes solely by 'valid' or mislabel softtask failure as success.

## Execution evidence / resource handling

Raw failedimport:/tmp/m1_wbc_modes_native_20261008.log.
Raw completed:/tmp/m1_wbc_modes_native_fixed_20261008.log, localartifactcopy.
--num_steps1 --wbc_snapshot --device cuda:0 --headless,300stimeout. Final
read_only_complete; no applied WBC effort, PREPARE/lift/training.
GPU7 exactplaceholder736509→780416→786369; final736509notreused,786369 confirmed
exactsleep.py solecompute10624MiB. No otherGPU/process/display/driver changes.

Next movingstate gap/slip/velocity guards, solver conditioning and soleowner
torque initialization/stance/rolling, then all4 singleleg obstaclecycles.
Counterfactual feasibility does not prove physical rollout or trained capability.
