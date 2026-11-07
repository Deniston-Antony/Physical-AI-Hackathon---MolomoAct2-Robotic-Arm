"""Board successes per task set for two submissions, from their result.json files.

Usage: python3 -I board_by_set.py <episode_sets.json> <result.json A> <result.json B>
episode_sets.json gives the set of each board episode, in the board order (the order of `scores.sim_time`).
A failure runs to 1 s before its time limit. A success can also end there, so the success count of each task
in `scores.per_task` settles those episodes.
"""

import collections
import json
import statistics as st
import sys


def successes(path: str, sets: list[dict]) -> tuple[list[bool], list[float]]:
    scores = json.load(open(path))['scores']
    eps = scores['sim_time']
    assert [e['task'] for e in eps] == [s['task'] for s in sets], 'the episode order differs'
    by_task = collections.defaultdict(list)
    for i, e in enumerate(eps):
        by_task[e['task']].append(i)
    ok = [False] * len(eps)
    for task, idx in by_task.items():
        count = scores['per_task'][task]['successes']
        early = [i for i in idx if eps[i]['sim_s'] < eps[i]['limit_s'] - 1.001]
        late = [i for i in idx if i not in early]
        assert len(early) <= count <= len(idx), task
        for i in early + late[: count - len(early)]:
            ok[i] = True
    assert sum(ok) == round(scores['primary'] * len(eps))
    return ok, [e['sim_s'] for e in eps]


def main(sets_path: str, a_path: str, b_path: str):
    sets = json.load(open(sets_path))
    (a, ta), (b, tb) = successes(a_path, sets), successes(b_path, sets)
    groups = collections.defaultdict(list)
    for i, s in enumerate(sets):
        groups[s['set'].removeprefix('Franka').removesuffix('Bench')].append(i)
    print('| Set | Episodes | A | B | A - B | A median s | B median s |')
    print('|---|---|---|---|---|---|---|')
    for name, idx in sorted(groups.items()):
        shared = [i for i in idx if a[i] and b[i]]
        med_a = f'{st.median(ta[i] for i in shared):.1f}' if shared else '-'
        med_b = f'{st.median(tb[i] for i in shared):.1f}' if shared else '-'
        na, nb = sum(a[i] for i in idx), sum(b[i] for i in idx)
        print(f'| {name} | {len(idx)} | {na} | {nb} | {na - nb:+d} | {med_a} | {med_b} |')
    shared = [i for i in range(len(sets)) if a[i] and b[i]]
    print(f'\nA {sum(a)}, B {sum(b)}. Only A solved {sum(x and not y for x, y in zip(a, b))}, '
          f'only B solved {sum(y and not x for x, y in zip(a, b))}.')
    print(f'Median time on the {len(shared)} episodes both solved: A {st.median(ta[i] for i in shared):.1f} s, '
          f'B {st.median(tb[i] for i in shared):.1f} s. (The median columns use the same episodes per set.)')


if __name__ == '__main__':
    main(*sys.argv[1:4])
