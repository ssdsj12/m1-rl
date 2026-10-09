import ast
from pathlib import Path


def test_unload_timeout_reads_last_executed_action_without_extra_step():
    tree=ast.parse((Path(__file__).parents[1]/'scripts/probe_m1_contact_prepare.py').read_text())
    blocks=[n for n in ast.walk(tree) if isinstance(n,ast.If)
            and any(isinstance(x,ast.Constant) and x.value=='M1_UNLOAD_FINAL_CHECK '
                    for x in ast.walk(n))]
    assert blocks,'final post-action unload check missing'
    block=min(blocks,key=lambda n:len(ast.unparse(n)))
    source=ast.unparse(block)
    assert 'observe_support(robot, sensor, selected)' in source
    assert 'unload_ready(' in source
    assert 'torch.where(ready_now, unload_count + 1, 0)' in source
    assert 'env.step(' not in source
    assert source.index('observe_support(')<source.index("stopped = 'unload_timeout'")
