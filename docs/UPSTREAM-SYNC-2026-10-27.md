# Upstream and fork sync checkpoint — 2026-10-27

`Rouniy/eda-agent/main` remains the integration branch. These are exact
fetched Git tips, not a claim that all their code has been merged:

| Source | Reviewed tip | Actual merge base with our `main` before this pass |
| --- | --- | --- |
| `salitronic/eda-agent` `main` | `ce53d6ea0f01db7aa43b840c53b758bd18812684` | `8e659a27b05ff46be2f9ae30225b5baf0c9a8395` |
| `MOREmbedded/eda-agent` `main` | `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41` | `0fc7f02a7a56a130d0cfded4a2a922d313c9ea99` |
| `mooreaa/eda-agent` `main` | `fc22136ca5d28e6442c979417d8615c8ff4a2d35` | `8e659a27b05ff46be2f9ae30225b5baf0c9a8395` |

Additional `MOREmbedded` branches fetched on this pass: `feature/company-profiles`
at `6bd492d`, `claude/project-thread-6aorpk` at `5954a6f`, and
`agent/sync-upstream-d6823d5` at `93141c6`. Their named profile, library,
fractional-layer-thickness and rotation-audit features are already present
in our adapted `main`; this is a feature-level observation, not an ancestry
claim. The `93141c6` branch syncs an older upstream point (`d6823d5`),
so it does not advance our reviewed-through upstream tip.

The merge bases are older than the reviewed tips because features have been
ported and adapted as separate commits. `git merge-base main upstream/main`
answers ancestry; this file answers the newer **reviewed-through** point.
Do not describe the reviewed tip as a Git merge or an exact source tree.

## Direct-fork inventory refreshed 2026-10-27

The GitHub API lists 60 direct forks of `salitronic/eda-agent`. Their default
branch tips were compared with the 60 cached `forks/*/main` refs by
`git ls-remote`: 58 were unchanged, our `Rouniy/main` advanced through this
integration, and `mooreaa/main` advanced from `bfa9bde` to `fc22136`.
`MOREmbedded/eda-agent` is a child of `Rouniy/eda-agent`, not a direct upstream
fork; its separate `morembedded/main` ref remains at `032fb4b`.

At the fetched upstream `ce53d6e`, ten **other** direct-fork main branches have
commits outside upstream: `4pplet` (128), `cad435` (5), `lda-audiotech` (1),
`mooreaa` (11), `pieterpotgieter` (1), `redbird98` (37),
`tisn1678065900-dot` (1), `viknandala-eng` (1), `xthanhn91` (3), and
`yniantongtian-oss` (52). These are commit counts, not missing-feature counts;
the earlier audit records features already ported from several of them.
`mooreaa/main` diverges at `0a9ccd46d1259e29c02ddb904b99b4dbd0d82f1d`.
Its unmerged work adds placement cleanup, per-part live pin queries, port
cross-reference repair, footprint model selection, display mode and pin-map
editing, plus DelphiScript fixes. Review the later `fc22136` corrections with
that block: earlier versions of its tidy and pin-filter logic stopped the
polling loop on AD 25.8.1. The CrossRef planner and corrected live-pin filter
have since been ported as separate commits; the remaining features below are
still under review.

Inventory source: GitHub `repos/salitronic/eda-agent/forks?per_page=100`,
`git ls-remote` for every default branch, and local `git rev-list` comparisons.

## Integrated from the newly fetched tips

