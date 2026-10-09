# Contact patch evidence and flat-diagnostic correction

Parent:[T306](../todo/T306-m1-ame-long-train-stability.md),effective-rolling-progress.
Baseline Ref:6ad5c5f. Candidate Ref:containing commit.
Key file:probe_m1_contact_prepare.py; read-only contact/scene telemetry only.

## Evidence collection

Source USD four wheel bodies and base have kinematicEnabled=false; no authored
locking attributes observed. This is source evidence, not a complete runtime audit.
Added exact env0 FBL contact view; APIs read from installed tensors api.py.
First /World/ground/* filter and then parent-ground filters yielded zero detailed
contacts despite netnormal113..123N. These were invalid filters, NOT no-contact
proof. Logs:/tmp/m1_contact_patch_20261007.log,/tmp/m1_contact_filter_20261007.log.
Using exact /World/ground/terrain/mesh yields two actual contacts and friction.
22 regression tests passed1.52s before runtime telemetry trials; probes exit0.

## Important prior-evidence correction

Scene enumeration revealed48semantic small obstacles remained in prior probes:
changing terrain sub_terrains alone did not disable authored semantic geometry.
Their label flat_only was too strong. They must be treated as flat BASE terrain,
not guaranteed obstacle-free. Re-ran with M1_OBSTACLE_STAGE=none; scene collision
inventory is exactly ['/World/ground/terrain/mesh']. Existing reset/command
overrides preserved. This clean scene reproduced all8 world-X deltas exactly
(-0.336..-0.349mm), so residual obstacles are not necessary for this symptom.
Raw:/tmp/m1_cleanflat_contact_20261007.log;180steps,stopped=null,exit0.

## Actual contact evidence

FBL row0 normal contact points at approximately X0.324503 and0.280242m,
Y-27.7834m,Z0: longitudinal span44.261mm. Both remain effectively fixed at
samples60,80,100. Loads shift from45.97/74.67N to94.63/19.10N.
Friction includes substantial Y components; this is direct contact evidence,
not inferred from contact-sensor normals. Two-point stationary support while
wheel angle returns is consistent with a finite flat contact face resisting
rolling, but cooked hull geometry and force/torque balance still need verification.
Do not replace tire geometry or reduce friction solely to obtain a passing test.

## Next and safety

Enforce and assert truly obstacle-free diagnostic setup in future probes; correct
metadata. Inspect cooked wheel support face and contact moments versus effective
drive torque. Keep actual-obstacle acceptance separate. No training or display/
driver changes. Placeholder sequence2112963->2134425->2145855->2154675; final
own placeholder2154675 verified. No unrelated processes touched.
