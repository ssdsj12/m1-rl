# M1 teacher lift evaluation — 2026-10-01

- GPU policy: the 100-update controlled evaluation ran only on `CUDA_VISIBLE_DEVICES=7`; the wrapper restored `/home/hexinkun/sleep.py` afterward. GPUs 3–6 were not touched.
- Runtime change: `ame_baseline/m1_mpc_teacher.py` now adds a serial single-leg minimum lift (default hip `-0.35 rad`, knee `+0.80 rad`) only to the selected swing leg; stance legs retain measured pose.
- FK evidence: wheel-bottom clearance reached 0.018 m, 0.040 m, 0.064 m, 0.090 m, 0.118 m, 0.147 m over six successive control updates.
- Focused tests: 38 passed.
- 30-update blend=0.5 smoke: `base_contact=0`, `bad_orientation=0`, geometry collision about `-0.75`, strict crossing `0` (too short for a complete pass).
- 100-update blend=0.5, learning-rate=0 evaluation: `base_contact=0`, `bad_orientation=0`, strict crossing `0`, geometry collision varied `-0.36` to `-1.20`; no long training was started because the full crossing acceptance gate was not met.
