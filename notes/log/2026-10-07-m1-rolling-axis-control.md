# Rolling command chain and matched stationary control

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),rolling-support-control.
Baseline Ref:854cf2a. Candidate Ref:commit containing this log.
Key file:probe_m1_contact_prepare.py (telemetry and explicit zero-speed control).

## Telemetry audit

Same8flatseed2GPU7run,90/20/90+100SETTLE,.12vertical/.16height.
Raw:/tmp/m1_rolling_axis_20261007.log;native0,reproduces supportrejection at99.
Actual wheel velocity target at99:1.0421226rad/s on each support,0onselected;
backend damping5.0. World Jacobian wheel-axis Y~.978...991 in row0,positiveY,
consistentwithpositiveX rolling underpositivejointvelocity. Do not flipsigns.
Actual loadedwheelvelocities aremixed -.128...534rad/s,wellshortoftarget.
Staticnormalforceallocation weak support~35.8N butmeasured~29.1N inrearleg
rows;quasistatic feedforward doesnotcoverthis transientloadtransfer.

## Matched zero-speed control

Add --roll_speed choices0/.1 (defaultunchanged), identicalhighhold/transport.
Raw:/tmp/m1_rolling_zero_20261007.log;native0. All20ROLLactionsexecutedwithout
supportguardrejection. Thusnegativeearlymovement alone wasnot sign evidence,
andforward step drive iscausally associatedwiththe observed supportfloorloss.
No collision/traversalclaim;noobstacleinthisscene.

Separate remaininglandingissue:zero-speed control reachesstep200 SETTLE with
selectedforces16.28,14.07,17.44,17.24,21.17,10.15,17.92,17.94N;then
settle_contact_lost_or_missing onnextadmission. Addedhold consumes20frames;
weakcontactcanoscillatearound10N. Notstablelanding,notpermissiontoextend4s
orweakencontactgate. Needcontact-latched landing control/settle transition
analysis ratherthan assumetouchdownisstable.

## Next

Implement/test bounded forward acceleration anddeceleration withmatchedcontrol,
preserve30Nsupportgate andactualtiming. Review dynamicloadreserve iframp
stillfails. Tracklandingcontactstability as sibling, notmixbothparameterchanges.
Runtime telemetry logging isread-only;py_compile passed beforesmoke. No training.
Placeholderrestored1845986afterfirst,1863813aftersecond;verifiedexactcommand.
