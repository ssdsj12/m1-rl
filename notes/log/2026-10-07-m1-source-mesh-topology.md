# Source wheel topology and installed SDF support audit

Parent: [T306](../todo/T306-m1-ame-long-train-stability.md), loaded-contact fidelity child.
Baseline Ref: dcbb21e. Candidate Ref: containing commit.
Key file: Go2Pvcnn/scripts/audit_m1_source_mesh.py.

## Scope / improvement over previous version

Previous comparison proved explicit wheel effort delivery but no useful loaded
rolling. This update adds a CPU-only, read-only topology audit of all four original
wheel meshes before proposing source-faithful SDF contact. No runtime controller,
training defaults, USD assets, mass/inertia/materials or acceptance gates changed.

## Procedure and results

Run the audit using amp Python, bundled omni.usd.libs on PYTHONPATH and its bin
directory on LD_LIBRARY_PATH. Initial import without LD_LIBRARY_PATH failed on
libtf.so; using the installed USD bin resolved it without installation changes.
TraverseInstanceProxies reads collision meshes; NumPy welds coordinates only in
temporary arrays, never writes them to USD. Both exact coordinates and rounding
to seven decimals were checked; this is an audit, not mesh repair.

Each of four wheels: 194634 input vertices, 64878 triangles, 32550 distinct
positions; finite coordinates; zero boundary edges; zero zero-area triangles;
zero inconsistent orientation among two-face edges. However six edges each
have four incident triangles (nonmanifold), unchanged under both weld checks.
Each wheel also contains five duplicate triangles (same three positions,
irrespective of winding), reproduced in the final successful full audit.
Minimum doubled triangle area 5.5023e-13 m^2. Signed volume .00045739914 m^3
is only the oriented-surface sum, not proof of a valid solid. Defect endpoints
are around radius .071 m, inside the outer ~.096 m envelope. Full endpoints
and source point/index digests are emitted for reproducible inspection.
No self-intersection or connected-solid validity test was performed yet.

Installed Isaac Sim extsPhysics/omni.physx.tests test
PhysxTriangleMeshCollisionAPI.py explicitly applies PhysxSDFMeshCollisionAPI,
sets sdfResolution and MeshCollisionAPI approximation='sdf', and verifies
cooking plus dynamic rigid-body behavior. This establishes installed API/test
support, NOT that this wheel/articulation has cooked or runs successfully.
Installed test also exposes optional SDF remeshing/reduction: do not silently
enable these and call the result identical geometry.

## Decision / follow-up

New child under loaded-contact fidelity: inspect nonmanifold local face overlap
and valid solid interpretation before SDF runtime comparison. Source hull may
still be relevant to the stall, but topology finding does not prove its cause.
No GPU probe, training, or process termination this audit. Exact placeholder
PID2915023 remains observed running. Original checkout and display are untouched.
Original-wheel obstacle traversal, stable far-side landing, bypass, policy/video
acceptance remain open. No success or upload claim.
