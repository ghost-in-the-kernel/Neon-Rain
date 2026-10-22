"""TODO.md is a chain in order, its first open item has a check, and DONE.md shares none (test/test_todo.py)."""
import re

ITEM = re.compile(r"^### (\d+)\.(\d+) ", re.MULTILINE)
PHASE = re.compile(r"^## Phase (\d+)", re.MULTILINE)


def items(text: str) -> list[tuple[int, int]]:
    """The items' numbers in file order: "### 0.5 x" gives (0, 5)."""
    return [(int(phase), int(step)) for phase, step in ITEM.findall(text)]


def order_problems(todo: str) -> list[str]:
    """Phases ascending, items ascending, and each item under its own phase's heading."""
    found = []
    phases = [int(p) for p in PHASE.findall(todo)]
    if phases != sorted(phases):
        found.append(f"phases out of order: {phases}")
    numbers = items(todo)
    if numbers != sorted(numbers):
        found.append(f"items out of order: {[f'{a}.{b}' for a, b in numbers]}")
    for match in ITEM.finditer(todo):
        heading = PHASE.findall(todo[: match.start()])
        if not heading or int(heading[-1]) != int(match.group(1)):
            found.append(f"item {match.group(1)}.{match.group(2)} is not under Phase {match.group(1)}")
    return found


def first_item_problems(todo: str) -> list[str]:
    """The first open item's body (up to the next heading) has a `Check:` line."""
    match = ITEM.search(todo)
    if match is None:
        return []
    rest = todo[match.end():]
    following = re.search(r"^#{2,3} ", rest, flags=re.MULTILINE)
    body = rest[: following.start()] if following else rest
    if re.search(r"^Check:", body, flags=re.MULTILINE):
        return []
    return [f"the first open item, {match.group(1)}.{match.group(2)}, has no Check: line"]


def problems(todo: str, done: str) -> list[str]:
    """Everything wrong with TODO.md given DONE.md; [] when the chain holds."""
    both = sorted(set(items(todo)) & set(items(done)))
    shared = [f"{a}.{b} is in both TODO.md and DONE.md" for a, b in both]
    return order_problems(todo) + first_item_problems(todo) + shared
