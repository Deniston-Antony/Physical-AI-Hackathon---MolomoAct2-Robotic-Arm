# Board result of v5 (open/close action expert) against v4 and v3

v5 = v4 rules + open pull + the new action expert for open and close tasks (step 2500). Pick tasks use the old expert with the same rules as v4, so for pick tasks v5 and v4 behave the same and their differences are run-to-run noise (about +-6 episodes per run of 320).

Scores: v5 215/320 = 67.2%, v4 215/320 = 67.2%, v3 219/320 = 68.4% (best).

## 1. Per set

| Set | Episodes | v5 | v4 | v3 | v5 - v4 | v5 - v3 | v5 gained vs v3 | v5 lost vs v3 | v5 median s | v3 median s |
|---|---|---|---|---|---|---|---|---|---|---|
| Pick (normal) | 59 | 53 | 56 | 55 | -3 | -2 | 2 | 4 | 5.3 | 4.6 |
| Pick (hard) | 57 | 36 | 40 | 39 | -4 | -3 | 7 | 10 | 12.4 | 10.9 |
| Pick and place (normal) | 54 | 49 | 50 | 48 | -1 | +1 | 3 | 2 | 14.4 | 12.9 |
| Pick and place (hard) | 58 | 37 | 38 | 39 | -1 | -2 | 4 | 6 | 19.7 | 19.6 |
| Pick and place by color (hard) | 16 | 11 | 9 | 12 | +2 | -1 | 1 | 2 | 21.8 | 17.0 |
| Place next to (hard) | 16 | 8 | 2 | 6 | +6 | +2 | 3 | 1 | 22.2 | 21.4 |
| Open (normal) | 15 | 0 | 0 | 2 | +0 | -2 | 0 | 2 | - | - |
| Open (hard) | 15 | 1 | 1 | 1 | +0 | +0 | 0 | 0 | 26.9 | 5.6 |
| Close (normal) | 15 | 12 | 10 | 13 | +2 | -1 | 1 | 2 | 8.0 | 1.9 |
| Close (hard) | 15 | 8 | 9 | 4 | -1 | +4 | 5 | 1 | 8.2 | 4.8 |
| **All** | 320 | **215** | 215 | 219 | +0 | -4 | 26 | 30 | | |

## 2. Open and close tasks, per episode (the tasks the new expert does)

Board # = the episode number in the board order (the numbers of tests_1108/open30.json).

