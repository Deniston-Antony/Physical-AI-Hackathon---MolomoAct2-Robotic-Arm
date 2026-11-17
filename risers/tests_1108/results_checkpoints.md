# Local tests of the saved open/close action experts: open tasks

Updated 2026-11-09 17:18. The 30 open episodes of the board (tests_1108/open30.json), on this PC. Rules of all runs: the v4 flags plus the open pull. "v4 + pull" uses the original action expert.

| Model | Solved | Episodes done | Open datagen | Open hard |
|---|---|---|---|---|
| v4 + pull | 4 | 30/30 | 3/15 | 1/15 |
| step 1000 | 2 | 30/30 | 1/15 | 1/15 |
| step 2400 | 4 | 30/30 | 3/15 | 1/15 |

| Board # | Episode | Kind | Top 7 | v4 + pull | step 1000 | step 2400 |
|---|---|---|---|---|---|---|
| 7 | open the drawer. | slide | 0/7 | no | no | no |
| 68 | open the wooden table. | slide | 4/7 | no | no | no |
| 107 | open the dresser. | slide | 6/7 | OK 6.5 s | no | no |
| 128 | open the dresser. | slide | 2/7 | no | no | no |
| 8 | open the dishwasher. | hinge | 0/7 | no | no | no |
| 17 | open the drawer. | slide | 1/7 | no | no | no |
| 18 | open the refrigerator. | hinge | 0/7 | no | no | no |
| 27 | open the oven. | hinge | 0/7 | no | no | no |
| 28 | open the wooden table. | slide | 2/7 | no | no | no |
| 37 | open the desk. | slide | 4/7 | OK 23.9 s | no | OK 25.5 s |
| 38 | open the wooden table. | slide | 5/7 | OK 13.5 s | OK 11.5 s | OK 26.3 s |
| 47 | open the oven. | hinge | 0/7 | no | no | no |
| 48 | open the desk. | slide | 0/7 | no | no | no |
| 57 | open the dresser. | slide | 2/7 | no | OK 10.0 s | no |
| 58 | open the dark table. | slide | 0/7 | no | no | no |
| 67 | open the dresser. | slide | 0/7 | no | no | no |
| 77 | open the drawer. | slide | 2/7 | no | no | no |
| 78 | open the large wooden dresser. | slide | 0/7 | no | no | no |
| 87 | open the drawer. | slide | 1/7 | no | no | no |
| 88 | open the dark fridge. | hinge | 0/7 | no | no | no |
| 97 | open the cabinet. | hinge | 0/7 | no | no | no |
| 98 | open the tall wooden shelf. | hinge | 2/7 | no | no | no |
| 108 | open the tall dark refrigerator. | hinge | 0/7 | no | no | no |
| 117 | open the dresser. | slide | 1/7 | no | no | no |
| 118 | open the table. | slide | 0/7 | no | no | no |
| 127 | open the table. | slide | 3/7 | OK 13.3 s | no | OK 24.9 s |
| 137 | open the refrigerator. | hinge | 1/7 | no | no | no |
| 138 | open the refrigerator. | hinge | 3/7 | no | no | no |
| 147 | open the drawer. | slide | 2/7 | no | no | OK 25.5 s |
| 148 | open the dresser. | hinge | 0/7 | no | no | no |
