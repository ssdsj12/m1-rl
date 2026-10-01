from types import SimpleNamespace
import pytest
from extension.batch_mpc_planner.manager import MpcTrajectoryManager


class IsaacBodyOrder:
    def find_bodies(self, pattern):
        if pattern == '.*_foot':
            raise ValueError('No lowercase foot bodies')
        return [7, 8, 15, 16], ['FAR_FOOT_LINK', 'FBL_FOOT_LINK', 'RAR_FOOT_LINK', 'RBL_FOOT_LINK']


def test_m1_foot_positions_match_planner_fl_fr_rl_rr_order():
    manager = MpcTrajectoryManager(SimpleNamespace(), 'cpu')
    assert manager._foot_ids(IsaacBodyOrder()).tolist() == [8, 7, 16, 15]


def test_unknown_foot_order_is_rejected_instead_of_silently_swapping_legs():
    class Unknown(IsaacBodyOrder):
        def find_bodies(self, pattern):
            return [1, 2, 3, 4], ['a', 'b', 'c', 'd']
    with pytest.raises(ValueError, match='foot'):
        MpcTrajectoryManager(SimpleNamespace(), 'cpu')._foot_ids(Unknown())
