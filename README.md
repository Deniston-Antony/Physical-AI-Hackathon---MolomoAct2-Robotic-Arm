# Physical-AI-Hackathon---MolomoAct2-Robotic-Arm
This Repository is related to the Physical AI Hackathon which I Participated in Oct-2026.

Team: **The Risers**. Competition: PHAIL stage 1 (Positronic platform, board `molmo.competition_v2`). A Franka robot
arm in the MolmoSpaces simulator does 320 episodes: pick, pick and place, place next to, open and close.

## Current status (6 November 2026, 20:10 CET)

| | |
|---|---|
| Best board score | **60.0% (192/320)**, rank 12 of 33 (rank 11 has the same score). 1st place: 67.8% |
| Best model | MolmoBot-Img-DROID (Ai2), half-overlap timing, left shoulder camera, 12 actions per call, 5 flow steps |
| Best image | `docker.io/denistonantony/molmobot-img-droid:v2` |

## Board submissions

| Date | Model and setting | Score |
|---|---|---|
| 31 Oct | MolmoAct2-DROID (best of 6 runs) | 28.1% |
| 1 Nov | GR00T N1.5, our fine-tune (step 10000) | 20.6% |
| 5 Nov | MolmoBot-DROID, normal timing | 36.6% |
| 5 Nov | MolmoBot-DROID, half-overlap timing | 40.6% |
| 5 Nov | MolmoBot-Img-DROID, half-overlap timing, left camera | 47.2% |
| 6 Nov | **MolmoBot-Img-DROID, half-overlap timing, left camera, 12 actions per call, 5 flow steps** | **60.0%** |

The full report of 5 November: [reports/2026-11-05-molmobot-report.md](reports/2026-11-05-molmobot-report.md).

## Where we lost points (47.2% image)

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
| 1 | Speed: play more actions per model call, and use fewer flow-matching steps | **Done**: 16/28 against 3/28 |
| 2 | Gripper rule: a closed gripper opens only when the model value is below 40 (of 255) | **Done**: no change |
| 3 | Look at the replay videos of top teams on hard episodes that we fail | **Done**: our robot is slower |

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

### Step 2 results: gripper rule

| Run | Solved | Hard pick | Hard pick and place | Failures where the gripper closed, then opened again |
|---|---|---|---|---|
| play12_flow5 | 16/28 | 9/16 | 7/12 | 11 |
| grip40 (play12_flow5 and the rule) | 16/28 | 9/16 | 7/12 | 11 |

- The rule changes nothing. When the robot opens the gripper, the model value is clearly low. The model decides to
  open, so a second threshold does not stop it.
- The two runs solved 12 of the same episodes and 4 different episodes each. So a difference of up to about 4
  episodes on this set can be chance. The step 1 gain (16 against 3) is much larger. The gains of `play12` and
  `flow5` alone are not.

### Step 3 results: top-team replay videos

We compared our board run with the runs of 3 top teams on 8 hard-pick episodes that they solve and we fail.

- In most episodes our robot moves along about the same path as the top teams' robots. It arrives late and runs out
  of time. The top teams finish in 6 to 19 s. The limit is 21 s.
- In some episodes our robot goes to the wrong place first, then turns back.
- We saw no grasp method of the top teams that differs from ours.

Full results: [reports/2026-11-06-overnight-results.md](reports/2026-11-06-overnight-results.md).

### Image v2 (6 November)

Image `docker.io/denistonantony/molmobot-img-droid@sha256:d0bdd083425e397046c6e4536000b4aa3b10a4445a0faf46ec6c6f85a7fb1e23`
(tag `v2`, public). It is the 47.2% image with one more layer (`risers/molmobot_image/Dockerfile.settings`). The
layer holds the current MolmoBot server code and these server flags:

```
--model.camera=left --pipeline.horizon_sec=0.7667 --model.num_flow_steps=5
```

The layer is small, so the build took 1 s and the push took 5 s. A full build needs about 30 GB more disk.

| Check | Result |
|---|---|
| Platform start test (`docker/test_policy_image.sh --gpu`, no network) | Pass: the server answered after about 95 s |
| 4 hard episodes that `play12_flow5` solved and `base` failed | 3/4 solved. The robot waits 41% (`play12_flow5`: 39%, `base`: 59%) |

The failed episode (goggles, pick and place) took 37.7 s of 40 s in the overnight run. So it is near the time limit.

The new code logs the model time once per 100 calls: "MolmoBot inference over 100 calls". The board log then
shows the model time on the competition machine.

### Board result of image v2

Submission `58f19b77fa0acea3`: **192/320 = 60.0%**, against 151/320 = 47.2% for image v1 (`30b01a00181a225`).

| Set | Episodes | v2 | v1 | Change | v2 median s | v1 median s |
|---|---|---|---|---|---|---|
| Pick, normal rooms | 59 | 56 | 56 | +0 | 5.0 | 7.5 |
| **Pick, hard** | 57 | **29** | 14 | **+15** | 9.2 | 16.0 |
| Pick and place, normal rooms | 54 | 39 | 37 | +2 | 12.9 | 21.3 |
| **Pick and place, hard** | 58 | **34** | 19 | **+15** | 19.2 | 33.3 |
| Pick and place, color | 16 | 11 | 9 | +2 | 22.6 | 25.5 |
| Place next to | 16 | 4 | 0 | +4 | - | - |
| Open, data generation | 15 | 1 | 3 | -2 | 19.5 | 21.3 |
| Open, hard | 15 | 1 | 1 | +0 | - | - |
| Close, data generation | 15 | 11 | 9 | +2 | 2.3 | 3.8 |
| Close, hard | 15 | 6 | 3 | +3 | 3.7 | 11.6 |

The median columns use the episodes that both images solved in that set.
`risers/competition_runs/board_by_set.py` makes this table.

- The two hard sets give 30 of the 41 more successes. The top 6 teams solve 25 to 40 hard pick episodes and 32 to
  39 hard pick and place episodes. Image v2 solves 29 and 34, so it is now in their range.
- On the 130 episodes that both images solved, the median time fell from 16.0 s to 9.9 s.
- v2 solved 62 episodes that v1 did not solve. v1 solved 21 episodes that v2 did not solve.
- The board log (`risers/competition_runs/molmobot_img_v2/policy_log.txt`) gives the model time on the competition
  machine: p50 245 ms per call (67 logs of 100 calls, 242 to 266 ms). On the local PC it is about 800 ms, because the simulator uses the same GPU.
- Open is the weakest task: 2 of 30. Place next to is 4 of 16.

### Next

1. Test 3 flow steps (218 ms per call on the local PC, model alone). The model predicts 16 actions and drops 4, so
   12 actions per call is the most it can play now.
2. Find why open fails (2 of 30). MolmoBot has no open or close training data.
3. Do not use the gripper rule.

## Repository layout

| Path | Content |
|---|---|
| `positronic_changes/` | The MolmoBot server, the image recipe and the MolmoAct2 GPU fix. `patches/` holds them as `git am` patches for Positronic commit `e6c45ba`. |
| `risers/eval_local/` | Local test tools, episode sets (`hard28.json`, `make_hard_set.py`) |
| `risers/overnight/` | Overnight test runner, results summary, progress timer, top-team video tool |
| `risers/molmobot_image/` | Image build script, and `Dockerfile.settings`: a one-layer image with other server flags |
| `risers/competition_runs/` | Submit scripts, board results, and `board_by_set.py` (successes per task set) |
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
