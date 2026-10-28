# Integration baseline

The current `main` builds on these two exact Git commits:

| Source | Integrated tip | Merge into `Rouniy/main` |
| --- | --- | --- |
| `salitronic/eda-agent` (`upstream/main`) | `0bb1b3154cca6e58a517b23edee3d7a108f1c232` | `63f7c16ab8dd7c703ba9a82ca17b7f06cee1e370` (second parent) |
| `MOREmbedded/eda-agent` (`morembedded/main`) | `d495c4d8802c0b7259068c2f414b7b23bfdf6ee6` | `ce7aab8fe1db6c0e804f142512246e2f0c4b4d13` (second parent) |

Both exact tips are ancestors of our `main`, so Git records the sync
points without relying on a manually maintained version number. A fresh
fetch on 2026-10-28 found zero commits pending from either source. The
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

The two merge-base outputs must equal the integrated tips in the table.
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
