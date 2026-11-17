"""Measure the grasp timeline of each board episode of each downloaded team from its wrist video.

Usage: ~/molmobot_src/venv/bin/python competition_runs/board_videos/measure_moves.py
For each team folder on the SSD it writes moves.json: per board episode the outcome, the duration, the time of the
first close and the number of closes (from grip_from_video.py; first close within 1 s in about 3 of 4 episodes).
A team folder that has moves.json is skipped.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grip_from_video as G  # noqa: E402

REPLAYS = Path('/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/board_replays')


def main() -> None:
    for folder in sorted(REPLAYS.iterdir()):
        if not (folder / 'replay.json').exists() or (folder / 'moves.json').exists():
            continue
        eps = json.loads((folder / 'replay.json').read_text())['episodes']
        out = []
        for e in eps:
            closure, times = G.closure_series(folder / 'episodes' / str(e['index']) / 'image.wrist.mp4')
            ev = G.grasp_events(closure, times)
            out.append({'index': e['index'], 'ok': e['values']['outcome'] == 'Success', 'duration_s': e['duration_s'],
                        'first_close_s': ev['first_close_s'], 'closes': ev['closes'],
                        'close_times': [round(t, 2) for t in ev['close_times']]})
        (folder / 'moves.json').write_text(json.dumps(out))
        print(f'{folder.name}: {len(out)} episodes measured', flush=True)


if __name__ == '__main__':
    main()
