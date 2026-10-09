import ast
from pathlib import Path
import torch
from test_m1_lift_forecast import fixture
from ame_baseline.m1_anticipatory_support import entry_plan


def test_translation_only_plan_preserves_attitude():
    x=fixture()
    out=entry_plan(model=x['model'],root=x['roots'][:,0],rpy=x['rpys'][:,0],
        anchors=x['anchors'],selected=x['selected'],wheel_q=x['wheel_q'],height=.16,
        translation_only=True)
    assert torch.equal(out['rpy'],x['rpys'][:,0])


def test_runtime_declares_translation_capability_before_selection():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='entry_plan')
    assert any(k.arg=='translation_only' and isinstance(k.value,ast.Constant) and k.value.value is True for k in call.keywords)
