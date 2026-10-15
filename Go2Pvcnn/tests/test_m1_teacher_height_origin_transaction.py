"""Catch missing/recaptured origin and coordinate scaling in real transactions."""
import pytest
import torch
from test_m1_teacher_load_feedback_transaction import load_teacher, fixture
from test_m1_reference_teacher import advance


def test_origin_is_atomic_capture_not_recaptured_on_root_motion():
    teacher, state = load_teacher()
    expected = state.root_pos_w[:, 2].clone()
    assert teacher.step(state).valid.item()
    row = teacher._rows[0]
    assert torch.equal(row['support_capture_root_z'], expected)
    height = row['support_execution_z'].clone()
    state = advance(state)
    state.root_pos_w[:, 2] -= .001
    assert teacher.step(state).valid.item()
    assert torch.equal(row['support_capture_root_z'], expected)
    assert torch.equal(row['support_execution_z'], height)


@pytest.mark.parametrize('missing', ['support_capture_root_z', 'support_execution_z'])
def test_partial_height_origin_history_is_rejected(missing):
    teacher, state = load_teacher()
    assert teacher.step(state).valid.item()
    row = teacher._rows[0]
    # Explicitly construct paired history even against the pre-v33 producer.
    row['support_capture_root_z'] = state.root_pos_w[:, 2].clone()
    del row[missing]
    with pytest.raises(ValueError):
        teacher.step(advance(state))


def test_reset_discards_captured_origin():
    teacher, state = load_teacher()
    assert teacher.step(state).valid.item()
    assert 'support_capture_root_z' in teacher._rows[0]
    teacher.step(advance(state, episode_id=state.episode_id+1,
                         reset_mask=torch.ones_like(state.reset_mask)))
    assert 'support_capture_root_z' not in teacher._rows[0]


def test_pose_transaction_origin_delta_is_not_scaled_twice():
    from ame_baseline.m1_teacher_pose import backtrack_feedback_reference, BodyPose, _rotation
    from ame_baseline.m1_teacher_ik import IKConfig
    q, ref = fixture()
    measured = BodyPose(ref.body.pos_w.clone(), ref.body.quat_w)
    measured.pos_w[:, 2] -= .001
    result = backtrack_feedback_reference(
        ref, ref, q.new_zeros(1, 3), q.new_zeros(1, 3), q.new_zeros(1),
        q, q, q, .02, IKConfig(), execution_valid=lambda ik, u: ik.valid,
        measured=measured, active_wheel=torch.tensor([0]), execution_mode=torch.tensor([1]),
        previous_support_reference_w_z=ref.wheels_w[:, :, 2],
        proposed_support_reference_w_z=ref.wheels_w[:, :, 2],
        support_capture_root_z=ref.body.pos_w[:, 2])
    assert result.valid.item()
    # The support body target remains the original pose under pure root translation.
    expected = torch.einsum('bij,bkj->bki', _rotation(ref.body.quat_w).transpose(1, 2),
                            ref.wheels_w-ref.body.pos_w[:, None])
    assert torch.allclose(result.execution_target.body_goal[:, 1:], expected[:, 1:], atol=1e-10, rtol=0)


def test_completed_restore_clears_origin_with_height():
    from dataclasses import replace
    from test_m1_reference_teacher import restoring_teacher, api
    from ame_baseline.m1_teacher_ik import body_feet
    from ame_baseline.m1_teacher_pose import _rotation
    teacher, state = restoring_teacher()
    teacher.cfg = replace(teacher.cfg, slow_rolling=True, load_feedback=True)
    row = teacher._rows[0]
    row['stable'] = 4
    row['support_capture_root_z'] = state.root_pos_w[:, 2].clone()
    row['support_execution_z'] = (state.root_pos_w[:, None]+torch.einsum(
        'bij,bkj->bki', _rotation(state.root_quat_w), body_feet(state.last_applied_leg_target)))[:, :, 2]
    state.recovered[:, 0, 0] = True
    result = teacher.step(state)
    assert result.valid.item()
    assert row['phase'] == api().Phase.APPROACH
    assert 'support_capture_root_z' not in row and 'support_execution_z' not in row
