"""Task wording for MolmoBot: the wording of its training data, and a task of several objects as steps in order.

MolmoBot learned pick tasks ("pick up the X.") and pick-and-place tasks ("Pick up the X and place it in or on the Y").
Other benchmarks word a task in other ways ("Put the X in the Y", "Stack the X on the Y", "Grab a X"). `steps` gives
the steps of a task in the training wording; a task in the board wording keeps its text, as one step.
"""

import re

_FLAGS = re.IGNORECASE
# The board wordings: pick, pick-and-place ("on", "in or on", "next to"), open and close. They keep their text.
_BOARD = re.compile(
    r'(?:pick up the .+ and place it (?:on|in or on|next to) the .+|pick up the (?:(?! and (?:place|put) ).)+|'
    r'open the .+|close the .+)',
    _FLAGS,
)
# The place words, longest first. Those of `_IN_OR_ON` mean "in or on" the target; a step keeps the others.
_PLACE = (
    r'(?P<place>in the center of|in front of|on top of|to the left of|to the right of|next to|outside of|behind|into|'
    r'inside|onto|in|on|to)'
)
_IN_OR_ON = r'in|into|inside|on|onto|on top of|to'
# A target that is not one object: the task keeps its text.
_NOT_A_TARGET = re.compile(r'\b(?:tower|order|row|line)\b|^(?:left|right)(?: side)?$', _FLAGS)
# Where the item is now: not part of its name.
_FROM = re.compile(r' (?:from|out of|off) .*$', _FLAGS)
# "pick up / grab / select / take the X and place / put it <place> the Y"
_PICK_THEN_PLACE = re.compile(
    rf'(?:pick up|grab|select|take) (?:the|a|an) (?P<item>.+?) and (?:place|put) (?:it|them) {_PLACE} (?:the|a) (?P<target>.+)',
    _FLAGS,
)
# "remove / take the X from / out of / off the Y and put / place it <place> the Z"
_MOVE_FROM = re.compile(
    rf'(?:remove|take) the (?P<item>.+?) (?:from|out of|off) the .+? and (?:place|put) (?:it|them|the .+?) {_PLACE} '
    r'(?:the|a) (?P<target>.+)',
    _FLAGS,
)
# "put / place / move / stack the X <place> the Y". The item can hold a place ("the spoon that's in the bowl"), so the
# place is the last one.
_PUT = re.compile(rf'(?:put|place|move|stack) the (?P<item>.+) {_PLACE} (?:the|a) (?P<target>.+)', _FLAGS)
# "grab / select a X"
_GRAB = re.compile(r'(?:grab|select) (?:the|a|an) (?P<item>[^,]+)', _FLAGS)
# Items of a task with several: "the A and the B", "A, B and C", "A then B". "or" means one of them: the first.
_SPLIT = re.compile(r',? (?:and|then|and then) (?:the )?|, (?:the )?', _FLAGS)
_OR = re.compile(r' or (?:the )?', _FLAGS)
# An item that is not one object: "all ...", a count, "any".
_NOT_ONE = re.compile(r'^(?:all|any|\d|one|two|three)\b|\(', _FLAGS)


def _clean(task: str) -> str:
    return ' '.join(task.strip().rstrip('.').split())


def _step(item: str, place: str, target: str) -> str:
    item = re.sub(r' (?:away|anywhere)$', '', _FROM.sub('', item.strip()), flags=_FLAGS)
    if re.fullmatch(_IN_OR_ON, place, _FLAGS):
        place = 'in or on'
    return f'Pick up the {item} and place it {place.lower()} the {target.strip()}'


def steps(task: str, split: bool) -> list[str]:
    """The steps of ``task`` in MolmoBot's training wording, in the order of the task, or ``[task]`` as it is.

    Without ``split``, a task of several objects keeps its text.
    """
    text = _clean(task)
    if _BOARD.fullmatch(text):
        return [task]
    for pattern in (_MOVE_FROM, _PICK_THEN_PLACE, _PUT):
        match = pattern.fullmatch(text)
        if match is None:
            continue
        item, place, target = match['item'], match['place'], match['target']
        if _NOT_ONE.search(item) or _NOT_A_TARGET.search(target):
            return [task]
        if _OR.search(item):
            item = _OR.split(item)[0]
        items = [x for x in _SPLIT.split(item) if x]
        if len(items) == 1:
            return [_step(items[0], place, target)]
        if not split or any(_NOT_ONE.search(x) for x in items):
            return [task]
        return [_step(x, place, target) for x in items]
    match = _GRAB.fullmatch(text)
    if match is not None and not _NOT_ONE.search(match['item']) and not _SPLIT.search(match['item']):
        return [f'pick up the {match["item"]}.']
    return [task]
