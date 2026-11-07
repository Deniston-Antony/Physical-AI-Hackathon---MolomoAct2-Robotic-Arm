# Overnight test results

Episodes: `eval_local/hard28.json` (16 hard pick, 12 hard pick-and-place). Model: MolmoBot-Img-DROID, half overlap, left camera. Local PC (RTX 4070).

| Run | Setting | Solved | Hard pick | Hard pick and place | Robot waits | Inference p50 | Time to success (shared with base) |
|---|---|---|---|---|---|---|---|
| base | play 8 actions, 10 flow steps (the submitted image) | 3/28 | 1/16 | 2/12 | 65% | 1062 ms | 29.2 s vs 29.2 s (3 episodes) |
| play12 | play 12 actions, 10 flow steps | 6/28 | 3/16 | 3/12 | 56% | 1165 ms | 21.7 s vs 26.9 s (2 episodes) |
| flow5 | play 8 actions, 5 flow steps | 7/28 | 2/16 | 5/12 | 56% | 790 ms | 31.3 s vs 29.2 s (3 episodes) |
| play12_flow5 | play 12 actions, 5 flow steps | 16/28 | 9/16 | 7/12 | 47% | 790 ms | 24.0 s vs 26.9 s (2 episodes) |
| grip40 | gripper rule (open only below 40) on play12_flow5 | 16/28 | 9/16 | 7/12 | 47% | 796 ms | 24.6 s vs 23.2 s (2 episodes) |

## Per episode

| Episode | Set | base | play12 | flow5 | play12_flow5 | grip40 |
|---|---|---|---|---|---|---|
| pick up the comb. | pick | no | no | no | OK 19.2 s | OK 14.4 s |
| pick up the knife. | pick | no | no | no | OK 14.5 s | no |
| pick up the cup. | pick | no | OK 16.6 s | no | no | OK 19.6 s |
| pick up the potato. | pick | no | no | no | no | no |
| pick up the brown pinecone keychain. | pick | no | no | no | OK 16.0 s | OK 18.3 s |
| pick up the album. | pick | no | no | no | no | OK 17.8 s |
| pick up the cup. | pick | no | no | no | no | no |
| pick up the butter knife. | pick | no | no | no | no | no |
| pick up the silver kettle. | pick | no | no | no | OK 17.8 s | OK 18.0 s |
| pick up the grenade. | pick | no | no | OK 18.9 s | OK 12.6 s | OK 13.5 s |
| pick up the red skull key. | pick | no | no | no | OK 19.3 s | OK 17.0 s |
| pick up the egg. | pick | no | no | no | OK 15.4 s | no |
| pick up the pot. | pick | no | no | no | no | no |
| pick up the kettle. | pick | OK 17.2 s | OK 12.7 s | OK 12.9 s | OK 16.2 s | OK 11.4 s |
| pick up the brown egg. | pick | no | OK 15.2 s | no | OK 13.5 s | OK 13.6 s |
| pick up the bottle. | pick | no | no | no | no | no |
| pick up the butter knife and place it on the bowl. | pick and place | no | no | no | no | OK 30.8 s |
| pick up the onion and place it on the bowl. | pick and place | no | no | no | OK 34.9 s | no |
| pick up the spoon and place it on the rustic clay bowl. | pick and place | no | no | OK 22.3 s | no | no |
| pick up the bee and place it on the gray bowl. | pick and place | OK 36.6 s | OK 30.8 s | OK 31.3 s | OK 31.8 s | no |
| pick up the white mug and place it on the bowl. | pick and place | no | OK 39.5 s | OK 36.4 s | OK 26.7 s | OK 35.3 s |
| pick up the candle and place it on the gray bowl. | pick and place | no | no | no | no | no |
| pick up the futuristic black key and place it on the ti | pick and place | no | no | no | OK 39.1 s | OK 36.7 s |
| pick up the raw meat and place it on the pot. | pick and place | OK 29.2 s | no | OK 33.6 s | no | OK 37.8 s |
| pick up the goggles and place it on the bowl. | pick and place | no | no | no | OK 37.7 s | OK 30.4 s |
| pick up the kitchen spatula and place it on the rustic  | pick and place | no | OK 34.1 s | no | OK 32.9 s | OK 33.7 s |
| pick up the leather-wrapped brass telescope and place i | pick and place | no | no | OK 37.2 s | OK 36.2 s | OK 37.6 s |
| pick up the bowl and place it on the mug. | pick and place | no | no | no | no | no |

## Step 2: gripper rule

`grip40` is `play12_flow5` with `--model.grip_release_below=40`: a closed gripper opens only when the model value is
below 40 (of 255).

| | play12_flow5 | grip40 |
|---|---|---|
| Solved | 16/28 | 16/28 |
| Solved by both runs | 12 | 12 |
| Solved by this run only | 4 | 4 |
| Failures: the gripper closed on the object, then opened again | 11 | 11 |
| Failures: the gripper never closed | 1 | 1 |

Findings:
- The rule changes nothing. When the robot opens the gripper, the model value is clearly low. The model decides to
  open; the value does not move near the 128 threshold.
- Two runs with almost the same setting differ in 8 of 28 episodes (4 each way). So a difference of up to about 4
  episodes can be chance. The step 1 gain of `play12_flow5` (16 against 3) is much larger than this.
- The gains of `play12` (6) and `flow5` (7) alone over `base` (3) are within this chance range.

## Step 3: top-team replay videos (8 hard-pick episodes that 6+ top teams solve and our board run failed)

Tool: `risers/overnight/team_strips.py` (6 exterior frames per run: 3 top teams that solved the episode, then us).

| Episode | Top-team success times | Our board run | What our robot did |
|---|---|---|---|
| comb | 9.5 s, 17.1 s, 19.3 s | fail (21 s) | Same path as the top teams; reached the comb late |
| knife | 8.6 s, 11.4 s, 12.7 s | fail | Same path; reached the knife late |
| potato | 6.9 s, 15.2 s, ~10 s | fail | Same path; closed on the potato only at the end |
| album | about 13 s | fail | Same path; at the album at the end, not lifted |
| butter knife | about 5 s, 13.0 s, 19.3 s | fail | Went to another place first, then turned back |

Findings:
- In most episodes our robot moves along about the same path as the top teams' robots. It arrives late and runs out of
  time. This agrees with the step 1 result: speed is the main problem.
- In some episodes our robot goes to the wrong place first. This costs time too.
- We saw no grasp method of the top teams that differs from ours. Their robots move without stops.
- Limit: 6 frames per episode show the path, not the details of the grasp.
