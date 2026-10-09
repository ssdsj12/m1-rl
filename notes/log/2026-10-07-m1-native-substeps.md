# Native wheel substep observation

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), traction/solver child.
Baseline Ref:a26fb0f. Candidate Ref:containing commit.
Key files:m1_substeps.py,probe_m1_contact_prepare.py,test_m1_substeps.py.

## Method / implementation

Read ManagerBasedRLEnv.step and M1MixedJointAction.apply_actions: normal path
applies targets then physics/update per decimation; wheel action writes velocity
targets, not wheel positions. Added default-off --roll_substep_audit. Only during
ROLL, wrap existing scene.update to read env3 native/cached q/qd after each real
physics step. No replacement/extra physics stepping. Restore method in finally,
including exception. This diagnoses cache/state consistency, not a controller.

## Tests and physical result

RED2missingmodule; GREEN18focused tests,1.48s. Same fixed-physics shoulder rear
preload probe as a72b16f, gain5, .1cap20ramp,90lift/90land/100settle, only add
roll_substep_audit. Raw:/tmp/m1_wheel_substeps_20261007.log.
Session25467 terminal exit0. stopped=null,landing_complete=true,finalstep244.
Last root rolling progress identical to no-observer baseline (negative
.548..1.109mm). No effective traversal; no observer-induced improvement.

20actions x4 samples withdt .005s. Native/cache q/qd maximum discrepancy0.
Across all80substeps env3 wheel netq vs sum(endpoint qd*dt), radians:

| Wheel | netq | endpoint velocity integral |
| --- | ---: | ---: |
| FBL | .00823605 | .03900408 |
| FAR | .00096915 | .02604810 |
| RBL | .00171675 | -.01446828 |
| RAR(selected) | .00041440 | -.00233147 |

This interval includes final zero-command action; earlier preaction-only angle
audit excluded it, so do not compare angle totals without matching endpoints.

## Interpretation / next

Stale cache is ruled out for these samples, not all possible action/event faults.
External endpoint integration need not equal TGS internally substepped position
integration. NVIDIA's [implicit drive description](https://nvidia-omniverse.github.io/PhysX/physx/5.3.0/_downloads/6acf3afb8f69452757e0e766b5a22978/implicitDrives.pdf)
describes forward position integration during TGS iterations; this is relevant
mechanism context, NOT verification of this installed binary or a solver defect.
The [stability guide](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/107.0/dev_guide/guides/articulation_stability_guide.html)
supports examining timestep/iteration resolution. Next controlled timestep
comparison must retain20ms control interval, total physical duration, preload,
contact geometry and guards. Do not infer locomotion from endpoint velocity.

No training/source asset changes. Original wheel/obstacle/clearance/landing/video,
policy and bypass acceptance remain open. Exact own placeholder2662902 stopped,
2696342 restored. No display/driver/unrelated process changes.
