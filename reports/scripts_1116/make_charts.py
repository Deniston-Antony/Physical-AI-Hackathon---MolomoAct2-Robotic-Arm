"""Make the charts of the README update of 16 November (work of 10 to 14 November) in reports_1116/images/.

Usage: python3 reports_1116/make_charts.py
The board numbers come from the result.json file of each submission (competition_runs/), the cloud test numbers from
tests_1108/results_cloud_*.md and tests_robolab/results_cloud_*.md, the real-robot numbers from the platform's check
of submission 2a74d6b52a67c4be.
"""

from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / 'images'

# Reference palette (dataviz skill, light mode), slots in fixed order.
BLUE, ORANGE, AQUA, YELLOW = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
INK, INK2, GRID, REF = '#0b0b0b', '#52514e', '#e4e3df', '#9a9893'
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
    'xtick.color': INK2, 'ytick.color': INK2, 'axes.titlesize': 12, 'axes.titleweight': 'bold',
    'axes.titlecolor': INK, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 150,
})


def finish(fig, ax, name: str, axis: str = 'x') -> None:
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / name, facecolor='white')
    plt.close(fig)


def scores_chart() -> None:
    rows = [('v3: 3 flow steps + still-arm rule (7 Nov)', 219), ('v4-push (7 Nov)', 217), ('v4 (7 Nov)', 215),
            ('v3 again (8 Nov)', 218), ('v5 (9 Nov)', 215), ('v5-touch (9 Nov)', 197),
            ('v6: both experts on the GPU (10 Nov)', 208), ('v3-jpeg: JPEG frames (11 Nov)', 210),
            ('v3-jpeg-rl: RoboLab still-arm wording (13 Nov)', 212),
            ('v3-jpeg-rl2: + wording, steps, deeper grasp (14 Nov)', 214)]
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    y = list(range(len(rows)))[::-1]
    ax.axvspan(213, 225, color=GRID, alpha=0.6, linewidth=0)
    ax.text(213.3, y[-1] - 0.75, 'v3 ± 6 (one-run noise)', color=INK2, fontsize=8)
    ax.hlines(y, 190, [r[1] for r in rows], color=GRID, linewidth=2)
    ax.scatter([r[1] for r in rows], y, s=70, color=BLUE, zorder=3, edgecolor='white', linewidth=2)
    for yi, (_, v) in zip(y, rows):
        ax.annotate(f'{v} ({v / 3.2 + 1e-9:.1f}%)', (v, yi), xytext=(8, -4), textcoords='offset points', color=INK, fontsize=9)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.set_xlim(190, 235)
    ax.set_ylim(y[-1] - 1.0, y[0] + 0.6)
    ax.set_xlabel('Episodes solved of 320 (board molmo.competition_v2)')
    ax.set_title('Board submissions since image v3', loc='left')
    finish(fig, ax, 'chart_board_scores.png')


def bars(name: str, title: str, xlabel: str, rows: list[tuple[str, float, str]], xmax: float, fmt: str = '{:g}',
         height: float = 3.2, note: str | None = None) -> None:
    fig, ax = plt.subplots(figsize=(8.8, height))
    y = list(range(len(rows)))[::-1]
    ax.barh(y, [r[1] for r in rows], 0.62, color=[r[2] for r in rows], edgecolor='white', linewidth=1)
    for yi, (_, v, _) in zip(y, rows):
        ax.text(v + xmax * 0.01, yi, fmt.format(v), va='center', color=INK, fontsize=9)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.set_xlim(0, xmax)
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc='left')
    if note:
        fig.text(0.01, 0.01, note, color=INK2, fontsize=8)
    finish(fig, ax, name)


def real_robot_chart() -> None:
    labels = ['Success', 'Failure', 'Ran out of time', 'Safety stop']
    ours, public = [0, 56, 44, 0], [42, 30, 26, 2]
    fig, ax = plt.subplots(figsize=(8.8, 3.4))
    x = range(len(labels))
    w = 0.38
    ax.bar([i - w / 2 - 0.01 for i in x], ours, w, color=BLUE, label='Our v3 (27 episodes)', edgecolor='white')
    ax.bar([i + w / 2 + 0.01 for i in x], public, w, color=ORANGE, label='Public models (50 episodes)',
           edgecolor='white')
    for i, (a, b) in enumerate(zip(ours, public)):
        ax.text(i - w / 2, a + 1, f'{a}%', ha='center', color=INK, fontsize=9)
        ax.text(i + w / 2, b + 1, f'{b}%', ha='center', color=INK, fontsize=9)
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 65)
    ax.set_ylabel('Share of episodes')
    ax.set_title('Real Franka robot, 9 tasks (platform check of 10 Nov)', loc='left')
    ax.legend(frameon=False, fontsize=8.5)
    finish(fig, ax, 'chart_real_robot.png', axis='y')


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scores_chart()
    bars('chart_flux.png', 'Cloud tests of FLUX 3 Action in 24 GB (40 episodes, 12-13 Nov)', 'Episodes solved of 40',
         [('FLUX as published', 15, BLUE), ('FLUX + v3 rules', 13, BLUE), ('Try 3: request earlier', 14, BLUE),
          ('Try 4: both cameras, whole plan', 18, BLUE), ('Try 4: both cameras, 1.03 s plan', 19, BLUE),
          ('Try 5: firm gripper', 14, BLUE), ('Try 5: firm gripper + hybrid timing', 20, BLUE),
          ('v3 (MolmoBot), same episodes', 26.5, REF)], 30, height=3.8)
    bars('chart_rules_board.png', 'New rules on 40 board episodes (cloud, 14 Nov)', 'Episodes solved of 40',
         [('Control (no new rule)', 22, BLUE), ('All new rules', 25, BLUE), ('Deeper grasp after a miss', 28, BLUE),
          ('Vote before a close', 27, BLUE), ('v3 on the same episodes (10-11 Nov)', 26.5, REF)], 32, height=2.9)
    bars('chart_rules_robolab.png', 'RoboLab, the 12 tasks of the platform (14 Nov)', 'Mean subtask score',
         [('Control (v3-jpeg-rl)', 0.36, BLUE), ('Training wording + steps', 0.36, BLUE), ('All new rules', 0.46, BLUE),
          ('Platform run of v3 (10 Nov)', 0.403, REF), ('pi0.5 baseline (platform)', 0.556, REF)], 0.7,
         fmt='{:.2f}', height=2.9)
    real_robot_chart()


if __name__ == '__main__':
    main()
