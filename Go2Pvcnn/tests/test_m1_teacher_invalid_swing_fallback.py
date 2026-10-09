import torch

from ame_baseline import m1_teacher_phase


def test_invalid_planner_frame_holds_last_leg_target_only_for_same_active_obstacle_swing():
    action = torch.zeros((3, 16))
    action[:, 12:] = 0.25
    previous = torch.arange(36, dtype=torch.float32).reshape(3, 12) / 10.0

    preserve = getattr(m1_teacher_phase, "preserve_invalid_obstacle_leg_action", None)
    assert callable(preserve), "active obstacle hold must preserve the last valid single-leg target"
    result, valid, held = preserve(
        action,
        valid=torch.tensor([False, True, False]),
        teacher_active=torch.tensor([True, True, True]),
        obstacle_hold=torch.tensor([True, True, True]),
        selected_leg=torch.tensor([0, 1, 2]),
        selected_phase=torch.tensor([4, 5, 6]),
        last_leg_action=previous,
        last_leg=torch.tensor([0, 1, 1]),
        last_phase=torch.tensor([4, 5, 6]),
        leg_cols=tuple(range(12)),
    )

    assert held.tolist() == [True, False, False]
    assert valid.tolist() == [True, True, False]
    assert torch.equal(result[0, :12], previous[0])
    assert torch.equal(result[1], action[1])
    assert torch.equal(result[2], action[2])
    assert torch.equal(result[:, 12:], action[:, 12:])
