#!/usr/bin/env bash
# Fine-tune only the action expert of MolmoBot-Img-DROID on the open/close demos, then save it.
# Run on the training VM.
# Usage: bash train_run.sh <run name> <steps> <global batch> <device batch> <time limit s> [save interval, default 1000]
# Data: ~/data/<set>/train/house_*/ from prep_train_data.py. Stats: ~/base_norm_stats.yaml (the base model's own).
# The settings copy the base model's training command (in its config.yaml), with the LLM, ViT and connector frozen.
set -euo pipefail
run=$1 steps=$2 gbs=$3 dbs=$4 limit=$5 every=${6:-1000}
cd ~/MolmoBot/MolmoBot
export OLMO_SHARED_FS=1 OMP_NUM_THREADS=8 LOG_FILTER_TYPE=rank0_only OLMO_NUM_THREADS_ENV_VAR=8 WANDB_MODE=disabled
# The script fills its wandb settings from these variables, also when --wandb=null turns wandb off.
export WANDB_PROJECT=risers WANDB_ENTITY=risers
sets=()
for s in normal_open normal_close hard_open hard_close; do
  [ -f ~/data/$s/train/valid_trajectory_index.json ] && sets+=(~/data/$s)
done
rates=()
for _ in "${sets[@]}"; do rates+=("$(python3 -c "print(1/${#sets[@]})")"); done
echo "$(date '+%F %T') TRAIN start $run: steps $steps, batch $gbs ($dbs per pass), sets ${sets[*]}"
.venv/bin/torchrun --nnodes=1 --nproc-per-node=1 --master_port=29401 launch_scripts/train_molmobot.py ~/base \
  --stats_path=$HOME/base_norm_stats.yaml --action_preset franka_joint --camera_names risers_exo risers_wrist \
  --seq_len=512 --max_duration="$steps" --device_batch_size="$dbs" --global_batch_size="$gbs" --log_interval=20 \
  --save_folder=$HOME/runs/$run --save_interval="$every" --save_num_checkpoints_to_keep=2 --time_limit="$limit" \
  --data.packing=null --model.mm_preprocessor.image.crop_mode=resize --model.mm_preprocessor.max_frames=1 \
  --model.mm_preprocessor.use_frame_special_tokens=True --model.mm_preprocessor.max_subtitle_tokens=null \
  --model.same_noise_per_time=False --weighted_sampling --img_aug --ft_embedding=ae \
  --model.mm_preprocessor.image.max_images=2 --model.num_flow_timestamps=8 \
  --no_val --num_workers=12 --prefetch_factor=4 --exp_name="$run" --wandb=null \
  --data_paths "${sets[@]}" --dataset_sample_rates "${rates[@]}"
last=$(ls -d ~/runs/$run/step* | sort -V | tail -1)
echo "$(date '+%F %T') TRAIN done $run, last checkpoint $last"
.venv/bin/python ~/cloud_job/extract_action_expert.py "$last" ~/runs/$run/action_expert_open_close.pt
echo "$(date '+%F %T') EXTRACT done ~/runs/$run/action_expert_open_close.pt"
