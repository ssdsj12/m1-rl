"""Execute the production recovery block without importing Isaac/starting a GPU.

The old string-only wiring test could not catch a step-local unbound ``robot``.
Compile the unchanged block from step, with no trace/debug prebinding. Native
probe additionally exercises this code inside the actual simulation wrapper.
"""
import ast
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from extension.parallelism.m1_kinematics import M1_PLANNER_JOINT_NAMES


def recovery_path():
    source = Path(__file__).parents[1] / "ame_baseline/ame_env_wrapper.py"
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AmeRslRlEnvWrapper")
    step = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "step")
    start = next(i for i, n in enumerate(step.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "strict_crossing_touchdown" for t in n.targets)
                 and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                 and n.value.func.attr == "clone")
    end = next(i for i in range(start + 1, len(step.body)) if isinstance(step.body[i], ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "strict_result" for t in step.body[i].targets))
    function = ast.parse("def run(self, touchdown_safe, done):\n    pass\n").body[0]
    function.body = step.body[start:end] + ast.parse(
        "return strict_crossing_touchdown, recovery_balance_safe").body
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    scope = {"torch": torch, "os": os, "__package__": "ame_baseline"}
    exec(compile(module, str(source), "exec"), scope)
    return scope["run"]


class Scene(dict):
    env_origins = torch.zeros(1, 3)


def healthy_robot():
    return SimpleNamespace(joint_names=M1_PLANNER_JOINT_NAMES, data=SimpleNamespace(
        root_quat_w=torch.tensor([[1., 0., 0., 0.]]), root_ang_vel_w=torch.zeros(1, 3),
        joint_pos=torch.zeros(1, 12), default_joint_pos=torch.zeros(1, 12),
        root_pos_w=torch.tensor([[0., 0., .456]]),
        default_root_state=torch.tensor([[0., 0., .456]])))


def run(robot, touchdown=True):
    wrapper = SimpleNamespace(unwrapped=SimpleNamespace(scene=Scene(robot=robot)))
    return recovery_path()(wrapper, torch.tensor([touchdown]), torch.tensor([False]))


def test_normal_no_debug_path_recovers_healthy_loaded_pose(monkeypatch):
    monkeypatch.delenv("M1_CONTROL_TRACE", raising=False)
    monkeypatch.delenv("M1_STEP_DEBUG", raising=False)
    touchdown, recovery = run(healthy_robot())
    assert touchdown.item()
    assert recovery.item(), "healthy recovery must not depend on debug binding robot"


def test_missing_joint_measurement_is_visible_not_silent_false():
    robot = healthy_robot()
    del robot.data.joint_pos
    with pytest.raises(RuntimeError, match="M1 recovery measurement failed") as error:
        run(robot)
    assert isinstance(error.value.__cause__, AttributeError)


@pytest.mark.parametrize("fault", ["tilt", "rate", "joint", "height", "nan", "unloaded"])
def test_recovery_still_rejects_actual_unsafe_state(fault):
    robot = healthy_robot()
    if fault == "tilt":
        robot.data.root_quat_w[:] = torch.tensor([[.98, .20, 0., 0.]])
    elif fault == "rate":
        robot.data.root_ang_vel_w[0, 0] = 1.
    elif fault == "joint":
        robot.data.joint_pos[0, 0] = .4
    elif fault == "height":
        robot.data.root_pos_w[0, 2] = .2
    elif fault == "nan":
        robot.data.root_quat_w[0, 0] = float("nan")
    _, recovery = run(robot, touchdown=fault != "unloaded")
    assert not recovery.item()


def test_wrapper_pays_real_subthreshold_progress_without_prelift_event():
    # Execute the real wrapper reward integration; checking helper alone would
    # miss a forgotten kwarg and leave the running job on the old sparse reward.
    from ame_baseline.m1_required_crossing import required_crossing_reward
    source = Path(__file__).parents[1] / "ame_baseline/ame_env_wrapper.py"
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AmeRslRlEnvWrapper")
    step = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "step")
    block = next(n for n in step.body if isinstance(n, ast.If) and any(
        isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        and c.func.id == "required_crossing_reward" for c in ast.walk(n)))
    flag = torch.tensor([False])
    scope = dict(torch=torch, required_crossing_reward=required_crossing_reward,
        self=SimpleNamespace(unwrapped=SimpleNamespace(cfg=SimpleNamespace(m1_flat_first=True),
            step_dt=.02, reward_manager=SimpleNamespace(_step_reward=torch.zeros(1, 1)))),
        rewards=torch.zeros(1), required_zone=~flag, collision=flag, done=flag,
        touchdown_safe=~flag, recovery_balance_safe=~flag,
        strict_result={"single_prelift_event": flag, "prelift_progress_delta": torch.tensor([.15]),
                       "recovery_complete": flag}, extras={})
    exec(compile(ast.fix_missing_locations(ast.Module(body=[block], type_ignores=[])), str(source), "exec"), scope)
    assert scope["rewards"].item() == pytest.approx(.045)
    assert scope["extras"]["log"]["RequiredCrossing/prelift_events"].item() == 0
