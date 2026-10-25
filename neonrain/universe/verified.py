"""Read a dataset's files only after their hashes check out (R-006; the review of J-048 found nothing did).

A dataset in the data repository is a folder of files and an `index.tsv` (`key<TAB>file<TAB>sha256`, one line per
file), and the SHA-256 of that index is the hash on the dataset's row of `data/MANIFEST.md`. Any loader of such a
dataset goes through `read_verified`: it hashes the index against the manifest row, then hashes each file it is
asked for against its index line, and **returns nothing unless every one matches**. A file's bytes are read once,
hashed, and the same bytes returned, so the file cannot change between the check and the read. Pure apart from
reading files: no clock, no network.
"""
import hashlib
from pathlib import Path

HASH_LENGTH = 64


class Unverified(Exception):
    """A dataset refused: the message names the file or row and what did not match."""


def sha256_bytes(data: bytes) -> str:
    """The SHA-256 of some bytes, hex."""
    return hashlib.sha256(data).hexdigest()


def manifest_hash(manifest: str, dataset: str) -> str:
    """The SHA-256 on a manifest row, whose last cell ends `sha256 <64 hex>`; refuses a row absent or without one."""
    for line in manifest.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] == dataset:
            words = cells[-1].split()
            if len(words) >= 2 and words[0] == "sha256" and len(words[1]) == HASH_LENGTH:
                return words[1]
            raise Unverified(f"the manifest row {dataset} has no 'sha256 <hash>' at the start of its last cell")
    raise Unverified(f"the manifest has no row {dataset}")


def parse_index(text: str) -> dict[str, tuple[str, str]]:
    """The index's lines as key -> (file, sha256); refuses a malformed line, a key twice, a file that is not a plain name."""
    entries: dict[str, tuple[str, str]] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        cells = line.split("\t")
        if len(cells) != 3 or len(cells[2]) != HASH_LENGTH:
            raise Unverified(f"index line {number} is not 'key<TAB>file<TAB>sha256'")
        key, name, digest = cells
        if key in entries:
            raise Unverified(f"index line {number} repeats the key {key}")
        if name != Path(name).name or name in ("", ".."):
            raise Unverified(f"index line {number} names {name!r}, which is not a file in the folder")
        entries[key] = (name, digest)
    return entries


def read_verified(folder: Path, manifest: str, dataset: str, keys: list[str] | None = None) -> dict[str, bytes]:
    """The bytes of the index's files (all, or those under `keys`), by key, once index and files all hash as recorded.

    Refuses, having returned nothing, an index that does not hash to the manifest row, a key the index lacks, a file
    that is missing, and a file that does not hash to its index line. Every file is read and checked before any is
    returned, so a caller never sees the bytes of a dataset part-way verified.
    """
    index_bytes = (folder / "index.tsv").read_bytes() if (folder / "index.tsv").is_file() else None
    if index_bytes is None:
        raise Unverified(f"{folder} has no index.tsv")
    wanted = manifest_hash(manifest, dataset)
    if sha256_bytes(index_bytes) != wanted:
        raise Unverified(f"index.tsv hashes to {sha256_bytes(index_bytes)}, the manifest says {wanted}: refusing every file")
    entries = parse_index(index_bytes.decode())
    chosen = list(entries) if keys is None else keys
    missing = [key for key in chosen if key not in entries]
    if missing:
        raise Unverified(f"the index has no key {missing[0]}")
    found: dict[str, bytes] = {}
    for key in chosen:
        name, digest = entries[key]
        path = folder / name
        if not path.is_file():
            raise Unverified(f"{name} is listed in the index and absent from {folder}")
        data = path.read_bytes()
        if sha256_bytes(data) != digest:
            raise Unverified(f"{name} hashes to {sha256_bytes(data)}, the index says {digest}: refusing")
        found[key] = data
    return found
