# T306 / required-crossing / model600 contact replay

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
`pure-ppo-learning/required-crossing/policy-contact-stall`.
Baseline: published cd638f4 implementation, 5af7a29 notes; server HEADbb57e7d
plus the deployed repair. Candidate: diagnostic collector only; production
reward, actions, terrain and success thresholds were not changed in this pass.

## Trigger and safe boundary

After99 repaired updates (501..599), no >=2cm early lift or strict crossing.
Iteration599 had nonzero raw progress1.4827368e-5, not an exactly-zero signal;
stage1, strict success0, negative sampled overlap clearance. These are learning
failure observations, not CUDA/runtime failure and not proof that training time
alone can solve it.

Validated this repaired run's model_600.pt on CPU: iter600,next601,stage1,
finite model weights and optimizer/curriculum metadata present. Exact PID12707
cmdline/cwd was checked before TERM and again after30s; TERM stalled, so only
that PID was killed. PT retained. No training or GPU probe overlapped. No old
watcher was restarted; old8573 lineage remains forbidden.

Checkpoint: logs/rsl_rl/m1_cross_large_complex_ame/2026-10-10_20-54-20/bb57e7d/model_600.pt.
Safe eventual continuation is next601 +9399 updates to total10000,2048env,
optimizer/std/curriculum retained. Do not restart until next repair decision.

## Measured replay

Diagnostic [collector](../../Go2Pvcnn/scripts/probe_m1_policy_contact.py) was
copied to /tmp/probe_m1_policy_contact.py, run with native4env/cuda0, exact
flat-first stage1, seed42, no actions overridden. Two1000-step modes: policy
mean and policy-sampled actions, both frozen BatchNorm/eval mode. This is
playback diagnosis, not exact2048-row training-batch statistics or training
with fewer environments. No threshold/gain/teacher changes.

Artifacts: /tmp/m1-contact-replay-600.jsonl (2003records including metadata and
course), /tmp/m1-contact-replay-600.log, /tmp/m1-contact-replay-600-summary.txt.
M1_CONTACT_REPLAY_COMPLETE present. SSH session closed with transport error
during shutdown, so shell exit0 is not claimed; reconnected to verify all2000
frames, completion marker, probe PID13222 absent, GPU only1MiB afterward.
The current train PID12707 is also absent.

Of3996 non-reset env-frames in each mode:

| Measurement | Mean actions | Sampled actions |
| --- | ---: | ---: |
| >=2cm early lifts / strict crossings / recovered crossings | 0/0/0 | 0/0/0 |
| Bound attempts | 2 (both env3) | 2 (both env3) |
| Nominal joint-pose gate passes | 12 | 16 |
| Tilt gate passes | 3996 | 3996 |
| Root-height gate passes | 232 | 644 |
| Loaded touchdown gate passes | 1128 | 245 |
| Joint maximum error mean | .40708rad | .40108rad |
| Root height mean | .53725m | .53714m |
| Maximum tilt | .12617rad | .07754rad |
| Mean body-forward speed | .46439m/s | .51863m/s |

Nominal root is .4560008m. The policy extends the legs and raises the body by
about8cm; low roll/pitch alone does not imply recovery to nominal support pose.
Most worst joint deviations are FBL_KNEE_JOINT. No recovery wiring error was
found: the physical joint/root predicates are actually false.

First failures occur on low-clearance overlap without preceding2cm lift.
Example sampled step232/env3: target FAR wheel bottom .0043765m, prior loaded
bottom -.0003814m, obstacle top .03m => clearance -.0256235m; three other
support wheels loaded but lift is late/insufficient. Mean step442/env3:
wheel bottom -.0002015m, top-clearance -.0302015m. Do not mislabel later
bumps/loaded climbing as pre-contact lifts.

## Reward audit and next decision

The .3 normalized progress budget still ends at2cm; stage1 needs wheel bottom
at obstacle top+.03m (about6cm). Remaining height has no incremental reward.
All positive base shaping, including configured small_obstacle_climb, is
removed in the required slab; Episode_Reward logs are pre-wrapper and are not
the final PPO reward. RequiredCrossing delta is a full-env per-step mean.

Read-only follow-up CONFIRMED the reward bypass, using final PPO rewards, not
raw Episode_Reward logs. Actual centers relative to origins are x2.9000015 and
4.7000008, y+/-.2149963; half extents(.05,.09). Last slab ends atx5.6500008.
Every mean-mode environment has zero strict recovery, yet all372/358/380/379
post-slab frames respectively have positive final PPO reward. Post-slab reward
sums are +12.1015/+10.3777/+12.1838/+12.3165, whereas reward sums inside the
slabs are -2.7652/-3.1848/-3.1097/-4.8771. Sampled mode also yields post-slab
net +7.5836/+6.5314/+6.8811/+8.3367. The finite-slab API has no crossing-state
input, so failed/bypassed routes explicitly regain positive shaping.

Env0..2 miss actual wheel lanes: mean rootY at first block approximately
-.461/-.433/-.339m, and at second -.950/-.859/-.541m. No geometrically eligible
encounter samples were found in these rows. This is primarily lateral drift,
not a phantom-obstacle or registry-detection failure. Independent conservative
wheel-envelope reconstruction corroborates no overlap; the JSON did not save
wheel quaternions, so reconstructed envelopes are not native saved geometry.

Proposed bounded reward fix: retain the positive-reward block after a missed
obstacle until its required wheels have actual strict recovered crossings;
also extend measured, single-airborne-wheel incremental shaping through the
obstacle-specific top+3cm target rather than ending at2cm. Retain collision
costs, no reward for loaded sliding/bobbing, no changed success denominator,
no action takeover or modified std. User-facing design confirmation is needed
under brainstorming before changing this reward contract. Training remains
paused at the saved600 boundary; no production reward changed this pass.

PurePPO,2048 training environments, initial585mm geometry, no speed-error
promotion gate, no teacher/MPC/IK/WBC/servo/display changes remain mandatory.
Actual successful10cm crossing/video remains OPEN.
