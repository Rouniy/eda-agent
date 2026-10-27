# Upstream and fork sync checkpoint — 2026-10-27

`Rouniy/eda-agent/main` remains the integration branch. These are exact
fetched Git tips, not a claim that all their code has been merged:

| Source | Reviewed tip | Actual merge base with our `main` before this pass |
| --- | --- | --- |
| `salitronic/eda-agent` `main` | `ce53d6ea0f01db7aa43b840c53b758bd18812684` | `8e659a27b05ff46be2f9ae30225b5baf0c9a8395` |
| `MOREmbedded/eda-agent` `main` | `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41` | `0fc7f02a7a56a130d0cfded4a2a922d313c9ea99` |

The merge bases are older than the reviewed tips because features have been
ported and adapted as separate commits. `git merge-base main upstream/main`
answers ancestry; this file answers the newer **reviewed-through** point.
Do not describe the reviewed tip as a Git merge or an exact source tree.

## Integrated from the newly fetched tips

| Source commit | Integration | Check |
| --- | --- | --- |
| MOREmbedded `789cabb` | SDK property-chain coverage and local reflection CLI, adapted to the existing `perf` command | Parser tests and reflected installed SDK |
| MOREmbedded `032fb4b` | NPI phase gates, with three criterion tool names adapted to our registry | NPI and generated-reference tests |
| Upstream `7a65a96` | Periodic datasheet reminder, preserving our bridge reattach workflow | Interval and datasheet-hint tests |
| Upstream `2b0344f` (response fix) | Schematic `obj_modify` reports dirty state without claiming a disk save | Source test and Pascal lint |

The older port-by-feature history and outstanding items remain in
`FORK-INTEGRATION-AUDIT-2026-10-26.md`. In particular, the new upstream
commits from `0a9ccd4` through `ce53d6e` add many project and PCB tools
that still need a dependency and native-behaviour review.

## Why this is not yet a merge commit

A trial `git merge --no-commit --no-ff -X ours upstream/main` was run in the
existing `eda-agent-large-integration` worktree and aborted without a commit.
It would have changed 439 files and removed local design pipeline modules
that our `DesignPlan` path still uses. It also left three modify/delete
conflicts. Accepting that tree would mark the upstream tip as merged while
losing working local capabilities. The next actual merge commit should be
created after remaining changes are either integrated or explicitly excluded
with a reason and a test.

The shared operating runbook linked by `AGENTS.md` is absent from the sibling
`PLT-hw` checkout. Source and offline tests can proceed; native CAD write
acceptance needs a disposable project and the release gates.
