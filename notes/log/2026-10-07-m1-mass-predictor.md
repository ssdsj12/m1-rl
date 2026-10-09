# Named batched M1 mass predictor

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md), anticipatory-support.
Baseline Ref:b8beff2. Candidate Ref:this commit.
Files:[predictor](../../Go2Pvcnn/ame_baseline/m1_mass_predictor.py),
[tests](../../Go2Pvcnn/tests/test_m1_mass_predictor.py).

## Improvement over baseline

Pure torch batched named-joint FK predicts each body COM and whole COM at
candidate joints/root poses; no USD/Isaac import or runtime wiring. Both parent
and child joint transforms consumed; wxyz/radian contract. Invalid rows return
validFalse/finite zero outputs, never a safe hold. Model names/tree/mass/vector
errors raise ValueError. Callers must still enforce IK, contact and pose bounds.

## Verification

Eight tests RED before module existed, then8passed: angle sign/mass weighting,
both joint frames/child anchor, root rigid transform, invalid-row isolation,
nonunit quaternion rejection, wrong/duplicate names, disconnected model.
Command:PYTHONPATH=. amp Python -m pytest -q tests/test_m1_mass_predictor.py.
CPU replay of `/tmp/m1_native_com_20261007.log`,792rows using authored USD
model inventory and DIRECT recorded root quaternions/bodyCOM (not fittedpose):
float64 wholeCOM max4.26505238e-6m, body3.66570950e-6m;
float32 wholeCOM5.72243653e-6m, body5.73224725e-6m.
Both validall, both under1e-5m. Reversing inputjointname/column order yields
bitwise-identical wholeCOM. This checks named mapping against real16jointdata.

## Next / limitations

Predictor now enables look-ahead of lifted candidate poses; integrate it into
bounded anticipatory support only after feasibility checks. No dynamics/contact
prediction, no CPU-to-GPU numeric equivalence claim, no controller integration
or new physical run this pass. Existing rolling rejection and full obstacle,
landing, bypass, video, teacher/PPO/policy-only gates remain open.
No training or resource/display changes. Notes synchronized; not uploaded.
