# Active-wheel execution progress

## Scope and evidence

T306 actual10cm crossing remains OPEN. v27 frame150 full LR target exceeds geometric reach9.93mm; common fraction.01123 throttles active leg despite its separate.25-step IK/slew feasibility. A common-height-only .4mm proposal commits5um, so a heave-only patch is insufficient. Actual measured seed crossing.10rad remains a distinct issue; this revision does not relax that gate.

User authorized direct scoped correction and isolated physical validation. No repeated design approval, no production/BC/PPO training. Existing live v27 source is immutable until its final audit ends and evidence is archived.

## Chosen architecture

After the original all-leg feedback transaction has selected a valid physical/support candidate, retain that candidate, all3 support joint targets, support geometry, load/heave histories and scalar fraction exactly. For mode1 LIFT/PASS only, search a larger interpolation fraction for the active leg toward that selected candidate's existing body_goal from FK(last_applied_q). No new target, clearance, phase advancement or success assertion.

Search at most8 coarse fractions1..1/128 and4 refinements; fractions must exceed the baseline. Solve with existing32-step IK/.1mm active tolerance, branch/extension/joint gates. Merge only active-leg IK fields into the baseline solution. Each assembled4-leg candidate must pass finite/allleg validity, alljoint2.5rad/s delta from last applied and original execution_valid callback (encoding/wheel headroom/feedback slew). On failure retain the original safe transaction, never promote an invalid baseline. mode0/RESTORE unchanged.

Scalar execution_fraction remains physical/support history fraction. Add execution_active_fraction explicitly; active body_step uses it, supports use scalar. It is bounded[scalar,1], equals scalar when no improvement. Active world goal does not change, and physical reference progress remains tied to measured lift. Do not infer support safety from IK alone: outer measured load/COM/attitude/collision gates remain authoritative, and next physical frame may reject.

## Alternatives rejected for this revision

Heave-only update was experimentally throttled. Fully independent support leg progress would invalidate zero-sum load-compensation history; it is not included. Numerical seed projection is not bundled: if it remains a physical blocker, diagnose and test separately.

## Verification

Frozen v27 frames122/137/150 must show active fraction above common fraction with unchanged3support joint outputs and unchanged committed load/heave. Alljoint slew and encoded residual gates remain. Negative cases:invalid baseline, mode0/2, invalid callback, nonfinite target, zero dt/invalid shapes, no feasible boost, all4active indices. Audit must reconstruct both fractions and reject tampered active/support steps or fractions. Complete prior772 regression plus new tests, one independent finalreview, then one isolated4env10cm actualcrossing test. Neither CPU success nor nativeexit0 proves crossing; rawwheel/load/obstacle passage and recovery plus video remain required.

Self-review: no relaxation of physical/IK limits; scalar/support state preserved; output evidence covers new degree of freedom. Risk: earlier active movement changes dynamic supportloads; actual test must determine this, not frozenIK.
