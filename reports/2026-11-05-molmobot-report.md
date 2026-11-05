# PHAIL competition: test report for 5 November 2026

Team: The Risers. Board: `molmo.competition_v2` (stage 1, MolmoSpaces simulator, 320 episodes, Franka arm).

## Summary

| | Start of the day | End of the day |
|---|---|---|
| Best board score | 28.1% (MolmoAct2-DROID) | **40.6% (MolmoBot-DROID, half-overlap timing)** |
| Board rank | 12 of 25 | 14 of 33 (more teams joined; the 5th place is now at 62.2%) |

Two changes gave the gain:

1. **A new model.** MolmoBot-DROID replaced MolmoAct2-DROID: +27 episodes (28.1% to 36.6%).
2. **Faster timing.** "Half overlap" requests the next action chunk before the current chunk ends: +13 episodes (36.6% to 40.6%).

The main open problems:

- Unusual objects in the "hard" scenes. These are about 147 of the 320 episodes, and MolmoBot solves only 0–19% of them.
- Open tasks (7%) and place-next-to tasks (0%).

A third image (MolmoBot-Img-DROID) was submitted at 19:38 UTC. Its score was not available when this report was written.

### Submissions on 5 November

| # | Time (UTC) | Submission | Image (Docker Hub, public) | Score |
|---|---|---|---|---|
| 1 | 07:28 | `783e6095782a813c` | `denistonantony/molmobot-droid:v1` (`sha256:e67fc527…f0f17b59`) | 36.6% (117/320) |
| 2 | 12:51 | `6571687c389055ca` | `denistonantony/molmobot-droid:v2` (`sha256:c60d02a3…83e9c92e`) | **40.6% (130/320)** |
| 3 | 19:38 | `30b01a00181a225` | `denistonantony/molmobot-img-droid:v1` (`sha256:0c003390…8415d83a`) | not available yet |

The platform accepted three submissions on 5 November. The rules page states one per day.

---

## Test 1: Is Molmo2-8B a robot model?

| Question | Answer |
|---|---|
| Model type | Vision-language model (image and video in, text and points out) |
| Robot actions out | No |
| Usable for the competition | No: it would score 0% |

**Finding.** Molmo2-8B has no action output. MolmoAct2 already builds on a Molmo2 model (Molmo2-ER) and adds the action part.

**Result.** We used MolmoBot-DROID instead. It is a Molmo2-4B model with an action part, trained only on simulation data from MolmoSpaces, the same simulator that the competition uses.

---

## Test 2: MolmoBot-DROID adapter, offline check

**Method.** We wrote a Positronic server for MolmoBot (`positronic/vendors/molmobot/`). We ran it on 12 recorded MolmoBot-Data test episodes (pick, pick and place, color, next-to). Every 8 steps, the model saw the recorded frames and state. We compared its first 8 actions with the expert's actions.

| Measure | Result |
|---|---|
| Mean joint error against the expert | 0.011 rad |
| Gripper open/closed agreement | 99% |
| Inference time per call (RTX 4070) | 0.55 s |
| Peak GPU memory | 10.06 GiB (fits the 12 GB card) |
| Model load time | 76 s |

