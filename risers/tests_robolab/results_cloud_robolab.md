# v3-jpeg on RoboLab: cloud test

The submitted image v3-jpeg (v3 with JPEG frames) on 12 RoboLab tasks, 4 of each RoboLab category, with the default instruction and both shoulder cameras. Cloud VM with an L40S GPU; 3 tasks at a time, one policy server. The score of a task is RoboLab's graded score at the end of the episode, from 0 to 1 (the share of the subtasks done). The platform ranks RoboLab by the mean of this score.

| Category | Tasks run | Successes | Mean score |
|---|---|---|---|
| visual | 4 | 3 | 0.88 |
| relational | 4 | 1 | 0.33 |
| procedural | 4 | 1 | 0.25 |
| **all** | 12 | 5 | 0.49 |

## Per task

| Task | Instruction | Kind | Difficulty | Episode s | Success | Subtasks done | Score at end | Best score |
|---|---|---|---|---|---|---|---|---|
| GrabAFruitTask | Pick up a fruit | semantics | simple | 30 | yes | 1/1 | 1.00 | 1.00 |
| RubiksCubeLeftOfBowlTask | Put the rubiks cube to the left of the bowl | spatial | moderate | 30 | no | 0/1 | 0.33 | 0.33 |
| StackYellowOnRedTask | Stack the yellow block on the red block | stacking | moderate | 60 | no | 0/1 | 0.00 | 0.00 |
| RubiksCubeAndBananaTask | Put the cube and the banana in the bowl | conjunction | simple | 60 | no | 0/1 | 0.00 | 0.00 |
| PickUpGreenObjectTask | Pick up the green vegetable block | color | simple | 30 | no | 0/1 | 0.50 | 0.50 |
| MustardInRightBinTask | Put the mustard in the right bin | spatial | simple | 30 | yes | 1/1 | 1.00 | 1.00 |
| CannedFoodInBinTask | Put the canned food in the grey bin | semantics | simple | 60 | yes | 1/1 | 1.00 | 1.00 |
| UnstackRubiksCubeTask | Unstack the rubiks cube tower | stacking | moderate | 90 | yes | 1/1 | 1.00 | 1.00 |
| BananaInBowlTask | Pick up the banana and place it in the bowl | semantics | simple | 50 | yes | 1/1 | 1.00 | 1.00 |
| ButterAboveRaisinTask | Pick up the butter box and place it on top of the  | spatial | simple | 40 | no | 0/1 | 0.00 | 0.00 |
| MarkerInMugTask | Put the whiteboard marker in the mug | affordance | moderate | 40 | no | 0/1 | 0.00 | 0.00 |
| Stack3RubiksCubeTask | Stack the rubiks cubes in a tower | stacking | moderate | 60 | no | 0/2 | 0.00 | 0.00 |

## Time per model call

- rl_v3jpeg_s1_p1: 204 calls, p50 161 ms, p95 201 ms
- rl_v3jpeg_s2_p1: 139 calls, p50 166 ms, p95 293 ms
- rl_v3jpeg_s3_p1: 187 calls, p50 163 ms, p95 199 ms
