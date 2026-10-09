"""Require native pose/body COM telemetry, not wheel-fitted attitude."""
import ast
from pathlib import Path


def test_lift_records_direct_native_pose_and_named_body_com():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    append=next(n for n in ast.walk(tree) if isinstance(n,ast.Call)
        and isinstance(n.func,ast.Attribute) and n.func.attr=='append'
        and isinstance(n.func.value,ast.Name) and n.func.value.id=='lift_samples')
    fields={k.arg:ast.unparse(k.value) for k in append.args[0].keywords}
    assert fields.get('root_quat_w')=='robot.data.root_quat_w.tolist()'
    assert fields.get('body_names')=='list(robot.body_names)'
    assert fields.get('body_com_w')=='robot.data.body_com_pos_w.tolist()'


def test_entry_snapshot_is_frozen_before_prepare():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    assignments=[n for n in ast.walk(tree) if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='entry_snapshot' for t in n.targets)]
    assert len(assignments)==1
    node=assignments[0]
    fields={k.arg:ast.unparse(k.value) for k in node.value.keywords}
    assert fields['root']=='entry_root.tolist()'
    assert fields['rpy']=='entry_rpy.tolist()'
    assert fields['joint_position']=='robot.data.joint_pos.tolist()'
    loop=next(n for n in ast.walk(tree) if isinstance(n,ast.For)
        and 'args.num_steps if stopped is None else 0' in ast.unparse(n.iter))
    assert node.lineno<loop.lineno
