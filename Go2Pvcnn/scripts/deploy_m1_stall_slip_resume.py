"""One-time approved model200 reward migration deployment; preserves all PTs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import torch
from ame_baseline.m1_stall_slip import convert_reward_checkpoint,validate_native_evidence


def main():
    production=Path('/root/quad/m1-rl/.worktrees/contact-recovery').resolve()
    candidate=Path('/tmp/m1-learning-tests-only-20261012').resolve()
    evidence=Path('/tmp/m1-stall-slip-native-reviewed-20261012.log')
    records=[json.loads(s.split('STALL_SLIP_NATIVE_COMPLETE ',1)[1]) for s in evidence.read_text().splitlines()
             if s.startswith('STALL_SLIP_NATIVE_COMPLETE ')]
    assert len(records)==1 and 'REFERENCE_LEARNING_NATIVE_COMPLETE' in evidence.read_text()
    validate_native_evidence(records[0]['evidence'])
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
        try:argv=(proc/'cmdline').read_bytes().split(b'\0')
        except (OSError,PermissionError):continue
        if any(Path(a.decode(errors='replace')).name.startswith(('train_m1_','evaluate_m1_','probe_m1_'))
               and a.endswith(b'.py') for a in argv):
            raise RuntimeError('existing train/eval/probe '+proc.name)
    memory=int(subprocess.check_output(['nvidia-smi','--id=0','--query-gpu=memory.used','--format=csv,noheader,nounits']))
    assert memory<500,'GPU not released'
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    files=['Go2Pvcnn/ame_baseline/'+n+'.py' for n in (
        'ame_env_wrapper','ame_runner','m1_ame_contract','m1_ame_env_cfg','m1_ame_rewards','m1_stall_slip')]
    attestation=json.loads(Path('/tmp/m1-stall-slip-native-candidate.json').read_text())
    for rel in files:assert sha(candidate/rel)==attestation[rel],rel
    source=production/'logs/rsl_rl/m1_cross_large_complex_ame/2026-10-12_12-26-20/bb57e7d/model_200.pt'
    digest=sha(source)
    assert digest=='098616326b726de0494f2a6376766a67073a01b2d00751ce8ec98f027b12a67f'
    src=torch.load(source,map_location='cpu',weights_only=False)
    converted=convert_reward_checkpoint(src,digest)
    assert src['iter']==200 and src['m1_learning_curriculum']['streak']==1
    checkpoint=production/'logs/rsl_rl/m1_cross_large_complex_ame/stall-slip-initialization/model_200_stall_slip.pt'
    logpath=Path('/tmp/m1-ppo-stall-slip-model200-20261012.log')
    assert not logpath.exists() and not checkpoint.exists(),'already deployed; never duplicate'
    backup=Path('/tmp')/('m1-stall-slip-production-before-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()))
    backup.mkdir();manifest=[]
    for rel in files:
        dst=production/rel;saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True)
        before=sha(dst) if dst.exists() else None
        if dst.exists():shutil.copy2(dst,saved)
        manifest.append(dict(path=rel,before=before,after=sha(candidate/rel)))
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
    checkpoint.parent.mkdir(parents=True,exist_ok=True)
    with checkpoint.open('xb') as f:torch.save(converted,f)
    check=torch.load(checkpoint,map_location='cpu',weights_only=False)
    for k,v in src['model_state_dict'].items():assert torch.equal(check['model_state_dict'][k],v)
    for k,values in src['optimizer_state_dict']['state'].items():
        for name,v in values.items():assert torch.equal(check['optimizer_state_dict']['state'][k][name],v)
    assert check['optimizer_state_dict']['param_groups']==src['optimizer_state_dict']['param_groups']
    assert check['m1_learning_curriculum']==src['m1_learning_curriculum'] and sha(source)==digest
    for item in manifest:
        shutil.copy2(candidate/item['path'],production/item['path'])
        assert sha(production/item['path'])==item['after']
    env=dict(os.environ)
    for key in list(env):
        if key.startswith('M1_') or key in ('CHECKPOINT','MAX_ITERATIONS','NUM_ENVS','DEVICE','COURSE_PROFILE',
                                             'CUDA_LAUNCH_BLOCKING','CUDA_VISIBLE_DEVICES','PYTHONPATH'):
            env.pop(key)
    env.update(NUM_ENVS='2048',MAX_ITERATIONS='9799',DEVICE='cuda:0',COURSE_PROFILE='flat-first',
        M1_FIXED_WHEEL_SPEED_M_S='.30',M1_LOAD_OPTIMIZER='1',CHECKPOINT=str(checkpoint),
        PYTHON_BIN='/opt/conda/envs/env_issacsim/bin/python')
    with logpath.open('xb') as log:
        p=subprocess.Popen(['bash','Go2Pvcnn/scripts/run_m1_pure_ppo.sh'],cwd=production,env=env,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    receipt=dict(pid=p.pid,backup=str(backup),log=str(logpath),checkpoint=str(checkpoint),
        source_sha256=digest,checkpoint_sha256=sha(checkpoint),next_iter=201,iterations=9799,
        native_log_sha256=sha(evidence),manifest=manifest)
    Path('/tmp/m1-stall-slip-resume-deploy.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
