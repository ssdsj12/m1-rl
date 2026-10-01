# M1 reference first-episode metrics

## Purpose / Stage / Related Todo

Implement pure diagnostics for [T306.6h.2](../todo/T306-m1-ame-long-train-stability.md). New standalone NumPy accumulator only; no changes to reference controller or production AME.

## Inputs / Method

`FirstEpisodeMetrics(num_envs,requested_steps,initial_root_pos)`, `update(step,sample)`, `report(process_finalized=False)`. Inputs must include finite pre-reset physical state, all named wheel/action/contact fields and boolean first-episode termination flags. No default zero evidence. Consecutive step enforcement, first-episode freeze, continue after goal, every environment in denominator.

Strict ordered FAR/RAR prelift→overbar→rear-edge pass→later touchdown; actual radius.0959 and5mm margin. Original .095-radius helper's independent flags are separate from ordered diagnostics. Reference recovery gate is `abs(mean(height)-.57)<=.04` plus final-active error<=.04; MAE remains diagnostic. Four signed time-mean wheel angular velocities must differ by<=.08. Require actual wave/nonwave/action-delta samples. Finalization is explicit and32step startup is never a behaviorpass.

## Tests / Evidence

amp/python, PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, pytest -q -p no:cacheprovider in independent temporarydirectory and deployed newtools directory.

- InitialRED68 failures, missingimplementationassertion;GREEN68.
- AdditionalRED/GREEN: initial-root reference, ordered events, physicalradius threshold, missing actiondelta/nonwave samples, touchdown behind bar, originalhelper flags vsordered chain, exactreferenceheight recovery formula.
- Finalfocused77passed in19.52s; mainindependentrerun77passed in19.37s.
- Deployed provenance+metrics union112passed in19.85s.
- MainCPU differential check calls actual reference update_wheel_obstacle_clearance for80randomsteps×8envs×2requiredwheels; exactboolean parity for independent prelift/overbar flags, exit0. This is syntheticCPU data, notsimulation.
- Independent specandqualityreviewfound andclosed missingnonwave evidence andheightmean-vs-MAE semantics; both approved finalcode.

## Result / Follow-up

Metric implementation passes CPU verification. Actual pre-reset sampling, physical contacts, scene geometry and controller behavior remain unverified untilruntimeadapter. NoIsaac run, no1024expansion, no10000training/restart. Task4inprogress. Newlydiscoveredsourcebar15mmembed is an openphysicalgeometry audit; no parameterschanged.

## Git Refs / Notes

BaselineRef88888f7. CandidateRef9672385: newmetrics.py andtests/test_metrics.py under tools/m1_reference_validation; runtimeplan amended with exactsourceformulas andgroundingrisk. Dashboard/branch/logindex aligned; productionAI/human contract unchanged.
