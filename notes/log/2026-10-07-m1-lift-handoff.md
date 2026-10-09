# Continuous UNLOAD to LIFT: physical flat single-leg lift passes

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),continuous-unload-lift-handoff.
Baseline Ref:6c1d1dd. Candidate Ref: commit containing this log.
Key files:m1_single_lift.py,test_m1_single_lift.py,probe_m1_contact_prepare.py.

## Change

Optional world_feedback carries accepted selected frame into each LIFT IK trial.
Stance9 remain nominal, selected3 receive same bounded vertical-frame correction
as UNLOAD. Height inherited, frameupdated only after executed action. Backtracking
checks composedjoint slew/limits. Disallow combining this with other diagnostic
whole-body/lift-support feedback to keep ownership explicit. Default LIFT remains
unchanged. RED missingkeyword; test fixture then corrected to finish bounded
unload correction before asserting fullframe; GREEN133focusedtests5.14s.

## Physical verification

Same8flatseed2 GPU7 probe.100PREPARE/100UNLOAD/200LIFT budget; .04m/s,.08mtransfer,
--prepare_load_floor --phase_effort --unload_steps100 (actual CLI uses spaces)
--unload_feedback --unload_com --unload_target_force0 --unload_world_pose
--unload_vertical_only --unload_min_speed.003 --lift_steps200.
Raw /tmp/m1_lift_handoff_20261007.log,native0. UNLOAD94samples, then200LIFTsamples,
stopped=null. All200actions execute; no episode reset/guard/effort abort.
Lastpreaction (step199) selectedwheel rise relative frozen phaseanchor:
[.173412,.177971,.174691,.176356,.173240,.178162,.174413,.176377]m;
all target.18m,allvalid/reason0. This covers each selectedleg twice across8rows.
Across all recorded LIFT samples: other3support normalforce minimum36.36996N,
roll/pitch component absmax.0128018rad, ratecomponent absmax.0410707rad/s,
non-supportcontactforce maximum0N. These are measured preaction snapshots, not
substep collision certification or video proof.

## Scope / next

Flat individual-wheel lift established, NOT obstacle crossing. No obstacle in
this diagnostic, no traversal/landing/settle/recovery/bypass orpolicy verification.
Next child controlled-land-cycle: preserve frame/force continuity through held
lift and controlled lowering; confirm contact-guided touchdown/settle for all4
legs before forward traversal over actual obstacle geometry and video. Maintain
singleleg4s total budget, no use of all4s forLIFT then unlimited extra phase.
Need timedphasebudget split for completecycle; no reward-based success shortcut.
No longtraining or push. Own1451314 placeholder stoppedexactly;1479138 restored
verifiedalive. No unrelated process/display/driver changes.
