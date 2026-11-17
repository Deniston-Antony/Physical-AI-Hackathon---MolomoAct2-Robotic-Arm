# v3 with JPEG camera frames: board-load test

11 Nov: cloud VM with an H100 GPU (no L40S was free) and 16 CPUs. Two policy servers share the GPU, each with 4 eval processes at a time, as the board does, on the same 40 episodes as the tests of 10 Nov. "v3 + JPEG" is image v3 with one change: the server asks the client for JPEG frames (quality 90) in place of raw frames. "v3, raw frames" is image v3 as it is. 10 Nov: cloud VM with an L40S GPU; v3 and v4 each had the GPU alone, v6 and v5-touch shared it.

| Group | Episodes | v3 + JPEG (11 Nov, H100) | v3, raw frames (11 Nov, H100) | v3 (10 Nov) | v4 (10 Nov) | v6 (10 Nov) | v5-touch (10 Nov) | Board v3 | Board v4 |
|---|---|---|---|---|---|---|---|---|---|
| Pick, hard | 14 | 10 | 0 (1 done) | 10 | 12 | 12 | 9 | 14 | 14 |
| Pick and place, normal | 6 | 5 | 1 (1 done) | 5 | 5 | 5 | 5 | 6 | 6 |
| Open, normal | 5 | 2 | 0 (1 done) | 3 | 2 | 2 | 4 | 2 | 0 |
| Open, hard | 5 | 1 | 0 (0 done) | 1 | 1 | 1 | 0 | 1 | 1 |
| Close, normal | 5 | 5 | 1 (1 done) | 4 | 4 | 5 | 4 | 4 | 4 |
| Close, hard | 5 | 3 | 2 (2 done) | 4 | 5 | 2 | 3 | 3 | 5 |
| **All** | 40 | 26 | 4 (6 done) | 27 | 29 | 27 | 25 | 30 | 30 |

## Time per model call and the image format

"Charged" is the time of a model call as the harness measures it: the robot waits this long. "compress_images" is the value that the episodes recorded from the server handshake.

| Image | Calls | Charged p50 per stream (ms) | Median of the streams (ms) | compress_images in the episodes |
|---|---|---|---|---|
| v3 + JPEG (11 Nov, H100) | 723 | 689, 284, 330, 322, 290 | 322 | True: 40 |
| v3, raw frames (11 Nov, H100) | 75 | 859, 792, 832, 808 | 820 | False: 6 |
| v3 (10 Nov) | 756 | 232, 235, 231, 232 | 232 | False: 40 |
| v4 (10 Nov) | 692 | 231, 234, 232, 230 | 231 | False: 40 |
| v6 (10 Nov) | 785 | 247, 240, 248, 243 | 245 | False: 40 |
| v5-touch (10 Nov) | 735 | 494, 335, 483, 509, 485 | 485 | False: 40 |

## Per episode

