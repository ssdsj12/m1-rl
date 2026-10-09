# First 8/8 PREPARE readiness result (not crossing)

Stage: AME contact-driven PREPARE; related
[T306.contact-transfer.front-feasibility](../todo/T306-m1-ame-long-train-stability.md).
Baseline Ref: `8a63752`; Candidate Ref: commit containing this log.
Key files: `m1_load_transfer.py`, `test_m1_load_transfer.py`, `probe_m1_contact_prepare.py`.

## Hypothesis and scoped change

Prior offline measured-support replay estimated approximately70mm total root
translation to reach the soft30mm margin. Expose diagnostic max_root_shift up to
.08m; default stays.06m. Root speed default stays.02; diagnostic requests.04.
No change to hard20mm margin, five fresh stable frames, >10N contact, tilt/rate
or joint slew limits. Five RED tests cover opt-in bound and invalid/unbounded
arguments; GREEN passed.

First bound08 diagnostic: `/tmp/m1_contact_prepare_live_bound08_8x100_20261007.log`,
native0, stops atstep77 on bound in env1. Env1 had already reached readiness at74,
but proposal continued pursuing soft30mm although actual margin23.9mm was above
the hard20mm criterion. Six rows had been ready before stop. This result is failed.

Correct phase behavior: once measured hard margin is reached, hold the previous
command so the five-frame gate can assess stability; do not continue transferring
toward the optional soft target. RED at25mm exposed an unwanted.4mm target update.
Changed stop condition, not acceptance threshold. Ideal-translation convergence
test now checks the design20mm hard target rather than requiring the optional30mm.

## CPU validation

Same ten focused test files as [previous physical evidence](2026-10-07-m1-prepare-physical.md):
**75 passed in3.24s, exit0**. Default6cm behavior retained; explicit bound must be
finite, positive and <=8cm. Joint slew/IK guards unchanged.

## Physical evidence

Actual GPU7/amp, seed2, flat8 environments,32 standing warmup steps,100 PREPARE
control steps atdt.02s, speed.04m/s, bound.08m. Command:
`python scripts/probe_m1_contact_prepare.py --device cuda:0 --headless --num_steps 100 --transfer_speed .04 --max_root_shift .08`.
Log: `/tmp/m1_contact_prepare_hold_ready_8x100_20261007.log`.

- Native exit0, all100 samples complete, stopped=null.
- Final readiness8/8, proposal validity8/8.
- First-ready steps [84,74,8,4,84,74,8,4] for legs[0,1,2,3,0,1,2,3].
- Slowest first ready1.68s, within2s PREPARE window.
- Final measured margins21.45..27.80mm (hard limit20mm).
- Max abs roll/pitch over logged pre-action samples.009302rad.
- Minimum signed vertical wheel force over samples51.95N; max non-support force0N.

Readiness combines actual contact, COM margin, angular/pose gates and five fresh
frames. This is one seed's PREPARE result only. It has no lifting, no crossing,
no substep collision oracle and no video acceptance; not a learned policy model.
Production defaults and old teacher are unchanged.

## Resource lifecycle and next gate

Exact placeholder502175 stopped/restored520658 for first run, then520658 restored
as538748 after second run. Final placeholder observed alive; ldc PID3227360
remained alive. No display/driver edits, no long training or GitHub push.

Next: implement/verify bounded single-leg lift and support-loss recovery using
this PREPARE candidate, then each leg across three seeds, obstacle-specific
traverse/landing/event oracle, video, six-obstacle and bypass gates. These are
still required before controller acceptance and PPO/policy-only training.
