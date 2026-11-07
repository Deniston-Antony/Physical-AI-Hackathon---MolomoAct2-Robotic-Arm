# Local tests, 7 November

Model: MolmoBot-Img-DROID, half overlap, left camera, 12 actions per call. Local PC (RTX 4070). Frozen: failed, and the median joint change over 3 s is below 0.02 rad (the number in brackets).

## 19 episodes where the arm froze on the board

| Run | Setting | Solved | By set | Frozen | Robot waits | Inference p50 | Rule used |
|---|---|---|---|---|---|---|---|
| frz_now | 5 flow steps, board wording (the 60% image) | 2/19 | pnp normal 2/11, pnp hard 0/8 | 14 | 37% | 584 ms | 0 |
| frz_word | 5 flow steps, training wording | 3/19 | pnp normal 2/11, pnp hard 1/8 | 15 | 37% | 600 ms | 0 |
| frz_flow3 | 3 flow steps, board wording | 4/19 | pnp normal 2/11, pnp hard 2/8 | 14 | 30% | 483 ms | 0 |
| frz_both | 3 flow steps, training wording | 2/19 | pnp normal 1/11, pnp hard 1/8 | 13 | 30% | 479 ms | 0 |
| frz_still3 | 3 flow steps, board wording, still-arm rule | 10/19 | pnp normal 8/11, pnp hard 2/8 | 0 | 30% | 489 ms | 15 |

| Episode | Set | frz_now | frz_word | frz_flow3 | frz_both | frz_still3 |
|---|---|---|---|---|---|---|
| pick up the spatula and place it on the bowl. | pnp normal | OK 19.0 s | OK 20.7 s | OK 20.6 s | frozen (0.005) | OK 27.7 s |
| pick up the bottle and place it on the bowl. | pnp normal | frozen (0.004) | frozen (0.004) | frozen (0.006) | frozen (0.004) | OK 18.7 s |
| pick up the bowl and place it on the dish. | pnp hard | frozen (0.004) | frozen (0.005) | frozen (0.005) | frozen (0.005) | OK 20.7 s |
| pick up the card and place it on the bowl. | pnp hard | no (0.357) | frozen (0.006) | frozen (0.004) | frozen (0.004) | no (0.325) |
| pick up the knife and place it on the bowl. | pnp normal | frozen (0.004) | frozen (0.004) | frozen (0.005) | frozen (0.004) | no (0.155) |
| pick up the pointed metal awl and place it on the white | pnp hard | no (0.051) | OK 33.5 s | frozen (0.005) | no (0.220) | no (0.351) |
| pick up the apple and place it on the bowl. | pnp normal | frozen (0.005) | frozen (0.004) | frozen (0.006) | no (0.277) | no (0.222) |
| pick up the spoon and place it on the rustic clay bowl. | pnp hard | frozen (0.005) | frozen (0.005) | frozen (0.006) | frozen (0.005) | OK 27.6 s |
| pick up the towel and place it on the bowl. | pnp normal | OK 16.3 s | OK 16.6 s | OK 15.4 s | OK 15.6 s | OK 16.0 s |
| pick up the fork and place it on the bowl. | pnp normal | frozen (0.005) | frozen (0.005) | frozen (0.005) | frozen (0.005) | OK 18.5 s |
| pick up the bowl and place it on the bowl. | pnp hard | frozen (0.009) | frozen (0.005) | OK 30.3 s | no (0.170) | no (0.258) |
| pick up the gray metal ring and place it on the bowl. | pnp hard | no (0.358) | frozen (0.004) | frozen (0.006) | frozen (0.004) | no (0.353) |
| pick up the watch and place it on the wooden box. | pnp hard | frozen (0.004) | frozen (0.005) | no (0.140) | no (0.106) | no (0.304) |
| pick up the ladle and place it on the bowl. | pnp normal | frozen (0.005) | frozen (0.004) | frozen (0.003) | frozen (0.004) | OK 24.0 s |
| pick up the fork and place it on the bowl. | pnp normal | frozen (0.005) | frozen (0.005) | frozen (0.005) | frozen (0.005) | OK 19.0 s |
| pick up the smart speaker and place it on the rustic br | pnp hard | frozen (0.005) | no (0.039) | OK 27.7 s | OK 29.9 s | no (0.294) |
| pick up the potato and place it on the bowl. | pnp normal | frozen (0.004) | frozen (0.004) | frozen (0.005) | frozen (0.004) | OK 19.8 s |
| pick up the bottle and place it on the bowl. | pnp normal | frozen (0.004) | frozen (0.004) | frozen (0.004) | frozen (0.004) | no (0.477) |
| pick up the cup and place it on the bowl. | pnp normal | frozen (0.004) | frozen (0.004) | frozen (0.005) | frozen (0.004) | OK 20.7 s |

## 28 hard episodes (eval_local/hard28.json)