| Board # | Group | Task | v3 + JPEG (11 Nov, H100) | v3, raw frames (11 Nov, H100) | v3 (10 Nov) | v4 (10 Nov) | v6 (10 Nov) | v5-touch (10 Nov) | Board v3 |
|---|---|---|---|---|---|---|---|---|---|
| 16 | Close, normal | close the drawer. | OK 1.9 s | - | OK 2.3 s | OK 1.4 s | OK 5.0 s | OK 6.9 s | OK |
| 36 | Close, normal | close the drawer. | OK 9.7 s | - | OK 3.0 s | OK 9.9 s | OK 7.7 s | OK 8.1 s | OK |
| 46 | Close, normal | close the drawer. | OK 1.6 s | - | OK 1.5 s | OK 1.5 s | OK 11.6 s | no | OK |
| 56 | Close, normal | close the table. | OK 3.6 s | OK 2.4 s | OK 1.8 s | OK 1.8 s | OK 6.7 s | OK 6.7 s | OK |
| 76 | Close, normal | close the drawer. | OK 1.5 s | - | no | no | OK 5.9 s | OK 10.6 s | no |
| 19 | Close, hard | close the table. | no | OK 20.9 s | OK 11.7 s | OK 6.8 s | no | no | OK |
| 49 | Close, hard | close the brown wooden desk. | OK 9.2 s | - | OK 7.7 s | OK 7.2 s | no | OK 14.9 s | OK |
| 59 | Close, hard | close the white dresser. | OK 7.0 s | OK 4.1 s | OK 7.9 s | OK 3.4 s | OK 6.6 s | OK 7.6 s | OK |
| 109 | Close, hard | close the dresser. | no | - | no | OK 16.5 s | OK 8.4 s | OK 7.3 s | no |
| 129 | Close, hard | close the dresser. | OK 26.4 s | - | OK 19.1 s | OK 6.7 s | no | no | no |
| 37 | Open, normal | open the desk. | no | - | OK 6.0 s | no | OK 10.8 s | OK 11.7 s | no |
| 57 | Open, normal | open the dresser. | no | - | no | no | no | OK 29.6 s | no |
| 107 | Open, normal | open the dresser. | OK 19.8 s | - | no | OK 2.8 s | no | OK 7.3 s | OK |
| 117 | Open, normal | open the dresser. | no | - | OK 25.5 s | no | OK 10.5 s | no | no |
| 127 | Open, normal | open the table. | OK 9.5 s | no | OK 4.3 s | OK 7.1 s | no | OK 18.7 s | OK |
| 28 | Open, hard | open the wooden table. | no | - | no | no | no | no | no |
| 38 | Open, hard | open the wooden table. | OK 8.1 s | - | OK 13.7 s | OK 10.6 s | OK 7.5 s | no | OK |
| 48 | Open, hard | open the desk. | no | - | no | no | no | no | no |
| 68 | Open, hard | open the wooden table. | no | - | no | no | no | no | no |
| 128 | Open, hard | open the dresser. | no | - | no | no | no | no | no |
| 12 | Pick, hard | pick up the brown pinecone keychain. | OK 15.0 s | - | OK 16.5 s | OK 13.8 s | OK 17.3 s | OK 16.6 s | OK |
| 32 | Pick, hard | pick up the comb. | OK 16.4 s | - | no | OK 15.3 s | OK 16.7 s | no | OK |
| 42 | Pick, hard | pick up the mechanism. | no | - | OK 17.9 s | no | no | no | OK |
| 122 | Pick, hard | pick up the bottle. | OK 13.5 s | - | OK 10.1 s | OK 10.5 s | OK 9.0 s | OK 16.5 s | OK |
| 132 | Pick, hard | pick up the kettle. | OK 10.0 s | - | OK 4.3 s | OK 6.8 s | OK 5.6 s | OK 6.9 s | OK |
| 178 | Pick, hard | pick up the cup. | no | no | OK 16.5 s | OK 14.4 s | OK 14.1 s | OK 14.8 s | OK |
| 214 | Pick, hard | pick up the screwdriver. | OK 11.6 s | - | OK 8.8 s | OK 8.8 s | OK 9.2 s | OK 13.6 s | OK |
| 218 | Pick, hard | pick up the egg. | no | - | no | OK 11.0 s | no | no | OK |
| 226 | Pick, hard | pick up the grenade. | OK 7.7 s | - | no | OK 9.0 s | OK 11.3 s | OK 10.0 s | OK |
| 234 | Pick, hard | pick up the juicer. | OK 16.8 s | - | OK 7.5 s | no | OK 11.7 s | no | OK |
| 242 | Pick, hard | pick up the red skull key. | OK 14.9 s | - | OK 12.2 s | OK 9.2 s | OK 10.8 s | OK 18.3 s | OK |
| 274 | Pick, hard | pick up the brown potato. | OK 17.2 s | - | OK 10.4 s | OK 14.1 s | OK 16.0 s | OK 18.9 s | OK |
| 282 | Pick, hard | pick up the small red potato. | OK 9.5 s | - | OK 12.1 s | OK 8.8 s | OK 11.3 s | OK 10.3 s | OK |
| 298 | Pick, hard | pick up the white stopwatch. | no | - | no | OK 8.8 s | OK 10.0 s | no | OK |
| 41 | Pick and place, normal | pick up the shaker and place it on the bowl. | OK 22.0 s | OK 27.1 s | OK 11.0 s | OK 10.4 s | OK 14.1 s | OK 17.6 s | OK |
| 71 | Pick and place, normal | pick up the bottle and place it on the bowl. | OK 18.6 s | - | OK 12.7 s | OK 12.7 s | OK 12.9 s | OK 16.8 s | OK |
| 177 | Pick and place, normal | pick up the mug and place it on the bowl. | OK 10.1 s | - | OK 9.9 s | OK 9.6 s | OK 9.7 s | OK 11.6 s | OK |
| 197 | Pick and place, normal | pick up the knife and place it on the bowl. | no | - | no | no | no | no | OK |
| 209 | Pick and place, normal | pick up the shaker and place it on the bowl. | OK 11.7 s | - | OK 9.8 s | OK 10.2 s | OK 10.1 s | OK 12.3 s | OK |
| 221 | Pick and place, normal | pick up the ladle and place it on the bowl. | OK 18.3 s | - | OK 20.5 s | OK 19.3 s | OK 16.2 s | OK 24.2 s | OK |
