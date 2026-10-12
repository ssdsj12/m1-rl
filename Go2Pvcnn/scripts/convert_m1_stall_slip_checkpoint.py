"""Explicit CPU-only reward-contract migration; never overwrite a checkpoint."""
import argparse
import hashlib
from pathlib import Path
import torch
from ame_baseline.m1_stall_slip import convert_reward_checkpoint


def main():
    p=argparse.ArgumentParser()
    p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args()
    digest=hashlib.sha256(args.input.read_bytes()).hexdigest()
    source=torch.load(args.input,map_location='cpu',weights_only=False)
    converted=convert_reward_checkpoint(source,digest)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb') as f:
        torch.save(converted,f)
    assert hashlib.sha256(args.input.read_bytes()).hexdigest()==digest
    print(dict(input=str(args.input),source_sha256=digest,output=str(args.output),
               iter=converted['iter'],next_iter=converted['next_iter'],
               curriculum=converted['m1_learning_curriculum']))


if __name__=='__main__':main()
