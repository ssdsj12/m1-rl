# First held-leg rolling probe rejects at support floor

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),rolling-support-control.
Baseline Ref:13c6247. Candidate Ref:commit containing this log.
Key files:m1_rolling_reference.py,probe_m1_contact_prepare.py,test_m1_rolling_reference.py.

## Implementation / tests

Optional20step rolling phase shares4s budget withLIFT/LAND. Three support wheels
request .1m/s, liftedwheel zero; defaultroll_steps0 leaves baseline unchanged.
Frozen root/anchors translate with measured forward displacement from roll entry;
previous selected IK frame translates only by progress delta. No vertical/lateral
integration. Displacement jump>.6m/s*dt,lateral>25mm orreverse>20mm reject.
RED3missingmodule;GREEN46focusedtests. Syntax compile passed before smoke.
Probe cannot enable rolling without preceding LIFT and following LAND.

## Physical evidence

8flat seed2 GPU7,90LIFT/20ROLL/90LAND plus100SETTLEbudget,retimed .12/.16m flags.
Raw:/tmp/m1_rolling_cycle_20261007.log. Native0,stopped=rolling_support_rejected,
landing_complete=false.10ROLLpreactionsamples:steps90..99; only9rollingactions
executed. Lastframe poses andIKvalidall8, butrows2/3/6/7 weakest support is
29.478/29.537/29.104/29.072N,below30N. Tiltswithin.017rad,rateswithin.045rad/s.
Progress isnegative .00057.. .00341m. This isnot proof of reversedwheelaxes:
actual loadedwheelvelocities are mixed and small at this transient; desired
wheel targets/axes were not logged. Do not blindly flip command sign.

## Investigation and next

Runtime actionterm resolves named wheel IDs and sends velocity targets;cfg
wheel stiffness0,damping5.0,scale1/radius. Preserve these until runtime target,
axis and actual body/wheel velocity audit. Newchild rolling-support-control:
distinguish velocity-command transient load transfer from sign/tracking errors.
Next record actual velocity targets,worldwheelaxis/Jacobian and rootvelocity;
then test acceleration-limited command rather than step input ifsupported.
Do not lower30N supportgate or claim rolling/traversal success. Realobstacle
smoke andtraining remain gated. Own placeholder restored PID1815158;other
processes/display/driver unchanged.
