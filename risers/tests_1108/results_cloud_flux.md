# FLUX 3 Action DROID in the 24 GB of a competition run, as published and with the v3 rules

12 Nov: cloud VM with an L40S GPU. The public image `positro/flux3-action` serves FLUX 3 Action DROID with 4 eval processes at a time, as the board does, on the 40 episodes of the tests of 10 and 11 Nov. In the "24 GB" runs (13 Nov), the GPU memory of FLUX is capped at the 24192 MiB slice of a competition run, its text encoder stays on the CPU and encodes there, its DiT is packed in place (BFL's own packing needs about 9 GB more and does not fit), and the container has 14 CPUs, as a competition run has. The published image keeps the text encoder on the GPU and uses about 27 GB. "FLUX, 24 GB" otherwise serves as published: `image.exterior` in both exterior slots, and each chunk of 32 actions played whole. "FLUX + v3 rules, 24 GB" adds the rules of v3: the left shoulder camera in both slots, the pick part of a pick-and-place task while the open arm is still for 3 calls, and the v3 schedule (0.77 s of each chunk, the next request 0.2 s before the end, the first 4 actions of later chunks dropped). "FLUX, no cap" is the published image with no cap; it was stopped early, when the cap was asked for. The v3 columns are MolmoBot v3 on the same episodes.

| Group | Episodes | FLUX, 24 GB | FLUX + v3 rules, 24 GB | FLUX, no cap (stopped early) | v3 + JPEG (11 Nov, H100) | v3 (10 Nov, L40S) | Board v3 |
|---|---|---|---|---|---|---|---|
| Pick, hard | 14 | 3 | 3 | 0 (3 done) | 10 | 10 | 14 |
| Pick and place, normal | 6 | 0 | 1 | 0 (2 done) | 5 | 5 | 6 |
| Open, normal | 5 | 1 | 0 | 4 (4 done) | 2 | 3 | 2 |
| Open, hard | 5 | 2 | 0 | 1 (2 done) | 1 | 1 | 1 |
| Close, normal | 5 | 5 | 5 | 4 | 5 | 4 | 4 |
| Close, hard | 5 | 4 | 4 | 4 | 3 | 4 | 3 |
| **All** | 40 | 15 | 13 | 13 (21 done) | 26 | 27 | 30 |

## Time per model call

"Charged" is the time of a model call as the harness measures it: the robot waits this long.

| Image | Calls | Charged p50 per stream (ms) | Median of the streams (ms) | Median time of a success (s) |
|---|---|---|---|---|
| FLUX, 24 GB | 290 | 705, 807, 700, 1019 | 756 | 6.7 |
| FLUX + v3 rules, 24 GB | 605 | 838, 866, 839, 996 | 852 | 11.1 |
| FLUX, no cap (stopped early) | 133 | 736, 744, 732, 734 | 735 | 4.9 |
| v3 + JPEG (11 Nov, H100) | 723 | 689, 284, 330, 322, 290 | 322 | 10.8 |
| v3 (10 Nov, L40S) | 756 | 232, 235, 231, 232 | 232 | 10.1 |

## Rules of v3 in the FLUX server

- Sessions where `image.exterior` was the left shoulder camera: 38; the right: 2.
- Sessions where the still-arm rule gave the pick part of the task: 0.

## GPU memory: does FLUX fit the 24 GB of a competition run?

- RESULT: FLUX starts in the 24192 MiB slice with the text encode on the cpu
- [fluxa24] DONE: 40 episodes, 0 out-of-memory lines in the server log
- [fluxv3] DONE: 40 episodes, 0 out-of-memory lines in the server log

A competition run gets 24192 MiB of GPU memory. The VM samples the memory every 2 s.

| Run | Peak of the FLUX process (MiB) | Peak of the whole GPU, with the simulators (MiB) |
|---|---|---|
| fluxa24 | 19084 | 29879 |
| fluxv3 | 19084 | 29583 |

The memory that the FLUX process reported (PyTorch):

- slice 24192 MiB, CUDA context 687 MiB, PyTorch cap 22993 MiB
- text encode on the cpu, 8 CPU threads
- after the DiT packing: device used 16421 MiB, allocated 15637 MiB, reserved 15734 MiB, peak reserved 15896 MiB
- after the compile: device used 16421 MiB, allocated 15637 MiB, reserved 15734 MiB, peak reserved 15896 MiB
- after an instruction encode: device used 16729 MiB, allocated 15644 MiB, reserved 15966 MiB, peak reserved 15966 MiB
- after the load and the warm-up: device used 18925 MiB, allocated 15633 MiB, reserved 16278 MiB, peak reserved 16862 MiB
- after an instruction encode: device used 18945 MiB, allocated 15643 MiB, reserved 16294 MiB, peak reserved 16312 MiB
- after an instruction encode: device used 21957 MiB, allocated 15749 MiB, reserved 16438 MiB, peak reserved 16438 MiB
- after an instruction encode: device used 21957 MiB, allocated 15749 MiB, reserved 16438 MiB, peak reserved 16438 MiB
- after an instruction encode: device used 21957 MiB, allocated 15749 MiB, reserved 16438 MiB, peak reserved 16438 MiB
- slice 24192 MiB, CUDA context 687 MiB, PyTorch cap 22993 MiB
- text encode on the cpu, 8 CPU threads
- after the DiT packing: device used 16421 MiB, allocated 15637 MiB, reserved 15734 MiB, peak reserved 15896 MiB
- after the compile: device used 16421 MiB, allocated 15637 MiB, reserved 15734 MiB, peak reserved 15896 MiB
- after an instruction encode: device used 16729 MiB, allocated 15644 MiB, reserved 15966 MiB, peak reserved 15966 MiB
- after the load and the warm-up: device used 18925 MiB, allocated 15633 MiB, reserved 16278 MiB, peak reserved 16862 MiB
- after an instruction encode: device used 18945 MiB, allocated 15643 MiB, reserved 16294 MiB, peak reserved 16312 MiB
- after an instruction encode: device used 21957 MiB, allocated 15749 MiB, reserved 16438 MiB, peak reserved 16438 MiB
- after an instruction encode: device used 21957 MiB, allocated 15749 MiB, reserved 16438 MiB, peak reserved 16438 MiB
- after an instruction encode: device used 21957 MiB, allocated 15749 MiB, reserved 16438 MiB, peak reserved 16438 MiB

## Per episode

| Board # | Group | Task | FLUX, 24 GB | FLUX + v3 rules, 24 GB | FLUX, no cap (stopped early) | v3 + JPEG (11 Nov, H100) | v3 (10 Nov, L40S) | Board v3 |
|---|---|---|---|---|---|---|---|---|
| 16 | Close, normal | close the drawer. | OK 2.0 s | OK 2.6 s | OK 3.0 s | OK 1.9 s | OK 2.3 s | OK |
| 36 | Close, normal | close the drawer. | OK 13.3 s | OK 27.1 s | OK 2.1 s | OK 9.7 s | OK 3.0 s | OK |
| 46 | Close, normal | close the drawer. | OK 3.1 s | OK 1.8 s | OK 1.7 s | OK 1.6 s | OK 1.5 s | OK |
| 56 | Close, normal | close the table. | OK 4.1 s | OK 4.4 s | OK 1.9 s | OK 3.6 s | OK 1.8 s | OK |
| 76 | Close, normal | close the drawer. | OK 6.7 s | OK 12.0 s | no | OK 1.5 s | no | no |
| 19 | Close, hard | close the table. | OK 2.4 s | OK 7.5 s | no | no | OK 11.7 s | OK |
| 49 | Close, hard | close the brown wooden desk. | OK 5.6 s | OK 13.1 s | OK 4.9 s | OK 9.2 s | OK 7.7 s | OK |
| 59 | Close, hard | close the white dresser. | no | no | OK 17.2 s | OK 7.0 s | OK 7.9 s | OK |
| 109 | Close, hard | close the dresser. | OK 2.2 s | OK 2.3 s | OK 1.3 s | no | no | no |
| 129 | Close, hard | close the dresser. | OK 17.2 s | OK 7.6 s | OK 13.1 s | OK 26.4 s | OK 19.1 s | no |
| 37 | Open, normal | open the desk. | no | no | - | no | OK 6.0 s | no |
| 57 | Open, normal | open the dresser. | no | no | OK 18.0 s | no | no | no |
| 107 | Open, normal | open the dresser. | OK 15.0 s | no | OK 2.4 s | OK 19.8 s | no | OK |
| 117 | Open, normal | open the dresser. | no | no | OK 10.9 s | no | OK 25.5 s | no |
| 127 | Open, normal | open the table. | no | no | OK 7.7 s | OK 9.5 s | OK 4.3 s | OK |
| 28 | Open, hard | open the wooden table. | no | no | - | no | no | no |
| 38 | Open, hard | open the wooden table. | OK 7.9 s | no | OK 13.3 s | OK 8.1 s | OK 13.7 s | OK |
| 48 | Open, hard | open the desk. | no | no | no | no | no | no |
| 68 | Open, hard | open the wooden table. | no | no | - | no | no | no |
| 128 | Open, hard | open the dresser. | OK 5.7 s | no | - | no | no | no |
| 12 | Pick, hard | pick up the brown pinecone keychain. | no | no | - | OK 15.0 s | OK 16.5 s | OK |
| 32 | Pick, hard | pick up the comb. | OK 11.2 s | no | - | OK 16.4 s | no | OK |
| 42 | Pick, hard | pick up the mechanism. | no | OK 14.8 s | no | no | OK 17.9 s | OK |
| 122 | Pick, hard | pick up the bottle. | no | no | - | OK 13.5 s | OK 10.1 s | OK |
| 132 | Pick, hard | pick up the kettle. | no | OK 12.7 s | - | OK 10.0 s | OK 4.3 s | OK |
| 178 | Pick, hard | pick up the cup. | OK 10.5 s | OK 11.1 s | no | no | OK 16.5 s | OK |
| 214 | Pick, hard | pick up the screwdriver. | no | no | no | OK 11.6 s | OK 8.8 s | OK |
| 218 | Pick, hard | pick up the egg. | OK 14.0 s | no | - | no | no | OK |
| 226 | Pick, hard | pick up the grenade. | no | no | - | OK 7.7 s | no | OK |
| 234 | Pick, hard | pick up the juicer. | no | no | - | OK 16.8 s | OK 7.5 s | OK |
| 242 | Pick, hard | pick up the red skull key. | no | no | - | OK 14.9 s | OK 12.2 s | OK |
| 274 | Pick, hard | pick up the brown potato. | no | no | - | OK 17.2 s | OK 10.4 s | OK |
| 282 | Pick, hard | pick up the small red potato. | no | no | - | OK 9.5 s | OK 12.1 s | OK |
| 298 | Pick, hard | pick up the white stopwatch. | no | no | - | no | no | OK |
| 41 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | no | no | OK 22.0 s | OK 11.0 s | OK |
| 71 | Pick and place, normal | pick up the bottle and place it on the bowl. | no | no | no | OK 18.6 s | OK 12.7 s | OK |
| 177 | Pick and place, normal | pick up the mug and place it on the bowl. | no | no | - | OK 10.1 s | OK 9.9 s | OK |
| 197 | Pick and place, normal | pick up the knife and place it on the bowl. | no | no | - | no | no | OK |
| 209 | Pick and place, normal | pick up the shaker and place it on the bowl. | no | no | - | OK 11.7 s | OK 9.8 s | OK |
| 221 | Pick and place, normal | pick up the ladle and place it on the bowl. | no | OK 29.8 s | - | OK 18.3 s | OK 20.5 s | OK |
