# Continuous COM trajectory integration / measured rejection

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md),rolling-support-control.
Baseline Ref:35176cc. Candidate Ref:containing commit.
Key files:probe_m1_contact_prepare.py,test_m1_com_trajectory.py.

## Implementation

Opt-in roll_com_trajectory requires roll_load_feedback. Keep offset and velocity
through ROLL/LAND/SETTLE; latch landing-entry offset as braking target rather than
resetting velocity. Validate complete prepared-root displacement against configured
bound, final actual-joint IK/slew and existing contact guards. Commit trajectory
state only after action. Landing completion additionally requires reference speed
<=.0001m/s. Default remains off; production training unchanged.

## Tests and physics

Wiring RED1failure, GREEN78passed13.16s, diff-check clean. Same controlled
8env seed2 none-stage shoulder diagnostic as prior moving-load run, adding only
--roll_com_trajectory. Raw:/tmp/m1_com_trajectory_runtime_20261007.log.
Exit0 but physical rolling_support_rejected103, landing_complete=false;
row3 FBL29.9284N<30N. Direct feedback rejected97; no-feedback baseline105.
Both feedback comparisons use support-centroid transport; baseline uses root
transport, so do not compare their progress signs as identical metrics.
Last centroid progress.015.. .186mm is not effective traversal, let alone crossing.

At103 all trajectory proposals valid; row3 proposed offset x/y=.2038/.1507mm,
reference speed~.00213m/s. Full entry shift row3=.013037m, row0=.076671m.
The failed row has much more COM room than the front-lift row that blocked the
earlier uniform40N reserve test. This makes per-selected-leg preload feasibility
a concrete next action rather than relaxing8cm for all rows.

## Decision / next

Smoothing reduces direct-feedback transient harm but does not fix support.
Keep experimental options off and do not train. Next evaluate direction/leg-aware
preload before rolling/lifting, checking each row's actual constraints rather
than uniformly increasing reserve or waiting for contact force to fall. Physical
LAND velocity continuity remains untested because rolling failed first. Original
geometry fidelity, actual obstacles/video/PPO acceptance all remain open.
Placeholder2471170->2523812 restored and exact own process verified. No unrelated
GPU, original-checkout, driver or display changes.
