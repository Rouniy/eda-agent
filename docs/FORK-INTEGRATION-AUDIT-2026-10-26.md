# Fork integration audit — 2026-10-26

## Scope and snapshots

The target is `Rouniy/eda-agent` `main`, locally at `cb21952` before this integration. Its remote `origin/main` was `3f3aecc` (24 local commits behind). Upstream `salitronic/eda-agent` `main` was `74d745d`; the two histories had 216 local-only and 85 upstream-only commits. The direct fork of `Rouniy/eda-agent`, `MOREmbedded/eda-agent`, was at `7062521`; its history had 52 commits absent from local main and local main had 163 commits absent from it. These are Git snapshots, not permanent fork counts.

The GitHub fork listing of `salitronic/eda-agent` contained 60 direct forks. Their `main` tips were fetched and compared with upstream main. Ten had commits outside that tip: `4pplet`, `cad435`, `lda-audiotech`, `pieterpotgieter`, `redbird98`, `rouniy`, `tisn1678065900-dot`, `viknandala-eng`, `xthanhn91`, and `yniantongtian-oss`. Feature branches visible in the fetched refs were also sampled. A unique commit does not necessarily mean an unincorporated feature: some changes were already present in local main through other history.

## Integrated into this branch

| Source | Change | Verification |
| --- | --- | --- |
| `MOREmbedded/eda-agent` | Advisory two-pad rotation audit | 8 focused tests |
| `MOREmbedded/eda-agent` | Find Altium's registered script project folder for CLI deployment | 3 focused tests |
| `MOREmbedded/eda-agent` | Offline performance report for bridge and Altium logs | 22 tests and a local log parse |
| `MOREmbedded/eda-agent` | DelphiScript routine structure check | 33 tests |
| `MOREmbedded/eda-agent` | Offline Gerber/Drill package inspection | 18 tests |
| `redbird98` | Localized dialog control recognition; activate OutJob before output container | 18 dialog tests and 2 OutJob tests |
| Upstream / `MityaFoxy` | Sharing-safe script file reader for the native bridge | IPC tests, Pascal lint, bundled script build |
| `yniantongtian-oss` | Cross-platform checkout and manifest integrity check | 848 tracked paths, one manifest, zero errors |
| `yniantongtian-oss` | Require the exact Windows sheet path before using an active-document size response | 33 sheet-plan tests |

The local branch's source script version is `2026.10.26.2`. The installed and loaded Altium runtime remains `2026.10.16.1`; source integration alone does not deploy or activate it.

## Reviewed but held for separate work

The direct fork contains board placement and stackup writes, manufacturing comparisons, profile defaults, calculators, and other larger features. The live manufacturing check in particular compares against an active board without exact project identity and limits its pad read to 5000 without a completeness guard. This branch imports its offline file inspection only. The other CAD writes need the project's explicit edit scope, exact-batch approval, native enforcement, and native acceptance gates before exposure.

The remaining upstream changes and active fork branches are not represented as fully merged. A trial merge of the direct fork produced 23 conflicted files; a trial upstream merge produced roughly 50 conflicted files and included broad native write paths. Those trials were abandoned without changing main. Some candidates such as Workspace part placement, note CRUD, board-quality scoring, and AD23/AD26 paste-flag compatibility require independent review or hardware/version coverage. Earlier `lda-audiotech` Unicode/BOM, `TerrenceHenry` TextColor guard, `redbird98` ResolvePCBBoard, and `4pplet` selected-project work were already present locally.

## Release boundary

The shared operating runbook referenced by `AGENTS.md` was unavailable at its documented GitHub URL during this audit. No Altium script replacement or native deployment was performed. The selected-project runtime needs coordinated shutdown, a side-by-side build and installation, and native acceptance against a disposable project before this source version can be considered live. The tests above are source/helper checks, not electrical or manufacturing sign-off.
