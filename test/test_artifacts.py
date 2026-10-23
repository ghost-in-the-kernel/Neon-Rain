"""The artifact store: put and get through a local bare repository, no network (R-016 b, TODO 0.4)."""
import hashlib
import subprocess
from pathlib import Path

import pytest

from scripts.fetch import artifacts


@pytest.fixture
def remote(tmp_path: Path) -> str:
    """An empty bare repository standing in for the private GitHub one."""
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--quiet", "--bare", "--initial-branch=main", str(bare)], check=True)
    return str(bare)


def commits(remote: str) -> int:
    """How many commits the remote's main holds (0 when empty)."""
    done = subprocess.run(["git", "-C", remote, "rev-list", "--count", "main"], capture_output=True, text=True)
    return int(done.stdout) if done.returncode == 0 else 0


def test_put_then_get_round_trips_a_megabyte(tmp_path: Path, remote: str) -> None:
    source = tmp_path / "in.bin"
    source.write_bytes(bytes(range(256)) * 4096)
    digest = artifacts.put(source, tmp_path / "clone1", remote)
    assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
    out = tmp_path / "deep" / "out.bin"
    artifacts.get(digest, out, tmp_path / "clone2", remote)  # a different clone: it came through the remote
    assert out.read_bytes() == source.read_bytes()


def test_the_blob_sits_under_its_two_character_fan_out(tmp_path: Path, remote: str) -> None:
    source = tmp_path / "in.txt"
    source.write_text("hello")
    digest = artifacts.put(source, tmp_path / "clone", remote)
    assert (tmp_path / "clone" / digest[:2] / digest).read_text() == "hello"


def test_putting_the_same_bytes_twice_is_one_blob_and_one_commit(tmp_path: Path, remote: str) -> None:
    first, second = tmp_path / "a.txt", tmp_path / "b.txt"
    first.write_text("same")
    second.write_text("same")
    one = artifacts.put(first, tmp_path / "clone", remote)
    two = artifacts.put(second, tmp_path / "other-clone", remote)
    assert one == two
    assert commits(remote) == 1


def test_a_commit_is_authored_as_ghost(tmp_path: Path, remote: str) -> None:
    source = tmp_path / "in.txt"
    source.write_text("x")
    artifacts.put(source, tmp_path / "clone", remote)
    author = subprocess.run(["git", "-C", remote, "log", "-1", "--format=%an <%ae>"], capture_output=True, text=True)
    assert author.stdout.strip() == "Ghost <118085043+ghost-in-the-kernel@users.noreply.github.com>"


def tamper(remote: str, clone: Path, digest: str) -> None:
    """Replace a stored blob's bytes in the remote itself, as a bad push or a bit rot would."""
    path = clone / digest[:2] / digest
    path.write_text("tampered")
    identity = ["-c", "user.name=x", "-c", "user.email=x@y"]
    subprocess.run(["git", *identity, "-C", str(clone), "commit", "-qam", "tamper"], check=True)
    subprocess.run(["git", "-C", str(clone), "push", "-q", "origin", "HEAD:main"], check=True)


def test_a_corrupted_blob_is_refused_and_nothing_is_written(tmp_path: Path, remote: str) -> None:
    source = tmp_path / "in.txt"
    source.write_text("honest")
    digest = artifacts.put(source, tmp_path / "clone", remote)
    tamper(remote, tmp_path / "clone", digest)
    out = tmp_path / "out.txt"
    with pytest.raises(artifacts.ArtifactError, match="corrupted"):
        artifacts.get(digest, out, tmp_path / "reader", remote)
    assert not out.exists()


def test_putting_over_a_corrupted_blob_repairs_it(tmp_path: Path, remote: str) -> None:
    source = tmp_path / "in.txt"
    source.write_text("honest")
    digest = artifacts.put(source, tmp_path / "clone", remote)
    tamper(remote, tmp_path / "clone", digest)
    assert artifacts.put(source, tmp_path / "clone", remote) == digest
    artifacts.get(digest, tmp_path / "out.txt", tmp_path / "reader", remote)
    assert (tmp_path / "out.txt").read_text() == "honest"


def test_an_absent_hash_is_refused(tmp_path: Path, remote: str) -> None:
    with pytest.raises(artifacts.ArtifactError, match="no artifact"):
        artifacts.get("0" * 64, tmp_path / "out", tmp_path / "clone", remote)


@pytest.mark.parametrize("bad", ["", "abc", "../" + "a" * 61, "A" * 64, "g" * 64])
def test_a_malformed_hash_is_refused(tmp_path: Path, remote: str, bad: str) -> None:
    with pytest.raises(artifacts.ArtifactError, match="not a SHA-256"):
        artifacts.get(bad, tmp_path / "out", tmp_path / "clone", remote)


def test_a_missing_source_is_refused(tmp_path: Path, remote: str) -> None:
    with pytest.raises(artifacts.ArtifactError, match="not a file"):
        artifacts.put(tmp_path / "nope", tmp_path / "clone", remote)


def test_the_default_clone_is_outside_the_repository(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEONRAIN_ARTIFACTS_CLONE", raising=False)
    assert root not in artifacts.default_clone().parents


def test_the_command_line_round_trips_and_reports_a_refusal(tmp_path: Path, remote: str,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEONRAIN_ARTIFACTS_CLONE", str(tmp_path / "clone"))
    monkeypatch.setenv("NEONRAIN_ARTIFACTS_REMOTE", remote)
    source = tmp_path / "in.txt"
    source.write_text("cli")
    assert artifacts.main(["put", str(source)]) == 0
    digest = hashlib.sha256(b"cli").hexdigest()
    assert artifacts.main(["get", digest, str(tmp_path / "out.txt")]) == 0
    assert (tmp_path / "out.txt").read_text() == "cli"
    assert artifacts.main(["get", "0" * 64, str(tmp_path / "x")]) == 1
    assert artifacts.main(["bogus"]) == 2
