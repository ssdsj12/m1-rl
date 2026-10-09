# Current-SDF moving-load comparison reaches horizontal-reference limit

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), proactive-support child.
Baseline Ref:f5b621f. Candidate Ref:samecode, existingopt-infeedbackcomparison.
Key files:m1_moving_load.py,m1_com_trajectory.py,m1_load_transfer.py.

## Method / improvement in evidence

12moving-load/COM/probe-gate tests pass1.57s. Same preceding fixed-gate GPU7
command plus --roll_load_feedback --roll_com_trajectory (paired existing path).
No code, bounds, collision, pose, contact or effort threshold changes.
Raw:/tmp/m1_sdf_load_feedback_20261007.log;session66175terminalexit0.
UNLOAD and first90LIFT samples exactlyequalbaseline. Feedback firstchangesROLL.
Own65616placeholder stopped;134617 restoredverified. No training/otherGPU/display.

## Result and cause

Stops rolling_load_proposal_rejected atglobal99/ROLLoffset9, row4 reason3
(fullentryreference displacement). It does not reachLAND/SETTLE/crossing.
Row4 actualsupport[FAR,RBL,RAR]=[204.717606,158.443619,30.168247]N.
Proportional redistribution target=[201.920395,156.409076,35]N.
Requested load shift[-4.625750,-2.148399]mm, resulting totalentrydisplacement
80.759626mm>80mm. Lastacceptedprepared+offset norm76.420455mm.
Geometricmargin afterrequestedshift [31.8276,332.8095,165.5815]mm,
so this rejection is not missing20mmmargin or torque saturation.

## Is proportional allocation needlessly rejecting a feasible reference?

Checked the same linear quasi-static redistribution model independently.
For measuredthree-wheel triangle, define unit inward edge normals n_i,
altitudes h_i, measuredforcecenter c_f=sum(f_j*p_j)/sum(f_j), measuredCOM c.
A horizontalcorrection d must satisfy BOTH:
n_i*d >= h_i*35/sum(f)-distance(c_f,edge_i),
n_i*d >= .02-distance(c,edge_i).
Projectzero onto thesehalfplanes using existingnearest-halfplane solver:
minimumstep d=[-2.300537,-3.624325]mm, forceprediction[203.317710,155.011761,35]N.
Even this choice yieldsentrynorm80.713264mm.
Stronger check: express constraints in totalentryreferencecoordinates,
rhs=requiredstep+n_i*currententryoffset. Required projections inmm are
[80.713262,-322.702398,-194.905788]. Since n_i isunitlength, firstconstraint
alone requiresnorm>=80.713262mm; the minimum-entry projection attains it.
Thus no80mm-bounded solution IN THIS MODEL for this measuredstate and35Nfloor.
This is NOT proof M1 itself cannotbalance: fixedorientation/height and linear
COMtranslation are restrictive assumptions; physical posture/dynamics differ.
Do not lowerfloor or expand80mm to hide an architecture limitation.

## Anticipatory support evidence

AfterUNLOAD preparedentrydisplacements byrow(mm):
[76.4665,64.3607,30.3390,17.3037,76.4680,64.3289,30.2952,16.9727].
AtLIFT89 lowfrontcase staticgravitysupport from measuredCOM/triangle is
~30.92..30.95N, rearcase~41..42N. Lifting changes COM/support geometry;
PREPARE's current-pose reserve isnot a guarantee atfullswingheight.

## Next / boundaries

Do not promote existingROLL-onlyfeedback. Need anticipate lifted-leg COM and
support reserve inPREPARE/LIFT; examine bounded posture/height degrees of
freedom permitted byapproveddesign, rather than fixedRPY/height+horizontal
feedback after reserve isalreadyspent. Diagnose reference/physicalfeasibility
before replacementcontroller. Keepactualforce/pose/effort/clearance bounds.
Full5cmclearance/4cmlanding/sixobstacles/bypass/video/policy-only remainopen.
Notes/evidencecommitonly,notuploaded. No runtimefix claimedthiscomparison.
