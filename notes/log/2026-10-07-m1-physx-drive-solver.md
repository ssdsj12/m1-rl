# PhysX drive readback and velocity-iteration comparison

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), effective-rolling-progress.
Baseline Ref:e681e8c. Candidate Ref:containing commit.
Key files:probe_m1_contact_prepare.py,m1_rolling_speed.py,test_m1_rolling_speed.py.

## Backend readback

Read actual root_physx_view get_dof_stiffnesses/get_dof_dampings/
get_dof_max_velocities instead of relying only on ArticulationData caches.
All8x4 wheel drives:stiffness0,damping5,maxvelocity20.842451rad/s.
Raw:/tmp/m1_actual_drive_20261007.log; bounded1-step probe exit0.
Thus there is no detected stale position-spring drive or low speed cap.

## Single-variable comparison

Added opt-in standing-only velocity-iteration comparison0/4; default remains0.
TDD:RED1missing-function failure/10pass; GREEN22focusedtests pass1.69s.
Same180-step flat8 diagnostic, gain0,damping5,0.1m/s cap, unchanged geometry.
Command adds `--standing_velocity_iterations 4` to prior sustained probe.
Raw:/tmp/m1_solver4_roll_20261007.log. Exit0,180samples,stopped=null.
Articulation USD attribute read back4 after environment reset.
Rolling-window X changes(mm):[-.37287,-.38374,-.37038,-.37468,-.37941,-.38280,-.37008,-.37448].
Row0 wheel angle changes(rad):[.00122058,.00114807,.00098124,.00095275].
No effective traversal. Raising velocity iterations alone does not resolve it;
do not propagate this diagnostic setting to production or claim a solver fix.

## Next and safety

Inspect contact constraints directly (including actual cooked shape/contact
manifold and body locking), not further gain/iteration guesses. Still no
crossing acceptance or training. Placeholder2076869 ->2102167 after readback,
then2112963 after comparison, exact own processes only; final PID verified.
No driver, display, original-checkout or unrelated GPU process changes.
