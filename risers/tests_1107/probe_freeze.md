# Probe: ask MolmoBot again at frozen moments

Median move (rad) of 3 answers. A frozen answer moves about 0.005 rad. Moves above 0.03 rad are in bold.

| Episode | State | t (s) | same | other camera | pick-only task | pick-only + other camera | training wording | 10 flow steps |
|---|---|---|---|---|---|---|---|---|
| pick up the spatula and place it on the bowl. | solved | 1.0 | **0.775** | **0.881** | **0.638** | **0.787** | **0.865** | **0.807** |
| pick up the bottle and place it on the bowl. | frozen | 8.0 | 0.016 | 0.011 | **0.586** | **0.567** | 0.013 | 0.014 |
| pick up the bottle and place it on the bowl. | frozen | 20.0 | 0.013 | 0.016 | **0.516** | **0.548** | 0.012 | 0.011 |
| pick up the bowl and place it on the dish. | frozen | 8.0 | 0.012 | **0.586** | **0.556** | **0.604** | 0.010 | 0.009 |
| pick up the bowl and place it on the dish. | frozen | 20.0 | 0.011 | **0.548** | **0.543** | **0.569** | 0.011 | 0.012 |
| pick up the card and place it on the bowl. | failed | 1.0 | **0.471** | **1.046** | **0.833** | **1.063** | **0.679** | **0.953** |
| pick up the knife and place it on the bowl. | frozen | 8.0 | **0.544** | **0.552** | **0.738** | **0.603** | **0.521** | **0.814** |
| pick up the knife and place it on the bowl. | frozen | 20.0 | **0.752** | **0.624** | **0.661** | **0.638** | **0.579** | **0.560** |
| pick up the pointed metal awl and place it on the  | failed | 1.0 | **1.012** | **1.031** | **0.240** | **0.466** | **0.898** | **0.362** |
| pick up the apple and place it on the bowl. | frozen | 8.0 | **0.531** | **0.538** | **0.568** | **0.605** | **0.511** | **0.493** |
| pick up the apple and place it on the bowl. | frozen | 20.0 | **0.454** | **0.552** | **0.554** | **0.480** | **0.597** | **0.664** |
| pick up the spoon and place it on the rustic clay  | frozen | 8.0 | 0.008 | 0.008 | **0.406** | **0.464** | 0.021 | 0.013 |
| pick up the spoon and place it on the rustic clay  | frozen | 20.0 | 0.012 | 0.020 | **0.639** | **0.609** | 0.011 | 0.017 |
| pick up the towel and place it on the bowl. | solved | 1.0 | **0.629** | **0.606** | **0.629** | **0.606** | **0.625** | **0.615** |
| pick up the fork and place it on the bowl. | frozen | 8.0 | **0.944** | **0.722** | **1.046** | **0.872** | **0.804** | 0.014 |
| pick up the fork and place it on the bowl. | frozen | 20.0 | **0.906** | **1.102** | **0.992** | **0.963** | **0.810** | **0.884** |
| pick up the bowl and place it on the bowl. | frozen | 8.0 | **0.164** | **0.121** | **0.264** | **0.321** | **0.189** | **0.160** |
| pick up the bowl and place it on the bowl. | frozen | 20.0 | **0.547** | **0.560** | **0.534** | **0.561** | **0.536** | **0.550** |
| pick up the gray metal ring and place it on the bo | failed | 1.0 | **0.286** | **0.369** | **0.529** | **0.420** | **0.351** | **0.430** |
| pick up the watch and place it on the wooden box. | frozen | 8.0 | 0.010 | 0.012 | **0.550** | **0.391** | 0.009 | 0.011 |
| pick up the watch and place it on the wooden box. | frozen | 20.0 | 0.009 | 0.008 | **0.488** | **0.674** | 0.008 | 0.011 |
| pick up the ladle and place it on the bowl. | frozen | 8.0 | 0.009 | 0.009 | **0.689** | **0.531** | **0.583** | 0.025 |
| pick up the ladle and place it on the bowl. | frozen | 20.0 | **0.646** | 0.011 | **0.620** | **0.544** | **0.622** | **0.607** |
| pick up the fork and place it on the bowl. | frozen | 8.0 | 0.015 | 0.008 | **0.527** | **0.436** | 0.016 | 0.011 |
| pick up the fork and place it on the bowl. | frozen | 20.0 | 0.012 | 0.011 | **0.478** | **0.460** | 0.013 | 0.012 |
| pick up the smart speaker and place it on the rust | frozen | 8.0 | **0.214** | **0.720** | **0.812** | **0.985** | **0.141** | **0.615** |
| pick up the smart speaker and place it on the rust | frozen | 20.0 | 0.010 | 0.009 | **0.423** | **0.529** | 0.007 | 0.008 |
| pick up the potato and place it on the bowl. | frozen | 8.0 | 0.015 | 0.011 | **0.481** | **0.517** | 0.016 | 0.010 |
| pick up the potato and place it on the bowl. | frozen | 20.0 | 0.011 | 0.009 | **0.536** | **0.495** | 0.009 | 0.010 |
| pick up the bottle and place it on the bowl. | frozen | 8.0 | **0.521** | 0.010 | **0.572** | **0.362** | 0.018 | **0.526** |
| pick up the bottle and place it on the bowl. | frozen | 20.0 | **0.461** | 0.015 | **0.573** | **0.390** | **0.517** | 0.014 |
| pick up the cup and place it on the bowl. | frozen | 8.0 | 0.012 | **0.502** | **0.495** | **0.552** | 0.011 | 0.013 |
| pick up the cup and place it on the bowl. | frozen | 20.0 | 0.011 | **0.523** | **0.520** | **0.505** | 0.015 | 0.012 |

Frozen moments where the answer moves above 0.03 rad (of 28):

- same: 12
- other camera: 13
- pick-only task: 28
- pick-only + other camera: 28
- training wording: 12
- 10 flow steps: 10
