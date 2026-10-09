# SDF contact substeps and effective conservative contact margin

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), loaded-contact fidelity.
Baseline Ref:46b6d53. Candidate Ref:containing commit.
Key files:probe_m1_contact_prepare.py,m1_contact_snapshot.py,m1_sdf_probe.py,
test_m1_contact_snapshot.py,test_m1_sdf_probe.py,audit_m1_sdf_surface.py.

## Improvement relative to previous version

Read-only standing/warmup substep observer records native force, sensor force,
independent env6RAR contact pairs, gaps, body pose and velocity. Reuses tested
scene.update wrapper; no extra physics steps. Contact-buffer offsets have tests.
Added explicitly opt-in1mm SDF rest margin and matching2mm contact detection
offset when inherited automatic contact offset is insufficient. Defaults stay
unchanged. Native readback must find requested margin on exactly32wheel shapes;
otherwise refuse the comparison rather than interpret a no-op as a failure.
Original mesh points/indices, masses/inertias/materials remain unchanged.
Numerical collision envelope expands by1mm; this is NOT identical contact
geometry and must retain original-envelope crossing oracle and fidelity checks.

## Evidence: why previous zero-force gate fired

GPU7 SDF128 same fixedphysics8envseed2 standing setup as previous log.
Raw /tmp/m1_sdf_contact_substeps_20261007.log session94761 and
/tmp/m1_sdf_contact_pose_20261007.log session18203, terminalexit0.
Observer standing JSON exactly equals no-observer baseline: same preaction3
rejection, no added motion/control change. All44observed substeps have matching
sensor/native/independent pair net forces. Last control action has RARzforces
97.98099,94.02765,83.62064,0N. Endpoint has6nearby contact points but all0impulse,
positive separations .3912.. .6844mm; not stale force-cache evidence.
Control-window mean68.907N is NOT substituted into the strict support gate.

CPU original triangle surface reconstruction from relative USD transform and
recorded link quaternion finds minimumz=-.02037mm before last substep and
-.37723mm afterward; contact separation is a different sampling/representation
quantity. This exposes discrepancy, not proof of total physical wheel lift or
a complete signed-distance error bound. No source mesh repair performed.

## Invalid margin attempt and correction

/tmp/m1_sdf_rest_margin_20261007.log session10885 had identical trajectory;
/tmp/m1_sdf_offset_readback_20261007.log session78480 exposed authored1mm but
native0rest, automatic wheel contact offset .929976mm. Contact must exceed rest;
this pair violates that requirement. Do not classify this no-op as physical
evidence against a margin. Added explicit2mm contact offset and native fail-closed
readback. Existing larger authored contact offsets are preserved by CPU test.

## Valid margin comparison

RED tests missing helper, keyword and auto-contact behavior; final14focused
tests pass1.73s using real USD schemas plus contact snapshot/substep tests.
Raw:/tmp/m1_sdf_valid_margin_20261007.log, session86414 terminalexit0.
Same sourceSDF128/fixedphysics/8envseed2/5ms physics/damping5/FF0,
--standing_roll --standing_effort_steps180 --diagnostic_source_sdf
--diagnostic_fixed_physics --diagnostic_sdf_rest_offset .001
--standing_contact_substeps (actual flags have spaces before numeric values).
Native offsets32wheel shapes:rest.001,contact.002; remaining shapes unchanged.
Mass/inertia/material arrays exactly match no-margin sourceSDF baseline.
180standing samples, stopped=null, cleared=true. Step160 minus60 world-X mm:
[112.3988,112.8701,112.8856,112.6340,112.9700,112.9074,113.1531,112.7382].
Minimum sampled wheel normal force51.8737N; final maxroll~.00104rad,
maxpitch~.00220rad. This demonstrates effective four-support rolling only.
Do NOT report obstacle crossing, a learned policy, or three-support acceptance.

## Next and safety

Proceed to matched full single-leg lift/three-support rolling/landing using this
candidate, with unchanged force/pose/joint guards. Then real obstacles, original
envelope5cm clearance, stablefar-side landing, bypass and video/policy acceptance.
No long training until these gates. No production asset/display/driver changes.
Own placeholders3078553->3108173->3121569->3136762->3148953->3162948 only;
last exact placeholder restored and verified. No unrelated process touched.
Local commit only; upload still not claimed. Todo/branch/log updated.