| Source commit | Integration | Check |
| --- | --- | --- |
| MOREmbedded `789cabb` | SDK property-chain coverage and local reflection CLI, adapted to the existing `perf` command | Parser tests and reflected installed SDK |
| MOREmbedded `032fb4b` | NPI phase gates, with three criterion tool names adapted to our registry | NPI and generated-reference tests |
| Upstream `7a65a96` | Periodic datasheet reminder, preserving our bridge reattach workflow | Interval and datasheet-hint tests |
| Upstream `2b0344f` (response fix) | Schematic `obj_modify` reports dirty state without claiming a disk save | Source test and Pascal lint |
| Upstream `f39f28b` (impedance profile read) | Read the board's solved impedance profiles and restore the NPI criterion's actual tool reference | Wrapper/source tests and Pascal lint |
| Upstream `ed4ef59` (partial) | Verify stored Altium checksums before extracting embedded 3D model bytes; compile an integrated library only with an explicit package path and a fresh nonempty IntLib artifact | 21 focused tests, Python compile and Pascal lint; native LibPkg build still pending |
| Upstream `5d79657` through `ce53d6e`, `ed4ef59` (footprint read) | Restore the native `library.get_footprint_primitives` handler, including body metadata, region shapes and layer names; restrict saved STEP extraction to a named footprint's live model files | 33 focused tests, Pascal lint/build, loaded `.3` runtime and no-target native dispatch; real PcbLib read still pending |
| Upstream `ce53d6e` (PCB pours/options) | Look up polygon outlines at a board point and read/set the new-polygon name template; include board identity and require an expected file for writes | 28 related tests, Pascal lint/build, loaded `.4` runtime, and no-target native refusals; real-board acceptance pending |
| `mooreaa` `ad8d5fa`, also in upstream by `ce53d6e` (font safety) | Guard generic `FontId` by actual schematic object type and expose `TextFontId` through typed sheet/harness entries | 22 related tests, Pascal lint/build, loaded `.5` runtime; native entry readback pending |
| `mooreaa` `dc36b7e`–`fc22136` (port cross-references, partial) | Plan CrossRef positions from a port's read-only `ConnectedEnd` and wire geometry; require an exact sheet, a reviewed plan digest and per-reference readback for writes | 41 related tests, Pascal lint/build, loaded `.6` runtime and bad-path refusal; native sheet acceptance pending |
| `mooreaa` through `fc22136` (live pins) | Filter hidden part/display-mode copies from schematic ePin queries, preserving explicit `OwnerPart` inspection; use visible pins in CrossRef planning and its digest | 21 focused tests, Pascal lint/build and loaded `.7` runtime; native multipart-sheet acceptance pending |
| `mooreaa` `64a71c3` through `fc22136` (part properties) | Read and write a placed part's display mode and current PCB model pin map, with type guards and readback | 22 related source tests, Pascal lint/build; native disposable-sheet acceptance pending |
| `mooreaa` `053aff9` through `fc22136` (placement model choice) | Select a named PCB model the library symbol already carries on single and bulk placement, verify all current flags and restore them on failure | Focused source tests and Pascal lint/build; native disposable-sheet acceptance pending |
| `mooreaa` `3d5817f` through `fc22136` (Footprint stamps) | Choose an existing model on single/bulk Footprint parameter writes before fallback rename; refuse unloaded explicit batch sheets | 52 related tests, Pascal lint/build and loaded `.10` runtime; native multi-model acceptance pending |
| `mooreaa` `dc36b7e`–`fc22136` (multipart placement and tidy) | Place an explicit sub-part, verify its sheet state and report issues; link the library, hide inherited model parameters and adopt the sheet designator font | 65 related tests, Pascal lint/build and loaded `.11` runtime; native multipart-sheet acceptance pending |
| `mooreaa` `dc36b7e`–`fc22136` (placement styling and Value) | Inherit or set fonts on new schematic objects, hold fixed port width, normalize text-frame line breaks, update existing Value parameters and hide new ones | 70 related tests, Pascal lint/build and loaded `.12` runtime; native disposable-sheet acceptance pending |
| `mooreaa` through `fc22136` (port AutoSize getter) | Return the native port AutoSize flag through generic queries, with a port-only type guard | Native `.12` query exposed the omission; loaded `.13` ePort query read back false, font 1 and width 400 on an isolated sheet |
| MOREmbedded through `032fb4b` (`pcb_check_fab_output`) | Rework fab comparison around one exact-board, uncapped native snapshot and require all three core comparisons | 23 focused tests, Pascal lint/build, loaded `.14`; disposable PCB facts and wrong-path refusal passed; full export comparison pending |
| Upstream `0a9ccd4`, `bb06837` (xSignals) | Read, create and delete xSignals on an exact PcbDoc; use count preconditions and verify native pair deltas | 28 focused tests, Pascal lint/build, loaded `.16`; disposable read and refusal/no-op checks passed; actual populated-board write pending |
| Upstream `0a9ccd4` (same package) | Compare all placed components with native package equality on an exact PcbDoc, including unhashed parts, and expose comparison errors | Eight focused tests, Pascal lint/build, loaded `.17`; 147-part read returned 14 groups, R62 matched 51 others; board unmodified |
| Upstream `bb06837` (net display) | Read and batch-set four per-net display flags on an exact PcbDoc, with old-state preflight, dry-run plan and readback | Six related tests, Pascal lint/build, loaded `.18`; one-net and two-net disposable writes read back; missing net/wrong board refused |
| Upstream `5797fc0` (board grids) | Read and set six board grids and dot mode on an exact PcbDoc, validating all values before writes with old-state preflight and readback | Three focused tests, Pascal lint/build, loaded `.19`; disposable changes read back, exact-path save/reload persisted snap X; broad Save All side effect recorded in CURRENT-STATE |
| Local persistence fix after upstream grid port | Save one exact loaded document with an observed disk write, without Save All | Nine related tests, Pascal lint/build, loaded `.20`; disposable grid persisted after close/reopen; owner PcbDoc hash unchanged during this test |

