# M1 dense forward PPO implementation plan

**Goal:** approved mixed terrain, fixed heading, every spawn facing dense 10cm alternating single-wheel obstacles;2048 environments.
**Architecture:** reserve eight wheel-track anchors before background packing. Extend tile forward extent to16x8m to preserve individual wheel landing space, not fill a solid wall. Keep M1 and PPO unchanged.
**Tech:** Python, IsaacLab4.5 runtime, pytest, shell launcher.

- [ ] Test dense_positions has8front anchors x=.9+.9*i, y=+/- .215 alternating, exact counts, no background inside traversal corridor; reject fewer than8.
- [ ] Add dense_positions using existing structured_positions for peripheral background; retain oldstrategy for oldtests/diagnostics. Route m1_dense_forward through semantic_course.
- [ ] Configure16x8mixedtiles, at least8small each nonplane row, flatcounts unchanged, zero resetxy/yaw, retain10cmphysicalheight. Opposite-front/rear rows staggered. Model axle spacing .544m versus obstacle pitch .9m leaves .356m between nominal front/rear encounters; actual dynamics not guaranteed.
- [ ] Run focused tests and native geometry probe; update probe expected counts.
- [ ] Wait for current model_100.pt, validate load, stop onlyPID2696; run2048health smoke fromsavedPT, then resume remaining planned iterations. No second live training.
- [ ] Update notes/monitor; report actual training and not crossing mastery.
