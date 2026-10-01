# Scale candidate19: phase reentry / first-activation conflict

2026-09-19 update: user approved revised A, allowing a new encounter after actual departure/reapproach and independent next obstacles. The reset-only proposal and waiting state below are historical. Written design e25e805 has passed scope reviews and awaits user review before implementation; no controller changes yet. See[revised design review](2026-09-19-m1-encounter-design-review.md).

T306.6h.6a.1a.2;2026-09-18. Diagnosis complete; behavior design A/B presented, awaitinguserchoice. Nofiximplementedornewsimulationstarted. Main used systematic-debugging/verification skills and independentreadonly sourceaudit; brainstormingrequiresconfirmationbeforechangingreferencebehavior.

## Evidence chain

Input:[candidate19failure](2026-09-18-m1-scale-candidate19.md),[baselinebehavior](2026-09-18-m1-scale-baseline-behavior.md). Mainre-readrelevantactualsourceandfreshNPZ,notjustagentconclusions.

Referencebase`/home/hexinkun/m1/Go2Pvcnn/go2_pvcnn/tasks/`:

1. `m1_rsl_rl_wrapper.py:426–464`: actualwave_spatial_reference=True;spatialhelperreturnsnon-Nonereferenceandobstacle_activeusedasrawgate. Actualwave_gate_from_spatial_reference=False.
2. `m1_curriculum.py:1632–1642`: selectedfinite semantic1hitswithinbodyalong[-.60,.70],lateralabs<=.25;rawgate=anyselectable.
3. `m1_curriculum.py:166`: sequence_gate keepsphases0..10aliveevenifrawgatefalse,butnotphase11. Atline220,phase11+gatefalsebecomes-1.
4. Lines167–172: subsequentrawgatetruewitholdphase<0andfrontwheelminrelativex>=-.45startsphase0. Noencounter-consumedstateandnopast-obstacleupperbound.
5. Lines371–373phase0enableslegs;wrapper653–659getsleg_wave_gate,979–990buildsreference,1091–1098applies/exportslegsandm1_wave_gate.
6. Adapter`sync_bridge.py:162–166`callsoriginalteacherpreparefirst;104–110readsfreshgate/drive. `post_cross_sync.py:237–241`storedpriorobservequalification;256–267combinesoldactivewithnewready>=5andthenrejectsfreshwave/nonzerolegsbeforeoverridingactions.

Thusenv523gotfivequalifiedsamples242..246,becamenewlyeligibleforprepare247,butteacherreenteredphase0inthatprepare;guardcorrectlyraisedbeforeoverride. Itwasnotalreadyactive:prepare246sidecaractivefalse,ready4;observerafter246suppliesfifthsample. 226otherenvswereactiveby246. Mainenv52328non-timingfields224..246bitwiseequalbaseline,baseline247phase0/waveTrue/legmax.266336799. Candidate247hasnofinishedsample:actualevidenceforitsfreshgateisexception,itmustnotbeinventedfrombaseline.

Not2-secondtimerloop:wrapper486–509takescounterbranchonlyifreferenceisNone;actualspatialreferenceisnon-None,sowave_single_cycle_duration_s2doesnotdrivethisrestart. Statechainis11→-1→0.

## Obstacle and root-mask boundaries

env24/523nearthiseventhave94–98ownsemanticbarhitsand0foreign. Runtime437–450auditssemantic1hitboundingboxes. Thisisconsistentwiththesameownbarreenteringspatialselection,notaforeignbar/newphysicalobstacle. Rawrays/selectedrawgate/spatial_obstacle_xwerenotsaved,sonospecificrayorwindow-boundaryoscillationhasbeenfullyreconstructed. Preserve thisuncertainty.

Actualwave_disable_obstacle_after_root_x=1.15. Wrapper1070–1079updateswheel-orientedwave_gateonly;legsusepriorseparateleg_wave_gateat1091–1095. Copyingrootmaskdirectlytolegswouldnotbeasafefix:env523sample240alreadyrootx1.45463whilephase10/legmax.674028:firstrestorationstillactive. Firstcrossingandrestorationmustnotbetruncated.

## Presented design alternatives — not authorization to implement

A(recommended): innewisolatedadapter,explicitconsumed/completedstateonlyafterfirstorderedFAR/RARcrossingandrestorationcomplete;preventsamereferenceobstaclefromstartinglegsagain,clearper-envstateonreset. Preservethefirstcrossingtrajectory,allguardsandthresholds;CPUregression/spec+qualityreviewsbefore8-envphysicalgate. Newbehaviorrequiresnewprovenance/baselineandexplicitvalidation;frozencandidate19/formalreference/externalm1source/SDKremainuntoucheduntilapprovedscopedplan.

B: onlydelayfirstsynchronizationactivationuntilfreshteacherconditionsalsoallowit;currentinapplicabilitykeepsinactivewithreason. Smallercontrollerchangebutdoesnotremovephase-reentryor21envnevercollecting5stablepackets;activeownershipstillneedsdefinedcontract. Neitherchoicefixesthe18initialgeometrymissesorproves10000/learnedbehavior.

MainpresentedA/Bandaskedoneasynchronouschoicebeforeimplementation. Noplan/codewrittenfornewbehavior;noguardremoved/nothresholdrelaxed/noautorestart. Thedenominatorremainsstrictly1024;previousartifactsremainunaltered.

GPU7currentlyonlyoriginal15GiBreservationPID351307,restoredandreverifiedaftercandidatecomputeended. SourcefreezeTask3diffremainsrequired;newworkmuststartinisolatedcopyafterapproveddesign. At23:36 the unchanged design-choice blocker met the three-consecutive-turn audit; goal is now BLOCKED pending user choice, not complete. See[blocked audit and resume condition](2026-09-18-m1-design-choice-blocked.md).

Refs:formal646f486;repoHEAD5553e84;frozenpost_cross_sync18aeb0c7,sync_bridge817ed035,verifier3930483e. See[T306](../todo/T306-m1-ame-long-train-stability.md).
