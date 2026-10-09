# Bounded ground search establishes all eight touchdown contacts

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),contact-seeking-landing.
Baseline Ref:5fba329. Candidate Ref:commit containing this log.
Key files:m1_single_lift.py,test_m1_single_lift.py,probe_m1_contact_prepare.py.

## Design and change

Re-read approved spec: singlelegaction<=4s, separateSETTLE<=2s. This trial doesnot
yet addSETTLEtime. Optional --land_search_depth.005 allowsreference up to5mm below
nominalanchor, onlywhen explicitnegative LANDtarget. Reachzero first, then search
at<=.01m/s; contact>10N hold remains. Default targetfloor0 unchanged. Joint/pose/
support/effort guards and4s budget unchanged. RED invalidnegative target;GREEN
106relatedtests5.15s including boundedslowsearch andcontacthold.

## Physical evidence

Same8flatseed2GPU7,90LIFT/110LAND,priorverticalfiniteunload flags plussearchdepth
.005 (actual CLI spaced). Raw /tmp/m1_land_search_20261007.log,native0.
All8firstLANDforce>10N atsteps182..184 within4s. Finalpostactionselectedforces
[38.63,27.84,36.15,35.16,42.51,27.43,33.14,37.24]N. Priorweakrows1/5 require
reference-2.0/-1.6mm, inside5mmcap. Otherrows hold atnonnegative reference.
stoppedlanding_timeout,landing_completefalse,streak0; finaleffortgap6.21..13.59Nm
duringtransition fromthree tofourcontact allocation. Thus touchdown established,
not stableloadtransfer. No fullcrossing/video/policyclaim.

## Next

Child four-support-settle: implement approvedseparate<=2s settling only afterall
measuredcontacts present within4s LANDbudget. Holdlandingreference; do not keep
searching beyondsinglelegdeadline. Ifcontactlost, fail/recover ratherthan grant
unlimitedextraairtime. Require5fresh stableframes andeffortconvergence. Then
restore required obstacleclearance trajectory/traversal and videoacceptance.
No longtraining/push. GPU7preflight13.4GBfree; own1547510 stoppedexactly,1598746
placeholder restoredverifiedalive. No unrelatedprocess/display/driverchange.