| Run | Setting | Solved | By set | Frozen | Robot waits | Inference p50 | Rule used |
|---|---|---|---|---|---|---|---|
| play12_flow5 | overnight: 5 flow steps, board wording (the 60% image) | 16/28 | pick hard 9/16, pnp hard 7/12 | 1 | 47% | 790 ms | 0 |
| grip40 | overnight: the same and the gripper rule | 16/28 | pick hard 9/16, pnp hard 7/12 | 1 | 47% | 796 ms | 0 |
| hard_flow3 | 3 flow steps, board wording | 17/28 | pick hard 10/16, pnp hard 7/12 | 1 | 42% | 723 ms | 0 |
| hard_both | 3 flow steps, training wording | 18/28 | pick hard 11/16, pnp hard 7/12 | 1 | 42% | 723 ms | 0 |
| hard_still3 | 3 flow steps, board wording, still-arm rule | 17/28 | pick hard 9/16, pnp hard 8/12 | 0 | 42% | 725 ms | 0 |

| Episode | Set | play12_flow5 | grip40 | hard_flow3 | hard_both | hard_still3 |
|---|---|---|---|---|---|---|
| pick up the comb. | pick hard | OK 19.2 s | OK 14.4 s | OK 13.5 s | OK 14.2 s | no (0.223) |
| pick up the knife. | pick hard | OK 14.5 s | no (0.468) | OK 18.0 s | OK 13.7 s | OK 17.7 s |
| pick up the cup. | pick hard | no (0.306) | OK 19.6 s | OK 12.7 s | OK 12.5 s | OK 15.0 s |
| pick up the potato. | pick hard | no (0.357) | no (0.449) | OK 18.5 s | no (0.734) | OK 14.8 s |
| pick up the brown pinecone keychain. | pick hard | OK 16.0 s | OK 18.3 s | OK 12.9 s | OK 17.9 s | no (0.259) |
| pick up the album. | pick hard | no (0.185) | OK 17.8 s | no (0.198) | no (0.317) | no (0.231) |
| pick up the cup. | pick hard | no (0.347) | no (0.257) | no (0.293) | no (0.178) | OK 18.8 s |
| pick up the butter knife. | pick hard | no (0.317) | no (0.417) | OK 18.0 s | no (0.232) | no (0.168) |
| pick up the silver kettle. | pick hard | OK 17.8 s | OK 18.0 s | no (0.219) | no (0.367) | no (0.264) |
| pick up the grenade. | pick hard | OK 12.6 s | OK 13.5 s | OK 15.9 s | OK 14.3 s | OK 9.4 s |
| pick up the red skull key. | pick hard | OK 19.3 s | OK 17.0 s | OK 14.3 s | OK 17.2 s | OK 17.4 s |
| pick up the egg. | pick hard | OK 15.4 s | no (0.266) | no (0.420) | OK 19.0 s | no (0.171) |
| pick up the pot. | pick hard | no (0.213) | no (0.208) | no (0.181) | OK 16.9 s | no (0.130) |
| pick up the kettle. | pick hard | OK 16.2 s | OK 11.4 s | OK 19.5 s | OK 8.8 s | OK 10.3 s |
| pick up the brown egg. | pick hard | OK 13.5 s | OK 13.6 s | OK 10.6 s | OK 18.5 s | OK 13.1 s |
| pick up the bottle. | pick hard | no (0.171) | no (0.184) | no (0.178) | OK 16.1 s | OK 16.0 s |
| pick up the butter knife and place it on the bowl. | pnp hard | no (0.226) | OK 30.8 s | no (0.234) | OK 31.2 s | no (0.218) |
| pick up the onion and place it on the bowl. | pnp hard | OK 34.9 s | no (0.185) | no (0.265) | no (0.240) | OK 38.5 s |
| pick up the spoon and place it on the rustic clay bowl. | pnp hard | frozen (0.004) | frozen (0.005) | frozen (0.006) | frozen (0.006) | OK 18.1 s |
| pick up the bee and place it on the gray bowl. | pnp hard | OK 31.8 s | no (0.195) | OK 39.3 s | OK 25.6 s | OK 27.4 s |
| pick up the white mug and place it on the bowl. | pnp hard | OK 26.7 s | OK 35.3 s | OK 33.0 s | OK 28.4 s | OK 32.7 s |
| pick up the candle and place it on the gray bowl. | pnp hard | no (0.187) | no (0.214) | no (0.265) | no (0.230) | no (0.252) |
| pick up the futuristic black key and place it on the ti | pnp hard | OK 39.1 s | OK 36.7 s | OK 31.9 s | OK 31.7 s | no (0.272) |
| pick up the raw meat and place it on the pot. | pnp hard | no (0.215) | OK 37.8 s | no (0.247) | no (0.201) | OK 31.7 s |
| pick up the goggles and place it on the bowl. | pnp hard | OK 37.7 s | OK 30.4 s | OK 39.2 s | no (0.252) | OK 32.3 s |
| pick up the kitchen spatula and place it on the rustic  | pnp hard | OK 32.9 s | OK 33.7 s | OK 33.3 s | OK 30.5 s | OK 31.4 s |
| pick up the leather-wrapped brass telescope and place i | pnp hard | OK 36.2 s | OK 37.6 s | OK 21.9 s | OK 18.0 s | OK 34.8 s |
| pick up the bowl and place it on the mug. | pnp hard | no (0.280) | no (0.264) | OK 28.0 s | OK 34.1 s | no (0.237) |

