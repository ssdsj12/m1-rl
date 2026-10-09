# Support reserve constrained by COM displacement

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md),rolling-support-control.
Baseline Ref:9aad7ab. Candidate Ref:containing commit.
Key files:probe_m1_contact_prepare.py,test_m1_prepare_reserve_wiring.py.

## Investigation/change

ROLL transports references by measured forward displacement but does not run
live COM load redistribution. The failing weak wheel had little load reserve.
Expose35/40N planning support floor consistently in PREPARE and coordinated
UNLOAD. Default remains35; actual30N protection and8cm entry bound unchanged.
Configuration wiring RED1failure, GREEN58tests pass13.13s (transfer/lift/settle).

## Physical comparison and reason verification

Same cleanflat8 shoulder-model cycle, only --prepare_support_floor40 added.
Raw:/tmp/m1_shoulder_reserve40_20261007.log;exit0,unload_com_rejected,0LIFT.
Added explicit rejection reason telemetry and reran same configuration:
/tmp/m1_reserve40_reason_20261007.log;exit0,UNLOADstep11,row0reason3.
Required entry displacement0.080264218m > unchanged0.08m bound;
previous accepted0.079092301m. Other rows reason0. Thus larger static reserve
does not fit current allowable translation for all rows, not a CUDA/IK claim.

## Decision/next

Do not promote40N as default or enlarge8cm boundary to pass this test. Need
measured moving load redistribution/speed coordination within available COM
space, with predictive admission before actual30N violation. Original35N default
retained; no production training/teacher changes or crossing acceptance.
Placeholder2265953->2290315->2299107; final own PID verified. No unrelated jobs,
display or driver operations.
