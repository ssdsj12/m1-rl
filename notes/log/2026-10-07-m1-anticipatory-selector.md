# Sampled anticipatory support candidate selector

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), anticipatory-support.
Baseline Ref:99ebb0b. Candidate Ref:this commit.
Files:[selector](../../Go2Pvcnn/ame_baseline/m1_anticipatory_support.py),
[tests](../../Go2Pvcnn/tests/test_m1_anticipatory_support.py).

## Improvement and contract

Choose minimum displacement/tilt cost among candidates whose EVERY supplied
lift sample satisfies35N minimum support,20mm margin and IK reachability.
Reference limits remain80mm totalshift, fixedZ/yaw,80mrad RPdelta norm,
150mrad absoluteRP. Nonfinite evidence is rejected. All-invalid returns
validFalse/index-1; fallback entrypose is not a safe recovery action.
This selector neither generates evidence nor certifies continuous motion.
Caller must produce causal candidates and sample enough, check dynamics,
effort, joint slew, collision and actual contact/anchor drift.

## Verification

Five tests RED before implementation, thenGREEN; regression total20passed:
test_m1_anticipatory_support.py, test_m1_mass_predictor.py,
test_m1_com_trajectory.py. Includes mid-lift failure despite goodapex,
all-invalid, fixedZ/yaw, unchangedbounds, NaN and lowmargin rejection.
No GPU runtime/control wiring or training was changed this pass.

## Integration issue / next

Historical PREPARE samples record root position but not rootquaternion/joints.
Do not feed LIFT89 attitude/direction into PREPARE and call it causal.
Next capture/freeze actualstageentry pose/joints, construct candidate lifted
poses using originalanchors and masspredictor, evaluate intermediateheights,
then pass results toselector. After path/slew/effort checks, default-off
physicalcomparison must verify support/anchortracking. No dynamic/crossing,
bypass or learnedpolicy acceptance claimed. Notes synchronized; notuploaded.
