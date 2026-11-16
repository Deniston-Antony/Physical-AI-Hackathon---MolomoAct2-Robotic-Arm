# FLUX 3 Action DROID with the v3 rules and a schedule for the delay of a FLUX call

13 Nov: all FLUX runs are in the 24192 MiB GPU memory of a competition run, with 4 eval processes at a time on the 40 episodes of the tests of 10 and 11 Nov. "FLUX + v3 rules" has the v3 schedule: 0.77 s of each chunk, the next request 0.2 s before the end, the first 4 actions of later chunks dropped. A FLUX call takes about 0.85 s, so the robot stood still for about 0.65 s after each chunk. "Fixed schedule" requests the next chunk 0.9 s before the end, plays 1.23 s of each chunk, and drops the first 13 actions (0.87 s) of later chunks. "FLUX as published" plays each chunk of 32 actions whole and requests at the end.

| Group | Episodes | FLUX + v3 rules, fixed schedule | FLUX + v3 rules | FLUX as published | v3 + JPEG (11 Nov, H100) | v3 (10 Nov, L40S) | Board v3 |
|---|---|---|---|---|---|---|---|
| Pick, hard | 14 | 0 | 3 | 3 | 10 | 10 | 14 |
| Pick and place, normal | 6 | 0 | 1 | 0 | 5 | 5 | 6 |
| Open, normal | 5 | 2 | 0 | 1 | 2 | 3 | 2 |
| Open, hard | 5 | 3 | 0 | 2 | 1 | 1 | 1 |
| Close, normal | 5 | 5 | 5 | 5 | 5 | 4 | 4 |
| Close, hard | 5 | 4 | 4 | 4 | 3 | 4 | 3 |
| **All** | 40 | 14 | 13 | 15 | 26 | 27 | 30 |

## Time

"Charged" is the time of a model call as the harness measures it. "Still" is an estimate: the calls of an episode times the part of the charged time that the lead of the schedule does not cover.

| Image | Calls per episode | Charged, median of the streams (ms) | Actions played per call | Moving per episode (s) | Still per episode (s) | Median time of a success (s) |
|---|---|---|---|---|---|---|
| FLUX + v3 rules, fixed schedule | 15.5 | 738 | 17.2 | 17.8 | 0.0 | 5.8 |
| FLUX + v3 rules | 15.1 | 852 | 11.3 | 11.4 | 9.9 | 11.1 |
| FLUX as published | 7.2 | 756 | 29.8 | 14.4 | 5.5 | 6.7 |
| v3 + JPEG (11 Nov, H100) | 18.1 | 322 | 11.3 | 13.6 | - | 10.8 |
| v3 (10 Nov, L40S) | 18.9 | 232 | 11.5 | 14.4 | - | 10.1 |

Fixed schedule: left shoulder camera in 10 sessions, right in 30; the still-arm rule gave the pick part in 0 sessions; 0 out-of-memory errors.

## Per episode

