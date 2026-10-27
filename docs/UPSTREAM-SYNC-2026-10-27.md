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
| Upstream `f39f28b` (impedance profile read) | Read the board's solved impedance profiles and restore the NPI criterion's actual tool reference | Wrapper/source tests and Pascal lint |
| Upstream `ed4ef59` (partial) | Verify stored Altium checksums before extracting embedded 3D model bytes; compile an integrated library only with an explicit package path and a fresh nonempty IntLib artifact | 21 focused tests, Python compile and Pascal lint; native LibPkg build still pending |
| Upstream `5d79657` through `ce53d6e`, `ed4ef59` (footprint read) | Restore the native `library.get_footprint_primitives` handler, including body metadata, region shapes and layer names; restrict saved STEP extraction to a named footprint's live model files | 33 focused tests, Pascal lint/build, loaded `.3` runtime and no-target native dispatch; real PcbLib read still pending |

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
| Upstream `5797fc0`, `bff741b`, `ce53d6e` | Board grids/options, editor preferences, jumpers, routing preferences, pours at a point, pair impedance, STEP export | Port one tool family at a time with source tests, script build and disposable-board native checks |
| Upstream `184301d` | Schematic property test dependency fix | Carry with the related property chain tests |
| MOREmbedded `84b682c`, upstream `5db72f2` | Edit 3D bodies and rotate complete footprints | Preserve exact library/footprint identity, dry run and readback before a save |
| Upstream `ed4ef59` | Use body height/standoff in footprint previews and natively qualify the restored footprint reader and model association | Verify against a disposable PcbLib and an isolated output directory |
| MOREmbedded `pcb_check_fab_output` | Compare exported fab package with one exact board | Eliminate the 5000-pad cap and reject incomplete/mismatched reads |

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
