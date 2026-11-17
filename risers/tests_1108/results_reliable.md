# The 34 reliable board episodes: top 5 vs us

Reliable: 3 or more of the top 5 teams solve the episode, and 2 or more of our 3 board runs fail it.
First close and closes: for the top teams and our board v3 run, read from the wrist video (right within 1 s
in about 3 of 4 episodes); for a local run, from the recorded gripper signal.

Solved by the local run reliable_v3: 15/34 (board v3 on the same episodes: 10/34)

| Set | Episodes | Top-5 solves (of 5 each) | Board v3 / v4 / v5 | Local run | Top first close s | Our board v3 first close s | Local first close s | Top closes | Our board closes |
|---|---|---|---|---|---|---|---|---|---|
| PickHard | 7 | 25 | 1 / 1 / 1 | 2/7 | - | - | 1.9 | - | - |
| PickandPlaceHard | 6 | 22 | 1 / 2 / 1 | 4/6 | - | - | 1.3 | - | - |
| CloseHard | 4 | 12 | 0 / 2 / 1 | 0/4 | 2.1 | 3.3 | 1.4 | 1.0 | 10.0 |
| OpenDataGen | 4 | 16 | 2 / 0 / 0 | 2/4 | 8.8 | 6.8 | 8.0 | 1.0 | 3.5 |
| PickandPlaceColorHard | 3 | 10 | 1 / 0 / 0 | 2/3 | - | - | 0.7 | - | - |
| PickDroidMini | 3 | 13 | 1 / 1 / 1 | 2/3 | 3.6 | 3.4 | 3.2 | 1.0 | 10.0 |
| PickandPlaceDroidMini | 2 | 6 | 1 / 0 / 1 | 1/2 | 3.6 | 6.4 | 5.3 | 1.0 | 7.0 |
| PickandPlaceNextToHard | 2 | 7 | 1 / 0 / 1 | 1/2 | - | - | 1.2 | - | - |
| CloseDataGen | 2 | 8 | 2 / 0 / 0 | 1/2 | 3.0 | 2.4 | 1.9 | 0.0 | 2.5 |
| OpenHard | 1 | 3 | 0 / 0 / 0 | 0/1 | 2.3 | - | 0.9 | 0.5 | - |
| All | 34 | 122 | 10 / 6 / 6 | 15/34 | 4.0 | 4.0 | 1.9 | 1.0 | 6.0 |

## Per episode

