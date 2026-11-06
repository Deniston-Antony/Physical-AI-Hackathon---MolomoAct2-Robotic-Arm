# Overnight test results

Episodes: `eval_local/hard28.json` (16 hard pick, 12 hard pick-and-place). Model: MolmoBot-Img-DROID, half overlap, left camera. Local PC (RTX 4070).

> Step 2 (`grip40`) is still running. Its row is not complete.

| Run | Setting | Solved | Hard pick | Hard pick and place | Robot waits | Inference p50 | Time to success (shared with base) |
|---|---|---|---|---|---|---|---|
| base | play 8 actions, 10 flow steps (the submitted image) | 3/28 | 1/16 | 2/12 | 65% | 1062 ms | 29.2 s vs 29.2 s (3 episodes) |
| play12 | play 12 actions, 10 flow steps | 6/28 | 3/16 | 3/12 | 56% | 1165 ms | 21.7 s vs 26.9 s (2 episodes) |
| flow5 | play 8 actions, 5 flow steps | 7/28 | 2/16 | 5/12 | 56% | 790 ms | 31.3 s vs 29.2 s (3 episodes) |
| play12_flow5 | play 12 actions, 5 flow steps | 16/28 | 9/16 | 7/12 | 47% | 790 ms | 24.0 s vs 26.9 s (2 episodes) |
| grip40 | gripper rule (open only below 40) on play12_flow5 | 0/0 | 0/16 | 0/12 | -% | - ms | - s vs - s (0 episodes) |

## Per episode

| Episode | Set | base | play12 | flow5 | play12_flow5 | grip40 |
|---|---|---|---|---|---|---|
| pick up the comb. | pick | no | no | no | OK 19.2 s |  |
| pick up the knife. | pick | no | no | no | OK 14.5 s |  |
| pick up the cup. | pick | no | OK 16.6 s | no | no |  |
| pick up the potato. | pick | no | no | no | no |  |
| pick up the brown pinecone keychain. | pick | no | no | no | OK 16.0 s |  |
| pick up the album. | pick | no | no | no | no |  |
| pick up the cup. | pick | no | no | no | no |  |
| pick up the butter knife. | pick | no | no | no | no |  |
| pick up the silver kettle. | pick | no | no | no | OK 17.8 s |  |
| pick up the grenade. | pick | no | no | OK 18.9 s | OK 12.6 s |  |
| pick up the red skull key. | pick | no | no | no | OK 19.3 s |  |
| pick up the egg. | pick | no | no | no | OK 15.4 s |  |
| pick up the pot. | pick | no | no | no | no |  |
| pick up the kettle. | pick | OK 17.2 s | OK 12.7 s | OK 12.9 s | OK 16.2 s |  |
| pick up the brown egg. | pick | no | OK 15.2 s | no | OK 13.5 s |  |
| pick up the bottle. | pick | no | no | no | no |  |
| pick up the butter knife and place it on the bowl. | pick and place | no | no | no | no |  |
| pick up the onion and place it on the bowl. | pick and place | no | no | no | OK 34.9 s |  |
| pick up the spoon and place it on the rustic clay bowl. | pick and place | no | no | OK 22.3 s | no |  |
| pick up the bee and place it on the gray bowl. | pick and place | OK 36.6 s | OK 30.8 s | OK 31.3 s | OK 31.8 s |  |
| pick up the white mug and place it on the bowl. | pick and place | no | OK 39.5 s | OK 36.4 s | OK 26.7 s |  |
| pick up the candle and place it on the gray bowl. | pick and place | no | no | no | no |  |
| pick up the futuristic black key and place it on the ti | pick and place | no | no | no | OK 39.1 s |  |
| pick up the raw meat and place it on the pot. | pick and place | OK 29.2 s | no | OK 33.6 s | no |  |
| pick up the goggles and place it on the bowl. | pick and place | no | no | no | OK 37.7 s |  |
| pick up the kitchen spatula and place it on the rustic  | pick and place | no | OK 34.1 s | no | OK 32.9 s |  |
| pick up the leather-wrapped brass telescope and place i | pick and place | no | no | OK 37.2 s | OK 36.2 s |  |
| pick up the bowl and place it on the mug. | pick and place | no | no | no | no |  |
