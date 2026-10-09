from pathlib import Path


def test_pd_oracle_is_separate_from_qp_execution_and_uses_measured_projected_force():
    s=(Path(__file__).parents[1]/'scripts/probe_m1_wbc_free.py').read_text()
    assert "parser.add_argument('--pd_oracle', action='store_true')" in s
    assert 'args.qp_control and args.pd_oracle' in s
    assert 'M1_PD_ORACLE ' in s
    assert 'get_dof_projected_joint_forces().clone()' in s
    assert 'projected_before=projected_before.tolist()' in s
    assert 'projected_mid_residual_max' in s
    assert 'projected_before_residual_max' in s
    assert "max_base_force_n=residual[:,:3].abs().amax(-1).tolist()" in s
    assert "max_base_moment_nm=residual[:,3:6].abs().amax(-1).tolist()" in s
    assert "max_joint_torque_nm=residual[:,6:].abs().amax(-1).tolist()" in s
    assert 'max(r[\'max_base_force_n\']) <= .05' in s
    assert 'max(r[\'max_base_moment_nm\']) <= .02' in s
    assert 'max(r[\'max_joint_torque_nm\']) <= .02' in s
    assert "residual_units='base_linear_N_base_angular_Nm_joint_Nm'" in s
    assert 'oracle_effort' in s
    assert 'if not args.pd_oracle:' in s
