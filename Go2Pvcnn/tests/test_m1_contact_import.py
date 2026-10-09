"""Guard the measured-contact path against a swallowed missing import."""
import ast
from pathlib import Path


def test_contact_resolver_imported_before_sensor_read():
    source = Path(__file__).resolve().parents[1] / "ame_baseline/ame_env_wrapper.py"
    tree = ast.parse(source.read_text())
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "get_mpc_teacher_action")
    calls = [n for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "resolve_named_indices"]
    imports = [n for n in ast.walk(method) if isinstance(n, ast.ImportFrom) and n.module == "extension.parallelism.rl_adapter" and any(a.name == "resolve_named_indices" for a in n.names)]
    assert calls, "Measured contact must resolve sensor body names"
    assert imports and min(n.lineno for n in imports) < min(n.lineno for n in calls), "Missing resolver import silently disables actual_contact_state"
