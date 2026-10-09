# M1 crossing time-budget audit

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline/Candidate Ref: f3b07f5 (read-only CPU audit; no controller change).
Key files: Go2Pvcnn/ame_baseline/m1_single_lift.py and scripts/probe_m1_contact_prepare.py.

## Procedure and evidence

On the remote amp Python, call the actual lift_target with four named-leg rows,
nominal root Z .554 m, joints [0,-.57,1.1] repeated, FK anchors, dt .02 s,
finite stable synthetic forces/pose/margin. Raise to .15 m, then lower to zero;
record each row's first arrival. No GPU/placeholder/process changes.

All four rows require 110 upward and 109 downward steps: 4.38 s total.
Remaining time under the approved 4 s action limit is -0.38 s, before any
forward traverse, contact search or real tracking error. This is a CPU nominal
IK timing result, not physical stability or crossing evidence.

The current vertical speed cap .08 m/s alone gives a 3.75 s continuous lower
bound for this path. Discrete Cartesian backtracking under .5 rad/s joint slew
adds time. The successful flat 90/110 trial therefore cannot establish a
10 cm obstacle plus 5 cm clearance cycle. Current probe also holds wheel speed
zero and world anchors fixed; merely adding wheel speed creates contradictory
support references.

## Conclusion and next

New obstacle-cycle child: trajectory-budget-feasibility. Before obstacle smoke,
measure joint-path time bounds and a rolling-aware horizontal trajectory with
explicit near/far boundaries. Preserve 4 s, joint slew, actual clearance and
support gates; reject infeasible cases rather than lower acceptance thresholds.
Investigate safe progress lost to discrete backtracking separately from the
physical trajectory requirement. No long training started.

Upload remains uncompleted: HTTPS push lacked credentials. Existing source
commits are intact; no force push or changes to original checkout.