After the source build, the live HTTP MCP endpoint reported 622 tools and
`app_ping` confirmed loaded/bundled script `2026.10.27.1` on Altium
`26.11.1.5`. This confirms deployment and tool registration, not native
acceptance of a CAD write.
After the impedance-profile port, the endpoint reported 623 tools and
loaded/bundled `2026.10.27.2`. The profile reader itself has not yet been
run against a disposable board.

The fork's `pcb_check_fab_output` was rewritten in `.14`: a single native
exact-board snapshot counts all drilled pads and vias, checks copper layers
and outline size, and the Python comparison refuses missing checks. The
native snapshot and wrong-path refusal passed on a disposable board. A real
exported package and a board with more than 5000 drilled pads have not yet
been checked end to end, so NPI DFM remains pending that acceptance.

## Next integration blocks

| Source | Remaining block | Integration check |
| --- | --- | --- |
| Upstream `0a9ccd4`, `bb06837` | Remaining net naming, project libraries, pin and pad properties, shared packages; native write acceptance for xSignals and unhashed package comparison | Split read and write paths; verify per-document targeting and property readback |
| Upstream `5797fc0`, `bff741b`, `ce53d6e` | Remaining editor preferences, jumpers, routing preferences, pair impedance and STEP export | Port one tool family at a time with source tests, script build and disposable-board native checks |
| Upstream `184301d` | Schematic property test dependency fix | Carry with the related property chain tests |
| MOREmbedded `84b682c`, upstream `5db72f2` | Edit 3D bodies and rotate complete footprints | Preserve exact library/footprint identity, dry run and readback before a save |
| Upstream `ed4ef59` | Use body height/standoff in footprint previews and natively qualify the restored footprint reader and model association | Verify against a disposable PcbLib and an isolated output directory |
| MOREmbedded `pcb_check_fab_output` | Native acceptance on an exported package and a >5000-drilled-pad board | Confirm Gerber/Excellon comparison from the same design revision |
| `mooreaa` `dc36b7e` through `fc22136` | Remaining relink paths and native acceptance of placement/parameter ports | Use final corrected handlers; verify exact-sheet targeting, native readback and disposable-sheet safety |

The previous audit has the other fork branches and older upstream work. This
table tracks next implementation batches, not a claim that the listed source
commits are absent in full: some of their smaller changes are already here.

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
