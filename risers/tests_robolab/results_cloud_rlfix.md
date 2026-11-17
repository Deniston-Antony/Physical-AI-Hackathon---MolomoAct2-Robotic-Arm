# v3-jpeg with the still-arm rule for RoboLab wordings: cloud test

13 Nov. v3 has a still-arm rule: when the arm is still for 3 model calls with the gripper open, the model gets only the pick part of the task ("pick up the X."). Its wording matched 0 of the 120 RoboLab tasks; the new wording matches 54, and the same tasks of the board as before. Image v3-jpeg with that code mounted, on the same 12 RoboLab tasks as the test of v3-jpeg, with the default instruction and both shoulder cameras; cloud VM with an L40S GPU, 3 tasks at a time. The score of a task is RoboLab's graded score at the end of the episode, from 0 to 1. The rule gave the pick part in 9 sessions.

| Category | Tasks | v3-jpeg: successes | v3-jpeg: mean score | v3-jpeg + RoboLab rule: successes | v3-jpeg + RoboLab rule: mean score |
|---|---|---|---|---|---|
| visual | 4 | 3 | 0.88 | 3 | 0.88 |
| relational | 4 | 1 | 0.33 | 1 | 0.42 |
| procedural | 4 | 1 | 0.25 | 1 | 0.25 |
| **all** | 12 | 5 | 0.49 | 5 | 0.51 |

## Per task

| Task | Instruction | v3-jpeg | v3-jpeg + RoboLab rule |
|---|---|---|---|
| GrabAFruitTask | Pick up a fruit | yes (1.00) | yes (1.00) |
| RubiksCubeLeftOfBowlTask | Put the rubiks cube to the left of the bowl | no (0.33) | no (0.67) |
| StackYellowOnRedTask | Stack the yellow block on the red block | no (0.00) | no (0.00) |
| RubiksCubeAndBananaTask | Put the cube and the banana in the bowl | no (0.00) | no (0.00) |
| PickUpGreenObjectTask | Pick up the green vegetable block | no (0.50) | no (0.50) |
| MustardInRightBinTask | Put the mustard in the right bin | yes (1.00) | yes (1.00) |
| CannedFoodInBinTask | Put the canned food in the grey bin | yes (1.00) | yes (1.00) |
| UnstackRubiksCubeTask | Unstack the rubiks cube tower | yes (1.00) | yes (1.00) |
| BananaInBowlTask | Pick up the banana and place it in the bowl | yes (1.00) | yes (1.00) |
| ButterAboveRaisinTask | Pick up the butter box and place it on top of the raisi | no (0.00) | no (0.00) |
| MarkerInMugTask | Put the whiteboard marker in the mug | no (0.00) | no (0.00) |
| Stack3RubiksCubeTask | Stack the rubiks cubes in a tower | no (0.00) | no (0.00) |

## Time per model call

- rl_v3jpegrl_s1_p1: 215 calls, p50 158 ms, p95 214 ms
- rl_v3jpegrl_s2_p1: 109 calls, p50 166 ms, p95 270 ms
- rl_v3jpegrl_s3_p1: 186 calls, p50 161 ms, p95 208 ms
