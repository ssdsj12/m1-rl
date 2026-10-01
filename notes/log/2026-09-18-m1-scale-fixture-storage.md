# Scale CPU fixture preservation / storage verification

Task: T306.6h.6a.1a, operational storage child; 2026-09-18 22:46 +08:00.

Root free space fell from about25GiB to11.675GiB while run18 remained alive. Its cause was not found in the already audited task paths. This operation only relocated our completed21:58:05–21:59:24 CPU test fixture; no user models, old real runs, SDK, live output, source or other jobs were changed.

## Exact scope and evidence

- Old entry: `/tmp/pytest-of-hexinkun/pytest-227`.
- Preserved full archive: `/data/hexinkun-m1-acceptance-20260918/cpu-fixtures/pytest-227`.
- Original tree:2816regularfiles,262subdirectories,22symlinks,UID/GID1005,root0700,device64769/inode876734666. All87tmp-path tests plus modulefixture matched our102-test command; no unknown top-level fixtures were found in the prior audit.
- `cp -a` completed0; `diff -qr --no-dereference` completed0 before and after the old-entry swap. Source/archive sorted file-path+SHA256 manifest both `3ea07c9f10806b8f5ef6bb90db5f0ff72eb7e7c9dfcae895b5a0027f392d9f12`.
- Independent final review: all relativepaths/type/mode/uid/gid/mtime_ns/regularsize/linktargets identical, common semantic metadata digest `2296ae9dd792175f90012ca4f567c26db2b492336356e029fbc33d8ead147593`. Only88directory st_size values differ betweenfilesystems; no regularfile or symlink size difference. Mainagent separately ran sorted metadata diff excluding directorysize:exit0.
- Source inode/owner/mtime/ctime stable. Readableproc FD/cwd/root/mmap scan found no references; inaccessible otherUID processes and two sameUIDsshd/one(sd-pam) remain a visibility limitation, not a claim of global zero references.

## Safe relocation and actual verification

Verified both resolved absolute paths, sourceinode/owner, archiveinode16652868504/device64768/owner, and nonexistent literal rollback target. Renamed source on its ownfilesystem to `/tmp/pytest-of-hexinkun/pytest-227.verified-source-copy-20260918`; created oldentry symlink to the archive. Actual22/22internal absolute symlinks resolved to existing archive targets, and full regular manifest via oldpath still matched. Rechecked contentdiff and exactinode/realpath guards, then removed **only** that verified redundant rollback directory with literal `rm -r --one-file-system -- ...`. No unique evidence was deleted; the whole tree can be copied back from archive if needed.

22:46:29 exact free space:root15,345,942,528bytes (about14.29GiB);data7,165,755,695,104bytes. Reclaimedabout2.6GiB. Unknown external root growth remains unresolved; recheck before nextlaunch. `/data` capacity is not proof of an unlimited quota.

Preserve the oldpath symlink:22archived links contain absolute targets underthatpath. Installedpytest retention explicitly skips symlink roots, but manual/tmp cleanup could still remove the entry; that would require restoring it, not regenerating evidence. No links/content were rewritten, so historical content hashes remain valid.

## Live task and next gate

During relocation run18PID132238 remained the same amp/GPU7 process,1408/1600 at22:46:04. No GPU launch/stop or code changes were part of this operation. Its actual1600/native/common completion must pass before candidate19; future new candidate output will use the private/data parent. No10000training or learned behavior claim.

Baseline/Candidate ref:formal646f486; scale frozen task3_accepted at repoHEAD5553e84. Storage-onlyoperation, no sourcecontract change. See [baseline18](2026-09-18-m1-scale-baseline18.md), [Task3](2026-09-18-m1-scale-verdict-implementation.md), [T306](../todo/T306-m1-ame-long-train-stability.md).
