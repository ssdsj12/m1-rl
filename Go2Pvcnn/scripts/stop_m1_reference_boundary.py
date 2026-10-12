"""One explicitly approved switch boundary, not a watcher or auto-restart tool."""
import hashlib
import json
import os
from pathlib import Path
import signal
import torch

production=Path('/root/quad/m1-rl/.worktrees/contact-recovery')
pid=2303
proc=Path('/proc')/str(pid)
assert proc.joinpath('cwd').resolve()==production
command=proc.joinpath('cmdline').read_bytes().split(b'\0')
assert b'Go2Pvcnn/scripts/train_m1_cross_large_complex_ame.py' in command
assert b'--resume' not in command
run=production/'logs/rsl_rl/m1_cross_large_complex_ame/2026-10-12_11-20-43/bb57e7d'
paths=sorted(run.glob('model_*.pt'),key=lambda p:int(p.stem.split('_')[-1]))
assert paths
path=paths[-1]
pt=torch.load(path,map_location='cpu',weights_only=False)
assert pt['next_iter']==pt['iter']+1 and pt['ame_num_actions']==12
assert pt['m1_training_contract']['version']==1
assert all(torch.isfinite(t).all() for t in pt['model_state_dict'].values() if torch.is_tensor(t))
assert torch.all(pt['model_state_dict']['std']>0)
states=pt['optimizer_state_dict']['state'];assert len(states)==33
assert all(torch.isfinite(t).all() for s in states.values() for t in s.values() if torch.is_tensor(t))
assert 'm1_learning_curriculum' in pt
result=dict(pid=pid,checkpoint=str(path),iteration=pt['iter'],next_iter=pt['next_iter'],
    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),old_pt_retained=True)
print(json.dumps(result),flush=True)
# Recheck identity immediately before the only process mutation.
assert proc.joinpath('cmdline').read_bytes().split(b'\0')==command
os.kill(pid,signal.SIGINT)
print('SIGINT_SENT_TO_VERIFIED_2303',flush=True)
