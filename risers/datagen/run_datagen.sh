#!/usr/bin/env bash
# Run a MolmoSpaces data-generation config from risers_datagen.py.
# Usage: bash run_datagen.sh RisersPickDroidTest
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
export MLSPACES_ASSETS_DIR="$HOME/molmospaces/assets"
export MLSPACES_CACHE_DIR="$HOME/molmospaces/cache"
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export PYTHONPATH="$here${PYTHONPATH:+:$PYTHONPATH}"
cd "$HOME/.cache/positronic/molmospaces/src"
exec "$HOME/.cache/positronic/molmospaces/src/.venv/bin/python" -m molmo_spaces.data_generation.main "risers_datagen:${1:?config name}"
