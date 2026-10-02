def test_m1_touchdown_offset_is_relative_to_obstacle_not_root(monkeypatch):
    from extension.batch_mpc_planner.planner import _m1_semantic_touchdown_offset

    # obstacle_forward is already the root-to-obstacle projection.  The
    # touchdown offset must only cover obstacle depth and post-obstacle margin.
    assert _m1_semantic_touchdown_offset(0.70, 0.08, 0.08) == 0.16


def test_m1_touchdown_offset_preserves_batch_shape_and_dtype():
    import torch
    from extension.batch_mpc_planner.planner import _m1_semantic_touchdown_offset

    approach = torch.tensor([0.30, 0.70, 1.20], dtype=torch.float64)
    offset = _m1_semantic_touchdown_offset(approach, 0.08, 0.08)
    assert offset.shape == approach.shape
    assert offset.dtype == approach.dtype
    assert offset.device == approach.device
    torch.testing.assert_close(offset, torch.full_like(approach, 0.16))
    assert offset[:, None, None].shape == (3, 1, 1)
