"""True point geometry only; no rolling acceleration or force assumptions."""
import numpy as np


def contact_inventory(*, points, normals, owners, gaps, normal_forces,
                      load_threshold=1e-3):
    """Retain native near-contact geometry independently of measured loading.

    A zero-force point can be approaching the surface. It is not discarded or
    labelled attached. Only geometrically coincident reports are merged;
    distinct moment arms survive. The loaded mask is evidence, not a mode.
    """
    force = np.asarray(normal_forces, dtype=np.float64)
    if (force.ndim != 1 or force.shape != (len(points),)
            or not np.isfinite(force).all() or np.any(force < 0)
            or not np.isfinite(load_threshold) or load_threshold < 0):
        raise ValueError('finite nonnegative aligned normal force and threshold required')
    result = deduplicate_contact_points(points=points, normals=normals,
        owners=owners, gaps=gaps)
    force = np.asarray([force[indices].sum() for indices in result['source_indices']],
                       dtype=np.float64)
    if not np.isfinite(force).all():
        raise ValueError('nonfinite merged normal force')
    result['normal_forces'] = force
    result['measured_loaded'] = force > load_threshold
    return result


def deduplicate_contact_points(*, points, normals, owners, gaps,
                               position_tolerance=1e-7,
                               normal_tolerance=1e-6,
                               gap_tolerance=1e-7):
    """Merge only duplicate contact records at the same physical point.

    Co-located forces have identical moment arms, so their resultant is
    representable by one force variable without losing a contact moment.
    Distinct points, normals, owners, or gaps remain separate.
    """
    points = np.asarray(points, dtype=np.float64)
    normals = np.asarray(normals, dtype=np.float64)
    owners = np.asarray(owners)
    gaps = np.asarray(gaps, dtype=np.float64)
    if (points.ndim != 2 or points.shape[1:] != (3,)
            or normals.shape != points.shape or owners.shape != (len(points),)
            or owners.dtype.kind not in 'iu' or gaps.shape != (len(points),)
            or not all(np.isfinite(v).all() for v in (points, normals, gaps))
            or not np.isfinite([position_tolerance, normal_tolerance,
                                gap_tolerance]).all()
            or min(position_tolerance, normal_tolerance, gap_tolerance) < 0):
        raise ValueError('finite aligned contact geometry, integer owners and nonnegative tolerances required')
    if len(points) == 0:
        return dict(points=points.copy(), normals=normals.copy(),
                    owners=owners.copy(), gaps=gaps.copy(),
                    multiplicities=np.zeros(0, dtype=np.int64), source_indices=[])
    unique_points, unique_normals, unique_owners, unique_gaps = [], [], [], []
    source_indices = []
    for index in range(len(points)):
        match = None
        for unique_index in range(len(unique_points)):
            if (owners[index] == unique_owners[unique_index]
                    and np.max(np.abs(points[index]-unique_points[unique_index])) <= position_tolerance
                    and np.max(np.abs(normals[index]-unique_normals[unique_index])) <= normal_tolerance
                    and abs(gaps[index]-unique_gaps[unique_index]) <= gap_tolerance):
                match = unique_index
                break
        if match is None:
            unique_points.append(points[index].copy())
            unique_normals.append(normals[index].copy())
            unique_owners.append(int(owners[index]))
            unique_gaps.append(float(gaps[index]))
            source_indices.append([index])
        else:
            source_indices[match].append(index)
    return dict(points=np.asarray(unique_points), normals=np.asarray(unique_normals),
                owners=np.asarray(unique_owners, dtype=owners.dtype),
                gaps=np.asarray(unique_gaps),
                multiplicities=np.asarray([len(v) for v in source_indices], dtype=np.int64),
                source_indices=source_indices)


def contact_geometry(points, normals, owners, com_jac, com_positions):
    points, normals, com_jac, com_positions = [np.asarray(x,dtype=np.float64)
        for x in (points,normals,com_jac,com_positions)]
    owners = np.asarray(owners)
    if (points.ndim != 2 or points.shape[1] != 3 or normals.shape != points.shape
            or owners.shape != (len(points),) or owners.dtype.kind not in 'iu'
            or com_jac.shape != (4,6,22) or com_positions.shape != (4,3)):
        raise ValueError('invalid M1 contact geometry dimensions or ownership')
    if (any(not np.isfinite(x).all() for x in (points,normals,com_jac,com_positions))
            or np.any(owners < 0) or np.any(owners >= 4)):
        raise ValueError('finite geometry and named wheel indices0..3 required')
    norm = np.linalg.norm(normals,axis=1)
    if not np.allclose(norm,1.,atol=1e-4,rtol=0):
        raise ValueError('contact normals must already be unit vectors')
    normal = normals/norm[:,None]
    offset = points-com_positions[owners]
    selected = com_jac[owners]
    jac = selected[:,:3]+np.cross(selected[:,3:].transpose(0,2,1),
                                offset[:,None,:],axis=-1).transpose(0,2,1)
    seed = np.eye(3)[np.abs(normal).argmin(axis=1)]
    tangent = seed-(seed*normal).sum(1)[:,None]*normal
    tangent /= np.linalg.norm(tangent,axis=1)[:,None]
    second = np.cross(normal,tangent)
    return dict(jac=jac,frames=np.stack((tangent,second,normal),axis=-1),
                group_ids=owners.copy(),points=points.copy())