| Board # | Set | Task | Top solves | Top time s | Top first close s | Board v3 | Board v3 first close s, closes | Local | Local first close s, closes |
|---|---|---|---|---|---|---|---|---|---|
| 86 | CloseDataGen | close the cabinet. | 5 | 1.6 | 9.4 | OK | -, 0 | OK 2.0 s | -, 0 |
| 116 | CloseDataGen | close the drawer. | 3 | 6.7 | 2.7 | OK | 2.4, 5 | no 30.0 s | 1.9, 14 |
| 69 | CloseHard | close the desk. | 3 | 7.5 | 2.1 | no | -, - | no 30.0 s | 0.3, 12 |
| 99 | CloseHard | close the light brown table. | 3 | 6.8 | 5.2 | no | -, - | no 30.0 s | 1.5, 13 |
| 139 | CloseHard | close the dark dresser. | 3 | 13.9 | 1.2 | no | 1.1, 10 | no 30.0 s | 1.2, 14 |
| 149 | CloseHard | close the dresser. | 3 | 11.7 | 5.4 | no | 5.4, 10 | no 30.0 s | 3.2, 14 |
| 57 | OpenDataGen | open the dresser. | 3 | 12.4 | 11.4 | no | 3.0, 13 | OK 24.8 s | 3.7, 8 |
| 107 | OpenDataGen | open the dresser. | 5 | 2.7 | - | OK | 11.7, 2 | OK 25.8 s | 24.6, 1 |
| 117 | OpenDataGen | open the dresser. | 3 | 9.0 | 5.5 | no | 6.8, 5 | no 30.0 s | 6.7, 3 |
| 127 | OpenDataGen | open the table. | 5 | 15.3 | 9.7 | OK | -, 0 | no 30.0 s | 9.2, 9 |
| 128 | OpenHard | open the dresser. | 3 | 10.2 | 2.3 | no | -, - | no 30.0 s | 0.9, 14 |
| 288 | PickDroidMini | pick up the box. | 4 | 3.8 | 3.7 | OK | 3.0, 1 | OK 4.0 s | 3.2, 1 |
| 292 | PickDroidMini | pick up the pot. | 4 | 11.0 | 3.7 | no | 4.0, 10 | OK 18.3 s | 4.9, 6 |
| 304 | PickDroidMini | pick up the bottle. | 5 | 4.2 | 2.8 | no | 3.4, 12 | no 30.0 s | 3.2, 15 |
| 52 | PickHard | pick up the toilet. | 3 | 8.8 | - | no | -, - | no 20.0 s | 4.3, 8 |
| 182 | PickHard | pick up the dog statue. | 3 | 11.4 | - | OK | -, - | OK 10.5 s | 0.5, 4 |
| 222 | PickHard | pick up the album. | 4 | 9.9 | - | no | -, - | no 20.0 s | 3.5, 9 |
| 254 | PickHard | pick up the black webcam. | 4 | 12.7 | - | no | -, - | no 20.0 s | 1.9, 4 |
| 262 | PickHard | pick up the green battery. | 3 | 16.9 | - | no | -, - | no 20.0 s | 7.5, 1 |
| 294 | PickHard | pick up the wooden fan. | 3 | 18.9 | - | no | -, - | OK 16.4 s | 1.3, 8 |
| 309 | PickHard | pick up the pot. | 5 | 11.4 | - | no | -, - | no 20.0 s | 0.7, 11 |
| 14 | PickandPlaceColorHard | Pick up the yellow flower with leaf and place it i | 3 | 22.0 | - | no | -, - | no 40.0 s | 0.5, 19 |
| 44 | PickandPlaceColorHard | Pick up the standard playing card with clubs and p | 4 | 13.1 | - | OK | -, - | OK 15.8 s | 0.7, 5 |
| 134 | PickandPlaceColorHard | Pick up the low-poly brown acorn and place it in o | 3 | 26.7 | - | no | -, - | OK 34.7 s | 1.1, 8 |
| 11 | PickandPlaceDroidMini | pick up the bottle and place it on the bowl. | 3 | 14.2 | 5.0 | no | 8.4, 8 | OK 26.5 s | 7.5, 6 |
| 253 | PickandPlaceDroidMini | pick up the towel and place it on the bowl. | 3 | 11.2 | 3.6 | OK | 4.4, 6 | no 45.0 s | 3.2, 5 |
| 43 | PickandPlaceHard | pick up the brush and place it on the bowl. | 4 | 23.3 | - | no | -, - | no 40.0 s | 0.8, 16 |
| 143 | PickandPlaceHard | pick up the candle and place it on the gray bowl. | 5 | 17.2 | - | no | -, - | OK 18.5 s | 1.1, 4 |
| 199 | PickandPlaceHard | pick up the gray metal ring and place it on the bo | 3 | 30.0 | - | no | -, - | no 40.0 s | 24.9, 7 |
| 279 | PickandPlaceHard | pick up the smart speaker and place it on the rust | 3 | 25.2 | - | OK | -, - | OK 29.3 s | 1.5, 5 |
| 303 | PickandPlaceHard | pick up the toy dog and place it on the dish. | 4 | 16.9 | - | no | -, - | OK 14.3 s | 6.5, 1 |
| 316 | PickandPlaceHard | pick up the glossy golden musical note and place i | 3 | 19.9 | - | no | -, - | OK 21.8 s | 0.3, 7 |
| 15 | PickandPlaceNextToHard | Pick up the blue patterned cat and place it next t | 3 | 24.1 | - | no | -, - | OK 17.2 s | 0.8, 4 |
| 125 | PickandPlaceNextToHard | Pick up the dark metal frying pan and place it nex | 4 | 19.2 | - | OK | -, - | no 30.0 s | 1.5, 5 |

## Every episode that 3 or more of the top 5 solve (sets with a right video closure)

| Set | Episodes | Top successes: first close s, closes, time s | Our board v3 successes: first close s, closes, time s | Our board v3 failures: first close s, closes |
|---|---|---|---|---|
| CloseDataGen | 14 | 3.0, 0.0, 2.1 (n=64) | 2.8, 0.0, 2.0 (n=13) | 5.3, 10.0 (n=1) |
| CloseHard | 10 | 2.3, 1.0, 5.1 (n=37) | 1.1, 0.0, 4.9 (n=3) | 1.3, 10.0 (n=3) |
| OpenDataGen | 4 | 8.8, 1.0, 11.4 (n=16) | 11.7, 1.0, 10.6 (n=2) | 4.9, 9.0 (n=2) |
| OpenHard | 2 | 3.6, 1.0, 9.4 (n=6) | 4.6, 1.0, 5.7 (n=1) | - |
| PickDroidMini | 58 | 2.9, 1.0, 4.6 (n=278) | 3.4, 1.0, 4.9 (n=55) | 3.4, 10.0 (n=3) |
| PickandPlaceDroidMini | 49 | 3.7, 1.0, 11.3 (n=221) | 3.8, 1.0, 13.0 (n=46) | 3.6, 11.0 (n=3) |
