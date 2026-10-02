# M1 synchronization promotion: main-agent verification

Date2026-09-18. Parent[T306.6h.6a.1](../todo/T306-m1-ame-long-train-stability.md). Stage: formal reference integration, not new physical run. Baseline Refa86cbf5;Candidate Ref is the exact8files in [promotion verification](2026-09-18-m1-sync-promotion-verification.md).

## Independent checks

Main agent read the complete formal tracked diff:run.py5newlines,runtime.py13new/1replacement; reset/sample/flush wiring only. Core/bridge/verdict SHA256 equal frozen candidate. Independent SPEC reviewer separately cmp-checked all8promotionfiles and all8unchangedfiles againsta86cbf5, verifiedtestsourcepath andmetadata binding, bashsyntax,diffcheck andemptyindex:PASS.

Main-agent CPU recheck initially used the wrong working directory:

```bash
cd /home/hexinkun/m1_rl
# same isolated amp/USD-libs environment as documented, but wrong cwd
python -m pytest -q --tb=short -p no:cacheprovider tools/m1_reference_validation/tests
```

Actual result11failed,362passed in75.69s. All11failures areModuleNotFoundError for sibling `post_cross_sync`/`sync_bridge`; tests dynamically import a file and later use sibling bareimports. They currently require the documented adaptercwd. No test assertions or runtime behavior failed in this extra invocation. Do not report this command aspassing.

Following systematic diagnosis, changed onlycwd/relativetestpath to the documented command, no code changes:

```bash
cd /home/hexinkun/m1_rl/tools/m1_reference_validation
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310 \
LD_LIBRARY_PATH=/home/hexinkun/miniconda3/envs/amp/lib/python3.10/site-packages/isaacsim/extscache/omni.usd.libs-1.0.1+d02c707b.lx64.r.cp310/bin \
/home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q --tb=short -p no:cacheprovider tests
```

Fresh actual result: **373passed in74.37s,exit0**. This is separate from implementer's373passed75.02s. Absolute-path formal `run.py --help`, invoked fromrepositoryroot withampPython-B, also exits0 and imports correctly; noIsaac starts. Python script-directory behavior makes actuallauncher independent oftestcwd. Record test-invocation constraint asminor; do not mutate physically-frozenfiles during mechanicalpromotion just to improve test discovery. A future explicittest-harness cleanup can address root-levelcollection separately.

## Limits

Formal runtime's source identity is byte-equal to threepassingphysicalcandidate runs, but no newformal-pathphysicalrun wasperformed inthisverification. No1024capacity/strict,AME,largeavoidance or10000update claim. SDK/driver/reference/unrelatedcode unchanged. FinalqualityreviewPASS:zeroCritical/Important,one documentedtestcwdMinor;separateabsoluteCLIchecksfromreporootexit0. Main committedonly8approvedpaths as **646f486**;formaladapterstatusnowclean. Overallgoalremainsactive. Newscale-spec/plancommit5553e84changesonly2documents,notfeatureverifiedref.
