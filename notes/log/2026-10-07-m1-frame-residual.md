# Frame divergence residual attribution

Parent [T306](../todo/T306-m1-ame-long-train-stability.md),frame-divergence.
Baseline Ref:c4afaa9. Candidate Ref: commit containing this log.
Key files:m1_selected_world.py,test_m1_selected_world.py.

## Change / verification

Read-only fullcandidate fields root_error,angle_error,previous_root_error,
previous_angle_error separate live vsaccepted frame guards. RED missingfield,
GREEN54tests across selected-world/loadtransfer/unloadreference/gate/evidence.
No controller or threshold modification.
Same8flatseed2 GPU7 probe,100PREPARE/100UNLOAD/200LIFT budget,worldpose+zero target.
Raw /tmp/m1_frame_residual_20261007.log,native0. Reproduces rejectionstep25,row5.

## Measurements

Live-command root vector[-.00979542,.02290630,-.00245553]m, norm.02503355m,
exceeds unchanged.025m. Angle[-.00701223,-.00754479,.03211521]rad within.08rad.
Previousframe-command root[-.00966903,.02252674,-.00254560]m,norm.02464598m;
previousangle[-.00641234,-.00717911,.03118643]rad within.08rad.
All8candidateIK/limits/slew pass,only row5 live-root translation guard fails.
Thus rejection is predominantly lateral tracking error, not vertical sag or
attitude/kinematic limit. This does not prove fullpose correction caused it.

## Next

Child vertical-only-frame comparison: preserve measured fullpose safety guards,
but experimentally correct selected-leg IK only for vertical sag; leave nominal
XY/attitude ownership with support transfer. A matched comparison can test
whether full3D selectedfoot feedback fights planned COM motion. Do not enlarge
25mm bound. Keep partial/full tracking semantics explicit, no success claims
without actual8/8unload, LIFT, obstacle andlanding verification. No long training.
Own1369869 placeholder stoppedexactly;1402415 restored verifiedalive. No other
process/display/driver changes or push. Initial local JSON parsing off-by-one
was corrected using prefix.Length; raw server evidence unchanged.
