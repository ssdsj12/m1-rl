# 2026-10-08 M1 live wheel material audit

Parent [T306](../todo/T306-m1-ame-long-train-stability.md), WBC contact-QP dependency.
Baseline Ref:dfdcfe2. Candidate Ref:this material-audit commit.
Key files: [adapter](../../Go2Pvcnn/ame_baseline/m1_wbc_materials.py),
[probe](../../Go2Pvcnn/scripts/probe_m1_contact_prepare.py),
[plan](../../docs/superpowers/plans/2026-10-08-m1-wbc-materials.md).

## Finding and implementation

Inherited TeacherElevationTrajectoryMpcSemanticEventCfg randomizes robot shape
static/dynamic friction separately in[.3,1.2], restitution[0,.15],64buckets.
Ground material1.0/1.0, multiply. Therefore a constant robot friction1.0 is invalid.
Installed tensor get_material_properties provides live per-shape static,dynamic,
restitution. Separate rigid-wheel views created before warmup; env0 audited.
USD bindings/modes read without applying or changing schemas. Coefficients are
runtime values, NOT the USD visual material's absent physics attributes.

First bounded run exited0 without completion markers. Added explicit traceback
before SimulationApp.close; it exposed the ValueError from missing combine mode.
Input instrumentation showed wheel bound Looks/DefaultMaterial has no physics API
(USD coefficientsnull) while native wheel coefficients are valid. Installed
Usd.SchemaRegistry.FindAppliedAPIPrimDefinition('PhysxMaterialAPI') returns
fallback frictionCombineMode='average'. Use it only when API absent, record source;
unknown modes still reject. Ground coefficients from bound unrandomized USD material.
No native shape ordering assumed: conservative bound spans all live coefficient/
authored-mode pairs and min(static,dynamic). This remains safe if dynamic>static.

Combine precedence average<min<multiply<max confirmed in
[PhysX documentation](https://nvidia-omniverse.github.io/PhysX/physx/5.4.0/_api_build/struct_px_combine_mode.html)
and installed schema generatedSchema.usda defaultaverage. No guessed higher mu.

## Verification

RED11 adapter tests +1 observer; additional RED exception visibility and schema
fallback wiring. GREEN77tests in2.06s: WBC materials/kinematics/contacts/QP/free/
dynamics/probe plus existing point-Jacobian tests. gitdiff whitespace checked.
CPU API read independently confirms installed fallbackaverage.

GPU7 only, exact own placeholder each run, EXIT restoration. Four bounded observer
runs (no PREPARE/lift), original collision/PD configuration. First three diagnostics
not success: incomplete/trace/input evidence preserved respectively as
/tmp/m1_wbc_materials_20261008.log,
/tmp/m1_wbc_materials_trace_20261008.log,
/tmp/m1_wbc_materials_inputs_20261008.log.
Successful /tmp/m1_wbc_materials_fixed_20261008.log copied to local artifacts.
Command probe_m1_contact_prepare.py --num_steps1 --wbc_snapshot --device cuda:0
--headless,300s timeout. Final stopped=wbc_read_only_complete; no crossing.
Wrapper now additionally requires material/contact/final markers, not exitcode0.

| Wheel | Native static | Native dynamic | Conservative combined mu |
|---|---:|---:|---:|
| FBL | .746055 | .599195 | .599195 |
| FAR | .945422 | .548554 | .548554 |
| RBL | .707219 | .868493 | .707219 |
| RAR | .605370 | .585559 | .585559 |

Contact geometry regression unchanged: pointcounts[2,3,2,2], normalclosure7.63e-6N,
pointvelocityerror9.40e-9. Placeholder650836→683638→693273→698079→706235;
final706235 verified soleGPU7compute10624MiB and exact sleep.py command.
No other process/GPU, driver, display, USD, production actuator or training change.

## Open work

Only env0 material acquisition audited; full-env/episode ownership and runtime
QP integration pending. Rolling contact migration acceleration, actual stance,
single-leg support/lift/roll/land and obstacle tests remain. No retraining until
physical gates; no model capability claim. Diagnostic exitcode swallowing is
handled by explicit traceback plus required output markers, not falsely accepted.
