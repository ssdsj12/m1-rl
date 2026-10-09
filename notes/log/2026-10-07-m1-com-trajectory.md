# COM trajectory transient evidence and bounded reference primitive

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md),rolling-support-control.
Baseline Ref:5619fee. Candidate Ref:containing commit.
Key files:m1_com_trajectory.py,test_m1_com_trajectory.py.

## Evidence changing next action

Read existing /tmp/m1_moving_support_frame_20261007.log, not a new physics run.
Env3 step94->96: FBL HIP PD -3.2158->-1.9322Nm and KNEE PD -.8217->+.7566Nm;
their feedforward changes only -2.9309->-2.9260 and -3.3267->-3.3080Nm.
Static allocation FBL37.5829->37.4833N, effort tracking error.01149Nm at96.
Actual weak contact falls34.6866 at95 ->32.9743 at96 ->28.7684 at97.
Thus the complete position-plus-feedforward response cannot be inferred from
the static allocation alone. This does not prove a complete inertial balance or
that acceleration smoothing will fix stability. Do not reverse correction signs
or increase gains merely from the weak contact reading.

## Implementation / scope

Add isolated com_step reference primitive: planar damped approach (36*error-
12*velocity), vector acceleration cap.05m/s2, speed cap.04m/s,dt<=.02s;
offset bound.08m. Invalid/nonfinite/out-of-bound rows return invalid, no clipped
success. Target reversal brakes instead of instant reversal. These are diagnostic
reference parameters, not proved physical limits or a whole-body controller.

Not wired into runtime yet. Integration must preserve velocity state through
ROLL->LAND->SETTLE rather than abruptly freezing offset at phase boundary;
check complete prepared-root displacement (not just offset norm), final actual
joint slew, contacts and4s deadline. Caller must recover on invalid proposal.

## Verification

TDD RED2 missing module. GREEN start/brake/end and invalid-input tests; added
reversal and bound regressions. Full relevant suite77passed13.14s (trajectory,
moving-load, transfer, lift, settle, rolling speed). git diff --check clean.
CPU reference tests are not physical acceptance. No new GPU probe or training.
Own placeholder2471170 still live, unchanged. No original checkout or display edits.

## Follow-up

Integrate opt-in continuous trajectory state with joint/entry-bound checks, then
matched fixed-physics smoke. If physical load still worsens, investigate full
support wrench/position-controller interaction rather than further static tuning.
Original wheel fidelity, obstacle traversal, video, PPO and policy-only acceptance
remain open. No completion claim.
