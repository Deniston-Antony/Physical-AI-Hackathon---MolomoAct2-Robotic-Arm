# v3 with the late-close rule

13 Nov: image v3 plays actions 4 to 15 of each chunk of 16. In a replay of 6 recorded episodes, 55% of the chunks for an open gripper close it, and for 21% the close starts in actions 12 to 15: most of those are chance (1 or 2 of 6 chunks of the same observation). The gripper then closes on nothing, about each 2 s. With the late-close rule, a chunk closes an open gripper only when the close starts before action 12; a later close is deferred (the gripper stays open for the chunk). "1 deferral": after one deferred chunk, the next late close goes out. "Each time": each late close is deferred. The servers of 13 Nov share one GPU, with 4 eval processes at a time each, on the 40 episodes of the tests of 10 and 11 Nov.

| Group | Episodes | v3 + late-close rule, 1 deferral | v3 + late-close rule, each time | v3 as it is (13 Nov) | v3 + JPEG (11 Nov, H100) | v3 (10 Nov, L40S) | Board v3 |
|---|---|---|---|---|---|---|---|
| Pick, hard | 14 | 10 | 8 | 0 (1 done) | 10 | 10 | 14 |
| Pick and place, normal | 6 | 4 | 6 | 0 (1 done) | 5 | 5 | 6 |
| Open, normal | 5 | 2 | 1 | 1 (1 done) | 2 | 3 | 2 |
| Open, hard | 5 | 1 | 1 | 0 (0 done) | 1 | 1 | 1 |
| Close, normal | 5 | 5 | 4 | 1 (1 done) | 5 | 4 | 4 |
| Close, hard | 5 | 2 | 4 | 1 (2 done) | 3 | 4 | 3 |
| **All** | 40 | 24 | 24 | 3 (6 done) | 26 | 27 | 30 |

## Gripper closings and time

A closing on nothing ends with the gripper fully closed. "Charged" is the time of a model call as the harness measures it.

| Image | Closings on nothing per episode: pick / open / close | Time closed on nothing per episode (s): pick / open / close | Closings on something per episode | Calls per episode | Charged, median of the streams (ms) | Median time of a success (s) |
|---|---|---|---|---|---|---|
| v3 + late-close rule, 1 deferral | 3.5 / 8.0 / 3.7 | 3.4 / 6.9 / 4.1 | 0.9 | 17.9 | 169 | 12.1 |
| v3 + late-close rule, each time | 3.0 / 7.9 / 3.9 | 3.1 / 6.8 / 3.3 | 0.7 | 17.2 | 171 | 9.7 |
| v3 as it is (13 Nov) | 3.0 / 0.0 / 1.3 | 5.5 / 0.0 / 2.2 | 1.0 | 12.3 | 2182 | 18.6 |
| v3 + JPEG (11 Nov, H100) | 3.6 / 6.5 / 3.6 | 5.1 / 5.1 / 3.2 | 0.7 | 18.1 | 322 | 10.8 |
| v3 (10 Nov, L40S) | 3.5 / 7.7 / 4.1 | 3.8 / 5.8 / 3.5 | 1.0 | 18.9 | 232 | 10.1 |

- late1: Late closes so far: 16, deferred 16
- late: Late closes so far: 13, deferred 13
- v3b: no late-close lines in the server log

## Per episode

