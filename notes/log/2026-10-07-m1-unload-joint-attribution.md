# Unload joint attribution and architecture checkpoint

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), unloading-realization.
Baseline/Candidate code Ref:0c2d157 (no controller change).
Input: /tmp/m1_unload_response_20261007.log, previously verified native0.
Procedure: select planner-leg triplet row%4 from signed joint_tracking_error;
compare absolute maxima with other triplets; compare force at40/70/99 and count
effort_settled_before false over70..99. This is offline analysis, no new simulation.

|row|selected error rad|stance error rad|force40 N|force70 N|force99 N|unload deltaZ mm|
|---|---|---|---|---|---|---|
|0|.00641|.02382|45.01|26.83|9.36|-.002|
|1|.00351|.03276|26.09|15.28|10.01|1.001|
|2|.00786|.02883|21.04|15.47|11.41|1.291|
|3|.00378|.02984|45.59|29.18|13.61|.994|
|4|.00967|.02723|47.03|31.16|19.09|.028|
|5|.00319|.03201|26.57|16.45|9.87|1.217|
|6|.00658|.02814|24.14|18.13|12.92|1.335|
|7|.00383|.02975|40.17|23.07|13.65|.983|

All rows have zero effort holds in last30steps. DeltaZ here is last minus first
UNLOAD sample, unlike previous log's displacement from pre-PREPARE anchors.
Conclusions: finite deadline missed, not demonstrated steady-state stall. Force
continues falling. Largest joint error is on stance legs, not selected leg.
Actual selected wheel unload rise<=1.34mm, not meaningful obstacle clearance.
Root sag and tracking correlation do not independently prove causal attribution.

## Architecture decision pending

Do not introduce global PD cancellation or blindly increase lift gain. Prior
pose-only feedback failed without contact effort; simply repeating it is not
evidence. Proposed next bounded experiment should explicitly coordinate stance
height/attitude tracking with existing three-contact allocation, and separate
measured unloading from desired Cartesian reference. Keep all physical gates,
limits, anchor identity and recovery requirements. Review frame consistency and
which loop owns each target before implementation; do not have independent loops
integrate the same root correction. Full crossing/landing/bypass still unverified.

Current state check:worktree clean at start, own1254648 placeholder alive, no
own train/probe process. No GPU workload launched, no display/driver/process
mutation, no training or push during this audit.
