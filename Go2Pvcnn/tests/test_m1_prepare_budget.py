"""Test real probe budget expressions without importing Isaac/starting GPU."""
import ast
from pathlib import Path
from types import SimpleNamespace


def rejected(field,**values):
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.If)
        and isinstance(n.test,ast.UnaryOp) and isinstance(n.test.op,ast.Not)
        and isinstance(n.test.operand,ast.Compare)
        and any(isinstance(x,ast.Attribute) and x.attr==field for x in ast.walk(n.test)))
    return eval(compile(ast.Expression(node.test),'<probe-budget>','eval'),dict(args=SimpleNamespace(**values)))


def test_prepare_accepts_confirmed_four_seconds_but_not_more():
    assert not rejected('num_steps',num_steps=200)
    assert rejected('num_steps',num_steps=201)
    assert rejected('num_steps',num_steps=0)


def test_lift_budget_is_not_extended_with_prepare():
    assert not rejected('lift_steps',lift_steps=200)
    assert rejected('lift_steps',lift_steps=201)
