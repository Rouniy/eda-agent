# Upstream and fork sync checkpoint - 2026-10-27

## Later upstream tip in this session

Script `.82` corrects a source-level omission in the adapted upstream
`pcb_pours_at` and `pcb_board_options`: `expect_file` had reached the bridge
but the native handlers ignored it. They now refuse a different board and
report the actual board path, which Python checks. Disposable-board native
reads and wrong-path refusals passed. A previously pending PcbLib read was
also accepted on a disposable 38-footprint library (`AD_FE38`: 493 tracks,
38 regions, 12 vias, one STEP body); wrong-path lookup was refused. The
saved STEP standoff resolver remains conditional on a clean active PcbLib.
The live fork inventory check returned 62/62 fresh default tips and 117/117
fresh branches, with MOREmbedded still at `032fb4b`.

The `.81` follow-up ports `40814ba`'s direct PCB net colours and
project-to-board colour synchronization into the exact-board net-display
command. The project path is explicit; native replies identify that project;
all net colours and display flags are checked before one batch board write.
On the disposable board, GND changed to `#123456` and was restored from the
loaded project's colour. The fresh upstream and MOREmbedded fetches on
2026-10-27 found unchanged tips `40814ba` and `032fb4b`; the upstream
merge base remains exactly `40814ba`.

The `.79` follow-up ports `40814ba`'s coarse visible-grid factor and
grid units into the exact-board grid command. Native change/restore and
stale-state refusal passed on a disposable PcbDoc.

`git fetch upstream main` advanced `upstream/main` from `9ee593e` to
`40814badc695813157fd8c50d24feafc5a553fcd`, one new commit. The
explicit two-parent merge `da566a8` is pushed to `Rouniy/main` with our exact-board
guards retained. Its new Gerber/print settings, paste preferences,
Testpoint Style fields and schematic border-zone reader are present in
script `.78`. A read of both output groups on the isolated PcbDoc and a
147-object schematic zone read passed in Altium 26.11.1.5. Net-colour
sync and grid factor/unit controls were subsequently adapted to our existing
preconditioned commands; see `TODO.md`. Expanded PCB editor and paste-array
options now have that adaptation and passed live change/restore checks.

## Current remote-tip check

