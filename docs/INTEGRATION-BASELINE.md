# Integration baseline

The current `main` builds on these two exact Git commits:

| Source | Integrated tip | Merge into `Rouniy/main` |
| --- | --- | --- |
| `salitronic/eda-agent` (`upstream/main`) | `e5fb6b28b2ad30a65b9e64189c4e03ba8ab6b022` | `cfb1346` (second parent) |
| `MOREmbedded/eda-agent` (`morembedded/main`) | `dbaef87269e28c44aaee41399fdfb636681e40b6` | `d91a1cb` (second parent) |

Both exact tips are ancestors of our `main`, so Git records the sync
points without relying on a manually maintained version number. The
annotated tag `upstream-sync-2026-10-29-e5fb6b2` points to the latest
upstream commit in this integration. Earlier tags retain the prior
checkpoints, including `upstream-sync-2026-10-28` at `0bb1b315`.
GitHub also records
`Rouniy/eda-agent` as a fork of `salitronic/eda-agent`. The
upstream merge incorporated variant management and BOM support; the
MOREmbedded merge incorporated its SDK and diagnostics lineage with local
adaptations. Our later commits, including selected work from other forks,
sit on top of these merges.

To check the baseline again:

```sh
git fetch --no-tags upstream main
git fetch --no-tags morembedded main
git merge-base main upstream/main
git merge-base main morembedded/main
git rev-list --count main..upstream/main
git rev-list --count main..morembedded/main
```

The two merge-base outputs must equal the integrated tips in the table
after fetching these exact heads.
The two `rev-list` counts show new source commits that have not been
merged. Upstream advances may be reviewed later; stabilization of the
current `main` does not depend on automatically merging them. For feature
reviews from other forks, compare their behavior with this `main` and
record accepted changes in `docs/FORK-BEHAVIOR-CHECK-2026-10-28.md`.

## Verification on 2026-10-28

- `git merge-base --is-ancestor` confirmed both source tips are ancestors
  of `main`; both `main..source` commit counts were zero after fresh fetches.
- `python -m pytest -q`: 9,784 passed, 165 skipped, one expected failure.
- `python scripts/altium/build.py`: 12 Pascal files, zero errors and zero
  warnings; the bundled script rebuilt without changing tracked output.
- A direct Streamable HTTP MCP session on TCP 14701 initialized and
  `app_ping` returned `success=true`, `version_match=true`,
  `script_location_match=true`, no stale units, and no warnings. Altium
  reported version 26.11.1.5 and script version `2026.10.28.172`.

These checks establish the Git baseline and current local regression state.
They do not establish native Altium 25 compatibility or complete behavior
parity for every divergent third-party fork branch; those checks remain in
the dated fork audit.

## Latest recheck

At `main` / `origin/main` `e75f3b6e85f205acca7c284759d6385f19654995`,
`git merge-base main upstream/main` still returns the table's upstream tip;
`git rev-list --count main..upstream/main` returns `1`.
`git merge-base main morembedded/main` still returns the table's child-fork
tip, with `0` pending commits. `fork-status --fetch --cached-forks
--verify-fork-branches --json` matched all 63 direct fork defaults and all
120 live branch tips to their cached refs. The new upstream commit
`75df990` is a broad feature release; it remains outside this integration
point while the current fork is stabilized. A native MCP ping on port 14701
reported script `2026.10.28.178` and `version_match=true` after the
net-lookup repair in `e75f3b6`.

On the latest 2026-10-28 recheck, `main` and `origin/main` were
`02d69644b12b2b104f5124e4e43247103f7c1903`. The child fork's
`claude/determined-gould-ebb38e` tip
`b1d0fa199d6f38438dde2449191248360f70fd95` is also an ancestor of
`main`, recorded by merge `02d6964`. The upstream sync point remains
`0bb1b315`; the child default remains `d495c4d` with zero pending
commits. The fresh fork-status check matched all 63 direct fork defaults
and all 120 live branch tips to their cached refs. Fifty-three cached
refs have divergent ancestry; they are a review inventory, not a count
of missing features.
