"""Verify the reward-only counterfactual on saved model600 contact trajectories.

This CPU-only verifier does not rerun the simulator, policy or encounter tracker.
It retains saved physical events and prelift increments, and changes only the
positive-shaping gate. Wheel quaternions were not recorded, so this is not a
new physical crossing evaluation or a prediction of the repaired policy.

Run with PYTHONPATH pointing at the candidate Go2Pvcnn package directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from ame_baseline import m1_required_crossing as reward_contract


SUPPORT_ORDER = [
    "FBL_FOOT_LINK", "FAR_FOOT_LINK", "RBL_FOOT_LINK", "RAR_FOOT_LINK",
]


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def vector(value, count, name, *, dtype=torch.float64):
    result = torch.as_tensor(value, dtype=dtype, device="cpu")
    require(result.shape == (count,), f"{name} must have shape [{count}]")
    if result.is_floating_point():
        require(torch.isfinite(result).all(), f"{name} must be finite")
    return result


def new_mode(record):
    source = record["course"]
    course = {
        name: torch.as_tensor(source[name], dtype=dtype, device="cpu")
        for name, dtype in (
            ("centers_top", torch.float64), ("half_extents", torch.float64),
            ("valid", torch.bool), ("ids", torch.long),
        )
    }
    count, capacity = course["valid"].shape
    origins = torch.as_tensor(record["origins"], dtype=torch.float64)
    require(origins.shape == (count, 3), "course origins must be [B,3]")
    require(count == 4, "this saved model600 diagnosis must have four environments")
    require((course["valid"].sum(-1) == 2).all(), "stage1 requires two real obstacles")
    required = reward_contract.progressive_required_wheels(course, origins[:, 1])
    require((required.sum(-1)[course["valid"]] == 2).all(),
            "each progressive obstacle must require its two same-side wheels")
    end = torch.where(
        course["valid"],
        course["centers_top"][..., 0] + course["half_extents"][..., 0] + .9,
        torch.full_like(course["half_extents"][..., 0], -torch.inf),
    ).amax(-1)
    return {
        "course": course, "origins": origins, "required": required, "end": end,
        "recovered": torch.zeros_like(required),
        "gate": reward_contract.RequiredCrossingRewardGate(count, capacity, "cpu"),
        "steps": 0, "max_old_reconstruction_error": 0.,
        "stats": [dict(
            env=i, nonterminal_frames=0, terminal_frames=0, blocked_frames=0,
            post_slab_frames=0, post_slab_old_positive_frames=0,
            post_slab_candidate_positive_frames=0, post_slab_old_reward_sum=0.,
            post_slab_candidate_reward_sum=0., post_slab_removed_positive_sum=0.,
            post_slab_negative_cost_sum=0., all_old_reward_sum=0.,
            all_candidate_reward_sum=0., all_negative_cost_sum=0.,
            strict_crossings=0, strict_recoveries=0,
        ) for i in range(count)],
    }


def consume_frame(state, record):
    require(record["step"] == state["steps"], "missing, repeated or unordered frame")
    state["steps"] += 1
    count = len(state["stats"])
    done = vector(record["done"], count, "done", dtype=torch.bool)
    physical = record["crossing"]
    result = physical["result"]
    recovery = vector(result["recovery_complete"], count, "recovery", dtype=torch.bool)
    crossing = vector(result["event_complete"], count, "crossing", dtype=torch.bool)
    # A zero receipt tensor is justified by saved actual events, not guessed.
    # Supporting a successful replay needs event identity captured before reset.
    require(not recovery.any(), "saved replay has recovery; zero-receipt proof does not apply")
    require(not crossing.any(), "saved replay has strict crossing; expected model600 counterexample")
    collision = vector(physical["collision"], count, "collision", dtype=torch.bool)
    prelift = vector(result["single_prelift_event"], count, "prelift", dtype=torch.bool)
    delta = vector(result["prelift_progress_delta"], count, "prelift progress")
    require(((delta >= 0) & (delta <= 1)).all(), "legacy saved progress must be in [0,1]")
    pre_root = torch.as_tensor(record["pre_root"], dtype=torch.float64)
    require(pre_root.shape == (count, 3), "pre_root must have shape [B,3]")
    require(torch.isfinite(pre_root).all(), "pre_root must be finite")
    world_pre_root = pre_root + state["origins"]
    old_blocked = reward_contract.required_crossing_zone(world_pre_root, state["course"])
    blocked = state["gate"].update(
        world_pre_root, state["course"], state["required"], state["recovered"])
    terms = torch.as_tensor(record["reward_terms"], dtype=torch.float64)
    require(terms.shape == (count, len(record["reward_names"])), "reward terms shape mismatch")
    require(torch.isfinite(terms).all(), "reward terms must be finite")
    old_actual = vector(record["reward"], count, "saved final PPO reward")
    base = terms.sum(-1)
    # The collector already integrated reward terms with step_dt. dt=1 avoids
    # a second integration; the saved event bonus remains a discrete amount.
    kwargs = dict(collision=collision, done=done, prelift=prelift,
                  recovery=recovery, prelift_progress_delta=delta)
    old_rebuilt, _, _ = reward_contract.required_crossing_reward(
        base, terms, 1., blocked=old_blocked, **kwargs)
    candidate, removed, bonus = reward_contract.required_crossing_reward(
        base, terms, 1., blocked=blocked, **kwargs)
    active = ~done
    error = (old_rebuilt - old_actual).abs()
    if active.any():
        state["max_old_reconstruction_error"] = max(
            state["max_old_reconstruction_error"], float(error[active].max()))
    require((error[active] <= 2.e-6).all(), "saved final reward does not match the legacy contract")
    negative = terms.clamp_max(0).sum(-1)
    expected_without_bonus = torch.where(blocked | collision, negative, base)
    require(torch.allclose(candidate - bonus, expected_without_bonus, atol=1.e-10, rtol=1.e-10),
            "candidate changed negative costs or unblocked reward")
    post = active & (world_pre_root[:, 0] > state["end"])
    require(blocked[post].all(), "persistent gate released an incomplete post-slab row")
    require((bonus[post] == 0).all(), "post-slab physical bonus exists; zero-bonus proof does not apply")
    require((candidate[post] <= 1.e-10).all(), "candidate still grants positive post-slab reward")
    require(torch.allclose(candidate[post], negative[post], atol=1.e-10, rtol=1.e-10),
            "post-slab negative costs were changed")
    for env, stats in enumerate(state["stats"]):
        if done[env]:
            stats["terminal_frames"] += 1
            continue
        stats["nonterminal_frames"] += 1
        stats["blocked_frames"] += int(blocked[env])
        stats["strict_crossings"] += int(crossing[env])
        stats["strict_recoveries"] += int(recovery[env])
        stats["all_old_reward_sum"] += float(old_actual[env])
        stats["all_candidate_reward_sum"] += float(candidate[env])
        stats["all_negative_cost_sum"] += float(negative[env])
        if post[env]:
            stats["post_slab_frames"] += 1
            stats["post_slab_old_positive_frames"] += int(old_actual[env] > 1.e-10)
            stats["post_slab_candidate_positive_frames"] += int(candidate[env] > 1.e-10)
            stats["post_slab_old_reward_sum"] += float(old_actual[env])
            stats["post_slab_candidate_reward_sum"] += float(candidate[env])
            stats["post_slab_removed_positive_sum"] += float(removed[env])
            stats["post_slab_negative_cost_sum"] += float(negative[env])
    # Terminal pose/origin ambiguity is excluded from aggregates. Match the
    # wrapper lifecycle by clearing that row's obligation after its frame.
    state["gate"].reset(done)


@torch.inference_mode()
def verify(path, expected_steps):
    metadata = None
    modes = {}
    records = 0
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            records += 1
            try:
                record = json.loads(line)
                kind = record["kind"]
                if kind == "metadata":
                    require(metadata is None and not modes, "duplicate or late metadata")
                    require(record["iter"] == 600 and record["stage"] == 1,
                            "verifier is scoped to the model600 stage1 counterexample")
                    require(record["body_names"] == SUPPORT_ORDER, "M1 support order mismatch")
                    metadata = record
                elif kind == "course":
                    require(metadata is not None, "course before metadata")
                    mode = record["mode"]
                    require(mode in ("mean", "sampled") and mode not in modes,
                            "unexpected or duplicate mode course")
                    modes[mode] = new_mode(record)
                elif kind == "frame":
                    consume_frame(modes[record["mode"]], record)
                else:
                    raise ValueError(f"unexpected record kind {kind!r}")
            except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    require(set(modes) == {"mean", "sampled"}, "both replay modes are required")
    for mode, state in modes.items():
        require(state["steps"] == expected_steps, f"{mode}: incomplete saved trajectory")
        for stats in state["stats"]:
            require(stats["post_slab_old_positive_frames"] > 0,
                    f"{mode}/env{stats['env']}: original positive-reward counterexample absent")
    return dict(
        verification="M1_REQUIRED_REWARD_REPLAY_VERIFIED", input=str(path.resolve()),
        helper_file=str(Path(reward_contract.__file__).resolve()), records=records,
        checkpoint=metadata["checkpoint"], checkpoint_iteration=metadata["iter"],
        stage=metadata["stage"], saved_step_dt=metadata["dt"],
        scope="CPU reward counterfactual on saved actual trajectories; unchanged saved events and deltas; no simulator or learning",
        negative_costs_preserved=True, zero_saved_strict_recoveries=True,
        modes={mode: dict(steps=state["steps"],
                         max_old_reconstruction_error=state["max_old_reconstruction_error"],
                         environments=state["stats"]) for mode, state in modes.items()},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--expected-steps", type=int, default=1000)
    args = parser.parse_args()
    require(args.expected_steps > 0, "expected steps must be positive")
    torch.set_num_threads(1)
    print(json.dumps(verify(args.input, args.expected_steps), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
