"""CPU-only, explicit 16->12 initialization; never overwrite the source."""
import argparse
import hashlib
from pathlib import Path
import torch
from ame_baseline.actor_critic_ame import ActorCriticAME
from ame_baseline.ame_runner import _atomic_torch_save
from ame_baseline.m1_fixed_wheel_checkpoint import convert_fixed_wheel_checkpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--speed', type=float, default=.30)
    args = parser.parse_args()
    if args.destination.exists() or args.destination.resolve() == args.source.resolve():
        raise ValueError('Destination must be new and distinct from source')
    digest = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if digest != args.source_sha256:
        raise ValueError('Source SHA256 mismatch')
    source = torch.load(args.source, map_location='cpu')
    old = ActorCriticAME(1589,1592,16)
    new = ActorCriticAME(1589,1592,12)
    result = convert_fixed_wheel_checkpoint(source,old,new,args.speed,digest)
    old.load_state_dict(source['model_state_dict']); new.load_state_dict(result['model_state_dict'])
    old.eval(); new.eval()
    with torch.no_grad():
        obs = torch.randn(8,1589)
        torch.testing.assert_close(new.act_inference(obs),old.act_inference(obs)[:,result['m1_action_conversion']['leg_rows']])
    _atomic_torch_save(result,args.destination)
    loaded = torch.load(args.destination,map_location='cpu')
    assert loaded['m1_action_contract'] == result['m1_action_contract']
    print(dict(destination=str(args.destination),sha256=hashlib.sha256(args.destination.read_bytes()).hexdigest(),
               iter=result['iter'],next_iter=result.get('next_iter',result['iter']+1),
               num_actions=result['ame_num_actions'],stage=result['m1_learning_curriculum']['stage'],
               optimizer_states=len(result['optimizer_state_dict']['state']),contract=result['m1_action_contract']))


if __name__ == '__main__':
    main()
