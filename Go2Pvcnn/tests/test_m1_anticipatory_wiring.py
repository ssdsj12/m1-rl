"""Probe opt-in contracts without Isaac startup; numerical helpers tested separately."""
import ast
from pathlib import Path


def test_entry_reference_is_opt_in_and_reused_in_both_phases():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
    flag=[n for n in calls if any(isinstance(a,ast.Constant) and a.value=='--anticipatory_prepare' for a in n.args)]
    assert len(flag)==1
    assert any(k.arg=='action' and k.value.value=='store_true' for k in flag[0].keywords)
    fixed=[n for n in calls if isinstance(n.func,ast.Name) and n.func.id=='fixed_reference_step']
    assert len(fixed)==2
    for n in fixed:assert any(k.arg=='goal' and isinstance(k.value,ast.Name) and k.value.id=='anticipatory_goal' for k in n.keywords)
    assert sum(isinstance(n.func,ast.Name) and n.func.id=='entry_plan' for n in calls)==1
    # Final PREPARE gate must not bypass unarrived references.
    assert any(isinstance(n,ast.keyword) and n.arg=='ik_valid' and
        isinstance(n.value,ast.BinOp) and any(isinstance(x,ast.Name) and x.id=='reference_ready' for x in ast.walk(n.value)) for n in ast.walk(tree))
