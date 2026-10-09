# Settled WBC support: native clock verified, sustained control not passed

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), child
execution-physical/handoff-transient. Baseline/candidate ref:223a0ec.
Stage: isolated GPU0 native diagnostic, no obstacle or training.

## Procedure and input

Existing probe `Go2Pvcnn/scripts/probe_m1_wbc_pd_handoff.py`, seed7,1env,
dt.001s, `--settle_steps 2000 --stable_frames 100`, production PD until measured
readiness. All actual WBC torques retain20Nm/s slew, native limits, full contact
model and35N predicted/30N measured support limits. Hold speed guard remains
the pre-existing.08m/s; no threshold was relaxed. GPU7 placeholder1768831 untouched.

## Distinct checks

| Check | Native evidence | Result |
| --- | --- | --- |
| Snapshot-only clock | `/tmp/m1_wbc_settled_snapshot_20261009_2RxSMr.log` | step294,time.2940000139642507 accepted; no WBC applied |
|100tick support | `/tmp/m1_wbc_settled_hold100_20261009_6WKzGI.log` |100feedbackticks plus initial tick; min82.9738N,maxspeed.0190269m/s,maxangular.028397rad/s,maxtilt.001685rad |
|500tick support | `/tmp/m1_wbc_settled_hold500_20261009_CXuOBF.log` | FAILED tick498,speed.0801463m/s; final success marker absent |

SHA256 respectively:
`b876c21ad0240f362d4f4779054a437bdf76aae41a96879aff7c2f56ec2de10e`,
`d357df7688253eaa34f5f586a5a169b82af9e5cb3cb90bcc15c1823726f07a79`,
`2331891f461c114f9666c0639f1e7e9227c7d28a57fcbb5b8fabbfe391c0be85`.

At failure loads108.20/121.44/101.75/93.43N,roll-.008518,pitch.012996rad.
Desired xdd+.154388; solved-.204981; measuredFD-.193365m/s2.
Thus wrong-way acceleration exists in the solution, not just the measurement.
100ticks is only.1s and does NOT establish sustained support/crossing.
Clock repair now has native evidence; longer settling is insufficient to fix control.

## Reporting caveats and next step

Process exit0 is not a physical pass: application cleanup can mask failure exit.
The final summary currently overwrites initial handoff step/qdd with last-loop
values; use first contact identity and per-tick traces. Reporting fix remains open.
Compact metrics: `/tmp/m1_summarize_wbc_hold_20261009.py LOG`.
Next use full frozen solver inputs to distinguish hard feasibility from task
allocation. See [feasibility audit](2026-10-09-m1-wbc-braking-feasibility.md).
Actual lift,10cm wheel-bottom clearance, safe landing, recovery and policy-only
avoidance remain unverified. No long train or checkpoint modification.
