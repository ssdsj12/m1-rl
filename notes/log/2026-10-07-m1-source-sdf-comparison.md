# Original-mesh SDF comparison: cooked, but standing contact gate rejects

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), loaded-contact fidelity.
Baseline Ref:191ef3a. Candidate Ref:containing commit.
Key files: m1_sdf_probe.py, probe_m1_contact_prepare.py, test_m1_sdf_probe.py.

## Change versus previous version

Added default-off --diagnostic_source_sdf, restricted to fixed-physics standing
rolling without prism replacement. Uses original points and triangle indices;
runtime asserts they are unchanged. In-memory SDF resolution128 or256, sparse
subgrid6, remeshing=false, triangle reduction factor1. Source USD untouched.
Schema existence alone is not acceptance: runtime checks wheel convex data is
empty and scene has triangle shapes. Actual observed counts in both runs are
33 triangle meshes (32 wheels + terrain),104 remaining convex shapes,8articulations.
This is a collision-representation comparison, not a production tire model.

## Verification

Real USD in-memory tests first failed missing helper (2), then resolution keyword
(2); final8tests passed1.76s including existing diagnostic wheel tests.
CPU schema registration needed PXR_PLUGINPATH_NAME pointing to the installed
plugins/PhysxSchema/resources directory, not just parent plugins. No install edit.

Both GPU7 runs: seed2,8env,M1_OBSTACLE_STAGE=none,flat terrain,fixed physics,
--num_steps100 --standing_roll --standing_effort_steps180 --standing_effort_gain0
(spaces between option and value in actual command), baseline5ms physics,
damping5. Only new SDF mode/resolution changes. Each bounded by timeout300s.

-128: /tmp/m1_source_sdf_20261007.log, session13044 terminalexit0.
  Four standing samples; rejected preaction3. Env6 RAR normal force0N.
-256: /tmp/m1_source_sdf256_20261007.log, session41241 terminalexit0.
  One standing sample; rejected preaction0. Env2/4 FAR0N;env6 RAR5.127N;
  env7 FAR/RAR0N. Tilt remains small (~.002rad), but contact floor>10Nfails.

Both stop=standing_effort_guard_rejected, requested speed0; neither reaches
rolling command atstep60. Do not compare travel or call higher resolution better.
Mass/inertia/material JSON arrays exactly equal between128,256 and existing
fixed-shoulder baseline. Source points/indices retained194634 each perwheel.
No Error/Traceback/cooking-failure matches in logs; this does not prove valid SDF
solid or absence of all simulation warnings. Original nonmanifold faces were
not repaired, and validity/quantization remains an open fidelity question.

## Decision / next

Keep default original collider and all safety guards. No training or success
claim. Next distinguish true intermittent support loss from sampled normal
impulse/contact-sensor behavior using contact geometry and substeps at zero
speed; do not relax support threshold or escalate resolution/gain blindly.
SDF cooking succeeded sufficiently to form shapes, but useful rolling and
original-envelope obstacle crossing are unverified. Geometry defect causality
is still unproven. Placeholder2915023->3067582->3078553 restored and verified;
only these exact own placeholder processes were stopped. No display/driver or
unrelated-process changes. Changes committed locally, not uploaded.
