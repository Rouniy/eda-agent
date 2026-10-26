# Fork integration audit — 2026-10-26

## Recheck of MOREmbedded/main at b48f970

The direct fork was fetched again from `https://github.com/MOREmbedded/eda-agent.git`
on 2026-10-26. Its `main` still points to `b48f970`. The target is
`Rouniy/eda-agent/main`. The counts of divergent Git commits are not feature
counts because several changes were ported with edited patches.

| State | Features from the direct fork | Evidence |
| --- | --- | --- |
| Integrated before this recheck | Replacement-part evidence, ten calculators and optional pcb-toolkit check, vendor stackups/fab data, profile document templates, library file/STEP inspection and footprint comparison, fractional layer thickness, circuit-loop/sheet-fit/smart-DRC analysis, Windows path normalization, keepalive through outages, restoring a hidden Altium frame | Integration commits `2368405` through `9ff5d3a`, plus wrapper fixes in `08ec57a` |
| Integrated during this recheck | Withdraw timed-out requests, batch PCB DRC, direct Altium 365 API, standard schematic symbols and library save tracking, schematic templates alongside DesignPlan, duplicate footprint guard, installed menu and dialog translations, localized dashboard, PCB coordinate zoom, mask-sliver and silk rule gaps, offline SPICE deck export for ngspice and LTspice, generic PCB keepout restrictions, decimal-mil rectangle corners for board outlines and polygon pours | `9206588` through `541d2ce`; focused tests and Pascal lint pass; native execution still pending |
| Already present before this recheck | Advisory two-pad rotation, bottom-side rotation scoring, offline fab package inspection, CLI script-folder discovery, performance report, DelphiScript routine checks | Earlier audit below; `2cabd7b` needs no second copy |
| Next source candidates | Remaining decimal-mil geometry handlers; true arcs and polygon settings; STEP/3D model editing; integrated libraries; multi-part schematic template support; ERC and project membership; session document isolation; update flow | Require conflict resolution, tests and in some cases disposable-board native acceptance |
| Held for rewrite or evidence | `be21eb3` bottom-side placement can flip a similarly named component on another open board after a failed placement; `bf9e08c` per-via tenting writes a pad cache that faulted the current repo's AD 26.10 session; `74d745d` forces one net-label colour; upstream removal of the main DesignPlan layout engine | Do not copy those patches literally; preserve exact-board targeting and both layout paths; qualify the via cache on the installed Altium build before exposing the write |

The running Altium worker is older than the current source and is hung; the owner
instructed us to finish source integration before terminating it. No native
acceptance claim is made for the newly ported Pascal routines.

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

The `main` source script version is `2026.10.26.2`. At 20:49 +02:00 on 2026-10-26, the Altium worker was restarted directly from the `main` checkout; `app_ping` confirmed the loaded and bundled versions both report `2026.10.26.2`. See `docs/CURRENT-STATE.md` for the live handoff.

## Reviewed but held for separate work

The direct fork contains board placement and stackup writes, manufacturing comparisons, profile defaults, calculators, and other larger features. The live manufacturing check in particular compares against an active board without exact project identity and limits its pad read to 5000 without a completeness guard. This branch imports its offline file inspection only. The other CAD writes need the project's explicit edit scope, exact-batch approval, native enforcement, and native acceptance gates before exposure.

The remaining upstream changes and active fork branches are not represented as fully merged. A trial merge of the direct fork produced 23 conflicted files; a trial upstream merge produced roughly 50 conflicted files and included broad native write paths. Those trials were abandoned without changing main. Some candidates such as Workspace part placement, note CRUD, board-quality scoring, and AD23/AD26 paste-flag compatibility require independent review or hardware/version coverage. Earlier `lda-audiotech` Unicode/BOM, `TerrenceHenry` TextColor guard, `redbird98` ResolvePCBBoard, and `4pplet` selected-project work were already present locally.

## Release boundary

The shared operating runbook referenced by `AGENTS.md` was unavailable at its documented GitHub URL during this audit. The owner subsequently authorized replacing the worker directly from `main`; the previous worker was detached without saving documents, and the new one passed startup/version checks. The new features still need native acceptance against disposable projects. The tests above are source/helper checks, not electrical or manufacturing sign-off.
