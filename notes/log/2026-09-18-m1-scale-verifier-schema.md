# Scale verifier schema audit (read-only)

Task3 implementation support. Read-only agent inspected actual accepted run14 JSON/NPZ headers and current scale adapter; no CUDA, edits or signals. This is schema evidence, not scale acceptance.

- `report.completed` checks native/cleanup/budget, not all source/scanner/measurement gates. Wrapper3 may be common failure or behavior failure; do not allow it without all common guards.
- Startup32 successful report is `startup_passed=true`, `passed=false`, `metrics.passed=false`, wrapper0. Verdict must explicitly add `validation_kind=startup` and `strict_behavior_passed=false`.
- Before finalization, candidate_report metrics `completed/passed/process_finalized` are false. Final report metrics completed/process_finalized become true. `candidate_process_finalized` remains false in both. Do not require pre-finalized values to be true.
- `configuration.after.scene.num_envs` is N, but pre-construction `after.scene.terrain.num_envs` remains1. Require actual layout counts all1024, not rewrite config.
- FirstEpisodeMetrics `reset_count` is first-episode ended count0/1, not all reset count. Baseline full `received_steps` may be1600 while active_sample_count is smaller after a termination. Samples terminated/timeout establish required-prefix continuity; sync additionally records episode_id/length.

## Required common evidence fields

`run_start`: num_envs/requested_steps/pid integers; nonempty run_id/reference/device/interpreter strings. `POST_CLEANUP`: same run_id/pid, steps S, candidate_sha256 bound to raw candidate_report bytes. `report`: completed/passed/startup_passed bool, native_exit_code/wrapper_return_code int, empty finalization_errors/measurement_issues, source_bindings_valid true.

`report.metrics`: num_envs/requested_steps/received_steps/passed_envs integers; completed/passed/process_finalized bool; validation_kind startup/strict; per_env exact N ordered env_id. Per-env active_sample_count/reset_count integers, terminated/timeout/failure_latched/passed bool, first_failure_step int/null, flags name->bool, failed_gates list, strict_clearance FAR/RAR event int/null. First_failure_step null alone is not behavioral pass because some gates are aggregate.

Report prepare_and_ik_calls both S, ik_sample_count S, sample_chunks S/32, physical_sensor_updates4*S. Scanner valid true, seen_by_env bool[N], own/foreign/invalid_hit_counts int[N], foreign_bar_force_peak_by_env float[N], bbox_atol_m2e-5. Check full arrays, not just valid summary.

Bindings before/after name->{path,sha256} equal within run and across same-scale pair. Initial_randomization JSON: seed, arrays name->shape list, gate_source controller_oracle, randomization_events/commands, wheel_velocity_signs all1. NPZ allfloat32: root_state_w(N,13), joint_pos/joint_vel(N,16), masses(N,17), material_properties(N,17,3), env_origins(N,3). Actual pair dtype/bytes equal.

Live contract: wheel_scale1, offset/default_velocity0, dt.02, velocity_limit_sim20,damping30,stiffness0, action_columns[12,13,14,15], wheel names FAR/FBL/RAR/RBL_FOOT_JOINT, four unique named IDs0..15. Baseline/candidate both validated and identical.

## Scene/layout consistency

`report.scene` and candidate_report.scene contain entire scene_manifest JSON: N, env_origins(N,3), bar_world_bboxes(N,2,3), bar_paths[N], own_filter_indices[N], sensor_row_for_env[N], generic_sensor_row_for_env[N]. Geometry JSON repeats bbox, ground/exposed heights; dimensions(N,3) [.06,.16,.06], local_centers_xy(N,2) [.85,-.2], existing2e-5 threshold.

Same layout object appears scale_layout.json, scene_manifest.scale_layout, report.scene.scale_layout, report.gpu.scale_layout, runtime_metadata.scale_layout. Counts num_envs/terrain_cfg_num_envs/scene_num_envs/scene_cfg_num_envs1024; rows/cols/maxlevel32. levels=id%32, types=id//32, origins[r,c]=(8r-124,8c-124,0), exact gather in terrain_env_origins/scene_env_origins, scene and randomization origins. Actual importer `scale_layout.make_scale_terrain_type.<locals>.ScaleSemanticCourseTerrainImporter`, parent `extension.semantic_course.SemanticCourseTerrainImporter`, source paths/hashes recorded.

Clone declared_graph_valid is true; dynamic_collision_filtering_verified and bar_own_environment_isolation_verified remain false honestly. Do not require these unproven claims to become true.

## NPZ and prefix

Chunks32: step int64(chunk,), ordinary fields(chunk,N,...). Exceptions ik_joint_ids(chunk,4,3), full_jacobian_shape(chunk,4), elapsed_seconds(chunk,). Scale full_jacobian_shape values[1024,17,6,22]. Samples terminated/timeout/wave_gate/reference_collision bool; phase/substep_counts/scanner counts int64. scanner_invalid_counts is not sampled, only report summary.

Sync episode_id/length int64, zero episode IDs and0..S-1 length when unreset. Initial wrapper reset occurs before core creation. Prefix is first episode samples [0,activation), excludes only elapsed_seconds, all other dtype/bytes equal. End atactivation-1 fails; end atactivation or later does not invalidate earlier prefix, but preserve baseline negative report publicly.

Run14 observed native/wrapper0, completed/passedtrue, startupfalse, exact8×1600,50+50chunks,8/8,reset0,scanner foreign/invalid/foreignforce0, sync acceptedtrue.
