"""The artifact store (R-016 b): files kept in a private git repository, each named by its SHA-256.

Layout inside the artifacts repository: `<first two hex characters>/<64-character hash>`, on branch `main`, no
extension, no other file. The two-character fan-out keeps any one directory under 256 siblings' worth of entries
(GitHub lists a directory badly past a few thousand); the name is the content, so a blob never changes and a
second put of the same bytes is no change at all. The main repository records only the hash it depends on.

The clone lives outside the main repository, at `$NEONRAIN_ARTIFACTS_CLONE` or `~/.cache/neon-rain/artifacts`, so
no blob can be committed to the code repository by accident (R-006). The remote is `$NEONRAIN_ARTIFACTS_REMOTE`
or the private GitHub repository; plain git over HTTPS is the only transport (NR-F-01).

    python scripts/fetch/artifacts.py put FILE            # prints the hash it is stored under
    python scripts/fetch/artifacts.py get HASH DEST       # refuses if the stored bytes do not hash to HASH
"""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REMOTE = "https://github.com/ghost-in-the-kernel/neon-rain-artifacts"
BRANCH = "main"
MAX_BYTES = 100 * 1000 * 1000  # R-016 (a): plain git files under 100 MB each
IDENTITY = ("-c", "user.name=Ghost", "-c", "user.email=118085043+ghost-in-the-kernel@users.noreply.github.com")
HASH_FORM = re.compile(r"[0-9a-f]{64}")


class ArtifactError(Exception):
    """A put or get that was refused; the message says why."""


def default_clone() -> Path:
    """Where the clone lives: `$NEONRAIN_ARTIFACTS_CLONE`, else ~/.cache/neon-rain/artifacts (never under the repo)."""
    return Path(os.environ.get("NEONRAIN_ARTIFACTS_CLONE") or Path.home() / ".cache" / "neon-rain" / "artifacts")


def default_remote() -> str:
    """The remote to clone: `$NEONRAIN_ARTIFACTS_REMOTE`, else the private GitHub repository."""
    return os.environ.get("NEONRAIN_ARTIFACTS_REMOTE") or REMOTE


def sha256_of(path: Path) -> str:
    """The SHA-256 of a file's bytes, hex, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def blob_path(clone: Path, digest: str) -> Path:
    """Where a hash's blob sits in the clone; refuses anything but 64 lowercase hex characters (no path tricks)."""
    if not HASH_FORM.fullmatch(digest):
        raise ArtifactError(f"{digest!r} is not a SHA-256 (64 lowercase hex characters)")
    return clone / digest[:2] / digest


def git(clone: Path, args: tuple[str, ...]) -> str:
    """One git command in `clone` as Ghost; its stdout, or an ArtifactError carrying git's complaint."""
    done = subprocess.run(["git", *IDENTITY, "-C", str(clone), *args], capture_output=True, text=True)
    if done.returncode != 0:
        raise ArtifactError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout


def sync(clone: Path, remote: str) -> None:
    """Make `clone` current: clone it if absent, else fetch; fast-forward to the remote's branch if it has one."""
    if not (clone / ".git").is_dir():
        clone.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(["git", "clone", "--quiet", remote, str(clone)], capture_output=True, text=True)
        if done.returncode != 0:
            raise ArtifactError(f"git clone failed: {done.stderr.strip()}")
    git(clone, ("fetch", "--quiet", "origin"))
    if git(clone, ("ls-remote", "--heads", "origin", BRANCH)).strip():
        git(clone, ("checkout", "--quiet", "-B", BRANCH, f"origin/{BRANCH}"))
        git(clone, ("reset", "--quiet", "--hard", f"origin/{BRANCH}"))  # the clone is a cache: local edits are not kept
    else:
        git(clone, ("checkout", "--quiet", "-B", BRANCH))  # an empty remote: the first commit makes the branch


def put(source: Path, clone: Path, remote: str) -> str:
    """Store `source` under its SHA-256 and push; return the hash. Bytes already stored are no new commit."""
    if not source.is_file():
        raise ArtifactError(f"{source} is not a file")
    if source.stat().st_size > MAX_BYTES:
        raise ArtifactError(f"{source} is over 100 MB; chunk it (R-016 a)")
    digest = sha256_of(source)
    sync(clone, remote)
    target = blob_path(clone, digest)
    if target.is_file() and sha256_of(target) == digest:
        return digest
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(source.read_bytes())
    git(clone, ("add", str(target.relative_to(clone))))
    git(clone, ("commit", "--quiet", "-m", f"Artifact {digest}"))
    git(clone, ("push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}"))
    return digest


def get(digest: str, dest: Path, clone: Path, remote: str) -> None:
    """Copy the blob named `digest` to `dest`; refuse if it is absent or its bytes do not hash to its name."""
    sync(clone, remote)
    target = blob_path(clone, digest)
    if not target.is_file():
        raise ArtifactError(f"no artifact {digest} in the store")
    data = target.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ArtifactError(f"artifact {digest} is corrupted: its bytes hash to something else")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def main(argv: list[str]) -> int:
    """The command line: `put FILE` or `get HASH DEST`; 0 on success, 1 on a refusal, 2 on a misuse."""
    try:
        if len(argv) == 2 and argv[0] == "put":
            print(put(Path(argv[1]), default_clone(), default_remote()))
        elif len(argv) == 3 and argv[0] == "get":
            get(argv[1], Path(argv[2]), default_clone(), default_remote())
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except ArtifactError as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
