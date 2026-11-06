# Physical-AI-Hackathon---MolomoAct2-Robotic-Arm
This Repository is related to the Physical AI Hackathon which I Participated in Oct-2026.

Team: **The Risers**. Competition: PHAIL stage 1 (Positronic platform, board `molmo.competition_v2`). A Franka robot
arm in the MolmoSpaces simulator does 320 episodes: pick, pick and place, place next to, open and close.

## Current status (6 November 2026, 10:00 CET)

| | |
|---|---|
| Best board score | **47.2% (151/320)**, rank 13 of 33 |
| Best model | MolmoBot-Img-DROID (Ai2), half-overlap timing, left shoulder camera |
| Best image | `docker.io/denistonantony/molmobot-img-droid:v1` |
| Work in progress | Overnight tests on hard episodes (see below). The best new setting is **not submitted yet**. |

## Board submissions

| Date | Model and setting | Score |
|---|---|---|
| 31 Oct | MolmoAct2-DROID (best of 6 runs) | 28.1% |
| 1 Nov | GR00T N1.5, our fine-tune (step 10000) | 20.6% |
| 5 Nov | MolmoBot-DROID, normal timing | 36.6% |
| 5 Nov | MolmoBot-DROID, half-overlap timing | 40.6% |
| 5 Nov | **MolmoBot-Img-DROID, half-overlap timing, left camera** | **47.2%** |

The full report of 5 November: [reports/2026-11-05-molmobot-report.md](reports/2026-11-05-molmobot-report.md).

## Where we lose points

The public board replays give the result of each episode for each team. The two hard sets hold the largest gap:

| Set | Episodes | Time limit | The Risers | Top 6 teams |
|---|---|---|---|---|
| Hard pick | 57 | 21 s | 14 (25%) | 25–40 (44–70%) |
| Hard pick and place | 58 | 41 s | 19 (33%) | 32–39 (55–67%) |
| Pick, normal rooms | 59 | 31 s | 56 (95%) | 51–56 (86–95%) |

On the episodes that both we and a top-6 team solved, our robot took 1.6 to 1.9 times as long. This is true for every
set. The hard sets have short time limits, so our slow robot often runs out of time. The robot waits for the model
for about 63% of each episode.

## Overnight tests, 5–6 November (local PC, RTX 4070)

### Plan

| Step | Content | Status |
|---|---|---|
| 1 | Speed: play more actions per model call, and use fewer flow-matching steps | **Done** |
| 2 | Gripper rule: a closed gripper opens only when the model value is below 40 (of 255) | Running |
| 3 | Look at the replay videos of top teams on hard episodes that we fail | Next |

### Test set

`risers/eval_local/hard28.json`: 28 board episodes from the two hard sets.

| Group | Hard pick | Hard pick and place |
|---|---|---|
| Our board run failed, and 6 or more of the 11 best teams solved | 12 | 9 |
| Our board run solved | 4 | 3 |

### Model time per call (model alone on the GPU)

| Flow-matching steps | Time per call |
|---|---|
| 10 (default) | 439 ms |
| 5 | 282 ms |
| 3 | 218 ms |

Each flow-matching step takes about 32 ms. The rest of the call takes about 120 ms.

### Step 1 results

All runs use MolmoBot-Img-DROID, half-overlap timing and the left camera.

| Run | Actions played per call | Flow steps | Solved | Hard pick | Hard pick and place | Robot waits | Time per call (with the simulator) |
|---|---|---|---|---|---|---|---|
| base (the 47.2% image) | 8 | 10 | 3/28 | 1/16 | 2/12 | 65% | 1062 ms |
| play12 | 12 | 10 | 6/28 | 3/16 | 3/12 | 56% | 1165 ms |
| flow5 | 8 | 5 | 7/28 | 2/16 | 5/12 | 56% | 790 ms |
| **play12_flow5** | **12** | **5** | **16/28** | **9/16** | **7/12** | **47%** | 790 ms |

By group:

| Run | Episodes that top teams solve and we failed (21) | Episodes we solved on the board (7) |
|---|---|---|
| base | 2 | 1 |
| play12 | 3 | 3 |
| flow5 | 5 | 2 |
| **play12_flow5** | **12** | **4** |

### Findings

- Speed is the main problem on the hard sets. The two speed changes together solved 16 of 28, against 3 of 28 for
  the settings of our best image.
- Each change alone helps a little (+3 and +4). Together they help much more (+13).
- Fewer flow steps cut the time per call by about 25% when the simulator runs on the same GPU.
- Playing 12 actions per call means fewer stops to wait for the model.

### Limits

- The local PC is slower than the competition machine. The model call takes about 1 s here, and about 0.5 s on the
  competition machine (estimate). So the gain on the board can be smaller.
- 28 episodes is a small test. Most of them are episodes that our board run failed.
- Fewer flow steps can make the actions less exact. The test shows no loss, but only on 28 episodes.

### Next

1. Step 2 (gripper rule) finishes at about 12:30. Its result goes into
   [reports/2026-11-06-overnight-results.md](reports/2026-11-06-overnight-results.md).
2. Step 3: compare our robot with the robots of the top teams on the same hard episodes.
3. Then build an image with the best setting and submit it.

## Repository layout

| Path | Content |
|---|---|
| `positronic_changes/` | The MolmoBot server, the image recipe and the MolmoAct2 GPU fix. `patches/` holds them as `git am` patches for Positronic commit `e6c45ba`. |
| `risers/eval_local/` | Local test tools, episode sets (`hard28.json`, `make_hard_set.py`) |
| `risers/overnight/` | Overnight test runner, results summary, progress timer, top-team video tool |
| `risers/molmobot_image/` | Image build script |
| `risers/competition_runs/` | Submit scripts and board results |
| `risers/datagen/`, `risers/nebius_train/` | Data generation and GR00T training scripts |
| `reports/` | Test reports |

To use the code: clone Positronic, check out commit `e6c45ba`, apply the patches with
`git am positronic_changes/patches/*.patch`, and put the `risers/` folders beside the `positronic` folder.

To run a speed setting on a local PC, start in the folder that holds `positronic/` and `eval_local/`:

```bash
SERVER_COMMAND=droid_half_overlap CHECKPOINT_DIR=~/molmobot_src/MolmoBot-Img-DROID \
SERVER_ARGS="--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=5" \
  bash eval_local/run_local_eval_molmobot.sh my_run eval_local/hard28.json
```
