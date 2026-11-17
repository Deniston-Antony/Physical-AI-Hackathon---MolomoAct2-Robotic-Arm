#!/usr/bin/env bash
# Set up the training VM: MolmoBot at the pinned commit, its locked training venv, and the base checkpoint.
# Run on the VM as user ubuntu. Writes ~/setup.log lines "SETUP <step> ok".
set -euo pipefail
export PATH=$HOME/.local/bin:$PATH
log() { echo "$(date '+%F %T') SETUP $*" | tee -a ~/setup.log; }
sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null 2>&1
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tmux ffmpeg >/dev/null 2>&1
log "apt ok"
if [ ! -d ~/MolmoBot ]; then
  git clone -q https://github.com/allenai/MolmoBot.git ~/MolmoBot
fi
cd ~/MolmoBot && git checkout -q 33c0ca7 && cd ~/MolmoBot/MolmoBot
log "repo ok $(git log --oneline -1)"
# The upstream uv.lock is older than its pyproject.toml, so --locked refuses it. --frozen installs the locked versions.
uv sync -q --frozen --extra train
.venv/bin/python -c "import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.cuda.get_device_name())"
log "venv ok"
if [ ! -f ~/base/model.pt ]; then
  .venv/bin/hf download allenai/MolmoBot-Img-DROID --local-dir ~/base >/dev/null
fi
ls -la ~/base | tee -a ~/setup.log
log "base ok"
