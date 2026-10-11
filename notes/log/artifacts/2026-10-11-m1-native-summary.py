"""Read saved diagnostic logs; no Isaac/PyTorch/CUDA initialization."""
import json, sys
from pathlib import Path
for filename in sys.argv[1:]:
    frames=[]; results=[]; errors=[]
    for line in Path(filename).read_text(errors='replace').splitlines():
        if line.startswith('M1_PLACEMENT_FRAME '): frames.append(json.loads(line.split(' ',1)[1]))
        elif line.startswith('M1_PLACEMENT_RESULT '): results.append(json.loads(line.split(' ',1)[1]))
        elif 'Error' in line or 'Traceback' in line: errors.append(line[:500])
    print(json.dumps(dict(log=filename,frames=len(frames),results=results,errors=errors[-8:],
        first_pose_failure=next((f['tick'] for f in frames if not f['pose_verified']),None),
        max_root_error=max((f['max_root_error'] for f in frames),default=None),
        max_joint_error=max((f['max_joint_error'] for f in frames),default=None),
        max_nonwheel_force=max((f['max_nonwheel_force'] for f in frames),default=None),
        min_support_margin=min((f['min_support_margin'] for f in frames),default=None)),indent=2))
