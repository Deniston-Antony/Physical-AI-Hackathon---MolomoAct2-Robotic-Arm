# FLUX 3 Action: fewer denoising steps (GD model)

17 Nov: the GD model (trained for 4 denoising steps) run with 4, 2 and 1 steps. All runs use both cameras, hybrid schedule (stop-and-think for pick, continuous for others), full gripper command, 24192 MiB GPU cap, text encoder on CPU. 40 episodes, 4 eval processes at a time. Fewer steps should be faster (fewer forward passes through the DiT) but may lose quality.

| Group | Episodes | FLUX hybrid, 4 steps (baseline) | FLUX hybrid, 2 steps | FLUX hybrid, 1 step | Best prev FLUX (hybrid, 4 steps) | v3 + JPEG (board) | Board v3 |
|---|---|---|---|---|---|---|---|
| Pick, hard | 14 | 3 | 3 | 4 | 4 | 10 | 14 |
| Pick and place, normal | 6 | 1 | 2 | 0 | 2 | 5 | 6 |
| Open, normal | 5 | 3 | 2 | 1 | 3 | 2 | 2 |
| Open, hard | 5 | 3 | 1 | 1 | 1 | 1 | 1 |
| Close, normal | 5 | 5 | 5 | 5 | 5 | 5 | 4 |
| Close, hard | 5 | 5 | 5 | 5 | 5 | 3 | 3 |
| **All** | 40 | 20 | 18 | 16 | 20 | 26 | 30 |

## Time

| Run | Calls per episode | Charged median (ms) | Actions per call | Moving per episode (s) | Still per episode (s) | Median success time (s) |
|---|---|---|---|---|---|---|
| FLUX hybrid, 4 steps (baseline) | 9.7 | 755 | 22.9 | 14.8 | 0.0 | 9.6 |
| FLUX hybrid, 2 steps | 11.0 | 398 | 22.6 | 16.6 | 0.0 | 10.2 |
| FLUX hybrid, 1 step | 11.6 | 225 | 22.7 | 17.5 | 0.0 | 7.4 |
| Best prev FLUX (hybrid, 4 steps) | 10.8 | 911 | 22.7 | 16.3 | 0.1 | 7.9 |
| v3 + JPEG (board) | 18.1 | 322 | 11.3 | 13.6 | 5.8 | 10.8 |

- fluxhyb4: left shoulder camera in 20 sessions, right in 20; the still-arm rule gave the pick part in 0 sessions; 0 OOM errors.
- fluxhyb2: left shoulder camera in 20 sessions, right in 20; the still-arm rule gave the pick part in 0 sessions; 0 OOM errors; overrode num_inference_steps: 4 -> 2.
- fluxhyb1: left shoulder camera in 28 sessions, right in 12; the still-arm rule gave the pick part in 1 sessions; 0 OOM errors; overrode num_inference_steps: 4 -> 1.

## Per episode

