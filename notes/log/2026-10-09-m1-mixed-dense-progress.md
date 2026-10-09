# SDD ledger — plan: docs/superpowers/plans/2026-10-09-m1-mixed-dense-terrain.md

Spec approved by user: 确认. Existing isolated worktree codex/m1-contact-crossing verified; no superproject, no nested worktree. Baseline29tests pass. Production edits not started.

Pre-flight interfaces: Task1 XY/counts -> Task2 groundedrecords -> Task3 runtime mapping. Shape bounding radius must include cuboid corners. Task2 selectedID/wheel/direction survives action frames and is cleared at reset, not inferred from registry array index. Task3 config activated only once consumers are ready.

Ruling: use a repository plan/ledger plus local staging because skills live on Windows and authoritative Git/Isaac live remotely; no new worktree or dependency installation — avoids copying/overwriting existing dirty M1 fixes. Cost: manual task verification and ledger sync.
Ruling: preserve conservative circumscribed footprint spacing, rather than current nominal diameter circle for boxes — avoids diagonal corner overlap. Cost: fewer feasible candidate positions; exact-count test must prove maximum density.

Task1: complete. Missing-module RED ->23 layout tests GREEN, including20seeds at165small+3large; exact count, conservative spacing, spawn and border protection.
Task2: complete at CPU level. Registry and encounter RED ->GREEN; actual grounded records, row/column mapping, direction latch, padding and reset guards. Native geometry verification belongs to Task4.
Task3: complete at CPU level. Production train defaults to mixed, explicit fixed diagnostic retained. M1 robot/actions preserved. Focused integration83passed/1skipped before final review.
Task4 scene/integration verification: complete. Third probe kCZSgT emitted RESULT and harness exit0;2376records,2280small bounds checked at10cm, representative15/165/0/4,172semantic-small rays with2.2874e-6m top error.4envs x2neutral steps,obs1589/1592,actions16,strict0. No physical crossing claim or long train. Full future-foot-placement and actual crossing acceptance remain OPEN, not marked complete by scene success.

Final independent review: review_m1_dense_course found4important issues. One fix pass: failed-event release, contact-based early lift, all-obstacle/all-wheel landing check, encounter-based primary strict rate. Regression RED19failed/4passed ->GREEN23passed. Expanded suite146passed/1skipped (2026-10-09).
Final: fixed failed-event lock — test_failed_encounter_releases_after_exit_and_next_obstacle_counts_attempt RED→GREEN.
Final: fixed uphill false lift — test_grounded_uphill_motion_is_not_early_lift_and_airborne_uses_last_contact RED→GREEN. Requires measured contact loss AND>=2cm rise from last loaded wheel-bottom position; unload alone insufficient.
Final: fixed omitted large/support landing geometry — registry landing table and4wheel parametrized test RED→GREEN. This gate checks actual support geometry; future trajectory feasibility still needs physical-controller validation.
Final: fixed constant-zero primary strict metric — test_mixed_primary_strict_rate_is_event_ratio_not_fixed_course_completion RED→GREEN. Proxy and episode metrics remain separate.
Final fix-pass edge coverage: early landing then rolling beyond must not reuse prior clearance; abandoned/bypassed encounters must release. Both regressions observed RED ->GREEN. Final expanded suite148passed/1skipped;9runtime modules py_compile succeeds.
Ruling: freeze only the bounded probe's terrain-level curriculum before representative reset — reset legitimately invokes curriculum and otherwise moves the requested test rows. Production curriculum retained. Cost: probe does not validate progression dynamics.
Ruling: require RESULT marker and absence of ERROR marker in addition to process return code — Isaac shutdown returned0 after a caught assertion. Cost: marker-based harness is required when launching this probe.
Ruling: do not commit existing modified integration files wholesale — they contain substantial earlier M1 work unrelated to this task. Cost: integration remains in the isolated dirty worktree until changes can be staged independently.
