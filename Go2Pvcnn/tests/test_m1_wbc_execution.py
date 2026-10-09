from pathlib import Path
import ast


def test_free_qp_execution_opt_in_uses_real_history_and_bounds():
    source=(Path(__file__).parents[1]/'scripts/probe_m1_wbc_free.py').read_text()
    assert "parser.add_argument('--qp_control', action='store_true')" in source
    assert 'effort_step_bounds(' in source
    assert 'solve_wbc(' in source
    assert 'M1_FREE_QP ' in source
    assert 'effort_history' in source
    assert "owner='explicit_total'" in source
    assert 'native implicit drive remains enabled' in source
    assert 'applied force differs from sole-owner request' in source
    tree=ast.parse(source)
    assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
               and n.func.attr=='get_dof_actuation_forces' for n in ast.walk(tree))
