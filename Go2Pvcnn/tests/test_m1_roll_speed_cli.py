"""Exercise the real CLI declaration without launching Isaac Sim."""
import argparse
import ast
from pathlib import Path


def test_low_speed_comparison_retains_default_and_upper_bound():
    tree = ast.parse((Path(__file__).parents[1] / 'scripts/probe_m1_contact_prepare.py').read_text())
    declaration = next(node for node in tree.body if isinstance(node, ast.Expr)
                       and isinstance(node.value, ast.Call) and node.value.args
                       and isinstance(node.value.args[0], ast.Constant)
                       and node.value.args[0].value == '--roll_speed')
    parser = argparse.ArgumentParser()
    exec(compile(ast.Module(body=[declaration], type_ignores=[]), '<cli>', 'exec'), {'parser': parser})
    assert parser.parse_args(['--roll_speed', '.02']).roll_speed == .02
    assert parser.parse_args([]).roll_speed == .1
    import pytest
    with pytest.raises(SystemExit):
        parser.parse_args(['--roll_speed', '.2'])
