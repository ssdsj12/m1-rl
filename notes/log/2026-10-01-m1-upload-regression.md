# M1 teacher physical regression after repository upload

- Purpose: verify the uploaded M1 source still creates a GPU7 PhysX teacher probe.
- Command: `scripts/probe_m1_teacher_physx.py --num_steps 80 --device cuda:7 --headless` through `run_m1_train_with_placeholder.sh`.
- Resource contract: the wrapper stopped and restored `/home/hexinkun/sleep.py`; GPU3-6 were untouched.
- Verification: `13 passed` for `tests/test_m1_teacher*.py`; probe created the environment and reported 80/80 valid teacher steps, one commanded swing leg, zero geometry-collision steps, max tilt 0.132 rad.
- Remaining gate: maximum wheel-bottom height was 0.0767 m, below the 0.15 m target for a 0.10 m obstacle plus 0.05 m clearance. No long training was started.
- Follow-up: continue support-leg/foot-trajectory tuning and rerun the physical gate before training.
