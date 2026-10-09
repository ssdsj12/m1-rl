# Guarded phase effort integration

Parent:[T306 feedforward-phase-handoff](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref:c3c6dcd; Candidate Ref:commit containing this log.
Key files:m1_effort_guard.py,test_m1_effort_guard.py,probe_m1_contact_prepare.py.

## Change versus baseline

New fresh-target PD helper uses proposed joint position and zero velocity target
before combined torque guarding (not stale target buffer). REDmissinghelper then
GREEN; focused14-file108tests pass5.82s. Optional --phase_effort requires load-floor
PREPARE, separate from standing experiment. Four-support allocation during PREPARE,
three-support30N allocation during LIFT. Named leg efforts slew20Nm/s across the
phase switch; invalid allocation aborts and clears all rows. Normal/finally paths
also clear and write effort zeros. Default production training unaffected.

## Physical smoke

Flat8seed2, GPU7,32warmup,100PREPARE,budget200LIFT; --prepare_load_floor
--phase_effort --lift_steps200 --transfer_speed.04 --max_root_shift.08, flags and
values separated. Raw:/tmp/m1_phase_effort_20261007.log; native0.
PREPARE100steps, readiness8/8. LIFTstops atstep7:lift_effort_rejected, allocation
invalidrows0,1,5,6. Original pose/contact lift guard stillvalid8/8. Actual nonselected
loads remain>30N; hypothetical post-unload30N equilibrium no longer accepted.
Measured wheel rise negative(-3.50..-.79mm), target6.4mm: no actual lift success.
Cleared=true. This earlier stop is a new allocation guard, not proof of support loss.

## Interpretation and next

Current trial starts height progress simultaneously with a rate-limited effort
transition from four to three contacts. Atstep7 the transition has not reached its
new target; the selected wheel still bears37..63N. Therefore add a bounded
UNLOAD/settle handoff holding height until actual unload/remaining supports and
effort tracking are ready, instead of assuming instantaneous three-contact control.
Preserve30N and shift/pose/IK constraints; no claim that this change alone will
solve balance. Then physical handoff and lift, followed by full crossing/recovery/
landing/collision/bypass/PPO. No long training or upload.
Own954856 placeholder restored973880 and verified alive; ldc3227360 untouched.
No display or driver changes.
