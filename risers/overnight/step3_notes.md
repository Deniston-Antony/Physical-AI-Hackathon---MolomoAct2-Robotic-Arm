## Step 3: top-team replay videos (8 hard-pick episodes that 6+ top teams solve and our board run failed)

Tool: `risers/overnight/team_strips.py` (6 exterior frames per run: 3 top teams that solved the episode, then us).

| Episode | Top-team success times | Our board run | What our robot did |
|---|---|---|---|
| comb | 9.5 s, 17.1 s, 19.3 s | fail (21 s) | Same path as the top teams; reached the comb late |
| knife | 8.6 s, 11.4 s, 12.7 s | fail | Same path; reached the knife late |
| potato | 6.9 s, 15.2 s, ~10 s | fail | Same path; closed on the potato only at the end |
| album | about 13 s | fail | Same path; at the album at the end, not lifted |
| butter knife | about 5 s, 13.0 s, 19.3 s | fail | Went to another place first, then turned back |

Findings:
- In most episodes our robot moves along about the same path as the top teams' robots. It arrives late and runs out of
  time. This agrees with the step 1 result: speed is the main problem.
- In some episodes our robot goes to the wrong place first. This costs time too.
- We saw no grasp method of the top teams that differs from ours. Their robots move without stops.
- Limit: 6 frames per episode show the path, not the details of the grasp.
