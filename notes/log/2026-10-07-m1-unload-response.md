# Unload realized response audit

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), unloading-convergence.
Baseline Ref:05dd6fb. Candidate Ref: commit containing this log.
Key files: probe_m1_contact_prepare.py, test_probe_evidence_contract.py.

## Procedure and scope

Read-only evidence additions: world wheel displacement relative to frozen anchor,
measured root, previous-command joint tracking error, effort-settle/load-ready
booleans. No control parameter or guard change. RED missing-field assertion;
GREEN48 tests (evidence contract, unload reference/gate, load transfer).
Same flat8 seed2 GPU7 probe as prior log with --unload_target_force 0,
100PREPARE/100UNLOAD/200LIFT budget, .04m/s/.08m transfer.
Raw /tmp/m1_unload_response_20261007.log. Native0; unload_timeout,0LIFT.

## Evidence

Rows0..7: final selected-force9.36,10.01,11.41,13.61,19.09,9.87,12.92,13.65N.
Commandheight3.70..6.44mm; actual wheel deltaZ relative to frozen anchor
-3.81,-.54,-1.52,.07,-3.66,-.36,-1.52,.09mm. These deltas include PREPARE
motion and are not absolute ground clearance. Root is4.59..5.18mm below command.
Max joint tracking error approximately .02..03rad.
Effort hold count42,41,32,33,43,41,32,33 of100; load hold4,0,0,5,4,0,0,5.
Thus load reserve gating is not the dominant delay. Reference advance consumes
only the remaining budget after effort transition, while realized vertical pose
does not follow the requested geometry. Cannot infer causality from root sag
alone or treat normal-only contact as full inverse dynamics.

## Next

Child unloading-realization under unloading-convergence: inspect selected-vs-
stance joint error and initial/late force slopes, then design bounded vertical
pose/effort coordination with fresh actual kinematics. Need architectural review
before adding another gain or lifting limit. Do not merely increase timeout,
relax5N/30N gates, or start training. Full obstacle crossing remains unverified.
Own1224540 stopped exactly;1254648 placeholder restored verifiedalive. No other
process or display changes. No push.
