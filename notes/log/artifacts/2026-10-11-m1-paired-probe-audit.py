"""CPU re-evaluation of raw native placement frames with the current checker.

Usage: PYTHONPATH=Go2Pvcnn python this.py RAW_LOG
Prints compact JSON; never starts simulation, loads a PT or changes criteria.
"""
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
import torch
from ame_baseline.m1_lift_roll_probe_checks import compare_placement

path=Path(sys.argv[1])
cases=defaultdict(list);final=None
for line in path.read_text().splitlines():
    if line.startswith('M1_PLACEMENT_FRAME '):
        f=json.loads(line.split(' ',1)[1])
        # Old raw files preceded normalized-angle reporting; recover exact
        # absolute angle from recorded quaternion vectors, without editing logs.
        actual=torch.tensor(f['root_quat'],dtype=torch.float64)
        requested=torch.tensor([r[3:7] for r in f['requested_root']],dtype=torch.float64)
        actual=actual/actual.norm(dim=-1,keepdim=True)
        requested=requested/requested.norm(dim=-1,keepdim=True)
        f['max_angle_error']=float((2*torch.acos((actual*requested).sum(-1).abs().clamp(0,1))).max())
        key=(f['kind'],f['row'],f['target'],f.get('selected_x'),f.get('travel'),f.get('fraction'))
        cases[key].append(f)
    elif line.startswith('M1_LIFT_ROLL_NATIVE_RESULT '):
        final=json.loads(line.split(' ',1)[1])
results=[]
for key,frames in cases.items():
    kind,row,target,sx,travel,fraction=key
    if kind=='recovery':refkey=('recovery_reference',row,0,None,None,None)
    elif kind=='fold':refkey=('fold_reference',row,target%2,None,None,None)
    else:refkey=key
    result=compare_placement(frames,cases[refkey])
    results.append(dict(kind=kind,row=row,target=target,selected_x=sx,travel=travel,fraction=fraction,
        min_clearance=min(f['min_clearance'] for f in frames),
        min_margin=min(f['min_support_margin'] for f in frames),
        max_nonwheel_force=max(f['max_nonwheel_force'] for f in frames),
        support_tail=[f['ground_support'] for f in frames[-5:]],**result))
groups=[]
for kind in ('recovery_reference','fold_reference','recovery','fold'):
    for row in (1,2,3):
        subset=[x for x in results if x['kind']==kind and x['row']==row]
        if not subset:continue
        groups.append(dict(kind=kind,row=row,count=len(subset),
            flags={k:sum(x[k] for x in subset) for k in ('verified','geometry_verified','support_verified','baseline_valid','calibrated_pose_verified')},
            min_clearance=min(x['min_clearance'] for x in subset),
            min_margin=min(x['min_margin'] for x in subset),
            max_paired_root_error=max(x.get('max_paired_root_error',math.inf) for x in subset),
            max_paired_joint_error=max(x.get('max_paired_joint_error',math.inf) for x in subset),
            max_nonwheel_force=max(x['max_nonwheel_force'] for x in subset)))
print(json.dumps(dict(raw_log=str(path),raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    checker_sha256=hashlib.sha256(Path(sys.modules[compare_placement.__module__].__file__).read_bytes()).hexdigest(),
    all_cases=len(cases),physics_ticks=sum(map(len,cases.values())),
    raw_complete=final is not None,raw_accepted=final and final['accepted'],
    raw_assessment=None if final is None else final.get('assessment'),groups=groups,
    raw_runtime_ready=None if final is None else sum(x['runtime_ready'] for x in final['recovery_results']),
    references=[x for x in results if x['kind'].endswith('_reference')]),indent=2))
