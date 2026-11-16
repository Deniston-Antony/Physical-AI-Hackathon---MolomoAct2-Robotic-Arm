# v3 with the new rules: RoboLab, the 12 tasks of the platform

14 Nov. Image v3-jpeg with the code of cloud_v3x_rl/code mounted, on the 12 tasks of the platform's robolab.subset_12 (default instruction, both shoulder cameras), one episode each; cloud VM with an L40S GPU, 3 tasks at a time, the variants one after the other. "Control": no new rule (v3-jpeg-rl, with the still-arm rule for RoboLab wordings). "Training wording + steps": the task in the wording of MolmoBot's training data ("Pick up the X and place it in or on the Y"), and a task of several objects one step at a time, in the order of the task (the next step after the gripper let go of a held object). "All": also the deeper grasp after a miss and the vote before a close. The last column is the platform's own run of v3 (10 Nov). The score of a task is RoboLab's graded score at the end of the episode, from 0 to 1; the platform ranks RoboLab by its mean.

| Category | Tasks | Control (v3-jpeg-rl): successes | Control (v3-jpeg-rl): mean score | Training wording + steps: successes | Training wording + steps: mean score | All new rules: successes | All new rules: mean score | Platform, v3 (10 Nov): successes | Platform, v3 (10 Nov): mean score |
|---|---|---|---|---|---|---|---|---|---|
| visual | 4 | 2 | 0.88 | 3 | 0.88 | 3 | 0.88 | 3 | 0.88 |
| relational | 4 | 0 | 0.12 | 0 | 0.12 | 1 | 0.38 | 1 | 0.25 |
| procedural | 4 | 0 | 0.08 | 0 | 0.08 | 0 | 0.13 | 0 | 0.08 |
| **all** | 12 | 2 | 0.36 | 3 | 0.36 | 4 | 0.46 | 4 | 0.40 |

## Per task

| Task | Instruction | Control (v3-jpeg-rl) | Training wording + steps | All new rules | Platform, v3 (10 Nov) |
|---|---|---|---|---|---|
| BananaInBowlTask | Pick up the banana and place it in the bowl | yes (1.00) | yes (1.00) | yes (1.00) | yes (1.00) |
| BowlStackingLeftOnRightTask | Stack the left bowl on the right bowl | no (0.00) | no (0.00) | no (0.00) | no (0.00) |
| MarkerInMugTask | Put the whiteboard marker in the mug | no (0.00) | no (0.00) | no (0.00) | no (0.00) |
| ReorientAllMugsTask | Reorient all the mugs upright so that the opening is fa | no (0.00) | no (0.00) | no (0.17) | no (0.33) |
| BananasInCrateTask | Put 2 bananas in the crate | no (0.00) | no (0.00) | yes (1.00) | yes (1.00) |
| GrabABagelTask | Grab a bagel | no (1.00) | yes (1.00) | yes (1.00) | yes (1.00) |
| PutBowlOnShelfTopTask | Put the serving bowl anywhere on the shelf in front of  | no (0.00) | no (0.00) | no (0.00) | no (0.00) |
| RubiksCubeAndBananaTask | Put the cube and the banana in the bowl | no (0.50) | no (0.50) | no (0.50) | no (0.00) |
| PickUpGreenObjectTask | Pick up the green vegetable block | no (0.50) | no (0.50) | no (0.50) | no (0.50) |
| SmallerObjectButterInBinTask | Place the smaller object in the grey bin. | yes (1.00) | yes (1.00) | yes (1.00) | yes (1.00) |
| StackYellowOnRedTask | Stack the yellow block on the red block | no (0.00) | no (0.00) | no (0.00) | no (0.00) |
| RubiksCubesInBinTask | Sort all rubiks cubes into the bin | no (0.33) | no (0.33) | no (0.33) | no (0.00) |

## What the rules did

- rlctl: tasks reworded 0, next steps 7, still-arm pick part 3, deeper grasps 0; last counts {'next step': 0, 'deeper': 0, 'votes': 0, 'vote kept the close': 0}
- rlword: tasks reworded 8, next steps 8, still-arm pick part 5, deeper grasps 0; last counts {'next step': 1, 'deeper': 0, 'votes': 0, 'vote kept the close': 0}
- rlall: tasks reworded 8, next steps 7, still-arm pick part 7, deeper grasps 24; last counts {'next step': 1, 'deeper': 24, 'votes': 135, 'vote kept the close': 134}

## Time per model call

- rl_rlall_s1_p1: 182 calls, p50 165 ms, p95 511 ms
- rl_rlall_s2_p1: 183 calls, p50 177 ms, p95 505 ms
- rl_rlall_s3_p1: 269 calls, p50 158 ms, p95 470 ms
- rl_rlctl_s1_p1: 200 calls, p50 159 ms, p95 260 ms
- rl_rlctl_s2_p1: 262 calls, p50 158 ms, p95 192 ms
- rl_rlctl_s3_p1: 282 calls, p50 158 ms, p95 202 ms
- rl_rlword_s1_p1: 199 calls, p50 160 ms, p95 195 ms
- rl_rlword_s2_p1: 259 calls, p50 159 ms, p95 198 ms
- rl_rlword_s3_p1: 292 calls, p50 157 ms, p95 191 ms
