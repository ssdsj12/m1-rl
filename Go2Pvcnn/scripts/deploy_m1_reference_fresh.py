"""One-time approved reference-contract deployment; never resumes or deletes PTs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

production=Path('/root/quad/m1-rl/.worktrees/contact-recovery').resolve()
candidate=Path('/tmp/m1-learning-tests-only-20261012').resolve()
evidence=Path('/tmp/m1-reference-native-fixed.log')
assert 'REFERENCE_LEARNING_NATIVE_COMPLETE' in evidence.read_text(), 'native gate incomplete'
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
    try:argv=(proc/'cmdline').read_bytes().split(b'\0')
    except (OSError,PermissionError):continue
    if any(Path(a.decode(errors='replace')).name.startswith(('train_m1_','evaluate_m1_','probe_m1_'))
           and a.endswith(b'.py') for a in argv):
        raise RuntimeError('existing train/eval/probe '+proc.name)

names=['ame_env_wrapper','m1_ame_assets','m1_ame_contract','m1_ame_env_cfg',
       'm1_dynamic_crossing','m1_strict_crossing','m1_required_crossing','m1_obstacle_rewards',
       'm1_reference_robot','m1_reference_geometry','m1_learning_observations','m1_learning_progress']
files=['Go2Pvcnn/ame_baseline/'+name+'.py' for name in names]+[
    'Go2Pvcnn/extension/parallelism/m1_kinematics.py',
    'Go2Pvcnn/tracking/mdp/policy_geometry_rewards.py']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
logpath=Path('/tmp/m1-ppo-reference-fresh-20261012.log')
assert not logpath.exists(), 'fresh run already launched; never duplicate'
assert production.is_dir() and candidate.is_dir()
backup=Path('/tmp')/('m1-reference-production-before-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()))
backup.mkdir()
manifest=[]
for rel in files:
    src=candidate/rel;dst=production/rel
    assert src.is_file()
    saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True)
    before=sha(dst) if dst.exists() else None
    if dst.exists():shutil.copy2(dst,saved)
    manifest.append(dict(path=rel,before=before,after=sha(src)))
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
for item in manifest:
    shutil.copy2(candidate/item['path'],production/item['path'])
    assert sha(production/item['path'])==item['after']
env=dict(os.environ)
for key in list(env):
    if key.startswith('M1_') or key in ('CHECKPOINT','MAX_ITERATIONS','NUM_ENVS','DEVICE','COURSE_PROFILE','CUDA_LAUNCH_BLOCKING'):
        env.pop(key)
env.update(NUM_ENVS='2048',MAX_ITERATIONS='10000',DEVICE='cuda:0',COURSE_PROFILE='flat-first',
    M1_FIXED_WHEEL_SPEED_M_S='.30',PYTHON_BIN='/opt/conda/envs/env_issacsim/bin/python')
with logpath.open('xb') as log:
    p=subprocess.Popen(['bash','Go2Pvcnn/scripts/run_m1_pure_ppo.sh'],cwd=production,env=env,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,backup=str(backup),log=str(logpath),fresh=True,checkpoint=None,
             native_log_sha=sha(evidence),manifest=manifest)
Path('/tmp/m1-reference-fresh-deploy.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2),flush=True)
