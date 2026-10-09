"""Ensure PREPARE and coordinated UNLOAD share the selected reserve."""
import ast
from pathlib import Path


def test_both_post_lift_load_models_use_configured_reserve():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    values=[kw.value for call in ast.walk(tree) if isinstance(call,ast.Call)
            and isinstance(call.func,ast.Name) and call.func.id=='transfer_target'
            for kw in call.keywords if kw.arg=='support_floor']
    # There are three transfer_target calls with a support_floor: the initial
    # PREPARE model uses its independent load-floor option, while both
    # post-lift checks must use the configured reserve.
    assert len(values)==3
    assert sum(isinstance(value,ast.Name) and value.id=='prepare_reserve'
               for value in values)==2
    source=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert '--rear_lift_reserve' in source
    assert 'selected>=2' in source
