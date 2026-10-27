# Upstream and fork sync checkpoint — 2026-10-27

`Rouniy/eda-agent/main` remains the integration branch. These are exact
fetched Git tips, not a claim that all their code has been merged:

| Source | Reviewed tip | Actual merge base with our `main` before this pass |
| --- | --- | --- |
| `salitronic/eda-agent` `main` | `ce53d6ea0f01db7aa43b840c53b758bd18812684` | `8e659a27b05ff46be2f9ae30225b5baf0c9a8395` |
| `MOREmbedded/eda-agent` `main` | `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41` | `0fc7f02a7a56a130d0cfded4a2a922d313c9ea99` |
| `mooreaa/eda-agent` `main` | `fc22136ca5d28e6442c979417d8615c8ff4a2d35` | `8e659a27b05ff46be2f9ae30225b5baf0c9a8395` |

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

After the source build, the live HTTP MCP endpoint reported 622 tools and
`app_ping` confirmed loaded/bundled script `2026.10.27.1` on Altium
`26.11.1.5`. This confirms deployment and tool registration, not native
acceptance of a CAD write.
After the impedance-profile port, the endpoint reported 623 tools and
loaded/bundled `2026.10.27.2`. The profile reader itself has not yet been
run against a disposable board.

The fork's `pcb_check_fab_output` remains to be rewritten: its board reads
do not verify an exact board identity across calls, and its pad count stops
at 5000 without a completeness check. The NPI DFM criterion is therefore
manual until an exact-board, complete comparison exists; it cannot claim an
automatic pass from the current partial reads.

## Next integration blocks

| Source | Remaining block | Integration check |
| --- | --- | --- |
| Upstream `0a9ccd4`, `bb06837` | xSignals, net naming/display, project libraries, pin and pad properties, shared packages | Split read and write paths; verify per-document targeting and property readback |
| Upstream `5797fc0`, `bff741b`, `ce53d6e` | Remaining board grids, editor preferences, jumpers, routing preferences, pair impedance and STEP export | Port one tool family at a time with source tests, script build and disposable-board native checks |
| Upstream `184301d` | Schematic property test dependency fix | Carry with the related property chain tests |
| MOREmbedded `84b682c`, upstream `5db72f2` | Edit 3D bodies and rotate complete footprints | Preserve exact library/footprint identity, dry run and readback before a save |
| Upstream `ed4ef59` | Use body height/standoff in footprint previews and natively qualify the restored footprint reader and model association | Verify against a disposable PcbLib and an isolated output directory |
| MOREmbedded `pcb_check_fab_output` | Compare exported fab package with one exact board | Eliminate the 5000-pad cap and reject incomplete/mismatched reads |
| `mooreaa` `3d5817f` through `fc22136` | Remaining placement cleanup and model choice during footprint name stamp/relink | Use final corrected handlers; verify exact-sheet targeting, native readback and disposable-sheet safety |

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
