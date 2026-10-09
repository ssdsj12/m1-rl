# Settled height activation exposes real three-support load deficit

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), unload coordination.
Baseline Ref:789f6fc. Candidate Ref:containing commit.
Key files:m1_selected_world.py,m1_single_lift.py,probe_m1_contact_prepare.py,
test_m1_selected_world.py.

## Evidence before change

Compared first12UNLOAD frames of vertical-only and height-only logs. Both start
selectedforce71.15N and effort error16.91Nm. At11 error still12.6..12.8Nm;
heightreference0. Height-only selectedforce40.09N vs55.03N, margin28.83mm vs
30.07mm, so correction acts before force-transfer feedforward is settled.
This motivates phase coordination, not raising displacement bounds.

## Default-off change / tests

unload_height_settled latches per-row activation after existing effort-settled
and post-lift load readiness are both true. Before activation selectedworld
uses exactly previous vertical-only IK; afterward height-only correction uses
the existing accepted frame/backtracking, alljoint slew and safety bounds.
Mask is propagated into LIFT; no phase reset of correction ownership.
TwoRED missingkeyword failures;39GREEN11.89s selectedworld/singlelift/unloadgate.
Tests cover mixed active rows, baseline equivalence and bounded switch.
No changes to5N/30N,5frames,80mm,phase deadlines orsourcecollisions.

## Physical test

Same8envseed2 GPU7 SDF128/rest1mm/contact2mm phasehold+heightonly completecycle
command, addONLYunload_height_settled. Raw:/tmp/m1_height_settled_20261007.log,
session3127 terminalexit0. Stopsunload_com_rejected53, noLIFT.
Activation steps=[41,39,32,31,41,39,32,32]. At52 allselectedwheel forces0N;
heightreferences0.081..0.660mm, actualrise-.575..+.641mm relativeentry.
This is sampled unloading, not geometric obstacleclearance or completedlift.
FAR/FBLrows0,1,4,5 have another supportwheel28.590,26.031,26.981,27.600N,
below30N. Other row minima remain>=34.264N at52. Efforterror<=.0763Nm.
Row4 requests80.2755mm shift>80mm; previous79.3543mm. Gatecorrectly stops.
Front rows notready despite selected0N, rear streaks6,2,4,2; no8/8acceptance.

## Next / architectural implication

Delayed correction avoids early12frame rejection and unloads selectedcontact,
but actual three-wheel load distribution still does not realize proposedreserve.
Do not further tune height or increase80mm/relax30N. Inspect target vs actual
support forces, COM and stancejoint tracking after frontwheel unload; existing
vertical-only static effort+nominalstance posture may conflict with actual load
distribution. Need a feasible coordinated body/stance support correction under
the approved bounds, or explicit infeasibility/recovery. Keep candidateoff until
front/rear cases all pass. Fullobstacle/landing/bypass/video/policy remain open.

Own3502498placeholder stopped,3579350restored/verified. NootherGPU,driver,
display,asset,dirtycheckout changes. No training. Notesaligned,localcommit only.
Improvement vs789f6fc: phase-controlled activation and physical attribution of
newblocker to supportload rather than continuing selected-wheel height error.
