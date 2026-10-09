# Causal entry-only sampled lift support forecast

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), anticipatory-support.
Baseline Ref:bd661f7. Candidate Ref:this commit.
Files:[forecast/selector](../../Go2Pvcnn/ame_baseline/m1_anticipatory_support.py),
[entry forecast](../../Go2Pvcnn/scripts/forecast_m1_entry.py), probe entry_snapshot.

## Change and CPU tests

Freeze root/rpy/named jointposition lists BEFORE PREPARE. Snapshottest RED
missingfield thenGREEN. New forecast_lift computes M1 IK and authored COM for
fixed candidate pose across supplied heights; ONLY selectedwheelZ changes,
three supportanchors unchanged. Static barycentric minimumforces/margins,
IK mask and jointpath returned to choose_pose. Invalid/nonmonotonic height
paths rejected. Four forecasttests RED missingfunction thenGREEN.
Total19passed:liftforecast/anticipatorysupport/masspredictor/probeCOMtests.
Synthetic unit fixture checks geometry contracts, not actual M1 mass values;
below replay uses original composed USD, not that synthetic fixture.

## Short physical snapshot and causal forecast

GPU7session58448 exit0; baselineSDF/holding flags, PREPAREbudget1 to capture
entry only. End lift_entry_not_ready expected,1PREPARE/0LIFT. Raw
`/tmp/m1_entry_snapshot_20261007.log`. Root and anchors exactlyequal prior
nativeCOMrunentry. Placeholder424671 stopped by exactcheck, restored656674.

CPU `scripts/forecast_m1_entry.py /tmp/m1_entry_snapshot_20261007.log` consumes
ONLY entry_snapshot/entry_anchor_w/selected_leg, never latertrajectory.
2401poses/row, direction centered on entrythree-support centroid,17heights
0..160mm every10mm. Constraints/selection from previousselectorunchanged.
All8rows eligible. Selected noRPchange, shiftmagnitudes75,70,40,20,75,70,40,20mm.
Worstheight minimumforcesN:
[35.24967,39.89887,49.85336,44.33433,35.25839,41.77649,49.87508,44.34346].
Minimumedge marginsmm:[30.674,34.751,43.499,38.522,30.682,36.387,43.520,38.542].
Eligiblecandidatecounts:[204,570,1547,1890,205,570,1547,1890].

## Next and limits

Entry-only model does find supportreserve without addedtilt; do not widenpose
or shiftranges. Next integrate selectedfixedreference with bounded transfer,
validate transferpath/jointslew/effort and actualanchor/contacttracking.
17staticpoints are NOT continuouspath/dynamics/collisionproof. No new physical
lift, obstacletraverse, landing, bypass or policy-only acceptance. No training.
No otherGPU/display/driver changes. Notes synchronized, not uploaded.
