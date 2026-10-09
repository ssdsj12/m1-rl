# M1 contact geometry and grouped support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans, inline in existing worktree.

**Goal:** Preserve actual multipoint wheel contact geometry and wheel-level load gates.
**Architecture:** Pure geometry adapter takes world contact points/normals and their named wheel owners, shifts COM Jacobians to those points, builds frames. CPU QP gets summed per-wheel normal bounds, not repeated per-point minima.
**Tech Stack:** NumPy, existing OSQP oracle and native contact view observer.

- [ ] RED `tests/test_m1_wbc_contacts.py`: material point rolling velocity, distinct moment arms,
  translation invariance, right-handed frames and invalid normals/owners/nonfinite data.
- [ ] Implement `ame_baseline/m1_wbc_contacts.py` with `contact_geometry(points,normals,
  owners,com_jac,com_positions)`: Kpoints,4wheel COM Jacobians6x22; return jacKx3x22,
  framesKx3x3 and copied integer group_ids. Formula Jpoint=Jlinear+Jangular×offset;
  frame tangent from least-aligned world axis projected onto normal plane.
- [ ] RED grouped-force test with two points per wheel: eachpoint max60N, wheelmin90N,
  wheelmax110N. Total392.4N must yield98.1N perwheel without requiring90N perpoint.
- [ ] Add optional group_ids/group_min/group_max to QP; validate integer ownership and
  sum `normal[k].dot(force[k])` across each group in hard bounds. No point deletion.
- [ ] GREEN full CPU set. Native observer creates per-wheel contact views before warmup,
  reads force/point/normal/count/start buffers at physics dt, keeps positive normal-force
  points, validates their vector sum against native net normal force within1e-3N.
  Adapter maps contact points via wheel COM Jacobians and validates point velocities
  with native link linear/angular velocities. Do not difference changing patch IDs.
- [ ] Bounded GPU7 read-only capture then stop; exact own placeholder restoration.
  Record counts, force closure, point moments/velocity errors. No actuator commands
  or contact acceleration constraints added yet; rolling Jdot*v still must be derived.
- [ ] Commit code, tests and evidence; static numerical allocation is not physical support.
