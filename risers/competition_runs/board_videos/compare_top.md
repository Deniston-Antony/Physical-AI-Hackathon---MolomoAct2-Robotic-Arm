# Top 5 teams vs our board runs (board snapshot board_2026-11-09T1845Z.json)

Successes per episode set. The last column is the gap between the top-5 mean and our best run (v3).

| Set | Episodes | #1 Mario_Gemoll | #2 Sleem | #3 Chans | #4 Natural_Inte | #5 syouya_tobit | us v3 | us v4 | us v5 | top-5 mean - v3 |
|---|---|---|---|---|---|---|---|---|---|---|
| PickDroidMini | 59 | 56 | 57 | 55 | 56 | 55 | 55 | 56 | 53 | +0.8 |
| PickandPlaceHard | 58 | 41 | 42 | 35 | 40 | 39 | 39 | 38 | 37 | +0.4 |
| PickHard | 57 | 44 | 39 | 37 | 33 | 41 | 39 | 40 | 36 | -0.2 |
| PickandPlaceDroidMini | 54 | 49 | 45 | 44 | 47 | 43 | 48 | 50 | 49 | -2.4 |
| PickandPlaceColorHard | 16 | 15 | 15 | 15 | 11 | 13 | 12 | 9 | 11 | +1.8 |
| PickandPlaceNextToHard | 16 | 8 | 4 | 0 | 5 | 4 | 6 | 2 | 8 | -1.8 |
| CloseDataGen | 15 | 13 | 13 | 15 | 14 | 11 | 13 | 10 | 12 | +0.2 |
| OpenDataGen | 15 | 4 | 6 | 6 | 5 | 5 | 2 | 0 | 0 | +3.2 |
| OpenHard | 15 | 4 | 5 | 6 | 4 | 4 | 1 | 1 | 1 | +3.6 |
| CloseHard | 15 | 4 | 12 | 12 | 9 | 7 | 4 | 9 | 8 | +4.8 |
| **All** | 320 | 238 | 238 | 225 | 224 | 222 | 219 | 215 | 215 | +10.4 |

Median time of a success (s) per set:

| Set | top-5 median | us v3 median |
|---|---|---|
| PickDroidMini | 4.6 | 4.8 |
| PickandPlaceHard | 16.6 | 19.9 |
| PickHard | 9.6 | 11.0 |
| PickandPlaceDroidMini | 11.5 | 13.0 |
| PickandPlaceColorHard | 15.9 | 17.1 |
| PickandPlaceNextToHard | 17.0 | 23.0 |
| CloseDataGen | 2.1 | 1.9 |
| OpenDataGen | 14.1 | 10.6 |
| OpenHard | 14.3 | 5.6 |
| CloseHard | 5.2 | 5.0 |

## Episodes that all our runs (v3, v4, v5) fail and 3 or more of the top 5 solve

| Board # | Set | Task | Top 5 that solve | Their median time (s) |
|---|---|---|---|---|
| 69 | CloseHard | close the desk. | 3 | 7.5 |
| 57 | OpenDataGen | open the dresser. | 3 | 12.4 |
| 117 | OpenDataGen | open the dresser. | 3 | 9.0 |
| 128 | OpenHard | open the dresser. | 3 | 10.2 |
| 52 | PickHard | pick up the toilet. | 3 | 8.8 |
| 222 | PickHard | pick up the album. | 4 | 9.9 |
| 262 | PickHard | pick up the green battery. | 3 | 16.9 |
| 309 | PickHard | pick up the pot. | 5 | 11.4 |
| 14 | PickandPlaceColorHard | Pick up the yellow flower with leaf and place it in or on the light yellow bowl | 3 | 22.0 |
| 134 | PickandPlaceColorHard | Pick up the low-poly brown acorn and place it in or on the black bowl | 3 | 26.7 |
| 43 | PickandPlaceHard | pick up the brush and place it on the bowl. | 4 | 23.3 |
| 199 | PickandPlaceHard | pick up the gray metal ring and place it on the bowl. | 3 | 30.0 |

12 episodes. Per set: PickHard 4, PickandPlaceColorHard 2, PickandPlaceHard 2, OpenDataGen 2, CloseHard 1, OpenHard 1
