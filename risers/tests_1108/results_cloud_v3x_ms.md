# v3 with the new rules: board tasks

14 Nov: image v3-jpeg with the code of cloud_v3x_ms/code mounted, on the 40 episodes of the tests of 10 and 11 Nov, 2 servers at a time on one L40S GPU, 4 eval processes each. The control has no new rule (it is v3-jpeg-rl). "Deeper grasp": after a close on nothing, a close within 6 cm of it goes 2 cm lower first (at most 3 times, not in open and close tasks). "Vote": a chunk that closes an open gripper is made 2 more times from the same observation, and the gripper closes only when 2 of the 3 chunks close it. "All" adds the training wording of a task and the steps of a task of several objects (the board tasks keep their text, so these two change nothing here). Batch 1: control and all; batch 2: deeper grasp and vote.

| Group | Episodes | v3-jpeg-rl, no new rule (control) | All new rules | Deeper grasp after a miss | Vote before a close | v3 + JPEG (11 Nov, H100) | v3 (10 Nov, L40S) | Board v3 |
|---|---|---|---|---|---|---|---|---|
| Pick, hard | 14 | 8 | 10 | 12 | 11 | 10 | 10 | 14 |
| Pick and place, normal | 6 | 5 | 5 | 5 | 5 | 5 | 5 | 6 |
| Open, normal | 5 | 0 | 1 | 1 | 1 | 2 | 3 | 2 |
| Open, hard | 5 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Close, normal | 5 | 4 | 4 | 5 | 5 | 5 | 4 | 4 |
| Close, hard | 5 | 4 | 4 | 4 | 4 | 3 | 4 | 3 |
| **All** | 40 | 22 | 25 | 28 | 27 | 26 | 27 | 30 |

## Gripper closings and time

A closing on nothing ends with the gripper fully closed. "Charged" is the time of a model call as the harness measures it.

| Image | Closings on nothing per episode: pick / open / close | Time closed on nothing per episode (s): pick / open / close | Closings on something per episode | Calls per episode | Charged, median of the streams (ms) | Median time of a success (s) |
|---|---|---|---|---|---|---|
| v3-jpeg-rl, no new rule (control) | 3.4 / 10.2 / 2.4 | 3.3 / 7.0 / 1.6 | 0.8 | 21.4 | 170 | 8.5 |
| All new rules | 3.1 / 7.0 / 3.5 | 3.3 / 5.8 / 3.0 | 0.8 | 19.1 | 200 | 11.3 |
| Deeper grasp after a miss | 3.4 / 9.1 / 3.7 | 3.1 / 6.5 / 2.8 | 0.8 | 19.4 | 169 | 9.7 |
| Vote before a close | 3.3 / 8.8 / 3.3 | 3.3 / 7.3 / 3.1 | 0.8 | 18.6 | 206 | 11.2 |
| v3 + JPEG (11 Nov, H100) | 3.6 / 6.5 / 3.6 | 5.1 / 5.1 / 3.2 | 0.7 | 18.1 | 322 | 10.8 |
| v3 (10 Nov, L40S) | 3.5 / 7.7 / 4.1 | 3.8 / 5.8 / 3.5 | 1.0 | 18.9 | 232 | 10.1 |

- ctl: {'next step': 0, 'deeper': 0, 'votes': 0, 'vote kept the close': 0}; deeper-grasp lines 0, next-step lines 8
- all: {'next step': 0, 'deeper': 16, 'votes': 223, 'vote kept the close': 215}; deeper-grasp lines 19, next-step lines 7
- deep: {'next step': 0, 'deeper': 16, 'votes': 0, 'vote kept the close': 0}; deeper-grasp lines 19, next-step lines 7
- vote: {'next step': 0, 'deeper': 0, 'votes': 220, 'vote kept the close': 212}; deeper-grasp lines 0, next-step lines 7

## Per episode