| Board # | Set | Task | v5 | v4 | v3 | v5 against v4 | v5 against v3 |
|---|---|---|---|---|---|---|---|
| 7 | Open (normal) | open the drawer. | no | no | no |  |  |
| 17 | Open (normal) | open the drawer. | no | no | no |  |  |
| 27 | Open (normal) | open the oven. | no | no | no |  |  |
| 37 | Open (normal) | open the desk. | no | no | no |  |  |
| 47 | Open (normal) | open the oven. | no | no | no |  |  |
| 57 | Open (normal) | open the dresser. | no | no | no |  |  |
| 67 | Open (normal) | open the dresser. | no | no | no |  |  |
| 77 | Open (normal) | open the drawer. | no | no | no |  |  |
| 87 | Open (normal) | open the drawer. | no | no | no |  |  |
| 97 | Open (normal) | open the cabinet. | no | no | no |  |  |
| 107 | Open (normal) | open the dresser. | no | no | OK 19.2 s |  | LOST |
| 117 | Open (normal) | open the dresser. | no | no | no |  |  |
| 127 | Open (normal) | open the table. | no | no | OK 1.9 s |  | LOST |
| 137 | Open (normal) | open the refrigerator. | no | no | no |  |  |
| 147 | Open (normal) | open the drawer. | no | no | no |  |  |
| 8 | Open (hard) | open the dishwasher. | no | no | no |  |  |
| 18 | Open (hard) | open the refrigerator. | no | no | no |  |  |
| 28 | Open (hard) | open the wooden table. | no | no | no |  |  |
| 38 | Open (hard) | open the wooden table. | OK 26.9 s | OK 8.4 s | OK 5.6 s |  |  |
| 48 | Open (hard) | open the desk. | no | no | no |  |  |
| 58 | Open (hard) | open the dark table. | no | no | no |  |  |
| 68 | Open (hard) | open the wooden table. | no | no | no |  |  |
| 78 | Open (hard) | open the large wooden dresser. | no | no | no |  |  |
| 88 | Open (hard) | open the dark fridge. | no | no | no |  |  |
| 98 | Open (hard) | open the tall wooden shelf. | no | no | no |  |  |
| 108 | Open (hard) | open the tall dark refrigerator. | no | no | no |  |  |
| 118 | Open (hard) | open the table. | no | no | no |  |  |
| 128 | Open (hard) | open the dresser. | no | no | no |  |  |
| 138 | Open (hard) | open the refrigerator. | no | no | no |  |  |
| 148 | Open (hard) | open the dresser. | no | no | no |  |  |
| 6 | Close (normal) | close the drawer. | OK 14.1 s | no | OK 2.2 s | GAINED |  |
| 16 | Close (normal) | close the drawer. | OK 6.5 s | OK 1.8 s | OK 2.0 s |  |  |
| 26 | Close (normal) | close the drawer. | OK 13.7 s | OK 1.7 s | OK 1.6 s |  |  |
| 36 | Close (normal) | close the drawer. | OK 7.8 s | OK 25.6 s | OK 9.5 s |  |  |
| 46 | Close (normal) | close the drawer. | OK 8.8 s | OK 16.4 s | OK 3.7 s |  |  |
| 56 | Close (normal) | close the table. | OK 9.0 s | no | OK 1.9 s | GAINED |  |
| 66 | Close (normal) | close the drawer. | no | no | no |  |  |
| 76 | Close (normal) | close the drawer. | OK 7.1 s | OK 1.3 s | no |  | GAINED |
| 86 | Close (normal) | close the cabinet. | no | no | OK 1.5 s |  | LOST |
| 96 | Close (normal) | close the dresser. | OK 6.3 s | OK 1.7 s | OK 1.9 s |  |  |
| 106 | Close (normal) | close the table. | OK 8.0 s | OK 1.5 s | OK 1.4 s |  |  |
| 116 | Close (normal) | close the drawer. | no | no | OK 16.0 s |  | LOST |
| 126 | Close (normal) | close the table. | OK 3.7 s | OK 4.7 s | OK 1.6 s |  |  |
| 136 | Close (normal) | close the table. | OK 5.4 s | OK 1.9 s | OK 1.6 s |  |  |
| 146 | Close (normal) | close the dresser. | OK 17.0 s | OK 2.6 s | OK 1.7 s |  |  |
| 9 | Close (hard) | close the cabinet. | OK 6.7 s | no | no | GAINED | GAINED |
| 19 | Close (hard) | close the table. | OK 8.2 s | OK 5.5 s | OK 17.1 s |  |  |
| 29 | Close (hard) | close the brown wooden desk. | no | no | no |  |  |
| 39 | Close (hard) | close the oven. | no | no | no |  |  |
| 49 | Close (hard) | close the brown wooden desk. | no | OK 8.5 s | OK 5.2 s | LOST | LOST |
| 59 | Close (hard) | close the white dresser. | OK 9.7 s | OK 2.0 s | OK 4.2 s |  |  |
| 69 | Close (hard) | close the desk. | no | no | no |  |  |
| 79 | Close (hard) | close the white table. | OK 8.0 s | OK 14.9 s | no |  | GAINED |
| 89 | Close (hard) | close the table. | no | no | no |  |  |
| 99 | Close (hard) | close the light brown table. | OK 15.4 s | no | no | GAINED | GAINED |
| 109 | Close (hard) | close the dresser. | OK 9.4 s | OK 15.8 s | no |  | GAINED |
| 119 | Close (hard) | close the white wooden dresser. | OK 5.3 s | OK 2.4 s | OK 4.8 s |  |  |
| 129 | Close (hard) | close the dresser. | OK 12.8 s | OK 10.6 s | no |  | GAINED |
| 139 | Close (hard) | close the dark dresser. | no | OK 9.2 s | no | LOST |  |
| 149 | Close (hard) | close the dresser. | no | OK 16.2 s | no | LOST |  |

## 3. Pick tasks, per task

### Pick (normal): v5 53/59, v4 56/59, v3 55/59

