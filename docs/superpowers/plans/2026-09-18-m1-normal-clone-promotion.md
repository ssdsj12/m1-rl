# M1 normal-clone promotion and strict gate plan

> **For agentic workers:** Use the existing approved reference-validation design and completed normal-clone TDD/reviews. Promote the frozen candidate without changing controller behavior; independent audits run alongside the main verification.

**Goal:** Promote the tested shutdown workaround and establish whether the original teacher actually crosses before enlarging the run or building a learned-policy bridge.

**Architecture:** Copy only six frozen source/test files from the isolated normal-clone adapter to `tools/m1_reference_validation`. Keep reference source, SDK, runtime, thresholds and GPU7 reservation unchanged. Process completion and physical success remain separate gates.

**Tech Stack:** amp Python 3.10, IsaacLab45, PhysX, pytest, read-only USD collision evidence.

## Tasks

- [x] Confirm production adapter is clean, candidate hashes and GPU7 reservation are unchanged. Independently audit AME 10000-update path and behavior gap without starting another simulator.
- [x] Promote six frozen source/test files, committed a86cbf5. No candidate log files copied. Integration spec then quality review passed.
- [x] Check promoted SHA256 equality, `bash -n run.sh`, full212tests passed27.02s.
- [x] Single-process run12 GPU7 completed1600/native0,wrapper3/strict4/8. All8 crossed FAR/RAR; four reject wheel speed spread. No restart, GDB or signals.
- [ ] If and only if all 8 environments pass every frozen strict flag, repeat twice independently. First strict failure stops enlargement and triggers first-failure diagnosis; it must not trigger threshold changes or restarts.
- [ ] After three strict passes, recheck selected GPU resources before1024. User's latest decision: GPU7 only; may stop the verified reservation when needed and restore after no compute tasks. Not needed/done for run12.
- [x] Update T306 dashboard, branch and per-test log. Expansion blocked by T306.6h.6; no10000-completion or learned cross/avoidance claim.

## Verification command

```bash
cd /home/hexinkun/m1_rl/tools/m1_reference_validation
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 \
LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin \
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q -p no:cacheprovider tests
```

## Long-term user objective

The user reiterated single-process 10000 updates plus genuine crossing and large-obstacle avoidance. These remain distinct unfinished outcomes. Follow-up architecture must be based on teacher/AME audits and must distinguish teacher-assisted execution from policy-only capability. The current gate does not train PPO and does not test large obstacles.
