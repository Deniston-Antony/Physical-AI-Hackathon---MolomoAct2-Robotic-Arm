# Local tests, 8 November: close tasks and the blocked camera

MolmoBot-Img-DROID with the v3 settings (half overlap, left camera, 12 actions per call, 3 flow steps, still-arm rule) and the changes named per run. Local PC (RTX 4070).

| Run | Result |
|---|---|
| cl_base | close hard 4/15, other blocked-camera episodes 1/2; pushes 0, camera switches 0, still-arm switches 0 |
| cl_push | close hard 7/15, other blocked-camera episodes 0/0; pushes 28, camera switches 0, still-arm switches 0 |
| cl_cam | close hard 6/15, other blocked-camera episodes 1/2; pushes 0, camera switches 6, still-arm switches 0 |
| cl_both | close hard 1/3, other blocked-camera episodes 0/0; pushes 6, camera switches 2, still-arm switches 0 |
| img_v4 | close hard 7/15, other blocked-camera episodes 1/2; pushes 26, camera switches 5, still-arm switches 0 |

| Board # | Episode | v3 board | Top 7 | Left camera blocked | cl_base | cl_push | cl_cam | cl_both | img_v4 |
|---|---|---|---|---|---|---|---|---|---|
| 9 | close the cabinet. | no | 3/7 |  | no | no | no | no | no |
| 19 | close the table. | OK | 6/7 | yes | OK 27.0 s | OK 11.4 s | OK 11.6 s | OK 11.0 s | OK 11.9 s |
| 29 | close the brown wooden desk. | no | 0/7 | yes | no | no | no | no | no |
| 39 | close the oven. | no | 1/7 | yes | no | no | no |  | no |
| 49 | close the brown wooden desk. | OK | 5/7 |  | OK 14.5 s | OK 8.4 s | OK 15.8 s |  | OK 8.0 s |
| 59 | close the white dresser. | OK | 7/7 |  | OK 3.6 s | OK 4.5 s | no |  | OK 5.0 s |
| 69 | close the desk. | no | 1/7 |  | no | no | no |  | no |
| 79 | close the white table. | no | 3/7 | yes | no | no | OK 27.5 s |  | OK 23.3 s |
| 89 | close the table. | no | 2/7 |  | no | no | no |  | no |
| 99 | close the light brown table. | no | 1/7 |  | no | no | no |  | no |
| 109 | close the dresser. | no | 4/7 |  | no | OK 21.8 s | no |  | OK 13.7 s |
| 119 | close the white wooden dresser. | OK | 7/7 |  | OK 4.2 s | OK 4.2 s | OK 4.2 s |  | OK 4.2 s |
| 129 | close the dresser. | no | 6/7 |  | no | OK 14.1 s | OK 6.8 s |  | OK 13.7 s |
| 139 | close the dark dresser. | no | 2/7 | yes | no | no | no |  | no |
| 149 | close the dresser. | no | 2/7 |  | no | OK 6.9 s | OK 15.8 s |  | no |
| 118 | open the table. | no | 0/7 | yes | no |  | no |  | no |
| 214 | pick up the screwdriver. | OK | 7/7 | yes | OK 15.8 s |  | OK 19.8 s |  | OK 14.5 s |
