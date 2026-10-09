# Sustained rolling diagnostic

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), effective-rolling-progress.
Baseline Ref: 055602c. Candidate Ref: containing commit.
Key files: m1_rolling_speed.py, probe_m1_contact_prepare.py, test_m1_rolling_speed.py.

## Change and test

Added explicitly bounded 180-step standing rolling diagnostic: 60 settling,
100 rolling, 20 stopped. Existing 100-step comparison remains unchanged.
No lift or training permitted in this diagnostic. Same acceleration limit
0.2 m/s^2, speed cap 0.1 m/s, normal guards and collision geometry.
TDD RED: 1 failed/9 passed (missing standing_window). GREEN: 21 focused tests
passed in 1.42 s (rolling speed, support effort, effort guard).

## Physical verification

GPU7, eight flat environments, support feedforward gain 0 and wheel damping 5.
Command: `python scripts/probe_m1_contact_prepare.py --device cuda:0 --headless --num_steps 1 --standing_effort_steps 180 --standing_roll --standing_effort_gain 0`.
Raw: `/tmp/m1_sustained_roll_20261007.log`.
Exit 0; 180 samples; stopped=null; cleared=true.
Rolling-window world X displacement (sample160 minus sample60), mm:
[-0.33623,-0.34857,-0.33605,-0.33638,-0.34426,-0.34873,-0.33643,-0.33822].
Command profile integral 0.148 m; this is NOT actual distance.
At sample110 all wheel targets 1.04212 rad/s, actual 0.13078..0.18449 rad/s.

## Conclusion and follow-up

Near-zero traversal persists after a sustained constant-speed segment, not
just the prior short startup window. Root cause still unresolved. Next obtain
accumulated wheel rotation and contact-point kinematics to distinguish slip,
oscillation and unintended constraint. Do not compensate by weakening gates.
No obstacle-crossing success, new training or production gain changes.
Exact placeholder 2043200 stopped; 2060766 restored and verified.
