import torch


def test_mixed_primary_strict_rate_is_event_ratio_not_fixed_course_completion():
    from ame_baseline.m1_crossing_metrics import CrossingEpisodeAccumulator
    a=CrossingEpisodeAccumulator(1,'cpu',strict_mode='encounter')
    yes=torch.tensor([True]);no=~yes
    for success in (yes,no):
        a.update(candidate=yes,large_candidate=no,crossing_complete=no,
            done=yes,terminated=no,collision=no,large_avoided=no,
            strict_crossing_attempt=yes,strict_crossing_event=success)
    out=a.snapshot()
    assert out['strict_crossing_success_rate']==.5
    assert out['strict_obstacle_attempts']==2
    assert out['strict_crossing_episodes']==0


def test_wrapper_selects_encounter_metrics_and_passes_measured_wheel_contacts():
    from pathlib import Path
    source=(Path(__file__).parents[1]/'ame_baseline/ame_env_wrapper.py').read_text()
    assert 'strict_mode=' in source and 'wheel_grounded=support_contact' in source
