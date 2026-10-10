"""CPU-only readback of the fresh run's initial checkpoint; no simulation."""
import sys
import torch

checkpoint = torch.load(sys.argv[1], map_location='cpu', weights_only=False)
assert checkpoint['iter'] == 0
assert checkpoint['next_iter'] == 1
assert checkpoint['m1_learning_curriculum']['stage'] == 0
weights = checkpoint['model_state_dict']
assert all(torch.isfinite(value).all() for value in weights.values() if torch.is_tensor(value))
print('FRESH_PT_OK iter=0 next_iter=1 stage=0 weights_finite=True')