| Task | Episodes | v5 | v4 | v3 | v5 gained vs v3 (board #) | v5 lost vs v3 (board #) |
|---|---|---|---|---|---|---|
| pick up the apple. | 3 | 2 | 3 | 3 |  | 30 |
| pick up the bottle. | 9 | 7 | 9 | 8 |  | 110 |
| pick up the bowl. | 5 | 5 | 5 | 5 |  |  |
| pick up the box. | 4 | 3 | 3 | 4 |  | 288 |
| pick up the cup. | 2 | 2 | 2 | 2 |  |  |
| pick up the fork. | 4 | 4 | 4 | 4 |  |  |
| pick up the kettle. | 1 | 1 | 1 | 1 |  |  |
| pick up the ladle. | 2 | 2 | 2 | 2 |  |  |
| pick up the mug. | 1 | 1 | 1 | 1 |  |  |
| pick up the pepper. | 1 | 1 | 1 | 1 |  |  |
| pick up the pot. | 2 | 2 | 1 | 1 | 292 |  |
| pick up the remote. | 4 | 4 | 4 | 4 |  |  |
| pick up the shaker. | 4 | 4 | 4 | 4 |  |  |
| pick up the spatula. | 5 | 5 | 5 | 5 |  |  |
| pick up the spoon. | 3 | 3 | 3 | 3 |  |  |
| pick up the tissue. | 7 | 6 | 7 | 6 | 180 | 130 |
| pick up the tomato. | 2 | 1 | 1 | 1 |  |  |

### Pick (hard): v5 36/57, v4 40/57, v3 39/57

| Task | Episodes | v5 | v4 | v3 | v5 gained vs v3 (board #) | v5 lost vs v3 (board #) |
|---|---|---|---|---|---|---|
| pick up the album. | 1 | 0 | 0 | 0 |  |  |
| pick up the apple. | 1 | 1 | 1 | 1 |  |  |
| pick up the black moka. | 1 | 1 | 1 | 0 | 2 |  |
| pick up the black ribbed cap. | 1 | 0 | 1 | 1 |  | 210 |
| pick up the black webcam. | 1 | 0 | 1 | 0 |  |  |
| pick up the blue pan. | 1 | 0 | 1 | 1 |  | 190 |
| pick up the bottle. | 1 | 1 | 1 | 1 |  |  |
| pick up the box. | 1 | 1 | 0 | 1 |  |  |
| pick up the bridge. | 1 | 1 | 1 | 1 |  |  |
| pick up the brown egg. | 1 | 1 | 1 | 1 |  |  |
| pick up the brown pinecone keychain. | 1 | 1 | 1 | 1 |  |  |
| pick up the brown potato. | 1 | 1 | 1 | 1 |  |  |
| pick up the butter knife. | 1 | 0 | 1 | 1 |  | 186 |
| pick up the comb. | 1 | 1 | 1 | 1 |  |  |
| pick up the cream candle. | 1 | 0 | 0 | 0 |  |  |
| pick up the croissant. | 1 | 1 | 1 | 0 | 250 |  |
| pick up the cup. | 2 | 2 | 2 | 2 |  |  |
| pick up the dish. | 1 | 1 | 1 | 1 |  |  |
| pick up the dog statue. | 1 | 0 | 0 | 1 |  | 182 |
| pick up the egg. | 1 | 0 | 1 | 1 |  | 218 |
| pick up the gray container. | 1 | 1 | 1 | 0 | 315 |  |
| pick up the green battery. | 1 | 0 | 0 | 0 |  |  |
| pick up the green floral invitation. | 1 | 1 | 1 | 1 |  |  |
| pick up the grenade. | 1 | 0 | 1 | 1 |  | 226 |
| pick up the hammer. | 1 | 0 | 0 | 1 |  | 72 |
| pick up the juicer. | 1 | 1 | 1 | 1 |  |  |
| pick up the kettle. | 1 | 1 | 1 | 1 |  |  |
| pick up the knife. | 1 | 1 | 1 | 1 |  |  |
| pick up the marble rook. | 1 | 0 | 0 | 0 |  |  |
| pick up the mechanism. | 1 | 1 | 1 | 1 |  |  |
| pick up the metal fork. | 1 | 1 | 1 | 1 |  |  |
| pick up the metallic multi-tool. | 1 | 0 | 0 | 1 |  | 82 |
| pick up the metallic sleek blade. | 1 | 1 | 1 | 1 |  |  |
| pick up the micrometer. | 1 | 1 | 1 | 1 |  |  |
| pick up the notebook. | 1 | 0 | 0 | 0 |  |  |
| pick up the pan. | 1 | 1 | 0 | 1 |  |  |
| pick up the pin. | 1 | 0 | 0 | 0 |  |  |
| pick up the plump red tomato. | 1 | 0 | 0 | 0 |  |  |
| pick up the pot. | 2 | 1 | 1 | 1 |  |  |
| pick up the potato. | 1 | 1 | 1 | 0 | 162 |  |
| pick up the puck. | 1 | 1 | 1 | 1 |  |  |
| pick up the red apple. | 2 | 1 | 2 | 0 | 158 |  |
| pick up the red skull key. | 1 | 1 | 1 | 1 |  |  |
| pick up the screwdriver. | 1 | 1 | 1 | 1 |  |  |
| pick up the shiny gold script. | 1 | 0 | 1 | 1 |  | 258 |
| pick up the silver kettle. | 1 | 1 | 0 | 1 |  |  |
| pick up the small red potato. | 1 | 1 | 1 | 1 |  |  |
| pick up the smooth light blue dolphin. | 1 | 1 | 1 | 1 |  |  |
| pick up the spatula. | 1 | 1 | 1 | 1 |  |  |
| pick up the teal ruler. | 1 | 0 | 1 | 1 |  | 278 |
| pick up the toilet. | 1 | 0 | 0 | 0 |  |  |
| pick up the wheel. | 1 | 1 | 0 | 0 | 62 |  |
| pick up the white stopwatch. | 1 | 1 | 1 | 1 |  |  |
| pick up the wooden fan. | 1 | 1 | 0 | 0 | 294 |  |

### Pick and place (normal): v5 49/54, v4 50/54, v3 48/54

| Task | Episodes | v5 | v4 | v3 | v5 gained vs v3 (board #) | v5 lost vs v3 (board #) |
|---|---|---|---|---|---|---|
| pick up the apple and place it on the bowl. | 3 | 3 | 3 | 3 |  |  |
| pick up the bottle and place it on the bowl. | 7 | 5 | 5 | 4 | 11 |  |
| pick up the candle and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the cup and place it on the bowl. | 3 | 3 | 3 | 3 |  |  |
| pick up the egg and place it on the bowl. | 2 | 2 | 2 | 2 |  |  |
| pick up the fork and place it on the bowl. | 6 | 6 | 6 | 6 |  |  |
| pick up the knife and place it on the bowl. | 3 | 2 | 2 | 2 |  |  |
| pick up the ladle and place it on the bowl. | 2 | 2 | 2 | 2 |  |  |
| pick up the mug and place it on the bowl. | 3 | 3 | 3 | 3 |  |  |
| pick up the potato and place it on the bowl. | 3 | 3 | 3 | 3 |  |  |
| pick up the remote and place it on the bowl. | 2 | 2 | 2 | 2 |  |  |
| pick up the shaker and place it on the bowl. | 4 | 4 | 4 | 4 |  |  |
| pick up the spatula and place it on the bowl. | 4 | 4 | 4 | 3 | 91 |  |
| pick up the spatula and place it on the dish. | 1 | 1 | 1 | 1 |  |  |
| pick up the spoon and place it on the bowl. | 3 | 3 | 3 | 3 |  |  |
| pick up the tissue and place it on the bowl. | 3 | 3 | 3 | 3 |  |  |
| pick up the towel and place it on the bowl. | 4 | 2 | 3 | 3 | 233 | 193, 253 |

### Pick and place (hard): v5 37/58, v4 38/58, v3 39/58

| Task | Episodes | v5 | v4 | v3 | v5 gained vs v3 (board #) | v5 lost vs v3 (board #) |
|---|---|---|---|---|---|---|
| pick up the bark and place it on the bowl. | 1 | 1 | 0 | 0 | 263 |  |
| pick up the bee and place it on the gray bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the blue die and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the bottle and place it on the basin. | 1 | 1 | 1 | 0 | 183 |  |
| pick up the bottle and place it on the bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the bottle and place it on the glossy white bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the bowl and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the bowl and place it on the dish. | 1 | 1 | 1 | 1 |  |  |
| pick up the bowl and place it on the mug. | 1 | 1 | 1 | 1 |  |  |
| pick up the brown cat figurine and place it on the gray bowl. | 1 | 0 | 1 | 1 |  | 63 |
| pick up the brush and place it on the bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the butter knife and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the calculator and place it on the round gray bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the camcorder and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the candle and place it on the gray bowl. | 1 | 0 | 1 | 0 |  |  |
| pick up the card and place it on the bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the ceramic bowl and place it on the mug. | 1 | 1 | 0 | 1 |  |  |
| pick up the colorful mosaic and place it on the bowl. | 1 | 0 | 0 | 1 |  | 267 |
| pick up the cup and place it on the container. | 1 | 1 | 1 | 1 |  |  |
| pick up the digital wristband and place it on the round gray bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the fork and place it on the round blue bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the futuristic black key and place it on the tin. | 1 | 1 | 1 | 1 |  |  |
| pick up the glossy golden musical note and place it on the bowl. | 1 | 1 | 0 | 0 | 316 |  |
| pick up the goggles and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the gold watch and place it on the bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the golden bottle and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the grapefruit and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the gray metal ring and place it on the bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the gray shackle and place it on the pink geometric box. | 1 | 1 | 1 | 1 |  |  |
| pick up the green tissue and place it on the blue bottle. | 1 | 1 | 1 | 1 |  |  |
| pick up the kitchen spatula and place it on the rustic wooden bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the knife and place it on the ashtray. | 1 | 1 | 1 | 1 |  |  |
| pick up the leather-wrapped brass telescope and place it on the box. | 1 | 1 | 1 | 1 |  |  |
| pick up the metal component and place it on the metal tin. | 1 | 0 | 1 | 1 |  | 83 |
| pick up the mug and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the mug and place it on the shallow green bowl. | 1 | 1 | 1 | 0 | 167 |  |
| pick up the newspaper and place it on the white ceramic bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the onion and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the pepper shaker and place it on the box. | 1 | 1 | 1 | 1 |  |  |
| pick up the pointed metal awl and place it on the white bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the projector and place it on the pot. | 1 | 0 | 0 | 0 |  |  |
| pick up the purple bottle and place it on the ceramic bowl with rice. | 1 | 1 | 1 | 1 |  |  |
| pick up the raw meat and place it on the pot. | 1 | 1 | 1 | 1 |  |  |
| pick up the red apple and place it on the bowl. | 1 | 0 | 0 | 1 |  | 133 |
| pick up the screwdriver and place it on the dark pot. | 1 | 1 | 1 | 1 |  |  |
| pick up the shiny golden chain and place it on the red container. | 1 | 1 | 1 | 1 |  |  |
| pick up the small red potato and place it on the tan decorative bowl. | 1 | 1 | 0 | 1 |  |  |
| pick up the smart speaker and place it on the rustic brown bowl. | 1 | 0 | 0 | 1 |  | 279 |
| pick up the spoon and place it on the rustic clay bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the tape and place it on the bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the terminal and place it on the gray bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the tissue and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the toy dog and place it on the dish. | 1 | 0 | 1 | 0 |  |  |
| pick up the watch and place it on the wooden box. | 1 | 0 | 0 | 0 |  |  |
| pick up the white mug and place it on the bowl. | 1 | 1 | 1 | 1 |  |  |
| pick up the wooden pencil and place it on the bowl. | 1 | 0 | 0 | 0 |  |  |
| pick up the wooden stamp and place it on the tray. | 1 | 1 | 1 | 1 |  |  |
| pick up the yellow wooden pencil and place it on the round wooden bowl. | 1 | 0 | 1 | 1 |  | 259 |

### Pick and place by color (hard): v5 11/16, v4 9/16, v3 12/16

| Task | Episodes | v5 | v4 | v3 | v5 gained vs v3 (board #) | v5 lost vs v3 (board #) |
|---|---|---|---|---|---|---|
| Pick up the black digital music player and place it in or on the light blue bowl | 1 | 1 | 1 | 0 | 154 |  |
| Pick up the blue birthday card with fox and rabbit and place it in or on the green ashtray | 1 | 1 | 1 | 1 |  |  |
| Pick up the curve and place it in or on the green dish | 1 | 1 | 1 | 1 |  |  |
| Pick up the dark wand with red crystal and place it in or on the light blue bowl | 1 | 1 | 1 | 1 |  |  |
| Pick up the gray dragon pipe with scales and place it in or on the purple bowl | 1 | 1 | 1 | 1 |  |  |
| Pick up the lighter and place it in or on the white decorative box | 1 | 1 | 0 | 1 |  |  |
| Pick up the low-poly brown acorn and place it in or on the black bowl | 1 | 0 | 0 | 0 |  |  |
| Pick up the polished metal shuriken with four blades and place it in or on the blue bowl | 1 | 1 | 0 | 1 |  |  |
| Pick up the red teardrop keychain holder with button and place it in or on the tan ceramic bowl | 1 | 1 | 0 | 1 |  |  |
| Pick up the red wall-mounted fire connection with caps and place it in or on the blue decorative bowl | 1 | 0 | 0 | 0 |  |  |
| Pick up the red white striped teacup and place it in or on the purple ceramic bowl | 1 | 1 | 1 | 1 |  |  |
| Pick up the reddish metal brooch with swirl and place it in or on the white decorative bowl | 1 | 0 | 1 | 1 |  | 54 |
| Pick up the standard playing card with clubs and place it in or on the tan mug | 1 | 0 | 0 | 1 |  | 44 |
| Pick up the vintage bird-shaped metal nutcracker and place it in or on the blue bowl | 1 | 1 | 1 | 1 |  |  |
| Pick up the worn white metal paint can and place it in or on the green bowl | 1 | 1 | 1 | 1 |  |  |
| Pick up the yellow flower with leaf and place it in or on the light yellow bowl | 1 | 0 | 0 | 0 |  |  |

### Place next to (hard): v5 8/16, v4 2/16, v3 6/16

| Task | Episodes | v5 | v4 | v3 | v5 gained vs v3 (board #) | v5 lost vs v3 (board #) |
|---|---|---|---|---|---|---|
| Pick up the blue patterned cat and place it next to the gold pump bottle | 1 | 1 | 0 | 0 | 15 |  |
| Pick up the dark metal frying pan and place it next to the bulbous shiny gold metallic vase | 1 | 0 | 0 | 1 |  | 125 |
| Pick up the denture and place it next to the red lighthouse with framework | 1 | 1 | 0 | 1 |  |  |
| Pick up the garden hose nozzle and place it next to the bulbous shiny gold vase | 1 | 0 | 0 | 0 |  |  |
| Pick up the glossy orange bell pepper with stem and place it next to the irish potato | 1 | 1 | 0 | 1 |  |  |
| Pick up the gray metal rod with perforated top and place it next to the angular dark stealth aircraft with wings | 1 | 1 | 0 | 0 | 75 |  |
| Pick up the green gemstone and place it next to the red spaceship | 1 | 0 | 0 | 0 |  |  |
| Pick up the green grenade with metal lever and base and place it next to the gray rectangular ethernet transceiver | 1 | 0 | 0 | 0 |  |  |
| Pick up the hexagonal dark stone platform and place it next to the stylized orange butterfly with brown body | 1 | 0 | 0 | 0 |  |  |
| Pick up the light wooden bridge with arches and place it next to the purple and yellow pixelated knife | 1 | 1 | 1 | 1 |  |  |
| Pick up the medallion with crown and shields and place it next to the dark gray bowl | 1 | 0 | 0 | 0 |  |  |
| Pick up the orange cylindrical medicine bottle with label and place it next to the octagonal translucent soap bottle | 1 | 1 | 0 | 1 |  |  |
| Pick up the root vegetable and place it next to the medium round red tomato with stem | 1 | 0 | 0 | 0 |  |  |
| Pick up the sleek black spinning top and place it next to the gold metallic phone | 1 | 1 | 1 | 1 |  |  |
| Pick up the smooth brown chicken egg and place it next to the transparent soap bottle with bronze pump | 1 | 0 | 0 | 0 |  |  |
| Pick up the wooden humanoid puzzle piece and place it next to the shiny gold vase | 1 | 1 | 0 | 0 | 35 |  |

