import torch
from ame_baseline import m1_crossing_state as crossing


def test_crossing_requires_front_and_rear_axles_then_emits_completion():
    s = crossing.CrossingState.create(1, "cpu")
    args = dict(candidate=torch.tensor([True]), wheel_clearance=torch.full((1, 4), .08),
               large_obstacle=torch.tensor([False]), done=torch.tensor([False]), terminated=torch.tensor([False]))
    crossing.update_crossing_state(s, wheel_x_from_obstacle=torch.zeros(1, 4), **args)
    assert bool(s.candidate[0])
    crossing.update_crossing_state(s, wheel_x_from_obstacle=torch.tensor([[.2, .2, -.1, -.1]]), **args)
    assert bool(s.crossed_front[0])
    event = crossing.update_crossing_state(s, wheel_x_from_obstacle=torch.full((1, 4), .2), **args)
    assert bool(event["completed"][0])


def test_large_obstacle_never_starts_crossing():
    s = crossing.CrossingState.create(1, "cpu")
    event = crossing.update_crossing_state(
        s, candidate=torch.tensor([True]), wheel_x_from_obstacle=torch.ones(1, 4),
        wheel_clearance=torch.ones(1, 4), large_obstacle=torch.tensor([True]),
        done=torch.tensor([False]), terminated=torch.tensor([False]),
    )
    assert not bool(event["candidate"][0])
