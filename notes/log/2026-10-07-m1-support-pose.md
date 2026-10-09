# Bounded lifted-pose feasibility: entry anchors versus late drift

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), anticipatory-support.
Baseline Ref:b7450cd. Candidate Ref:this evidence commit; control unchanged.
Key file:[offline audit](../../Go2Pvcnn/scripts/audit_m1_support_pose.py).

## Procedure

CPU originalUSD masspredictor + existing M1 IK, recorded nativeCOM run step89.
1715 poses/row: horizontalradius40/60/70/75/79.9mm around PREPARE entry,
seven directions near actual displacement,7x7 roll/pitch deltas[-.06,.06].
RootZ held entryZ; deltaRP norm<=.08, absoluteRP<=.15, IKallreachable,
COMtriangle margin>=20mm. Static load barycentrics from wholeCOM and original
totalmass*9.81. Candidate load minimum>=35N. No command slewrate/effort/path
or collision verification, no dynamicfeasibility claim. Orientation/direction
uses observed endpose as search center: this is offline diagnosis, not causal
PREPARE implementation. Finitegrid absence does not prove globalinfeasibility.

Run amp Python with installed USD paths:
`scripts/audit_m1_support_pose.py /tmp/m1_native_com_20261007.log`
and same with `--entry-anchors`. Both exit0.

## Results

Late actual wheel anchors: FBL rows0/4 have0 sampled35Nsolutions; bestminimum
26.094/26.144N. FAR rows1/5 have143/145solutions (max38.13/38.26N).
Rear rows all1575IK/geometryvalid sampledposes meet35N.
Originalentrywheelanchors with selectedwheel raised160mm: ALL8rows have
sampled35Nsolutions:counts344,893,1575,1447,345,891,1575,1350.
FBL bestminimum41.408/41.414N inside79.9mmcommandbound withRPdelta[-.04,.06].
This supports anticipating lifted geometry before drift, not late pose repair.
Measured FBL root shift atLIFT89 is86.979/86.945mm fromentry; current80mm limit
constrains reference, not actualroot. Do not misreport actual root within80mm.

## Next / scope

Implement candidate selection using only actualstageentry pose/anchors and
forecast selectedwheelheight (not retrospective searchcenter). Prefer minimum
shift/tilt satisfying reserve, verify full liftpath and reference slew/effort,
then default-off physicalcomparison. Live contact/anchor drift must still gate
execution; not assumed solved by staticcandidate. Fullcrossing/bypass/policy
acceptance remainopen. No GPU/training/display or asset changes this pass.