| Board # | Group | Task | FLUX + v3 rules, fixed schedule | FLUX + v3 rules | FLUX as published | v3 + JPEG (11 Nov, H100) | v3 (10 Nov, L40S) | Board v3 |
|---|---|---|---|---|---|---|---|---|
| 16 | Close, normal | close the drawer. | OK 1.8 s | OK 2.6 s | OK 2.0 s | OK 1.9 s | OK 2.3 s | OK |
| 36 | Close, normal | close the drawer. | OK 5.3 s | OK 27.1 s | OK 13.3 s | OK 9.7 s | OK 3.0 s | OK |
| 46 | Close, normal | close the drawer. | OK 2.0 s | OK 1.8 s | OK 3.1 s | OK 1.6 s | OK 1.5 s | OK |
| 56 | Close, normal | close the table. | OK 5.7 s | OK 4.4 s | OK 4.1 s | OK 3.6 s | OK 1.8 s | OK |
| 76 | Close, normal | close the drawer. | OK 4.8 s | OK 12.0 s | OK 6.7 s | OK 1.5 s | no | no |
| 19 | Close, hard | close the table. | OK 2.6 s | OK 7.5 s | OK 2.4 s | no | OK 11.7 s | OK |
| 49 | Close, hard | close the brown wooden desk. | OK 5.9 s | OK 13.1 s | OK 5.6 s | OK 9.2 s | OK 7.7 s | OK |
| 59 | Close, hard | close the white dresser. | no | no | no | OK 7.0 s | OK 7.9 s | OK |
| 109 | Close, hard | close the dresser. | OK 1.3 s | OK 2.3 s | OK 2.2 s | no | no | no |
| 129 | Close, hard | close the dresser. | OK 6.3 s | OK 7.6 s | OK 17.2 s | OK 26.4 s | OK 19.1 s | no |
| 37 | Open, normal | open the desk. | no | no | no | no | OK 6.0 s | no |
| 57 | Open, normal | open the dresser. | no | no | no | no | no | no |
| 107 | Open, normal | open the dresser. | OK 6.1 s | no | OK 15.0 s | OK 19.8 s | no | OK |
| 117 | Open, normal | open the dresser. | OK 18.0 s | no | no | no | OK 25.5 s | no |
| 127 | Open, normal | open the table. | no | no | no | OK 9.5 s | OK 4.3 s | OK |
| 28 | Open, hard | open the wooden table. | OK 19.1 s | no | no | no | no | no |
| 38 | Open, hard | open the wooden table. | OK 15.9 s | no | OK 7.9 s | OK 8.1 s | OK 13.7 s | OK |
| 48 | Open, hard | open the desk. | OK 6.4 s | no | no | no | no | no |
| 68 | Open, hard | open the wooden table. | no | no | no | no | no | no |
| 128 | Open, hard | open the dresser. | no | no | OK 5.7 s | no | no | no |
| 12 | Pick, hard | pick up the brown pinecone keychain. | no | no | no | OK 15.0 s | OK 16.5 s | OK |
| 32 | Pick, hard | pick up the comb. | no | no | OK 11.2 s | OK 16.4 s | no | OK |
| 42 | Pick, hard | pick up the mechanism. | no | OK 14.8 s | no | no | OK 17.9 s | OK |
| 122 | Pick, hard | pick up the bottle. | no | no | no | OK 13.5 s | OK 10.1 s | OK |
| 132 | Pick, hard | pick up the kettle. | no | OK 12.7 s | no | OK 10.0 s | OK 4.3 s | OK |
| 178 | Pick, hard | pick up the cup. | no | OK 11.1 s | OK 10.5 s | no | OK 16.5 s | OK |
| 214 | Pick, hard | pick up the screwdriver. | no | no | no | OK 11.6 s | OK 8.8 s | OK |
| 218 | Pick, hard | pick up the egg. | no | no | OK 14.0 s | no | no | OK |
| 226 | Pick, hard | pick up the grenade. | no | no | no | OK 7.7 s | no | OK |
| 234 | Pick, hard | pick up the juicer. | no | no | no | OK 16.8 s | OK 7.5 s | OK |
| 242 | Pick, hard | pick up the red skull key. | no | no | no | OK 14.9 s | OK 12.2 s | OK |
| 274 | Pick, hard | pick up the brown potato. | no | no | no | OK 17.2 s | OK 10.4 s | OK |
| 282 | Pick, hard | pick up the small red potato. | no | no | no | OK 9.5 s | OK 12.1 s | OK |
| 298 | Pick, hard | pick up the white stopwatch. | no | no | no | no | no | OK |
| 41 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | no | no | OK 22.0 s | OK 11.0 s | OK |
| 71 | Pick and place, normal | pick up the bottle and place it on the bowl. | no | no | no | OK 18.6 s | OK 12.7 s | OK |
| 177 | Pick and place, normal | pick up the mug and place it on the bowl. | no | no | no | OK 10.1 s | OK 9.9 s | OK |
| 197 | Pick and place, normal | pick up the knife and place it on the bowl. | no | no | no | no | no | OK |
| 209 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | no | no | OK 11.7 s | OK 9.8 s | OK |
| 221 | Pick and place, normal | pick up the ladle and place it on the bowl. | no | OK 29.8 s | no | OK 18.3 s | OK 20.5 s | OK |