**Adapter details** (from MolmoBot's own `FrankaState8ClampAbsPosConfig`):

- Cameras: one shoulder camera and the wrist camera. Each has two frames: the current frame and the frame of the previous call.
- State: 7 joints and the finger position. The finger position is Positronic grip × 0.824033.
- Actions: 16 predicted, 8 executed. A gripper value above 128 closes the gripper. Each joint step is capped at 0.2 rad.
- Weights: the 20 GB float32 file loads through a memory map straight into a bfloat16 model on the GPU. This keeps RAM use low.

**Finding.** The wiring is correct, and the model fits the local GPU.

---

## Test 3: Local practice set (20 pick episodes, `molmo.franka_pick_mini`)

| Model | Solved |
|---|---|
| **MolmoBot-DROID** | **17/20 (85%)** |
| GR00T step 10000 (our fine-tune) | 12/20 and 13/20 (two runs) |
| MolmoAct2-DROID | 8/20 (earlier practice run on Nebius serverless) |
| GR00T, not fine-tuned | 6/20 |

**Finding.** MolmoBot was the best model on this set. It missed a thin remote control, a green ladle and a vague "cookware" task.

---

## Test 4: Mixed local set of 40 board episodes (stopped after 6)

**Method.** `make_mixed_set.py` picks 40 board episodes in the board's task proportions. Our MolmoAct2 board run solved 14 of the 40. The user stopped the run after 6 episodes, all open or close.

| | Solved (6 open/close episodes) |
|---|---|
| MolmoBot-DROID (local) | 2/6 |
| MolmoAct2-DROID (same episodes on the board) | 4/6 |

**Finding.** MolmoBot is weaker on open and close tasks. Its training data has no Franka open or close demonstrations.

---

## Test 5: Submission 1, MolmoBot-DROID (normal timing)

### Build problems and fixes

| Problem | Fix |
|---|---|
| The bfloat16 weight conversion used too much RAM, and `systemd-oomd` stopped it | Use the float32 weights in the image (29.7 GB image, under the 50 GB limit) |
| `.dockerignore` excludes `docker/*` | Add `!docker/molmobot-constraints.txt` |
| The project setting `exclude-newer = 2026-07-21` hides `pyarrow` 26 | Install the MolmoBot packages with `uv pip install --no-config` |
| `docker/test_policy_image.sh` pulls the image with `--pull=always` | Push first, or test a local copy of the script without the pull |

The platform start test passed: the server answered after 81 s, offline, on the GPU.

### Result by task type

| Task type | Episodes | MolmoBot-DROID | MolmoAct2-DROID (28.1% run) | GR00T step 10000 |
|---|---|---|---|---|
| Pick | 116 | **55 (47%)** | 28 (24%) | 28 |
| Pick and place (incl. color) | 128 | **48 (38%)** | 32 (25%) | 16 |
| Place next to | 16 | 0 | **3** | 0 |
| Open | 30 | 2 | **6** | 4 |
| Close | 30 | 12 (40%) | **21 (70%)** | 18 |
| **Total** | 320 | **117 (36.6%)** | 90 (28.1%) | 66 (20.6%) |

### Result by scene (pick and place tasks only)

| Scene | MolmoBot-DROID | MolmoAct2-DROID |
|---|---|---|
| Normal rooms (`procthor-10k`) | **60%** | 32% |
| Unusual objects (`procthor-objaverse`, `holodeck-objaverse`) | 12% | 13% |

Episode overlap: both models solved 56 episodes, only MolmoBot 61, only MolmoAct2 34, and neither 169.

**Findings.**

- MolmoBot almost doubles the score in normal rooms.
- Neither model handles unusual objects well.
- Every failed episode ran to the time limit (204 of 320 episodes).
- Across 6 runs, the same MolmoAct2 image scored between 25.6% and 28.1%. So the +8.5 points are not chance.

---

## Test 6: Combine MolmoAct2 and MolmoBot (estimate, not built)

**Idea.** One image sends open, close and next-to tasks to MolmoAct2 and all other tasks to MolmoBot.

| Routing | Estimated score (MolmoAct2 = mean of 6 board runs) |
|---|---|
| Open and close to MolmoAct2 | 39.7% |
| Open, close and next-to to MolmoAct2 | 40.6% |
| Same, both with half-overlap timing | about 43% |

**Finding.** The two models do not fit the competition GPU together:

- MolmoAct2 needs about 15 GB and MolmoBot about 10.5 GB.
- The competition slice is one `1g.24gb` RTX PRO 6000 slice with 24 192 MiB, and a competition plan cannot ask for more.

An 8-bit MolmoAct2 (about 6 GB) could fit. This idea was not tested.

---

## Test 7: Timing, inference while the robot moves (local, 20 pick episodes)

**Background.** On the local PC, one inference round trip takes 1.33 s (p50). The model alone takes 0.55 s; the simulator shares the GPU and the CPU. The platform charges inference time to the simulation clock. So the robot waited 73% of each episode.

**Method.** `ChunkedSchedule` has an `inference_lead` setting: it requests the next chunk before the current chunk ends. The new chunk then starts some actions after its observation, so the server drops those actions (`skip_actions`).

| Mode | Server command | Request the next chunk | Actions dropped | Solved | Robot waits | Time to success (episodes that both runs solved) |
|---|---|---|---|---|---|---|
| Normal | `droid` | at chunk end | 0 | **17/20** | 73% | 13.0 s |
| Full overlap | `droid_overlap` | at chunk start (lead 1.0 s) | 8 | 14/20 | 64% | **8.4 s** |
| **Half overlap** | `droid_half_overlap` | 0.2 s before the end | 4 | 16/20 | 69% | 10.8 s |

**Findings.**

- Full overlap is the fastest, but it misses more grasps, because the plan comes from an older image.
- Half overlap is 17% faster, and its success rate is almost the same as normal timing.
- Camera side was not controlled in these runs. Full overlap used the left camera; the other two runs used the right camera.

**Check.** The platform client must support `inference_lead`. It came in on 17 October (#947) and scheduler spec v3 on 18 October (#963). The platform accepted our v3 spec in submission 1, so it supports the setting.

---

## Test 8: Submission 2, MolmoBot-DROID with half overlap

| Task type | Episodes | v2 (half overlap) | v1 (normal) | Change |
|---|---|---|---|---|
| Pick | 116 | **63 (54%)** | 55 (47%) | +8 |
| Pick and place | 128 | 47 (37%) | 48 (38%) | −1 |
| Place next to | 16 | 0 | 0 | 0 |
| Open | 30 | 2 | 2 | 0 |
| Close | 30 | **18 (60%)** | 12 (40%) | +6 |
| **Total** | 320 | **130 (40.6%)** | 117 (36.6%) | **+13** |

| Timing on the platform | v2 | v1 |
|---|---|---|
| Median simulation time of a success | 15.3 s | 17.4 s |
| Episodes that ran to the time limit | 192 | 204 |

**Finding.** The faster timing helps most on the short tasks (pick and close).

---

## Test 9: Why does next-to score 0%? (16 board episodes, local, half overlap)

**Result.** 0/16 locally, the same as on the board.

| What happened | Episodes |
|---|---|
| Closed on the object, then opened the gripper again 1–4 s later and retried without success | 11 |
| Closed on the wrong object | 1 |
| Never closed the gripper (hovered, or did not find the object in a dark scene) | 4 |
| Carried the object to the target and ran out of time | **0** |

### Time limit compared with expert time

Expert time is the time to first success in MolmoBot-Data demonstrations; 66 ms per step.

| Task set | Expert time | Time limit | Limit ÷ expert | MolmoBot v1 |
|---|---|---|---|---|
| Pick (easy rooms) | 3.8 s | 31 s | 8.2× | 88% |
| Pick and place (easy rooms) | 8.2 s | 46 s | 5.6× | 61% |
| Pick (hard) | 3.8 s | 21 s | 5.5× | 12% |
| Pick and place (hard) | 8.2 s | 41 s | 5.0× | 16% |
| Color (hard) | 8.3 s | 41 s | 4.9× | 19% |
| Next to (hard) | 11.5 s | 31 s | 2.7× | 0% |

**Findings.**

- Next-to has the tightest time limit. But the robot fails much earlier than the limit: it cannot hold unusual objects.
- The task wording matches MolmoBot's training data ("Pick up the X and place it next to the Y").
- The same cause affects all the hard sets: hard pick (57 episodes), hard pick and place (58), color (16) and next-to (16). That is about 147 episodes.

**Local problem fixed.** The asset server returned HTTP 500 for two objects. We downloaded the two `objaverse_<hash>.tar.zst` packages and extracted them into `~/molmospaces/cache/objects/objaverse/20260131/`.

---

## Test 10: Does MolmoBot's training data already have unusual objects?

**Method.** We read the object names of 350 MolmoBot-Data episodes (our matched subset).

| Object source | Episodes |
|---|---|
| Objaverse objects (`obja…`) | 178 (51%) |
| Standard objects (mug, pepper shaker, remote, …) | 172 |

**Finding.** About half of MolmoBot's training data already uses unusual objects. A few hundred more demonstrations are not likely to change much; our estimate is a 35–40% chance of a clear gain on the hard sets. Open and close training stays promising, because MolmoBot has no examples of these tasks. Our estimate there is a 70–80% chance with 1 000–2 000 demonstrations.

---

## Test 11: Left or right shoulder camera?

**Facts.**

- In the competition, `image.exterior` is the left or the right shoulder camera, chosen per episode. MolmoAct2 run `2d30ed2cf955a93` had 159 left and 161 right.
- In a local run, the side is fixed for the whole run.
- The right shoulder camera is Positronic's mirror copy of the benchmark's left camera.

**Method.**

1. `camera_side.py` decides which first frame comes from the left camera. The left camera sees the white robot base in the lower right of the image. The check was right in 112 of 119 local episodes (94%).
2. `replay_camera_split.py` applies the check to the public replay videos of submission 2.

| Task type | Left camera | Right camera |
|---|---|---|
| **All** | **73/164 (45%)** | **57/156 (37%)** |
| Pick | 58% | 50% |
| Pick and place | 39% | 33% |
| Close | 58% | 61% |
| Open | 10% | 5% |
| Next to | 0% | 0% |

**Finding.** MolmoBot does about 8 points better with the left camera, which is the camera type that it trained on. The gap is suggestive (z ≈ 1.5) but not proven.

**Change.** The adapter now gets both shoulder cameras. A `camera` option (`exterior`, `left` or `right`) picks one camera per episode.

---

## Test 12: Survey of the Ai2 models (58 Hugging Face collections)

The relevant collections were MolmoAct2 (models, fine-tuned models, datasets, eval rollouts), MolmoBot (models, data), MolmoAct v1, MolmoMotion, MolmoPoint, WildDet3D and Molmo2. The others are language-model collections.

### Franka models, from the MolmoBot paper's simulation table (arXiv 2603.16861)

| Model | Simulation average | Real robot |
|---|---|---|
| **MolmoBot-DROID** (2 frames) | **64.1%** | **79.2%** |
| MolmoBot-Ablation-MF3-DROID (3 frames) | 62.4% | 75.0% |
| MolmoBot-Img-DROID (1 frame) | 61.6% | 72.5% |
| MolmoBot-Pi0-DROID | 41.5% | 46.7% |
| π0.5 fine-tuned on MolmoBot data | 36.0% | – |
| π0.5 | 10.0% | 31.3% |

### Models that do not fit this competition

| Models | Reason |
|---|---|
| MolmoBot-SPOC | Needs object image points and a fixed camera |
| MolmoBot-RBY1 | A different robot |
| MolmoAct2 for LIBERO, SO-100/101 and YAM | A different simulator or robot |
| MolmoAct2-Pretrain, FAST tokenizer | Not complete controllers |
| Molmo2, Molmo2-ER, MolmoPoint, MolmoMotion, WildDet3D | No action output |

MolmoAct2-DROID is the only MolmoAct2 model that runs on a Franka arm without more training.

**Finding.** The MolmoBot family is the best fit. MolmoBot-Img sees 2 images per call instead of 4, so it is a candidate for faster inference.

---

## Test 13: MolmoBot-Img-DROID (local, 20 pick episodes, half overlap)

| Model (all with half overlap unless stated, right camera) | Solved | Inference p50 | Robot waits | Time to success (shared episodes) |
|---|---|---|---|---|
| MolmoBot-DROID, normal timing | 17/20 | 1.33 s | 73% | 13.0 s |
| MolmoBot-DROID | 16/20 | 1.33 s | 69% | 10.8 s |
| **MolmoBot-Img-DROID** | **18/20 (90%)** | **1.02 s** | **63%** | **9.5 s** |

The camera option chose the right camera in 19 of 20 episodes.

**Findings.**

- MolmoBot-Img is 23% faster per call.
- It solved the thin remote control, which every earlier run missed.
- The difference is 2 episodes on 20, so the score gain is not proven.

**Result.** We built `molmobot-img-droid:v1` (half overlap, `camera=left`). It passed the start test (64 s) and solved 4/5 in a local check against the real image. We submitted it as submission 3.

---

## Other findings and limits

| Topic | Finding |
|---|---|
| MolmoAct2 with half overlap | Not tested: MolmoAct2 needs about 15 GB of GPU memory, and the local card has 12 GB. Estimate: 29–31%, still below MolmoBot. |
| Several simulators at the same time on the PC | Not possible. One simulator uses about 6.5 GB of RAM on objaverse scenes, and the PC has 15 GB. The GPU is at 11.7 of 12.3 GB with the model loaded. |
| Local simulation speed | 9–17% of real time. One 31 s episode takes about 5 minutes. |
| Image builds | One 30 GB image needs about 60 GB of free disk while it builds. Delete the build cache after each build (`docker builder prune -af`). |
| Model storage | The original MolmoBot-DROID weights (revision `cbe6ec35`) are on the external drive `Deniston2TB/Physical AI Hackathon - trained_models/MolmoBot-DROID`. |

---

## Code in this branch

| Path | Content |
|---|---|
| `positronic_changes/positronic/vendors/molmobot/` | MolmoBot server: model wrapper (memory-map load, frame history, joint step cap, camera choice), codec, server commands `droid`, `droid_overlap` and `droid_half_overlap` |
| `positronic_changes/docker/Dockerfile.serve-molmobot-droid` | Policy image. Build arguments: `CHECKPOINT_NAME`, `SERVER_COMMAND`, `SERVER_ARGS` |
| `positronic_changes/docker/molmobot-constraints.txt` | Tested versions of the extra packages for the MolmoBot code |
| `positronic_changes/docker/Dockerfile.serve-molmoact2-droid` | Adds the NVIDIA variables that the platform GPU needs (the fix for the 31 October `policy_setup_crash`) |
| `positronic_changes/patches/` | The same changes as three `git am` patches for Positronic commit `e6c45ba` (the patches also add `!docker/molmobot-constraints.txt` to `.dockerignore`) |
| `risers/molmobot_image/build.sh` | Builds an image from a checkpoint folder |
| `risers/eval_local/` | Local test runner, episode-set builder, run comparison, failure phases, camera-side check, board replay split, episode lists |
| `risers/competition_runs/` | Submit scripts and the `result.json` of our board runs |
| `risers/datagen/`, `risers/nebius_train/` | Data generation and GR00T training scripts from 31 October to 2 November |

To use the code:

1. Clone Positronic (`https://github.com/Positronic-Robotics/positronic`) and check out commit `e6c45ba`.
2. Apply the patches: `git am <this repo>/positronic_changes/patches/*.patch`.
3. Put the `risers/` folders beside the `positronic` checkout. The scripts expect this layout.

---

## Next steps (in order)

1. Read the MolmoBot-Img score (submission 3). Keep the better image.
2. Test a gripper rule with two thresholds: close above 128, open again only below about 40. It is a free local test.
3. Test fewer flow-matching steps (5 instead of 10) for faster inference. It is a free local test.
4. Fine-tune MolmoBot on 1 000–2 000 open and close demonstrations from our data generator, mixed with MolmoBot-Data. Estimate: one H100 for several hours, $25–45.
