"""Require measured angle and contact-patch evidence in lifted rolling audit."""
import ast
from pathlib import Path


def test_lift_samples_include_measured_wheel_angle():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call)
              and isinstance(n.func,ast.Attribute) and n.func.attr=='append'
              and isinstance(n.func.value,ast.Name) and n.func.value.id=='lift_samples')
    assert 'wheel_joint_position' in {k.arg for k in call.args[0].keywords}


def test_contact_audit_has_exact_weak_and_loaded_wheels():
    text=(Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text()
    assert '/World/envs/env_3/Robot/' in text
    assert 'M1_ROLL_CONTACT_PATCH ' in text
