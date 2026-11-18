# FLUX 3 Action at 1 denoising step: faster timing and a retry after a miss

18 Nov: FLUX at 1 denoising step, both cameras, hybrid schedule, full gripper, 24192 MiB cap. "Faster timing": the next request 0.35 s before the end of a chunk (was 0.9 s) and the arm holds 6 actions after a pick chunk (was 14); a pick chunk that keeps the gripper open plays 1.25x faster. "Retry": a close on nothing opens the gripper and lifts it 5 cm; the next close near the miss goes 2 cm deeper (the 2nd retry also turns the gripper 30 deg); at most 2 retries per episode.

| Group | Episodes | FLUX 1 step, faster timing | FLUX 1 step, faster + retry | FLUX 1 step (17 Nov) | FLUX 4 steps (17 Nov) | v3 + JPEG | Board v3 |
|---|---|---|---|---|---|---|---|
| Pick, hard | 14 | 3 | 5 | 4 | 3 | 10 | 14 |
| Pick and place, normal | 6 | 0 | 2 | 0 | 1 | 5 | 6 |
| Open, normal | 5 | 1 | 1 | 1 | 3 | 2 | 2 |
| Open, hard | 5 | 2 | 0 | 1 | 3 | 1 | 1 |
| Close, normal | 5 | 5 | 5 | 5 | 5 | 5 | 4 |
| Close, hard | 5 | 5 | 5 | 5 | 5 | 3 | 3 |
| **All** | 40 | 16 | 18 | 16 | 20 | 26 | 30 |

## Time

| Run | Calls per episode | Charged median (ms) | Actions per call | Moving per episode (s) | Still per episode (s) | Median success time (s) |
|---|---|---|---|---|---|---|
| FLUX 1 step, faster timing | 13.1 | 211 | 21.4 | 18.7 | 0.0 | 4.0 |
| FLUX 1 step, faster + retry | 12.9 | 213 | 21.5 | 18.5 | 0.0 | 5.1 |
| FLUX 1 step (17 Nov) | 11.6 | 225 | 22.7 | 17.5 | 0.0 | 7.4 |
| FLUX 4 steps (17 Nov) | 9.7 | 755 | 22.9 | 14.8 | 0.0 | 9.6 |
| v3 + JPEG | 18.1 | 322 | 11.3 | 13.6 | 5.8 | 10.8 |

- ffast1: rule counts {'miss lifts': 0, 'changed closes': 0, 'fast chunks': 143}  ; left shoulder camera in 20 sessions, right in 20; the still-arm rule gave the pick part in 2 sessions; 0 OOM errors; overrode num_inference_steps: 4 -> 1.
- fretry1: rule counts {'miss lifts': 14, 'changed closes': 8, 'fast chunks': 124} ; left shoulder camera in 20 sessions, right in 20; the still-arm rule gave the pick part in 1 sessions; 0 OOM errors; overrode num_inference_steps: 4 -> 1.

## Per episode