| Board # | Group | Task | FLUX hybrid, 4 steps (baseline) | FLUX hybrid, 2 steps | FLUX hybrid, 1 step | Best prev FLUX (hybrid, 4 steps) | v3 + JPEG (board) | Board v3 |
|---|---|---|---|---|---|---|---|---|
| 16 | Close, normal | close the drawer. | OK 3.6 s | OK 3.6 s | OK 2.5 s | OK 2.6 s | OK 1.9 s | OK |
| 36 | Close, normal | close the drawer. | OK 2.6 s | OK 2.0 s | OK 2.9 s | OK 5.2 s | OK 9.7 s | OK |
| 46 | Close, normal | close the drawer. | OK 4.4 s | OK 3.2 s | OK 1.5 s | OK 3.9 s | OK 1.6 s | OK |
| 56 | Close, normal | close the table. | OK 3.7 s | OK 6.7 s | OK 3.1 s | OK 5.6 s | OK 3.6 s | OK |
| 76 | Close, normal | close the drawer. | OK 6.8 s | OK 9.6 s | OK 6.8 s | OK 3.7 s | OK 1.5 s | no |
| 19 | Close, hard | close the table. | OK 6.0 s | OK 5.6 s | OK 5.3 s | OK 4.5 s | no | OK |
| 49 | Close, hard | close the brown wooden desk. | OK 9.5 s | OK 10.8 s | OK 9.0 s | OK 6.1 s | OK 9.2 s | OK |
| 59 | Close, hard | close the white dresser. | OK 6.1 s | OK 5.3 s | OK 5.0 s | OK 2.6 s | OK 7.0 s | OK |
| 109 | Close, hard | close the dresser. | OK 1.9 s | OK 1.3 s | OK 1.1 s | OK 3.2 s | no | no |
| 129 | Close, hard | close the dresser. | OK 9.7 s | OK 8.1 s | OK 7.9 s | OK 5.1 s | OK 26.4 s | no |
| 37 | Open, normal | open the desk. | no | no | no | OK 24.8 s | no | no |
| 57 | Open, normal | open the dresser. | OK 19.8 s | OK 16.8 s | no | no | no | no |
| 107 | Open, normal | open the dresser. | OK 7.6 s | no | no | OK 15.0 s | OK 19.8 s | OK |
| 117 | Open, normal | open the dresser. | OK 14.4 s | OK 12.1 s | OK 12.5 s | no | no | no |
| 127 | Open, normal | open the table. | no | no | no | OK 13.7 s | OK 9.5 s | OK |
| 28 | Open, hard | open the wooden table. | OK 27.6 s | no | no | no | no | no |
| 38 | Open, hard | open the wooden table. | no | no | no | no | OK 8.1 s | OK |
| 48 | Open, hard | open the desk. | no | no | no | no | no | no |
| 68 | Open, hard | open the wooden table. | OK 11.2 s | no | no | OK 18.0 s | no | no |
| 128 | Open, hard | open the dresser. | OK 13.8 s | OK 27.1 s | OK 18.6 s | no | no | no |
| 12 | Pick, hard | pick up the brown pinecone keychain. | no | no | no | no | OK 15.0 s | OK |
| 32 | Pick, hard | pick up the comb. | OK 17.8 s | no | OK 15.8 s | no | OK 16.4 s | OK |
| 42 | Pick, hard | pick up the mechanism. | no | no | OK 19.0 s | no | no | OK |
| 122 | Pick, hard | pick up the bottle. | OK 19.4 s | OK 17.0 s | OK 14.5 s | no | OK 13.5 s | OK |
| 132 | Pick, hard | pick up the kettle. | no | no | no | OK 10.6 s | OK 10.0 s | OK |
| 178 | Pick, hard | pick up the cup. | no | OK 13.3 s | no | no | no | OK |
| 214 | Pick, hard | pick up the screwdriver. | no | no | no | no | OK 11.6 s | OK |
| 218 | Pick, hard | pick up the egg. | no | no | no | no | no | OK |
| 226 | Pick, hard | pick up the grenade. | OK 14.9 s | OK 16.3 s | OK 14.3 s | OK 13.9 s | OK 7.7 s | OK |
| 234 | Pick, hard | pick up the juicer. | no | no | no | no | OK 16.8 s | OK |
| 242 | Pick, hard | pick up the red skull key. | no | no | no | no | OK 14.9 s | OK |
| 274 | Pick, hard | pick up the brown potato. | no | no | no | no | OK 17.2 s | OK |
| 282 | Pick, hard | pick up the small red potato. | no | no | no | OK 12.3 s | OK 9.5 s | OK |
| 298 | Pick, hard | pick up the white stopwatch. | no | no | no | OK 9.6 s | no | OK |
| 41 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | OK 22.7 s | no | OK 35.8 s | OK 22.0 s | OK |
| 71 | Pick and place, normal | pick up the bottle and place it on the bowl. | no | no | no | no | OK 18.6 s | OK |
| 177 | Pick and place, normal | pick up the mug and place it on the bowl. | no | no | no | no | OK 10.1 s | OK |
| 197 | Pick and place, normal | pick up the knife and place it on the bowl. | no | OK 31.9 s | no | OK 21.4 s | no | OK |
| 209 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | no | no | no | OK 11.7 s | OK |
| 221 | Pick and place, normal | pick up the ladle and place it on the bowl. | OK 35.4 s | no | no | no | OK 18.3 s | OK |
