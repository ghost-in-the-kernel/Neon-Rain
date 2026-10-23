"""Which surviving mutants docs/MUTATION.md does not explain (scripts/precommit.sh, R-015a)."""
import re

UNFINISHED: tuple[str, ...] = ("survived", "no tests", "timeout", "suspicious", "segfault", "not checked")
LINE = re.compile(r"^\s*(\S+): (.+)$")
PRAGMA = re.compile(r"#\s*pragma:\s*no mutate")


def survivors(results: str) -> list[str]:
    """The mutants `mutmut results` lists as anything but killed: "    a.b__mutmut_3: survived" gives ["a.b__mutmut_3"]."""
    found = []
    for line in results.splitlines():
        match = LINE.match(line)
        if match and match.group(2) in UNFINISHED:
            found.append(match.group(1))
    return found


def explained(mutation_doc: str) -> set[str]:
    """The mutant names in the first column of docs/MUTATION.md's table: "| `a__mutmut_3` | ..." gives {"a__mutmut_3"}."""
    return set(re.findall(r"^\| `([^`]+__mutmut_\d+)` \|", mutation_doc, flags=re.MULTILINE))


def unexplained(results: str, mutation_doc: str) -> list[str]:
    """Survivors with no line in docs/MUTATION.md; the push is refused while this is not empty."""
    known = explained(mutation_doc)
    return [name for name in survivors(results) if name not in known]


def stale(results: str, mutation_doc: str) -> list[str]:
    """Lines in docs/MUTATION.md for mutants that no longer survive (renamed by an edit, or killed): to remove."""
    return sorted(explained(mutation_doc) - set(survivors(results)))


def exempt_files(mutation_doc: str) -> set[str]:
    """The files named in the first column of MUTATION.md's "Exempt from mutation" table."""
    sections = re.findall(r"^## Exempt from mutation$.*?(?=^## |\Z)", mutation_doc, flags=re.MULTILINE | re.DOTALL)
    return {name for section in sections for name in re.findall(r"^\| `([^`]+)` \|", section, flags=re.MULTILINE)}


def pragma_problems(sources: dict[str, str], mutation_doc: str) -> list[str]:
    """Files with a `pragma: no mutate` that MUTATION.md's exemptions do not list: an exemption is Ghost's to grant."""
    listed = exempt_files(mutation_doc)
    return [f"{path} has a 'no mutate' pragma not listed in docs/MUTATION.md's exemptions"
            for path, text in sorted(sources.items()) if PRAGMA.search(text) and path not in listed]
