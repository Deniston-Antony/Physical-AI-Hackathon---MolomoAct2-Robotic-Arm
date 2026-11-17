"""Save the action expert of a MolmoBot training checkpoint as a bfloat16 state dict.

The training freezes everything but the action expert, so this file is all that the fine-tune changed.

Usage (in the MolmoBot repo venv): python extract_action_expert.py <checkpoint dir, e.g. run/step4000> <out.pt>
"""

import sys

import torch
from olmo.train.checkpointer import load_model_state
from olmo.train.trainer_config import TrainConfig
from olmo.util import prepare_cli_environment, resource_path


def main() -> None:
    checkpoint_dir, out = sys.argv[1], sys.argv[2]
    prepare_cli_environment()
    config = TrainConfig.load(resource_path(checkpoint_dir, 'config.yaml'))
    with torch.device('meta'):
        model = config.model.build_model()
    model.to_empty(device=torch.device('cpu'))
    load_model_state(checkpoint_dir, model)
    state = {k: v.detach().to(torch.bfloat16).clone() for k, v in model.action_expert.state_dict().items()}
    torch.save(state, out)
    n = sum(v.numel() for v in state.values())
    print(f'saved {len(state)} tensors, {n / 1e6:.1f}M parameters, to {out}')


if __name__ == '__main__':
    main()