| Board # | Group | Task | FLUX 1 step, faster timing | FLUX 1 step, faster + retry | FLUX 1 step (17 Nov) | FLUX 4 steps (17 Nov) | v3 + JPEG | Board v3 |
|---|---|---|---|---|---|---|---|---|
| 16 | Close, normal | close the drawer. | OK 2.4 s | OK 3.2 s | OK 2.5 s | OK 3.6 s | OK 1.9 s | OK |
| 36 | Close, normal | close the drawer. | OK 3.2 s | OK 3.0 s | OK 2.9 s | OK 2.6 s | OK 9.7 s | OK |
| 46 | Close, normal | close the drawer. | OK 1.5 s | OK 1.5 s | OK 1.5 s | OK 4.4 s | OK 1.6 s | OK |
| 56 | Close, normal | close the table. | OK 2.3 s | OK 2.3 s | OK 3.1 s | OK 3.7 s | OK 3.6 s | OK |
| 76 | Close, normal | close the drawer. | OK 3.7 s | OK 3.9 s | OK 6.8 s | OK 6.8 s | OK 1.5 s | no |
| 19 | Close, hard | close the table. | OK 2.4 s | OK 2.2 s | OK 5.3 s | OK 6.0 s | no | OK |
| 49 | Close, hard | close the brown wooden desk. | OK 4.6 s | OK 4.5 s | OK 9.0 s | OK 9.5 s | OK 9.2 s | OK |
| 59 | Close, hard | close the white dresser. | OK 2.0 s | OK 2.0 s | OK 5.0 s | OK 6.1 s | OK 7.0 s | OK |
| 109 | Close, hard | close the dresser. | OK 1.5 s | OK 1.3 s | OK 1.1 s | OK 1.9 s | no | no |
| 129 | Close, hard | close the dresser. | OK 5.0 s | OK 5.8 s | OK 7.9 s | OK 9.7 s | OK 26.4 s | no |
| 37 | Open, normal | open the desk. | no | no | no | no | no | no |
| 57 | Open, normal | open the dresser. | no | no | no | OK 19.8 s | no | no |
| 107 | Open, normal | open the dresser. | OK 4.4 s | no | no | OK 7.6 s | OK 19.8 s | OK |
| 117 | Open, normal | open the dresser. | no | OK 13.0 s | OK 12.5 s | OK 14.4 s | no | no |
| 127 | Open, normal | open the table. | no | no | no | no | OK 9.5 s | OK |
| 28 | Open, hard | open the wooden table. | no | no | no | OK 27.6 s | no | no |
| 38 | Open, hard | open the wooden table. | OK 12.3 s | no | no | no | OK 8.1 s | OK |
| 48 | Open, hard | open the desk. | no | no | no | no | no | no |
| 68 | Open, hard | open the wooden table. | no | no | no | OK 11.2 s | no | no |
| 128 | Open, hard | open the dresser. | OK 11.2 s | no | OK 18.6 s | OK 13.8 s | no | no |
| 12 | Pick, hard | pick up the brown pinecone keychain. | no | no | no | no | OK 15.0 s | OK |
| 32 | Pick, hard | pick up the comb. | OK 7.8 s | OK 7.7 s | OK 15.8 s | OK 17.8 s | OK 16.4 s | OK |
| 42 | Pick, hard | pick up the mechanism. | no | no | OK 19.0 s | no | no | OK |
| 122 | Pick, hard | pick up the bottle. | OK 9.7 s | OK 8.3 s | OK 14.5 s | OK 19.4 s | OK 13.5 s | OK |
| 132 | Pick, hard | pick up the kettle. | no | OK 8.5 s | no | no | OK 10.0 s | OK |
| 178 | Pick, hard | pick up the cup. | no | no | no | no | no | OK |
| 214 | Pick, hard | pick up the screwdriver. | no | no | no | no | OK 11.6 s | OK |
| 218 | Pick, hard | pick up the egg. | no | no | no | no | no | OK |
| 226 | Pick, hard | pick up the grenade. | OK 7.6 s | OK 7.5 s | OK 14.3 s | OK 14.9 s | OK 7.7 s | OK |
| 234 | Pick, hard | pick up the juicer. | no | no | no | no | OK 16.8 s | OK |
| 242 | Pick, hard | pick up the red skull key. | no | OK 7.9 s | no | no | OK 14.9 s | OK |
| 274 | Pick, hard | pick up the brown potato. | no | no | no | no | OK 17.2 s | OK |
| 282 | Pick, hard | pick up the small red potato. | no | no | no | no | OK 9.5 s | OK |
| 298 | Pick, hard | pick up the white stopwatch. | no | no | no | no | no | OK |
| 41 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | no | no | no | OK 22.0 s | OK |
| 71 | Pick and place, normal | pick up the bottle and place it on the bowl. | no | OK 23.4 s | no | no | OK 18.6 s | OK |
| 177 | Pick and place, normal | pick up the mug and place it on the bowl. | no | no | no | no | OK 10.1 s | OK |
| 197 | Pick and place, normal | pick up the knife and place it on the bowl. | no | no | no | no | no | OK |
| 209 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | OK 38.5 s | no | no | OK 11.7 s | OK |
| 221 | Pick and place, normal | pick up the ladle and place it on the bowl. | no | no | no | OK 35.4 s | OK 18.3 s | OK |
