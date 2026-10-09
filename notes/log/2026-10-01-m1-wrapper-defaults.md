# M1 serial teacher wrapper defaults

- Change: GPU7 wrapper now exports the validated Cartesian IK teacher defaults and bypasses the legacy early-roll mask when the deterministic serial trajectory is enabled.
- Verification: `tests/test_m1_teacher*.py`, `tests/test_m1_online_teacher_schedule.py`, and `tests/test_m1_teacher_episode_reset.py` passed (`15 passed`).
- Physical smoke: wrapper invoked without any M1 environment overrides for 160 PhysX steps; `teacher_valid_steps=160`, `max_commanded_leg_count=1`, `max_wheel_bottom_m=0.2320`, `max_tilt_rad=0.1351`, `geometry_collision_steps=0`.
- Resource handling: GPU7 placeholder stopped and restored; GPU3-6 untouched.
- Follow-up: run a longer repeated-obstacle smoke with collision trace before starting PPO training.
