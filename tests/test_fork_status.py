# SPDX-License-Identifier: Apache-2.0
"""A fork status must report the exact shared commit after divergence."""

import subprocess

from eda_agent.diag.fork_status import fork_status, format_fork_status


def _git(cwd, *args):
    return subprocess.check_output(
        ["git", "-C", str(cwd), *args], text=True).strip()


def _commit(repo, name):
    (repo / name).write_text(name, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-m", name)
    return _git(repo, "rev-parse", "HEAD")


def test_status_distinguishes_exact_sync_commit_from_divergent_tips(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.name", "Test")
    _git(source, "config", "user.email", "test@example.invalid")
    shared = _commit(source, "shared.txt")

    remote = tmp_path / "remote.git"
    subprocess.check_call(["git", "clone", "--bare", str(source), str(remote)])
    local = tmp_path / "local"
    subprocess.check_call(["git", "clone", str(remote), str(local)])
    _git(local, "config", "user.name", "Test")
    _git(local, "config", "user.email", "test@example.invalid")
    local_head = _commit(local, "local.txt")

    _commit(source, "remote.txt")
    _git(source, "push", str(remote), "main")

    stale = fork_status(local, remotes=("origin",))
    assert stale["sources"]["origin"]["behind"] == 0
    fresh = fork_status(local, remotes=("origin", "upstream"), fetch=True)
    origin = fresh["sources"]["origin"]
    assert fresh["head"] == local_head
    assert origin["merge_bases"] == [shared]
    assert (origin["ahead"], origin["behind"]) == (1, 1)
    assert origin["tip_in_head"] is False
    assert fresh["sources"]["upstream"]["available"] is False
    assert shared in format_fork_status(fresh)
