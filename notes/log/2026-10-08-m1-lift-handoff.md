# 2026-10-08 measured lift-to-roll handoff

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), baselinea22aed1.

## Evidence and implementation

Replay of original and pair-cleaned logs: no row has five consecutive preROLL
samples satisfying target-height error<=1mm, measured vertical speed<=.01m/s,
remaining supports>=30N, selectedcontact<=10N, existing posture/margin/collision
conditions. Fixed step90 transition is not a measured settling test.

New explicit default-off lift_handoff gate counts five consecutive valid samples.
Step gaps reset the streak; collisions poison this same-episode gate. Instantiate
again for new episodes/leg batches. Standalone eight-row diagnostic startsROLL
when all rows qualify; this is not the final independent per-environment teacher.
Existing observed support/effort checks remain active through all later phases.

TotalLIFT+ROLL+LAND budget remains200steps/4s; waiting does not extend it. Reserve
ceil((target_height+land_search_depth)/vertical_speed/dt) minimum landing steps
and unchanged20ROLL steps. This lower bound does not promise feasible IK descent;
remaining physical gates may still reject. If no readiness before deadline111,
reject lift_handoff_timeout. Roll speed profile/transport uses actualroll age.
Original5ms/sourceSDF128/uncleanedmesh baseline used for comparison.

## Verification

RED3missinggate tests and missing runtimewiring test; GREEN55 gate,prepare,
rolling,observer andsinglelift regressions. Raw physical log
`/tmp/m1_lift_handoff_20261008.log`. No training or crossing success claim.

Physical: all8 become ready at96 (firstindividualready94..96), then execute5ROLL
actions; at101/ROLL5 row7FBL21.1639N rejects advancement. Heights160.004..160.269mm,
landing_completefalse. Handoff requirement now met; sustained dynamic support
is independently still insufficient. Do not label this a crossing fix.
Ownplaceholder62471 stopped after verification;99388 restored soleGPU7compute.
Default physics/mesh unchanged, sourceasset untouched. No longtraining.

Next: rolling contact wrench/stance control rather than more entry waiting or
mesh/resolution sweeps. Current vertical-only static effort model omits tangential
traction and angular momentum; stable entry alone does not certify rolling.

## Follow-up architecture audit

Same final101 row7 actual wheel triangle/COM gives static normal loads
[43.195921,185.449983,174.008681]N versus measured
[21.163919,186.665604,179.214478]N. Last5ms wholeCOM acceleration
[.0199256,.192483,-.380326]m/s2 implies horizontal resultant
[.817851,7.900508]N for41.045319557kg. This is measured momentum change,
not a desired control wrench or unique root-cause proof.
Current vertical_support_solution intentionally omits these horizontal forces
and angular dynamics. User design confirmation requested before replacing the
diagnostic quasi-static architecture with bounded 3D contact/full-body control.
Do not treat this as authorization to change motor modes, thresholds or budgets.
No newGPUrun; verified current placeholder99388 remained running.
