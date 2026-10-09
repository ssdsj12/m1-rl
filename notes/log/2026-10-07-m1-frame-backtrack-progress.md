# Frame backtracking progress and physical rejection

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),selected-frame-slew.
Baseline Ref:0d7479d. Candidate Ref: commit containing this log.
Key files:m1_selected_world.py,test_m1_selected_world.py,probe_m1_contact_prepare.py.

## Diagnostic evidence and fix

Raw /tmp/m1_world_rejection_20261007.log,native0: last full candidates all safe,
reachable, within jointlimits, but required .01524..03181rad vs.01rad per-step.
Backtracking always started from nominal frame, so .5 stayed a discrete plateau.
New previous_frame carries accepted IK frame. Backtracking interpolates from it
toward fresh live pose; nominal stance9 joints unchanged. No gain/limit relaxation.
Frame resets on phase entry; finite/bounded previous-frame checks. Diagnostic
fullcandidate fields distinguish safe/reachable/limits/slew and maxjoint/delta.
RED missing-full-field and missing-previous_frame tests, then GREEN127tests5.09s.
Repeated-frame regression proves full FKtarget convergence under .5rad/s limit.

## Physical result (not accepted)

Same8flatseed2GPU7/100PREPARE/100UNLOAD/200LIFT budget,zero force/world pose flags.
/tmp/m1_world_incremental_20261007.log,native0: unload_world_pose_rejected at25,
0LIFT. Fullscale1 achieved prior to rejection. Follow-up unchanged controller
with rejection print /tmp/m1_world_incremental_reject_20261007.log,native0,
reproduces row5 safe=false at25; reachable/limits/slew alltrue for all8.
Thus the discretization defect is fixed but live-vs-command frame safety bound
is now the physical blocker; do not claim unloading/crossing improvement overall.
The combined safe flag does not yet identify translation vs attitude vs priorframe.
Next child frame-divergence: expose these residuals and separate intended COM
translation from unintended sag before altering correction ownership. Keep25mm/
.08rad gates, do not globally loosen or start training. LIFT handoff remainsopen.

Own placeholders1310281->1339429->1357062->1369869 through exactPID lifecycle;
final1369869 verifiedalive. No unrelated process/display/driver mutation or push.