| Board # | Group | Task | v3 + late-close rule, 1 deferral | v3 + late-close rule, each time | v3 as it is (13 Nov) | v3 + JPEG (11 Nov, H100) | v3 (10 Nov, L40S) | Board v3 |
|---|---|---|---|---|---|---|---|---|
| 16 | Close, normal | close the drawer. | OK 1.5 s | OK 2.0 s | - | OK 1.9 s | OK 2.3 s | OK |
| 36 | Close, normal | close the drawer. | OK 1.8 s | no | - | OK 9.7 s | OK 3.0 s | OK |
| 46 | Close, normal | close the drawer. | OK 1.4 s | OK 1.4 s | - | OK 1.6 s | OK 1.5 s | OK |
| 56 | Close, normal | close the table. | OK 7.9 s | OK 6.7 s | OK 5.5 s | OK 3.6 s | OK 1.8 s | OK |
| 76 | Close, normal | close the drawer. | OK 5.8 s | OK 6.8 s | - | OK 1.5 s | no | no |
| 19 | Close, hard | close the table. | no | no | OK 23.0 s | no | OK 11.7 s | OK |
| 49 | Close, hard | close the brown wooden desk. | OK 14.7 s | OK 11.9 s | - | OK 9.2 s | OK 7.7 s | OK |
| 59 | Close, hard | close the white dresser. | OK 13.4 s | OK 6.8 s | no | OK 7.0 s | OK 7.9 s | OK |
| 109 | Close, hard | close the dresser. | no | OK 22.9 s | - | no | no | no |
| 129 | Close, hard | close the dresser. | no | OK 13.0 s | - | OK 26.4 s | OK 19.1 s | no |
| 37 | Open, normal | open the desk. | no | no | - | no | OK 6.0 s | no |
| 57 | Open, normal | open the dresser. | OK 17.6 s | no | - | no | no | no |
| 107 | Open, normal | open the dresser. | OK 14.2 s | no | - | OK 19.8 s | no | OK |
| 117 | Open, normal | open the dresser. | no | no | - | no | OK 25.5 s | no |
| 127 | Open, normal | open the table. | no | OK 13.2 s | OK 18.6 s | OK 9.5 s | OK 4.3 s | OK |
| 28 | Open, hard | open the wooden table. | no | no | - | no | no | no |
| 38 | Open, hard | open the wooden table. | OK 11.7 s | OK 5.1 s | - | OK 8.1 s | OK 13.7 s | OK |
| 48 | Open, hard | open the desk. | no | no | - | no | no | no |
| 68 | Open, hard | open the wooden table. | no | no | - | no | no | no |
| 128 | Open, hard | open the dresser. | no | no | - | no | no | no |
| 12 | Pick, hard | pick up the brown pinecone keychain. | OK 14.0 s | OK 17.9 s | - | OK 15.0 s | OK 16.5 s | OK |
| 32 | Pick, hard | pick up the comb. | OK 16.4 s | OK 11.6 s | - | OK 16.4 s | no | OK |
| 42 | Pick, hard | pick up the mechanism. | no | no | - | no | OK 17.9 s | OK |
| 122 | Pick, hard | pick up the bottle. | OK 7.1 s | OK 8.5 s | - | OK 13.5 s | OK 10.1 s | OK |
| 132 | Pick, hard | pick up the kettle. | OK 5.5 s | OK 6.5 s | - | OK 10.0 s | OK 4.3 s | OK |
| 178 | Pick, hard | pick up the cup. | no | no | no | no | OK 16.5 s | OK |
| 214 | Pick, hard | pick up the screwdriver. | OK 12.5 s | no | - | OK 11.6 s | OK 8.8 s | OK |
| 218 | Pick, hard | pick up the egg. | OK 17.7 s | no | - | no | no | OK |
| 226 | Pick, hard | pick up the grenade. | OK 14.5 s | OK 5.3 s | - | OK 7.7 s | no | OK |
| 234 | Pick, hard | pick up the juicer. | no | no | - | OK 16.8 s | OK 7.5 s | OK |
| 242 | Pick, hard | pick up the red skull key. | OK 7.6 s | OK 9.0 s | - | OK 14.9 s | OK 12.2 s | OK |
| 274 | Pick, hard | pick up the brown potato. | OK 14.3 s | OK 10.4 s | - | OK 17.2 s | OK 10.4 s | OK |
| 282 | Pick, hard | pick up the small red potato. | OK 8.3 s | OK 10.3 s | - | OK 9.5 s | OK 12.1 s | OK |
| 298 | Pick, hard | pick up the white stopwatch. | no | no | - | no | no | OK |
| 41 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | OK 43.3 s | no | OK 22.0 s | OK 11.0 s | OK |
| 71 | Pick and place, normal | pick up the bottle and place it on the bowl. | OK 22.5 s | OK 25.3 s | - | OK 18.6 s | OK 12.7 s | OK |
| 177 | Pick and place, normal | pick up the mug and place it on the bowl. | OK 9.0 s | OK 8.8 s | - | OK 10.1 s | OK 9.9 s | OK |
| 197 | Pick and place, normal | pick up the knife and place it on the bowl. | no | OK 41.1 s | - | no | no | OK |
| 209 | Pick and place, normal | pick up the shaker and place it on the bowl. | OK 9.3 s | OK 9.0 s | - | OK 11.7 s | OK 9.8 s | OK |
| 221 | Pick and place, normal | pick up the ladle and place it on the bowl. | OK 13.1 s | OK 14.3 s | - | OK 18.3 s | OK 20.5 s | OK |
