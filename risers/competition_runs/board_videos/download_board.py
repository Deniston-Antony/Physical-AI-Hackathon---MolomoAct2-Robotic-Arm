"""Download the public replays of the best runs on the stage-1 board (molmo.competition_v2) to the SSD.

For each team it saves the replay data (task and outcome of each of the 320 episodes) and the 3 camera videos of
each episode. It reads the board without the API key: the board and its replays are public.
The rules forbid training on these runs ("Do not train on data from our evaluation runs, other than the results of
your own team"). Use them only to compare.

Usage, from the positronic folder:
  uv run --locked python ../competition_runs/board_videos/download_board.py [--top 5] [--also d2504d]
A run again skips the files that are already there. A team with a new best run gets a new folder.
"""

import argparse
import concurrent.futures
import csv
import datetime
import json
import re
from pathlib import Path

import httpx
from platform_client.client import PlatformClient

OUT = Path('/media/antonlucy/Deniston2TB/Physical AI Hackathon - trained_models/board_replays')
EVAL = 'molmo.competition_v2'
OUR_TAG = 'd2504d'


def fetch(h: httpx.Client, url: str, path: Path) -> int:
    if path.exists() and path.stat().st_size > 0:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            r = h.get(url)
            r.raise_for_status()
            part = path.with_suffix('.part')
            part.write_bytes(r.content)
            part.rename(path)
            return len(r.content)
        except httpx.HTTPError:
            if attempt == 2:
                raise
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--top', type=int, default=5, help='the number of ranked teams from the top')
    parser.add_argument('--also', nargs='*', default=[OUR_TAG], help='more team tags (default: The Risers)')
    args = parser.parse_args()
    client = PlatformClient(None)
    client.api_key = None
    with client:
        board = next(b for b in client.list_boards().boards if str(b.eval) == EVAL).board
        rows = client.rankings(board=board).rankings
    now = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H%MZ')
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot = [
        {'rank': r.rank, 'team': f'{r.display_name}#{r.tag}', 'tag': r.tag, 'score': r.scores.primary,
         'submission_id': str(r.submission_id), 'submitted_at': r.submitted_at.isoformat(),
         'baseline': r.baseline is not None}
        for r in rows
    ]
    (OUT / f'board_{now}.json').write_text(json.dumps(snapshot, indent=1))
    chosen = [r for r in rows if r.rank is not None and r.rank <= args.top] + [
        r for r in rows if r.tag in args.also and not (r.rank is not None and r.rank <= args.top)
    ]
    with httpx.Client(timeout=120, follow_redirects=True) as h:
        for r in chosen:
            if r.replay is None:
                print(f'{r.display_name}#{r.tag}: no replay yet')
                continue
            name = re.sub(r'[^A-Za-z0-9]+', '_', r.display_name).strip('_')
            folder = OUT / f'{name}_{r.tag}_{r.submission_id}'
            data = h.get(r.replay.data_url).raise_for_status().json()
            folder.mkdir(exist_ok=True)
            (folder / 'replay.json').write_text(json.dumps(data))
            with open(folder / 'outcomes.csv', 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['index', 'task', 'outcome', 'duration_s'])
                for e in data['episodes']:
                    w.writerow([e['index'], e['values']['task'], e['values']['outcome'], e['duration_s']])
            jobs = [(v['url'], folder / v['src']) for e in data['episodes'] for v in e['videos']]
            with concurrent.futures.ThreadPoolExecutor(4) as pool:
                got = sum(pool.map(lambda job: fetch(h, *job), jobs))
            ok = sum(e['values']['outcome'] == 'Success' for e in data['episodes'])
            print(f'rank {r.rank}: {r.display_name}#{r.tag} {r.scores.primary:.4f} ({ok}/{len(data["episodes"])}), '
                  f'{len(jobs)} videos, {got / 1e6:.0f} MB new -> {folder.name}', flush=True)
    print(f'board snapshot: board_{now}.json; folder: {OUT}')


if __name__ == '__main__':
    main()
