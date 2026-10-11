"""One-variable diagnostic: first recovery placement at empty spawn instead.

Execute the unchanged candidate probe in memory; do not alter its criteria,
actuators, initial posture or the candidate/production sources. Expected to
stop at the first inconclusive placement. This is not a deployment test.
"""
from pathlib import Path
source = Path('Go2Pvcnn/scripts/probe_m1_lift_roll_layout.py').read_text()
original = "root_x=course['centers_top'][:,target,0]+.05+.119208+.04-selected_x+travel"
assert source.count(original) == 1
source = source.replace(original, "root_x=env.scene.env_origins[:,0].clone()")
print('M1_DIAGNOSTIC_BASELINE empty_spawn_same_pose_and_actuators', flush=True)
exec(compile(source, 'probe_m1_lift_roll_layout_spawn_control.py', 'exec'))
