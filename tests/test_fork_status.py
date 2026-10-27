# SPDX-License-Identifier: Apache-2.0
"""A fork status must report the exact shared commit after divergence."""

import subprocess

from eda_agent.diag import fork_status as fork_module
from eda_agent.diag.fork_status import fork_status, format_fork_status, verify_fork_tips


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

    _git(local, "update-ref", "refs/remotes/forks/example/main", shared)
    with_forks = fork_status(local, remotes=("origin",), cached_forks=True)
    cached = with_forks["cached_forks"]["forks/example/main"]
    assert cached["tip"] == shared
    assert cached["merge_bases"] == [shared]
    assert (cached["ahead"], cached["behind"]) == (1, 0)
    assert cached["tip_in_head"] is True
    assert "not refreshed by --fetch" in format_fork_status(with_forks)


def test_live_fork_tip_check_distinguishes_stale_direct_and_current_child(monkeypatch, tmp_path):
    from types import SimpleNamespace

    def git(_root, *args):
        if args == ("remote",):
            return "origin\nupstream\nmorembedded"
        if args[:2] == ("remote", "get-url"):
            return {"origin": "https://github.com/Rouniy/eda-agent.git",
                    "upstream": "https://github.com/salitronic/eda-agent.git",
                    "morembedded": "https://github.com/MOREmbedded/eda-agent.git"}[args[2]]
        if args[0] == "for-each-ref":
            return "forks/example/main\told"
        if args[0] == "rev-parse":
            return {"origin/main": "ours", "upstream/main": "base",
                    "morembedded/main": "child"}[args[-1]]
        raise AssertionError(args)

    def forks(repo):
        if repo == "salitronic/eda-agent":
            return [{"full_name": "Example/eda-agent", "default_branch": "main",
                     "owner": {"login": "Example"}, "clone_url": "direct"}]
        return [{"full_name": "MOREmbedded/eda-agent", "default_branch": "main",
                 "owner": {"login": "MOREmbedded"}, "clone_url": "child"}]

    def ls_remote(command, **_kwargs):
        return SimpleNamespace(returncode=0, stdout={
            "direct": "new\trefs/heads/main\n",
            "child": "child\trefs/heads/main\n"}[command[2]], stderr="")

    monkeypatch.setattr(fork_module, "_git", git)
    monkeypatch.setattr(fork_module, "_github_forks", forks)
    monkeypatch.setattr(fork_module.subprocess, "run", ls_remote)
    check = verify_fork_tips(tmp_path)
    assert (check["checked"], check["fresh"]) == (2, 1)
    assert check["forks"][0]["ref"] == "forks/example/main"
    assert check["forks"][0]["fresh"] is False
    assert check["forks"][1]["ref"] == "morembedded/main"
    assert check["forks"][1]["fresh"] is True
    assert "Example/eda-agent" in format_fork_status({
        "branch": "main", "head": "ours", "fetch_requested": False,
        "sources": {}, "fork_tip_check": check})
