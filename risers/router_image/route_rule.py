"""Which model a task text belongs to: MolmoSpaces wordings go to v3 (MolmoBot), anything else to FLUX.

MolmoSpaces (the Franka benchmarks of the platform) words every task in one of these forms:
  'pick up the X.'                                   'open the X.'   'close the X.'
  'pick up the X and place it on the Y.'
  'Pick up the X and place it in or on the Y'        'Pick up the X and place it next to the Y'
Any other wording (RoboLab, the real robot) goes to FLUX.
"""
import re

_MOLMO = [
    re.compile(r'^pick up the [^.]+\.$'),
    re.compile(r'^(open|close) the [^.]+\.$'),
    re.compile(r'^pick up the [^.]+ and place it on the [^.]+\.$'),
    re.compile(r'^Pick up the .+ and place it (in or on|next to) the [^.]+$'),
]


def is_molmospaces(task: str) -> bool:
    t = task.strip()
    return any(p.match(t) for p in _MOLMO)