After `f339ee5` was pushed, `git fetch` kept `upstream/main` at
`9ee593ea0dce989bf3bfc97d0c982044ed41badb` and
`morembedded/main` at `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.
`git merge-base main upstream/main` equals the exact upstream tip;
`git rev-list --left-right --count upstream/main...main` returned
`0 354`. This is an ancestry claim for upstream, not for the child fork.

The GitHub forks API listed 61 direct upstream forks and one child fork
of `Rouniy/eda-agent`, `MOREmbedded`. For each direct fork, the branch
named by its `default_branch` was checked with `git ls-remote` against
its `refs/remotes/forks/<owner>/<branch>` cache. All 60 external branch
tips matched; only our own cached `forks/rouniy/main` lagged, and it was
refreshed to `f339ee5`. The child fork was fetched separately and had no
new `main` commit. This checks tip freshness; the older rows below remain
the feature-level audit and native-acceptance ledger.

The same audit is now repeatable with
`eda-agent fork-status --verify-fork-tips --json`. It reads the two GitHub
fork inventories and compares each live default-branch tip with a local
`forks/*` or configured remote ref; it does not update refs. On this
checkpoint the command returned `checked=62, fresh=62`, including
`MOREmbedded` as the one child fork. A mismatch gives the exact repo,
branch, remote commit and local ref to fetch and review.

`--verify-fork-branches` expanded the check to 117 live branches across
those 62 forks. Twenty branches were absent from the old cache. Their
refs were fetched from `vincent-himpe`, `yanivbi1`,
`andrzej-sikora-elte`, `pieterpotgieter` and `redbird98`; a rerun returned
`117/117` matching tips. The new branches expose mostly features already
adapted into `main` (for example decimal mils, true-arc regions, via masks
and footprint body editing). The `andrzej-sikora-elte/elte` branch also
exposed generic DbLib link flags and current footprint model reads. Their
component-typed, read-only property paths were ported in script `.61`;
native read acceptance is still pending. Re-linking a database component
and changing its footprint remain dedicated operations rather than bare
property assignments, so their multi-field identity can be verified.

`Rouniy/eda-agent/main` remains the integration branch. The October 27
integration merge has `9ee593ea0dce989bf3bfc97d0c982044ed41badb`
(`salitronic/eda-agent/main`) as its second parent. `git merge-base main
upstream/main` identifies this precise
upstream synchronization point. The fork rows below record feature review
and ports, not Git ancestry with those forks.

These are the exact Git tips reviewed in this pass:

| Source | Reviewed tip | Actual merge base with our `main` before this pass |
| --- | --- | --- |
| `salitronic/eda-agent` `main` | `9ee593ea0dce989bf3bfc97d0c982044ed41badb` | `8e659a27b05ff46be2f9ae30225b5baf0c9a8395` |
| `MOREmbedded/eda-agent` `main` | `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41` | `0fc7f02a7a56a130d0cfded4a2a922d313c9ea99` |
| `mooreaa/eda-agent` `main` | `fc22136ca5d28e6442c979417d8615c8ff4a2d35` | `8e659a27b05ff46be2f9ae30225b5baf0c9a8395` |

Additional `MOREmbedded` branches fetched on this pass: `feature/company-profiles`
at `6bd492d`, `claude/project-thread-6aorpk` at `5954a6f`, and
`agent/sync-upstream-d6823d5` at `93141c6`. Their named profile, library,
fractional-layer-thickness and rotation-audit features are already present
in our adapted `main`; this is a feature-level observation, not an ancestry
claim. The `93141c6` branch syncs an older upstream point (`d6823d5`),
so it does not advance our reviewed-through upstream tip.

The table records merge bases before the October 27 merge. Upstream is now
an actual second parent; fork features remain reviewed and adapted ports.

`eda-agent fork-status --fetch --json` now reports the live Git boundary
without relying on this dated note. It lists all merge bases when histories
have more than one. On October 27 the refreshed upstream tip was
`9ee593e` and was an ancestor of our `main` (zero upstream commits behind).
The direct child fork's tip was `032fb4b`, with two merge bases; its Git
commit count is not a list of unported features. This command is read-only
except for the explicit `--fetch`, which updates remote-tracking refs.
`eda-agent fork-status --cached-forks --json` additionally compares every
locally cached `forks/*` branch ref, including feature branches, with exact
merge bases and Git ahead/behind counts. The local checkout has 90 such
refs at this check. `--fetch` refreshes the configured main remotes only;
the cached fork refs are explicitly identified as unrefreshed.

On 2026-10-27 after commit `f61565f`, `git fetch` advanced the
`upstream/main` ref to `9ee593ea0dce989bf3bfc97d0c982044ed41badb`.
Its three newer commits are `172d254` (pour growth and related PCB tools),
`642e6a8` (rigid-flex and stack features), and `9ee593e` (physical stack,
dielectrics, impedance and vias). These commits are included in the merge
candidate, with our already tested exact-board adaptations retained.
`morembedded/main` was unchanged at
`032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.

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
| `mooreaa` `dc36b7e`-`fc22136` (port cross-references, partial) | Plan CrossRef positions from a port's read-only `ConnectedEnd` and wire geometry; require an exact sheet, a reviewed plan digest and per-reference readback for writes | 41 related tests, Pascal lint/build, loaded `.6` runtime and bad-path refusal; native sheet acceptance pending |
| `mooreaa` through `fc22136` (live pins) | Filter hidden part/display-mode copies from schematic ePin queries, preserving explicit `OwnerPart` inspection; use visible pins in CrossRef planning and its digest | 21 focused tests, Pascal lint/build and loaded `.7` runtime; native multipart-sheet acceptance pending |
| `mooreaa` `64a71c3` through `fc22136` (part properties) | Read and write a placed part's display mode and current PCB model pin map, with type guards and readback | 22 related source tests, Pascal lint/build; native disposable-sheet acceptance pending |
| `mooreaa` `053aff9` through `fc22136` (placement model choice) | Select a named PCB model the library symbol already carries on single and bulk placement, verify all current flags and restore them on failure | Focused source tests and Pascal lint/build; native disposable-sheet acceptance pending |
| `mooreaa` `3d5817f` through `fc22136` (Footprint stamps) | Choose an existing model on single/bulk Footprint parameter writes before fallback rename; refuse unloaded explicit batch sheets | 52 related tests, Pascal lint/build and loaded `.10` runtime; native multi-model acceptance pending |
| `mooreaa` `dc36b7e`-`fc22136` (multipart placement and tidy) | Place an explicit sub-part, verify its sheet state and report issues; link the library, hide inherited model parameters and adopt the sheet designator font | 65 related tests, Pascal lint/build and loaded `.11` runtime; native multipart-sheet acceptance pending |
| `mooreaa` `dc36b7e`-`fc22136` (placement styling and Value) | Inherit or set fonts on new schematic objects, hold fixed port width, normalize text-frame line breaks, update existing Value parameters and hide new ones | 70 related tests, Pascal lint/build and loaded `.12` runtime; native disposable-sheet acceptance pending |
| `mooreaa` through `fc22136` (port AutoSize getter) | Return the native port AutoSize flag through generic queries, with a port-only type guard | Native `.12` query exposed the omission; loaded `.13` ePort query read back false, font 1 and width 400 on an isolated sheet |
| MOREmbedded through `032fb4b` (`pcb_check_fab_output`) | Rework fab comparison around one exact-board, uncapped native snapshot and require all three core comparisons | 23 focused tests, Pascal lint/build, loaded `.14`; disposable PCB facts and wrong-path refusal passed; full export comparison pending |
| Upstream `0a9ccd4`, `bb06837` (xSignals) | Read, create and delete xSignals on an exact PcbDoc; use count preconditions and verify native pair deltas | 28 focused tests, Pascal lint/build, loaded `.16`; disposable read and refusal/no-op checks passed; actual populated-board write pending |
| Upstream `0a9ccd4` (same package) | Compare all placed components with native package equality on an exact PcbDoc, including unhashed parts, and expose comparison errors | Eight focused tests, Pascal lint/build, loaded `.17`; 147-part read returned 14 groups, R62 matched 51 others; board unmodified |
| Upstream `bb06837` (net display) | Read and batch-set four per-net display flags on an exact PcbDoc, with old-state preflight, dry-run plan and readback | Six related tests, Pascal lint/build, loaded `.18`; one-net and two-net disposable writes read back; missing net/wrong board refused |
| Upstream `5797fc0` (board grids) | Read and set six board grids and dot mode on an exact PcbDoc, validating all values before writes with old-state preflight and readback | Three focused tests, Pascal lint/build, loaded `.19`; disposable changes read back, exact-path save/reload persisted snap X; broad Save All side effect recorded in CURRENT-STATE |
| Local persistence fix after upstream grid port | Save one exact loaded document with an observed disk write, without Save All | Nine related tests, Pascal lint/build, loaded `.20`; disposable grid persisted after close/reopen; owner PcbDoc hash unchanged during this test |
| Upstream drill layer pair family | Read pair spans/flags; set flags and add pairs with exact-board identity, count preflight, dry-run and readback | Three focused tests, Pascal lint/build, loaded `.21`; disposable pair flag changed and independently read back; duplicate span and wrong board refused; new TopLayer-MidLayer1 span added and independently read back on disposable three-layer board |
| Upstream rule resolution (`pcb_find_dominant_rule`, `pcb_check_rule_scope`) | Ask Altium's rule engine about component/pad/net objects, with exact PcbDoc identity and complete replies | Two focused tests, Pascal lint/build, loaded `.22`; on a 47-rule board R62 dominant-rule lookup worked, unary and binary scope queries returned native answers, missing binary object and wrong board refused; owner SHA256 unchanged |
| MOREmbedded `84b682c` (`lib_set_3d_body`) | Edit an existing footprint body's height, opacity and layer; preserve saved STEP rotations while setting model Z offset, with exact PcbLib identity, count preflight and dry-run | Three focused tests, Pascal lint/build, loaded `.23`; on an isolated copy of a 38-footprint library, STEP Z offset persisted at 10 mil with all three rotations unchanged and opacity 0.7; overall height read back at 50 mil before discard; owner library and board hashes unchanged |
| MOREmbedded complete-footprint rotation | Rotate pads, tracks, arcs, regions, vias, texts and 3D bodies about the footprint origin with an exact PcbLib path; plan first and verify pad centres/angles | Three focused tests, Pascal lint/build, loaded `.24`; on an isolated library copy, AD_FE38 rotated 580 primitives with zero pad mismatches, exact save and reopen preserved all 32 pad rotations/positions and STEP Z offset; owner library and board hashes unchanged |
| Upstream PCB editor preference family (`bff741b`, `ce53d6e`) | Read and set view, edit and route preferences with exact active PcbDoc identity, old-value preflight, default dry-run and native readback | Three focused tests, Pascal lint/build, loaded `.25`; show-pad-numbers, auto-pan and auto-via toggled and independently read back, then restored; wrong board refused; owner PcbDoc hash unchanged |
| Upstream placed-component STEP export (`f39f28b`, `5797fc0`) | Export one installed component through both Altium model and part APIs, with exact-board identity and observed new STEP bytes | Two focused tests, Pascal lint/build, loaded `.26`; U1 produced valid 704,493-byte part STEP and 649,650-byte model STEP in isolated output; wrong board refused; owner PcbDoc SHA256 unchanged |
| Upstream differential-pair routing rule (`ce53d6e`) | Read impedance mode and numeric fields; set the mode with exact-board identity and old-state checks | Three focused tests and Pascal lint/build. On an isolated PcbDoc, the mode persisted after exact save/reopen in both directions. Direct SDK numeric writes read back in memory but reverted to 50 ohms after save/reopen in both mode states; those writes now return `UNSUPPORTED_PERSISTENCE` pending a verified Altium API. |
| Upstream via structures (`9ee593e`, partial) | Count each via's protection features and back-drill configuration on an exact PcbDoc; report when a distinct-kind limit omits vias | Two focused tests, Pascal lint/build, loaded `.29`; owner PcbDoc returned 730 vias in one structure group, and a wrong-board path was refused. Other `9ee593e` layer-stack tools remain pending. |
| Upstream physical stack (`9ee593e`, partial) | Read every physical layer in order, with Z coordinates, thickness and dielectric material on an exact PcbDoc | Two focused tests, Pascal lint/build, loaded `.30`; owner PcbDoc returned 13 layers and 70.0078 mil overall Z span; a wrong-board path was refused. Layer ordering and rigid-flex stack edits remain pending. |
| Upstream dielectric editor (`9ee593e`, partial) | Plan and edit type, material, Dk, Df and thickness of one named dielectric or solder-mask layer, with exact-board and old-state checks | Two focused tests, Pascal lint/build, loaded `.32`; on isolated PcbDoc, type 2→1 and material, Dk, Df, thickness changes persisted after exact save/reopen. `IsStiffener` read back in memory but reverted on reopen, so its write is refused in Python and native code. |
| Upstream impedance profiles (`9ee593e`, partial) | Create, edit, rename and remove a named profile with exact-board identity, count and old-value checks | Three new focused tests and 20 related passing, Pascal lint/build, loaded `.33`; isolated PcbDoc saved/reopened with 100 Ω differential profile, then 110 Ω renamed coplanar profile, then zero profiles after removal. |
| Upstream impedance profile layer (`9ee593e`, partial) | Read or edit one copper layer's enablement, width/gap and limits, clearance and solder-mask settings with exact-board profile/layer tokens | Three new focused tests and six related passing, Pascal lint/build, loaded `.34`; isolated PcbDoc retained all tested values after exact save/reopen. Altium normalized an unspecified minimum width from 0 to 4 mil. A wrong-board write was refused. |
| Upstream stack style (`9ee593e`, partial) | Plan and set a board's numeric layer-stack style with exact-board and old-state checks | Two focused tests and four related passing, Pascal lint/build, loaded `.35`; isolated PcbDoc persisted style 0→1 after exact save/reopen with 13 layers and 70.0078-mil Z span unchanged; wrong-board write refused. |
| Upstream relative copper order (`9ee593e`, adapted) | List visible and canonical layer IDs; insert a free ID above/below a reference and move an existing layer with an exact-board old-order token | Five focused tests, Pascal lint/build, loaded `.38`; isolated PcbDoc saved/reopened with `MidLayer3` above `Int2`, then below it. A renamed existing `MidLayer1` was refused for insertion. Populated-layer movement remains unqualified. |
| Upstream rigid-flex inventory (`642e6a8`, partial) | Read exact-board regions, split/bend lines and named stacks with copper membership | Two focused tests, Pascal lint/build, loaded `.39`; owner board reported one region, one four-copper-layer rigid stack and zero split/bend lines; wrong-board request refused. Multi-region flex board acceptance and write operations remain pending. |
| Upstream plane connections (`172d254`, partial) | Read a named component's pad plane connection settings with exact-board identity | Four focused tests, Pascal lint/build, loaded `.40`; R62 pad 1 returned style/relief values and a wrong-board request was refused. The owner board has zero internal-plane layers, so actual plane connectivity remains unqualified. |
| Upstream pour growth (`172d254`, partial) | Grow one exact-board polygon outline by a signed distance, with dry-run and reviewed bounds token | Three focused tests, Pascal lint/build, loaded `.41`; isolated PcbDoc grew 1 mil and retained the new bounds after exact save/reopen. Altium changed its polygon index on reload; the old index with old bounds was refused. Repour remains a separate action. |

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
exported package has since been compared below, revealing an outline
mismatch. A board with more than 5000 drilled holes has not yet been checked.

## Next integration blocks

| Source | Remaining block | Integration check |
| --- | --- | --- |
| Upstream `0a9ccd4`, `bb06837` | Remaining net naming, project libraries, pin and pad properties, shared packages; native write acceptance for xSignals and unhashed package comparison | Split read and write paths; verify per-document targeting and property readback |
| Upstream `5797fc0`, `bff741b`, `ce53d6e` | Find a persistent Altium API for numeric differential-pair impedance rule fields, plus broader project STEP export; placed-component STEP export, editor preferences, pours-at-point, board options and per-net jumper display are now present | Keep numeric writes disabled until exact save/reopen proves they survive; port other families with source tests, script build and disposable-board native checks |
| Upstream `184301d` | Schematic property test dependency fix | Carry with the related property chain tests |
| MOREmbedded `84b682c`, upstream `5db72f2` | Further qualify 3D-body layer changes, multi-body STEP edits and rotation on footprints containing unsupported polygon/dimension primitives | Preserve exact library/footprint identity, dry run and readback before a save |
| Upstream `ed4ef59` | Use body height/standoff in footprint previews; restored footprint reader and STEP model association are natively qualified below | STEP model Z offset is now resolved from a matching clean saved PcbLib; compare further body types |
| MOREmbedded `pcb_check_fab_output` | A >5000-drilled-pad board and revision provenance of external packages | Real Altium GerberX2/NC Drill package now parsed and compared to its production-review PcbDoc; copper and hole counts match, exported Profile is larger than the live board. Keep that mismatch visible; a package manifest/revision proof is still needed for sign-off. |
| `mooreaa` `dc36b7e` through `fc22136` | Remaining relink paths and native acceptance of placement/parameter ports | Use final corrected handlers; verify exact-sheet targeting, native readback and disposable-sheet safety |

The previous audit has the other fork branches and older upstream work. This
table tracks next implementation batches, not a claim that the listed source
commits are absent in full: some of their smaller changes are already here.

The older port-by-feature history and outstanding items remain in
`FORK-INTEGRATION-AUDIT-2026-10-26.md`. In particular, the new upstream
commits from `0a9ccd4` through `ce53d6e` add many project and PCB tools
that still need a dependency and native-behaviour review.

## Real fab-package acceptance

The MOREmbedded-derived fab checker was run on the production-review
`modem-stm32-2trx-lr2021` package. Altium exports nested `GerberX2` and
`NC Drill` directories. The plated `RoundHoles_Type_7` file repeats all
991 vias already in `RoundHoles-Plated`; the parser now verifies that
subset and ignores it instead of double-counting. It excludes edge-routing
tool moves from drilled-hole counts and refuses a subtype with holes absent
from the base set. The resulting package has eight copper layers and 1053
drilled holes, matching a single native snapshot of the exact PcbDoc
(62 drilled pads and 991 vias). The exported Profile measures
107.9755 × 43.9757 mm after stroke correction, while the board reports
90.0002 × 40.0000 mm. The tool therefore returns `passed=false` with two
outline errors. The corresponding PANEL PcbDoc is 231 × 180 mm and does
not explain this package. No design file was modified. Twenty-five focused
Gerber/fab tests pass; a >5000-hole board remains untested.

## October 27 integration merge

The earlier aborted trial was followed by a two-parent merge `f71a076` of the
fetched upstream tip, pushed to `origin/main`. The merge retains the local `DesignPlan` tools,
exact-board write guards and Altium crash refusals while adding the upstream
design, library, routing, simulation, fabrication and maintenance modules.
The MOREmbedded NPI and SDK features remain integrated as adapted ports.
The native runtime now answers script `.49`; post-merge Pascal fixes are in
a separate follow-up commit.
Pascal lint/build, source tests and the live runtime check are recorded in
`docs/RELEASE_VERIFICATION.md`. Native acceptance of new write paths must
use disposable CAD documents; this Git merge alone does not validate them.

The shared operating runbook linked by `AGENTS.md` is absent from the sibling
`PLT-hw` checkout. Native CAD write acceptance still needs disposable
documents. The candidate was built with Pascal lint at zero errors and zero
warnings. A broad Python run had 7419 passes, 147 skips, one expected failure
and 30 failures; the identified production gaps were addressed in focused
groups afterwards. Upstream's legacy `test_added_altium_tools.py` still has
17 cases that assume implicit board selection or old argument forms, so they
do not yet qualify the exact-board wrappers.

## Fork branch integration after the upstream merge

`git merge-base main upstream/main` is `9ee593ea0dce989bf3bfc97d0c982044ed41badb`.
The two-parent merge `f71a076` records that upstream point in history.
`MOREmbedded/main` remains `032fb4b`; it is the only child fork returned by
the GitHub API for `Rouniy/eda-agent`. The upstream fork network was checked
again on October 27. `RHSvekon/main` equals the upstream tip and adds no code.
The child fork of MOREmbedded is `slatyb/eda-agent` at `6197a5c`;
its tip is an ancestor of `MOREmbedded/main` with zero additional commits.
Fresh October 27 fetches left `upstream/main` at `9ee593e` and
`MOREmbedded/main` at `032fb4b`, so the recorded upstream merge base remains
current at this check.

The `vanlong2109` branch `feat/dblib-placement` (`476d75e`) supplied
bulk database-library placement; the repository already had a singular
`lib_place_dblib_component` path. `sch_place_dblib_components` now sends one
batch to `SchServer.LoadComponentFromDatabaseLibrary`, preserves the
database-linked symbol, selects multipart IDs and reports per-part failures.
The port adds exact-sheet resolution in the native handler, a part-ID
readback and parameter checks. Eleven focused tests and Pascal lint/build
passed. Altium loaded script `.51`; an actual DbLib placement on a
disposable sheet is still required before claiming native write acceptance.

The `tisn1678065900-dot` `boardquality` branch (`21f0412`) contributed
the English/Chinese PCB quality rules, board-intent and fab-profile
templates, and an optional client skill. These are now in `docs/pcb-quality`
and `skills/boardquality`, with attribution. They add guidance, not MCP
commands. The `xthanhn91` note CRUD branch (`fc08cf1`) was also reviewed:
`eNote`/`eTextFrame` generic mapping and placement already exist locally;
its small loop-renewal helper duplicates the more capable supervisor and
was not copied.

The other active branch heads checked in this pass mostly contain changes
already integrated by function: `prototrace/961e6c3` Unicode JSON escapes
and schematic polylines; `vincent-himpe/bf31274` footprint fills;
`TerrenceHenry/89c017f` schematic property refusals;
`mityafoxy/bba6811` non-raising IPC file reads;
`bblacklock3/78791d3` fractional-mil PCB coordinates; and
`darshp848/d89589b` schematic repair tools. Source comparisons confirmed
the corresponding handlers and Python tools in `main`. The AD23/AD26 paste
flag guard `4f9b64a` is an ancestor of `main`, so the earlier audit's
paste-compatibility candidate is no longer outstanding.

The `yniantongtian-oss` fix `0bbf48e` exposed one remaining WSL path
bug in `plan_from_live_sheet`: it used the host's `Path` for Altium's
Windows project and sheet names. Those names now use `PureWindowsPath`.
The existing same-filename/different-directory guard was already present.
The repository's EasyEDA extension build and distribution checks likewise
already cover the fork's delivery work through equivalent modules. A
forced POSIX-path test confirms the Windows sheet name round-trips; all
38 focused sheet-plan tests passed.

From `cad435/4f57311`, the available-library diagnostic is now integrated
as `lib_list_available_libraries`. It enumerates Altium's Available list,
including libraries not installed, and separately reports a Workspace name
seen on an open managed part. The AvailableLibraryType ordinal is interpreted
as TLibraryType; it is not used to claim that an entry is a connected
Workspace. The existing `lib_get_installed_libraries` remains the installed
inventory. Two focused tests cover the difference and source dispatch.

From `wizd/6d6cb62`, `pcb_recenter_component_origins` was adapted to
repair an imported PCB component whose library origin is far from its pads.
The native port computes a pad-centroid plan, requires an exact focused
`board_path` and a matching plan token for a write, and checks the pad
centroid after moving the origin. It supports a single designator or a whole
board and defaults to dry run.

Live acceptance on Altium 26.11.1.5 and script `.53` completed on a
disposable copy of `vd-tx-imod-QPA2237.PcbDoc`. A 100 mil dry run examined
351 components and proposed 12. A stale plan was refused as `PLAN_CHANGED`;
J12 then changed once with zero reported failures. Exact save, close and
reopen left J12 centred with zero remaining candidates. All six J12 pad
names, locations, layers and rotations matched the untouched source board
after reopen; its SHA-256 stayed
`DDECD5314589EFC38D059A11000743E6C452A1F8209C8DEA603A63D2B5C17B05`.
The disposable saved PcbDoc remains in the Windows TEMP directory because
automatic file removal was denied by the command policy. Other primitive
types and large bulk recentering still need separate acceptance.

The `viknandala-eng/main` commit `d4a259b` supplied managed Workspace
component resolution through EDMS and placement of a selected immutable
revision through `DM_UseItemRevision`. The two commands are integrated as
`lib_resolve_workspace_component` and `sch_place_workspace_components`.
The port validates GUIDs and rotation, checks the exact focused SchDoc in
both Python and Pascal, and preserves the manual-layout guard. The source
fork's Workspace search checks only the first fuzzy result against the
requested exact Comment; until an Altium Workspace is available for live
testing, a search that returns a near match first can report no exact match
even when a later result would match. It fails closed in that case. No
managed component was written to a real design during this integration.

Reviewing `rabihnd/integration` exposed a real merge defect in
`Gen_CreateObject`: an older patch left two calls without the required
diagnostic argument and an undeclared `DiagJson`, while applying the same
properties twice. The corrected handler checks unsupported and failed
property writes before registering an object, returns an explicit error
and destroys the provisional object on failure, then registers a valid
object once. On Altium 26.11.1.5, script `.55`, a rejected label property
left zero matching labels. A valid label on an isolated copy of
`Title.SchDoc` was present at 100,100 mil after exact save and reopen;
the source SHA-256 remained unchanged. This qualifies the document path;
library-component creation still needs a separate native test.

A `rabihnd/integration` multipart-library review also exposed the same
off-by-one `ICompInfoReader.PartCount` in the fast `lib_get_components`
inventory. On an isolated 70-component SchLib, all 70 disk-reader counts
were one above the live `ISch_Component.PartCount`. The new optional
`accurate_part_counts=true` reads each live component from the exact open
library and marks every row with `part_count_exact`. Parameter and default
designator reads now require that exact library instead of silently mixing
one file's inventory with another active library's symbol data. The fast
default remains available and explicitly marks its counts approximate.
The same isolated library verified the existing batch-rename collision
guard: one occupied-name row failed, the next row renamed successfully,
and the result survived exact save/reopen. The source SchLib hash stayed
`62CD36DBA4B4372CCF5CF01077550464D5BC27D6E33B4D02D8E2ED6D2BB4B45B`.

The `rabihnd/integration` multipart composition workflow was accepted on
Altium 26.11.1.5 with both two- and three-part symbols in that disposable
SchLib. A three-part symbol had seven pins, including one shared pin with
`OwnerPartId=0`, and one body rectangle on each of parts 1, 2 and 3. The
part count, pins and rectangles survived exact save, close and reopen. The
Python tool now accepts an optional absolute `library_path` to verify the
focused SchLib before writing and stops with an explicit partial result if
native creation, pin addition, part selection or body drawing fails. The
native `create_symbol` reply must confirm the requested count before pins
are added, preventing writes to a previously selected symbol on failure.

On script `.56`, the restored `library.get_footprint_primitives` read
`AD_FE38` in the disposable 38-footprint `BodyEdit_20261027.PcbLib`. It
reported one body on Mechanical13 with the named STEP model
`LTC3895EFE.STEP`, 1.20000014 mm overall height and 0 mm standoff. The
separate `TEST PAD` footprint returned an embedded non-STEP body (model
type 2), so the reader distinguished both body types. For `AD_FE38`,
`lib_extract_embedded_models` selected the model by its live footprint
association and wrote the checksum-verified original STEP into an isolated
output directory. Its 1,069,643-byte file SHA-256 was
`B5B123B0B7B89D446A648885C3979F56A3810F7E76BCC358F43980B61393C4CF`.
The disposable PcbLib's SHA-256 was
`A5AFD8514E06C3ED379C5249BA8FE7B7AC384DB35C0D5BC3A88878A2E4DBFDDB`.

From `rabihnd/integration`, `lib_position_3d_body` now centres one selected
3D body at requested footprint-relative X/Y coordinates. The port requires
an exact existing PcbLib path and footprint name, defaults to a dry run,
and has native preconditions on body count and old centre. It uses
`MoveByXY`, then reads the centre back; saving remains a separate command.
On Altium 26.11.1.5, script `.57`, a deliberately wrong old centre was
refused. A non-STEP body moved to (1, -1) mm and remained there after
save/reopen. A STEP body moved to (0.5, -0.5) mm and retained its named
`LTC3895EFE.STEP` association, [90, 0, 90] degree saved rotations and
10-mil model Z offset after save/reopen. These writes used only the
disposable `BodyEdit_20261027.PcbLib`; multi-body footprints are still
unverified natively.
Script `.58` added a native file-existence check after a direct wrong-path
probe showed that Altium otherwise opened an empty, unsaved PcbLib tab.
The invalid path now returns `NO_LIBRARY_FILE` without changing focus;
a valid no-op on the saved STEP body returns `changed=0`.

The upstream live land-pattern conversion already consumed each 3D body's
`standoff_mm`, but Altium's `ComponentBody.StandoffHeight` returned 0 for
the `AD_FE38` STEP body even though its saved `MODEL.3D.DZ` was 10 mil.
`lib_get_footprint_primitives` and its shared footprint-read path now use
the saved model's Z offset only when the focused PcbLib is unmodified and
every body matches its saved record by order, type and file name. They
retain the raw body field and report `standoff_source`. The live scratch
read returned 0.254 mm from the saved STEP record; conversion to the
land-pattern model used `z0=0.254`, `z1=1.20000014` mm. The saved
PcbLib SHA-256 was identical before and after this read:
`F4A08E82AC6807564893AB0C692D42D9DAAE69128416A1F311663EF125E16EDC`.

The `MOREmbedded/be21eb3` bottom-placement fix had already been adapted
in `pcb_place_components`: bottom requests land on top first, then flip
on the exact reported board path in a separate transaction. A native
check on an isolated copy of `DC-DCmodule_DT11328.PcbDoc` placed the same
three-pad SOT-23 at 0 degrees on both sides. After exact save/reopen,
`EDA_QA_TOP` was on TopLayer and `EDA_QA_BOTTOM` on BottomLayer, both at
0 degrees. Their pad triangles had equal-magnitude, opposite-sign
orientation cross products (about +5890 and -5890 square mils), proving
mirror geometry rather than a layer flag alone. The source board SHA-256
remained `F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.
