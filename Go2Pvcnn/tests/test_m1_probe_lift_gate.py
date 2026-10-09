"""Check the actual probe's safety-mask wiring without launching Isaac."""
import ast
from pathlib import Path
from types import SimpleNamespace
import torch


def mask_expression():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call)
              and isinstance(n.func,ast.Name) and n.func.id=='lift_target')
    value=next(k.value for k in call.keywords if k.arg=='advance_mask')
    return compile(ast.Expression(body=value),'<actual-probe-mask>','eval')


def test_world_frame_lift_receives_support_mask_without_legacy_transfer():
    advance=torch.tensor([True,False])
    result=eval(mask_expression(),dict(torch=torch,is_settling=False,is_landing=False,
        touchdown=torch.tensor([False,False]),advance=advance,
        args=SimpleNamespace(lift_support_transfer=False)))
    assert result is not None, 'computed support gate must reach LIFT in world-frame mode'
    torch.testing.assert_close(result,advance)


def test_landing_and_settle_keep_their_touchdown_masks():
    values=dict(torch=torch,touchdown=torch.tensor([True,False]),
        advance=torch.tensor([False,False]),args=SimpleNamespace(lift_support_transfer=False))
    torch.testing.assert_close(eval(mask_expression(),dict(values,is_landing=True,is_settling=False)),
                               torch.tensor([False,True]))
    torch.testing.assert_close(eval(mask_expression(),dict(values,is_landing=True,is_settling=True)),
                               torch.tensor([False,False]))
