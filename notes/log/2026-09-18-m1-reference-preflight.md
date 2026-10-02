# M1 reference controller provenance and USD preflight

## Purpose / Stage / Related Todo

Approved independent controller/oracle validation, [T306.6h](../todo/T306-m1-ame-long-train-stability.md). Source/asset prerequisite only, not learned-policy or simulation success. Reference source remains read-only; amp runtime only.

## Procedure / Inputs

- ReferenceCPU: PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONPATH=reference Go2Pvcnn, amp/python -m pytest -q -p no:cacheprovider reference/tests/test_m1_curriculum.py.
- Newguard TDD in task-only tmp/ref_provenance_tdd_20260918; sameamp/pytestflags. Localedits uploaded totemp, not reference.
- Real audit_provenance against suppliedreference Go2Pvcnn, checksmanifest/fourUSDhashes/overlayequivalence.
- Read-only pxr0.22.11: installedomni.usd.libs path; Ar.DefaultResolverContext binds installed omni/mdl/core/Base. ComputeAllDependencies+Usd.Stage.Open, enumerate actualprims/Physxattributes. Stage.GetCompositionErrors unavailable inthisversion; checked eachprim.GetPrimIndex().localErrors andTf.Error.Mark instead.

## Evidence

- Referencebaseline:88passed in3.90s.
- Runtime-adapter preparation rerun (2026-09-18 13:34 CST, same read-only amp command):88passed in1.97s,exit0. GPU/process precheck at13:33:39 foundGPU4 idle5MiB andno M1training/referencevalidation process. This isCPU/source evidence only, notanIsaac run.
- GuardRED:35failed,allmissingimplementationassertion;GREEN35passed in0.19s;mainrerun35passed in0.31s. Independent specandqualityreviews approved. Universalnewlinenormalization isintentional, matchingPath.read_text.
- Realguardpassed;fourbinaryhashesmatchhistoricalsource_files.sha256. Sourcecopyprovenance described in reference2026-08-14offlineassetlog. Originalhistoricalmachine'sbinarypathabsent; donotclaimliveequalitytoabsentfile.
- PortableLFoverlaySHA:b4eb87c46a12d653e50aa012f32de45abd6d5447ca72a9a5b2afdaf60531e63c. Entireoverlaytext matchesoriginalaftersoleabsolutephysicslayerURI→`@./m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_physics.usd@` andnewlines.
- USD:3layers,1OmniPBR.mdl,0unresolved; allprimindexlocalErrors empty,Tfclean. MDLfile resolutionverified, notrenderer/MDLcompilation.
- DefaultprimZJ_V3_URDF_V1_0,17rigidbodies,16namedrevolutejoints,oneBASE_LINKarticulation,inactiveroot_joint,13mesh+4cylinderrobotcolliders; wheelradius0.0959,width0.0465,axisY. Mass41.04531955718994kg.
- Floatingoverlay standalonestageunits0.01/upAxisY areinheritedfallbacksharedbyold/new; actualspawnedsceneZ/meters1stillmustbeverified, notsilentlyrewritten.

## Findings / Follow-up

Groundingfollow-upT306.6h.3: sourceDEFAULT_GROUNDING_EMBED_DEPTH_M=.015 andspawnworldcenter subtractsembeddepth. Taskcfgsearchfoundnooverride. Thusnominal.06mcuboidisexpectedtoexpose.045maboveflatground; runtimebboxnotyetmeasured. Preserveoriginalbaselineandmeasure,neverclaimactual60mmobstacleheightsolelyfromcuboidsize; noheightchangeapproved.

Separate [amp Vulkan recheck](2026-09-18-m1-reference-vulkan-preflight.md) returnedvkCreateInstance0/eightphysicaldevices/exit0. Noenvironment/driverchange; runtime stability stillpending.

Actualradius+barheight+margin=0.1609m, originalhelper0.160m; recordboth,enforcestrictactualcriterion. Originalsemantic_contact_small netforce isgenericcontact, while filteredforce_matrix identifiesbarforce. Existing sensoronly4wheels. Adddiagnostic-only17bodyviewwithownbar-pathmapping andsubsteppeaklatch; cannotclaimnonwheelbar-safetyfromoldfourwheeldata. Terrain1x1wouldduplicateorigins; nextadapteruses1xN8mtileoriginsandvalidatesactualgeometry/filter/scannerisolation.

## Result / Contract / Notes

Preflight passed. NoIsaacappstart, no8-env or1024-env behaviorresult, no10000training/restart/monitor. ProductionAME and referencecontroller/reward/actioncontracts unchanged. Newfiles are standaloneguardandtestsonly; nextmetrics/adapter planinprogress. Dashboard,T306branch,logindexupdated. Stagehuman/AIdocsnotchangedbecauseproductioncontractnotchanged.

## Git Refs

BaselineRef:bd78daa pluspreserveddirtywork. CandidateRef:newtools/m1_reference_validation/provenance.py andtests/test_provenance.py. Keyplans:[preflight](../../docs/superpowers/plans/2026-09-18-m1-reference-preflight.md),[runtime](../../docs/superpowers/plans/2026-09-18-m1-reference-runtime.md).
