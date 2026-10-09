"""Offline same-state counterfactuals; never imports Isaac or applies control."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from ame_baseline.m1_wbc_qp import solve_wbc
from ame_baseline.m1_wbc_execution_adapter import (
    support_damping_target, pd_handoff_acceleration_contract,
)

source = Path(sys.argv[1])
raw = source.read_bytes()
rows = [json.loads(line.split(' ', 1)[1]) for line in raw.decode().splitlines()
        if line.startswith('M1_WBC_STATE ')]
if len(rows) != 1:
    raise ValueError('exactly one immutable native snapshot required')
s = rows[0]
for key in ('mass', 'bias', 'jac', 'frames', 'group_ids', 'mu', 'contact_matrix',
            'contact_rhs', 'effort_lower', 'effort_upper', 'native_limits',
            'prior_effort', 'root_com_velocity', 'joint_velocity', 'gaps'):
    s[key] = np.asarray(s[key])
k = len(s['jac'])
assert s['contact_matrix'].shape == (3*k, 22)
assert np.allclose(s['contact_matrix'], s['jac'].reshape(-1, 22))
velocity = np.r_[s['root_com_velocity'], s['joint_velocity']]
contact_v = np.einsum('kij,j->ki', s['jac'], velocity)
normal = s['frames'][:, :, 2]
vn = np.einsum('ki,ki->k', contact_v, normal)
rhs = s['contact_rhs'].reshape(k, 3)
normal_rhs = np.einsum('ki,ki->k', rhs, normal)
target = support_damping_target(root_com_velocity=s['root_com_velocity'],
                                joint_velocity=s['joint_velocity'])
print(json.dumps(dict(scope='offline_counterfactual_not_controller_validation',
    source=str(source), sha256=hashlib.sha256(raw).hexdigest(), identity=s['identity'],
    dt=s['dt'], contacts=k, gap_m=s['gaps'].tolist(), normal_velocity_mps=vn.tolist(),
    normal_rhs_mps2=normal_rhs.tolist(),
    gap_correction_mps2=np.maximum(0., -s['gaps']/s['dt']**2).tolist(),
    velocity_correction_mps2=(-vn/s['dt']).tolist(), target_base=target[:6].tolist())))
for native_capacity in (False, True):
    for zero_normal_rhs in (False, True):
        # Removing the normal RHS is an intentionally invalid diagnostic, not
        # a proposed rolling/contact controller. Preserve every tangent row.
        trial_rhs = rhs-normal_rhs[:, None]*normal if zero_normal_rhs else rhs
        solution = solve_wbc(mass=s['mass'], bias=s['bias'], jac=s['jac'],
            frames=s['frames'], mu=s['mu'], normal_min=np.zeros(k),
            normal_max=np.full(k, s['weight']), group_ids=s['group_ids'],
            group_min=np.full(4, 35.), group_max=np.full(4, s['weight']),
            effort_lower=-s['native_limits'] if native_capacity else s['effort_lower'],
            effort_upper=s['native_limits'] if native_capacity else s['effort_upper'],
            contact_matrix=s['contact_matrix'], contact_rhs=trial_rhs.reshape(-1),
            **pd_handoff_acceleration_contract(target_qdd=target))
        report = dict(native_capacity=native_capacity, zero_normal_rhs=zero_normal_rhs,
                      valid=solution['valid'], reason=solution['reason'])
        if solution['valid']:
            report.update(qdd_base=solution['qdd'][:6].tolist(),
                target_error_norm=float(np.linalg.norm(solution['qdd']-target)),
                max_violation=solution['max_violation'],
                max_dynamics_residual=float(np.max(np.abs(solution['dynamics_residual']))),
                effort_step_max=float(np.max(np.abs(solution['effort']-s['prior_effort']))))
            report['largest_effort_changes'] = [dict(name=s['joint_names'][i],
                prior=float(s['prior_effort'][i]), desired=float(solution['effort'][i]),
                joint_velocity=float(s['joint_velocity'][i]))
                for i in np.argsort(np.abs(solution['effort']-s['prior_effort']))[-4:]]
        print(json.dumps(report), flush=True)