| Board # | Group | Task | v3-jpeg-rl, no new rule (control) | All new rules | Deeper grasp after a miss | Vote before a close | v3 + JPEG (11 Nov, H100) | v3 (10 Nov, L40S) | Board v3 |
|---|---|---|---|---|---|---|---|---|---|
| 16 | Close, normal | close the drawer. | OK 1.8 s | OK 1.8 s | OK 1.8 s | OK 2.0 s | OK 1.9 s | OK 2.3 s | OK |
| 36 | Close, normal | close the drawer. | OK 6.3 s | OK 12.9 s | OK 6.3 s | OK 9.3 s | OK 9.7 s | OK 3.0 s | OK |
| 46 | Close, normal | close the drawer. | OK 1.5 s | OK 1.7 s | OK 2.2 s | OK 2.8 s | OK 1.6 s | OK 1.5 s | OK |
| 56 | Close, normal | close the table. | OK 2.4 s | OK 1.8 s | OK 1.8 s | OK 1.6 s | OK 3.6 s | OK 1.8 s | OK |
| 76 | Close, normal | close the drawer. | no | no | OK 1.4 s | OK 2.0 s | OK 1.5 s | no | no |
| 19 | Close, hard | close the table. | OK 8.6 s | OK 9.7 s | OK 6.2 s | no | no | OK 11.7 s | OK |
| 49 | Close, hard | close the brown wooden desk. | OK 3.9 s | OK 19.7 s | OK 9.1 s | OK 16.7 s | OK 9.2 s | OK 7.7 s | OK |
| 59 | Close, hard | close the white dresser. | OK 2.0 s | OK 5.1 s | OK 3.3 s | OK 1.5 s | OK 7.0 s | OK 7.9 s | OK |
| 109 | Close, hard | close the dresser. | no | OK 28.8 s | no | OK 24.4 s | no | no | no |
| 129 | Close, hard | close the dresser. | OK 3.0 s | no | OK 25.7 s | OK 14.8 s | OK 26.4 s | OK 19.1 s | no |
| 37 | Open, normal | open the desk. | no | no | no | no | no | OK 6.0 s | no |
| 57 | Open, normal | open the dresser. | no | no | no | no | no | no | no |
| 107 | Open, normal | open the dresser. | no | no | no | OK 17.1 s | OK 19.8 s | no | OK |
| 117 | Open, normal | open the dresser. | no | no | no | no | no | OK 25.5 s | no |
| 127 | Open, normal | open the table. | no | OK 1.9 s | OK 9.8 s | no | OK 9.5 s | OK 4.3 s | OK |
| 28 | Open, hard | open the wooden table. | no | no | no | no | no | no | no |
| 38 | Open, hard | open the wooden table. | OK 12.3 s | OK 12.3 s | OK 9.7 s | OK 13.1 s | OK 8.1 s | OK 13.7 s | OK |
| 48 | Open, hard | open the desk. | no | no | no | no | no | no | no |
| 68 | Open, hard | open the wooden table. | no | no | no | no | no | no | no |
| 128 | Open, hard | open the dresser. | no | no | no | no | no | no | no |
| 12 | Pick, hard | pick up the brown pinecone keychain. | no | OK 14.7 s | OK 12.7 s | OK 17.3 s | OK 15.0 s | OK 16.5 s | OK |
| 32 | Pick, hard | pick up the comb. | OK 9.6 s | OK 11.9 s | OK 13.7 s | OK 11.2 s | OK 16.4 s | no | OK |
| 42 | Pick, hard | pick up the mechanism. | no | no | no | no | no | OK 17.9 s | OK |
| 122 | Pick, hard | pick up the bottle. | OK 18.9 s | OK 11.4 s | OK 10.0 s | OK 10.4 s | OK 13.5 s | OK 10.1 s | OK |
| 132 | Pick, hard | pick up the kettle. | OK 6.7 s | OK 6.6 s | OK 6.4 s | OK 7.7 s | OK 10.0 s | OK 4.3 s | OK |
| 178 | Pick, hard | pick up the cup. | OK 14.8 s | OK 14.4 s | OK 13.3 s | OK 17.5 s | no | OK 16.5 s | OK |
| 214 | Pick, hard | pick up the screwdriver. | OK 8.8 s | OK 9.4 s | OK 7.1 s | OK 8.8 s | OK 11.6 s | OK 8.8 s | OK |
| 218 | Pick, hard | pick up the egg. | no | no | OK 15.0 s | OK 18.5 s | no | no | OK |
| 226 | Pick, hard | pick up the grenade. | OK 6.0 s | OK 11.0 s | OK 7.0 s | OK 10.2 s | OK 7.7 s | no | OK |
| 234 | Pick, hard | pick up the juicer. | no | no | no | no | OK 16.8 s | OK 7.5 s | OK |
| 242 | Pick, hard | pick up the red skull key. | OK 13.3 s | OK 18.4 s | OK 10.1 s | OK 18.9 s | OK 14.9 s | OK 12.2 s | OK |
| 274 | Pick, hard | pick up the brown potato. | OK 8.4 s | OK 11.3 s | OK 13.1 s | OK 12.7 s | OK 17.2 s | OK 10.4 s | OK |
| 282 | Pick, hard | pick up the small red potato. | no | no | OK 14.4 s | OK 14.2 s | OK 9.5 s | OK 12.1 s | OK |
| 298 | Pick, hard | pick up the white stopwatch. | no | OK 18.7 s | OK 12.3 s | no | no | no | OK |
| 41 | Pick and place, normal | pick up the shaker and place it on the bowl. | OK 12.8 s | OK 11.1 s | OK 9.8 s | OK 15.8 s | OK 22.0 s | OK 11.0 s | OK |
| 71 | Pick and place, normal | pick up the bottle and place it on the bowl. | OK 12.4 s | OK 11.6 s | OK 11.4 s | OK 11.2 s | OK 18.6 s | OK 12.7 s | OK |
| 177 | Pick and place, normal | pick up the mug and place it on the bowl. | OK 9.2 s | OK 11.0 s | OK 8.6 s | OK 11.0 s | OK 10.1 s | OK 9.9 s | OK |
| 197 | Pick and place, normal | pick up the knife and place it on the bowl. | no | no | no | no | no | no | OK |
| 209 | Pick and place, normal | pick up the shaker and place it on the bowl. | OK 8.4 s | OK 10.0 s | OK 9.4 s | OK 10.0 s | OK 11.7 s | OK 9.8 s | OK |
| 221 | Pick and place, normal | pick up the ladle and place it on the bowl. | OK 16.6 s | OK 18.3 s | OK 13.8 s | OK 15.3 s | OK 18.3 s | OK 20.5 s | OK |
