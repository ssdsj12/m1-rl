# T306/pure-ppo-learning/flat-first

## Approved design

User confirmed: openTensorBoard and start over on obstacle-free flat ground;
learn forward locomotion before obstacle terrain. Still2048purePPO, no forced
lift/reference/teacher/WBC. Previous fresh run6169 stopped; priorPTs retained.
Current Work Ref:codex/m1-contact-recovery, baselinebb57e7d plus uncommitted diff.

Stages:0emptyflat,1two3cm alternating wheel obstacles,2four6cm,
3eight10cm,4existing mixed terrain rows4--9. Startflatspawn2m behindtilecenter
so20s*.45m/s remains within16mflat tile. Colliders are prebuilt elsewhere;
only episode-reset origins change, never current colliders under the robot.
Initialposture585mmgeometry remainsapproved, originalrewardnumbers unchanged.

## Evidence and gates

Each completed window>=2048episodes; early failures count in denominator.
Three consecutivewindows require>=90% full-duration nonterminated finite
episodes with positive worldX progress >=70%integrated commanddistance,
and time-averaged actual bodyX speed error<.08m/s. Initial/fake resets excluded.
Stages1--3 additionally require strictattempts>0 and stable recovery/attempts>=.5.
These gates are training progression, not final crossing capability acceptance.
Stage-stamped episodes prevent priorstage successes contaminating newstage.
Per-env strict cumulativecounters ignore post-resetterminalposeevents.
Gate checkpointstate includesstage/window/streak, discards inflightepisodes;
flat-firstresume rejects checkpoints withoutcurriculummetadata.

Files:ame_baseline/m1_learning_curriculum.py,m1_mixed_course.py,ame_env_wrapper.py,
ame_runner.py; extension/semantic_course.py; train_m1_cross_large_complex_ame.py;
run_m1_pure_ppo.sh; probe_m1_flat_first.py and dedicatedtests.
Terrain3RED->30GREEN(withexistingmixedtests); strictcounterREDthenGREEN;
checkpointmetadataREDthenGREEN; combined newgate/terrain/checkpoint18passed.
Nativefirstprobe exposed frozenlayoutcfg mutation; replaced bydataclasses.replace.
Finalnativeprobe /tmp/m1-flat-first-probe-v2.log passed:initial0objects,
actualsmallcolliderheights.0299999993/.0600000033/.1000000015; fourenvresetcounts
2/4/8 atstages1/2/3; finalmixed8/8/8/90; returningstage0 gives0/0/0/0.
10neutralstepsfinite, rewardhooksteps10; policy4x1589. Forcedstageassignment
wasdiagnosticonly,notlearnedpromotion. Probeexited beforelongrun.
Spec reviewpassed; qualityreviewfoundstage1--3tileexitexposure at9mvs8mhalfsize.
Fixedallflatstages0--3startX-2m, notonlystage0. Addedroot/wheel-envelopeboundary
timeoutusingactualtilecenter, notshiftedspawnorigin. Shortboundaryepisodescannot
qualifyasfullsuccess. Re-reviewapproved, noimportantissue. Strongerrecoverygate
andboundaryhaveRED->GREENregressions. Newtests19passed; finalnativeprobe
/tmp/m1-flat-first-probe-final.log passedwithboundaryactive. Full118passed4.05s.

## Next

FreshPID7747 verified --num_envs2048 --max_iterations10000 --course-profileflat-first,
noresume/checkpoint. Log:/tmp/m1-ppo-flat-first-20261010.log. Runtimeassertion:
flat_first_verified envs=2048 stage=0 active_obstacles=0. Iteration0 loss.1130,
surrogate-.0025 finite; model_0.pt existsinrun2026-10-10_14-16-08/bb57e7d.
TensorBoardpointsnewrun,localhost16006APIworks. m1-ppoheartbeatupdatedtoflat-first
course,includingstage0liftreward0expected andcurriculumcheckpointmetadata.
No learnedwalking orcrossing claim without real evidence.

Finalhandoff:iteration5/10000observed. model_0.pt independentlyloaded:allpolicy
weightsfinite,iter0/next_iter1,curriculumversion1/stage0metadata present.
TensorBoardAPI exposesCurriculum/terrain_levels/{stage,sample_count,pass_rate,
velocity_error,qualifying_streak,strict_attempts,strict_successes,strict_success_rate}.
All implementation-plan tasks completed; worktree preserved, no merge/push requested.
