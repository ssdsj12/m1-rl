# Landing timing isolation and final contact evidence

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),contact-seeking-landing.
Baseline Ref:738bae0. Candidate Ref:commit containing this log.
Key files:probe_m1_contact_prepare.py,test_probe_evidence_contract.py.

## Change / tests

Read-only final_observation and final_height_reference after last executedaction,
beforeclearingeffort. RED missingfields, GREEN43evidence/lift/gatetests3.45s.
Test checks evidencefield contract; runtime verifies actualpoststep data.
No controller/gain/threshold changes. One diagnostic timing comparison90LIFT+
110LAND vs100+100 withsame4s total. This shorterpeak trial is NOT10cm crossing
acceptance and doesnotreplace requested obstacleclearance target.

## Runtime

Raw /tmp/m1_land_timing_20261007.log,native0. Same8flatseed2GPU7, priorfiniteunload/
verticalworldconfiguration; --lift_steps90 --land_steps110 (CLI spaced).
stoppedlanding_timeout,landing_completefalse. Finalpostaction selectedforce
[38.63,.11,36.15,35.16,42.51,1.40,33.14,37.24]N. FirstLANDforce>10N at
[182,none,182,184,182,none,182,183]; allfinalreadinessstreak0.
Compared with100/100 no preaction>10N, sixrows nowcontact. Rows1/5 havezeroheight
reference but weakcontact, showing zero-reference is not a reliable contactgate.
Timing contributes, but doesnotexplain allrows. Need contact-seekingground and
contacted-support effortsettle, notlowerthresholds or pureheight success.

## Next

Read approved LAND/SETTLE budget before modifying phaseownership. Evaluate bounded
contact-guided downwardsearch around groundreference; preserve support/pose/
effortlimits, reject search exhaustion. Separate truefirsttouch and stableload
transfer; confirm allwheels contact before extending into any4-supportSETTLE.
No unboundedextra singlelegtime. No obstacle/video/policy completion ortraining.
Own1515614 stoppedexactly;1547510 placeholder restored verifiedalive. No unrelated
process/display/driver mutation or push.
