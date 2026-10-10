# Flat-first boundary regression watch

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline bb57e7d; candidate codex/m1-contact-recovery existing uncommitted diff.
No runtime code or configuration changes in this check.

2026-10-10 15:54 CST heartbeat: exact PID7747 verified, 2048 envs,
flat-first, GPU0, iteration407/10000. model_400.pt saved in the existing
2026-10-10_14-16-08/bb57e7d run. No extra native simulation launched.

Read process command, checkpoint listing, production env_cfg.yaml and log
window trends. Stage remains0. At iteration278 pass_rate1.0 and speed error
.0896; at407 pass_rate.5879, speed error.1342, course_boundary.4141.
Base-contact/bad-orientation/nonfinite termination metrics remain0.
Boundary metric starts rising around325 and worsens across multiple windows.
No Traceback/CUDA error/out-of-memory/Fatal Python match in current log.

Code inspection: boundary uses actual terrain tile center, root and tire XY
envelopes. Velocity reward tracks body-frame XY with exp(-squared_error/.25),
weight1.5. Neither proves the direction or physical cause of the excursion.
Production logs lack pre-reset boundary position and signed velocities;
overspeed versus yaw/lateral drift is unresolved. Do not loosen the boundary
or promotion thresholds, and do not claim a fix based on these metrics.

Next diagnostic dependency: capture pre-reset root/tire XY relative to tile,
body/world velocity, command and orientation on a bounded checkpoint rollout.
Use only this flat-first run; pause verified current training at a saved PT
boundary before native replay (training uses about22GB). Do not run a native
probe concurrently. Then make only evidence-backed reward/terrain corrections.
