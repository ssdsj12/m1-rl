# M1 mixed-terrain migration dependency audit

Date: 2026-10-09. Stage: environment/layout and measured crossing contract.
Parent: [T306](../todo/T306-m1-ame-long-train-stability.md).
Baseline ref: `0768d96645c86d8bb635a9f76cb110cf17d9ef78`.
Candidate: existing dirty `codex/m1-contact-crossing`; no production edit this pass.
Reference: lukeyang117/Go2Pvcnn `m1_rl`, SHA `a5b5c5f32f80192452f5326cb25f173ddeaa21b5`.

## User contract

Keep M1. Use reference default train mixed terrain; increase only flat small
obstacle counts by approximately 50%. See [design](../../docs/superpowers/specs/2026-10-09-m1-mixed-dense-terrain-design.md).
Prior goal turn yielded source evidence and was progress, not a live-process wait.

## Source audit

- Reference scripts/train.py defaults to teacher_elevation_trajectory_mpc_semantic.
  Its scene uses UNITREE_GO2_CFG; do not copy robot/actions into M1.
- Default terrain: 8x8m,10rows,20cols, seven families (flat/rough/slope/inverse
  slope/boxes/stairs/inverse stairs). Plane small sequence10,30,40,50,60,70,80,
  90,100,110; 1.5x gives15,45,60,75,90,105,120,135,150,165.
- Current ame_baseline/m1_ame_env_cfg.py binds fixed six small coordinates and
  disables terrain_levels. extension/semantic_course.py `_stage_slots` raises
  if requested fixed count exceeds supplied points. This is not just a count edit.
- ame_baseline/ame_env_wrapper.py initializes tracker capacity6, triggers from
  fixed coordinates, constructs strict world centers from env origin+fixed XY
  and configured height. Random new obstacles would disagree with that path.
- Importer currently does not retain grounded obstacles as a consumable registry.
  Reset/terrain changes and direction-aware event identities need explicit handling.

## CPU layout experiment

Read-only AMP Python stdin, OMP_NUM_THREADS=1. Existing test helper stubs only
Isaac TerrainImporter; real `_stage_slots` sampling/spacing code is executed.
For seed0..9, row9,col0,stageS4, tile8x8m, reset half extent.85m, margin.5m,
small diameter.05/height.10 and large diameter.45/height.55, request
15/45/90/165 small plus3large. Verify exact returned length; catch layout errors.

| Edge clearance | Small count | Seeds completing |
| --- | --- | --- |
| .45 m | 15 / 45 / 90 | 10/10 each |
| .45 m | 165 | 0/10 |
| .15 m | 15 / 45 / 90 / 165 | 10/10 each |

Failure: `semantic obstacle layout exhausted all candidates while preserving safety/spacing`.
Conclusion: current random layout cannot satisfy tested maximum density with
current M1 clearance. .15m is a diagnostic comparison only, NOT deployed and
NOT verified safe for M1 landing. Need structured placement and full count/safety
verification; do not silently reduce obstacle count or landing space.

## Previous live measurement result recovered

`/tmp/m1_bottom_runtime_20261009_EAoyQm.log` contains both step0/1 and
M1_MEASURED_BOTTOM_RUNTIME with2finite frames, mesh shape4x2259x3, strict_crossings[0].
Wheel bottoms range .000177346--.000279732m across those2neutral PD steps.
PID287470 absent on readback. No exit status recovered in this pass, but final
measurement marker was emitted. This is live measurement integration only,
NOT lift, Climb pose, crossing or training readiness.

## Process state and limits

Fresh user-process readback found no M1 train/probe; GPU7 placeholder PID1768831
still running and untouched. No training/display/robot control initiated.
No physical crossing acceptance or new checkpoint. Notes/design only changed.
Open child T306/mixed-terrain-registry depends on placement, registry, event
mapping; sibling Climb-pose-source and physical lift/roll/landing remain open.
