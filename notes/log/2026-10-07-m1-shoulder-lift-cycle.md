# Shoulder model lift/landing regression and rolling-load isolation

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md),rolling-support-control.
Baseline Ref:c611393. Candidate Ref:containing commit.
Key files:m1_wheel_collision_probe.py,probe_m1_contact_prepare.py,test_m1_wheel_collision_probe.py.

## Change / verification

Permit shoulder diagnostic geometry in a complete lift+land cycle only; cylinder
still standing-only. Existing phase, time, effort and support guards remain.
TDD RED1missing allowed_cycle failure/2pass; GREEN53focusedtests pass12.74s.
Cleanflat8seed2GPU7;90LIFT/20ROLL/90LAND/100SETTLE,vertical.12,height.16,
PREPARE100,.04transfer/.08shift,phase_effort,UNLOAD100,feedback+COM,
targetforce0,minspeed.003,world_pose+vertical_only,land_search.005.
No semantic obstacles (M1_OBSTACLE_STAGE=none), no training.

## Rolling case

Raw:/tmp/m1_shoulder_cycle_20261007.log. Exit0,stopped=rolling_support_rejected,
laststep102 (12executed rolling actions),landing_complete=false.
All8 actual selected-wheel rise155.74..157.81mm. At rejection row3 support
FBL load29.982N<30N; row7 counterpart30.085N. Pose<.01rad,rate<.034rad/s,
COM margin>.026m and non-support force0; limiting condition is support load.
Do not lower30N floor or call this crossing success.

## Zero-speed matched control

Only difference `--roll_speed 0` (20high-hold frames instead of roll).
Raw:/tmp/m1_shoulder_hold_cycle_20261007.log. Exit0,stopped=null,
landing_complete=true,laststep246,all8 landing streak5. Final selected loads
55.73,71.06,57.14,67.17,57.84,71.10,55.84,66.47N.
Thus static lift/hold/land works on shoulder model; support redistribution
during commanded rolling is next control issue.46SETTLEactions=.92s,within2s.

## Next / safety

Implement measured support-load-aware moving reference/COM redistribution,
not extra clearance reward or weaker gates. Retest rolling and full actual
obstacle sequence with conservative original wheel envelope; training remains
blocked by physical acceptance, not by infrastructure.
Placeholder2221235->2246688 afterrollprobe->2265953 afterhold;finalverified.
No original checkout/display/driver/unrelated GPU process changes.
