"""Which surviving mutants docs/MUTATION.md does not explain (scripts/precommit.sh, R-015a)."""
import re

UNFINISHED: tuple[str, ...] = ("survived", "no tests", "timeout", "suspicious", "segfault", "not checked")


def survivors(results: str) -> list[str]:
    """The mutants `mutmut results` lists as anything but killed: "    a.b__mutmut_3: survived" gives ["a.b__mutmut_3"]."""
    found = []
    for line in results.splitlines():
        name, _, status = line.strip().rpartition(": ")
        if name and status in UNFINISHED:
            found.append(name)
    return found


def explained(mutation_doc: str) -> set[str]:
    """The mutant names in the first column of docs/MUTATION.md's table: "| `a__mutmut_3` | ..." gives {"a__mutmut_3"}."""
    return set(re.findall(r"^\| `([^`]+)` \|", mutation_doc, flags=re.MULTILINE))


def unexplained(results: str, mutation_doc: str) -> list[str]:
    """Survivors with no line in docs/MUTATION.md; the push is refused while this is not empty."""
    known = explained(mutation_doc)
    return [name for name in survivors(results) if name not in known]


def stale(results: str, mutation_doc: str) -> list[str]:
    """Lines in docs/MUTATION.md for mutants that no longer survive (renamed by an edit, or killed): to remove."""
    return sorted(explained(mutation_doc) - set(survivors(results)))
