# Controlled lowering cycle: no verified touchdown yet

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),controlled-land-cycle.
Baseline Ref:2b23174. Candidate Ref: commit containing this log.
Key files:m1_single_lift.py,test_m1_single_lift.py,probe_m1_contact_prepare.py.

## Change and tests

Optional target_height0..18cm moves up/down at bounded8cm/s before Cartesian
backtracking/joint slew. advance_mask holds on measuredcontact. Opt-in land_steps
shares total<=200steps/4s withLIFT. On measured selectedforce>10N stopdownward
advance and include contact in effortallocation. Fresh PrepareGate validates
all4contact>10N,pose/margin/collision/IK and priorLAND effortgap<=1Nm for5frames.
Explicit landing_complete and landing_timeout, phase/streak evidence. No crossing
claim from heightzero. RED2missingkeyword;GREEN104relatedtests5.14s.

## Physical evidence

Sameflat8seed2GPU7. Priorworldvertical/finiteunload configuration, --lift_steps100
--land_steps100. Raw /tmp/m1_land_cycle_20261007.log,native0.94UNLOAD then200
LIFT/LAND actions, no guard/effort/reset abort; stoppedlanding_timeout.
Peak selectedrise12.72..14.44cm, below prior4sLIFT-only17.3..17.8cm because phase
budget is split. Last measuredrise-1.50..2.83mm relativefrozenanchor; reference
0..4.46mm. Allfinalselectedforces0; noLANDsample ever>10N, allstreak0.
Effortgapfinal.01075..01218Nm, so this is not postcontacteffortsettling delay.
No finalpostaction sample means last integration-step contact not certified.

## Next

Child contact-seeking-landing: distinguish remaining trajectorybudget from
referenceground mismatch; capture landing target vs actual wheel collisionbottom
and finalpostaction contact, then contact-guided bounded descent/phase timing.
Do not declare ground-height proxy touchdown or add unlimited landing time.
Current4s cycle does not satisfy10cmobstacle+5cmclearance, cannot promote totrain.
Flat landing, actualobstacle traversal, far-side landing, recovery/bypass/video
andpolicy remain open. No longtraining or push.
Own1479138 stoppedexactly;1515614 placeholder restored verifiedalive. No other
process/display/driver mutation. Slowstartup observed samePID1504530 alive, no
duplicate run started.
