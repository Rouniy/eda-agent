# Upstream and fork sync checkpoint - 2026-10-27

After the `adf6526` main-only relaunch fix, another `git fetch upstream
main` returned `ee7589c9fc543d0b99bb142dc8ca12b618fffeab`.
`git merge-base main upstream/main` returned that exact commit and
`git rev-list --count main..upstream/main` returned zero.

The remaining 14 donor-only tool argument pairs were reviewed against
their implementations. All have a current route or are an internal
helper; the complete mapping is in
`docs/FORK-ARGUMENT-AUDIT-2026-10-28.md`. On a fresh fetch,
`MOREmbedded/main` stayed at `032fb4b`, and an AST inventory of its
994 decorated tool names found no name missing from the current tool
modules. This closes the signature queue, not the behavior-level fork
review.

The Altium `pcb_calc_track_current_capacity` tool now accepts the
`delta_t_c` argument already present in the fork/shared calculator, while
preserving its fixed-rise and length/resistance outputs. This reduces the
donor-only argument queue from 15 to 14; 53 calculator tests pass.

On 2026-10-28 `rabihnd/integration`'s multipart rectangular IC layout
arguments were integrated into the existing symbol generator and
`lib_create_multipart_symbol`, with `lib_create_ic_symbol(parts=...)` as a
convenient entry point. It accepts blank group rows, hidden pins and
custom pin length, spacing, character width and body padding. A duplicate
package pin across parts is rejected before the SchLib is touched. In a
disposable AD26.11 SchLib, a two-part symbol was created with five pins;
Altium read back owner parts 1/2, the hidden pin and the custom gap. The
same pins survived save, close and reopen. Twenty-nine focused tests pass.
This brings the live donor-only argument queue from 20 to 15.

On 2026-10-28 the older `rabihnd/integration` multipart-symbol patch was
checked again. Its `eTextString` name for schematic labels was absent
from the current resolver. Source `.157` initially copied `eText` too,
but native QA found that spelling already means PCB text and its query
scope guard refused a SchLib query. Source `.159` preserves `eText` for
PCB, uses `eTextString` for schematic `eLabel`, and checks the schematic
resolver before rejecting PCB-only scopes. Its force-save-before-
`lib_get_components` behavior was not
ported: the current read reports saved and unsaved symbol inventories
separately and must not save a user's edited library as a side effect.
Native `.159` queries confirmed the intended split: `eTextString` worked
in a SchLib component scope, while `eText` and `eTextObject` each found
five texts on a disposable board. Both documents closed without saving.
The same donor's STEP `overall_height_mm` was absent from the current
one-call body add, though a separate body edit could set it later. Script
`.158` now accepts and verifies the requested height. A native disposable
PcbLib saved and reopened with the new body at 3.25000112 mm; the original
library was unchanged.
Its pin-batch `default_owner_part_id` is now an optional public argument.
The current-part default remains when omitted; explicit 0 shares the
batch, while per-pin values override it. A disposable three-part symbol
read back owners 3, 0 and 2 before and after save/reopen. The source SchLib
was unchanged.

The Rosen E1 baseline was exercised in AD26.11 on a disposable project:
a footprint created and saved in that project's PcbLib during the session
validated and entered the board via ECO. This does not reproduce the
donor's AD25 case with the library also listed through an aliased drive.
The first ECO exposed a separate closed-board `WRONG_FOCUS` refusal.
Script `.160` opens the exact primary PCB from the project before Compare
and checks board and project focus. A second ECO reached its modal without
manual focus and added C2 with the expected footprint and two pads.
The ECO class-member validation row looked red, but the execution log
and exact-board class readback showed both C1 and C2 in `Only` after save.

The E1 alias-path case was repeated on that disposable project in AD26.11:
`Footprints_QA.PcbLib` was installed in Available Libraries through a
temporary `Q:` substitution while the project used its original `C:`
path. `lib_copy_footprint` created and saved `ECO_QA_ALIAS` in the project
PcbLib during the session. `sch_relink_components` changed C2 to the new
footprint with `footprint_library=Q:\Footprints_QA.PcbLib`; Altium stored
the library basename. The ECO's sole footprint-change row validated and
executed green. After exact-board focus, C2 read back as `ECO_QA_ALIAS`
with two pads, designators 1 and 2. The scratch board was saved and its
project closed; the Q: Available Library entry and substitution were
removed. This narrows the open E1 condition to the donor's AD25 behavior
or another unmodeled project setting; it does not justify a speculative
source patch.

The `yniantongtian-oss/feat/comsol-ai-ecosystem` branch was reviewed at
`0168f7f`: its six `external/comsol-ai/*` entries are Git submodule pins,
not code called by the package. Its `docs/comsol-ai-ecosystem.md` describes
them as a reference base for a future adapter. All six project names and
links are already in `research/battery-ai-comsol-lab/docs/09-reference-stack.md`,
and that lab has its own optional MPh adapter. Adding the pinned Gitlinks
would make clone/checkout depend on six external repositories without
adding a callable feature. No submodule files were imported; the distinct
research code and workflow from this fork remain in `main`.

A fresh `fork-status --fetch --cached-forks --verify-fork-branches --json`
matched 62/62 live fork default tips and 117/117 branch tips to cached
refs. `upstream/main` is still `ee7589c9fc543d0b99bb142dc8ca12b618fffeab`,
the exact merge base of `main`, with zero upstream commits pending.
Comparing Python test paths in 112 fork refs (including MOREmbedded) with
the 691 tracked tests on `main` found ten absent paths. The six previously
reviewed paths still have adapted coverage or a deliberate policy difference.
The four additional paths are `mooreaa`'s placement and Rosen fixes and
MOREmbedded's SDK and update tests. The first two have adapted source and
native checks recorded below. The SDK and update capabilities are present
under current modules. The older via-mask refusal test among the prior
six was superseded by a native-verified pad-cache write, so restoring it
would discard working functionality. Running MOREmbedded's
original update tests against this checkout passed 38/50; its remaining
assertions target the older `run_update`/`_deploy_from` API or manual
reload advice. The original MOREmbedded SDK tests passed 12/12 against the
current source after pointing their source-file lookup at this checkout.
The original `mooreaa` small-fixes tests passed 15/18: two assert its old
plain-string print refusal instead of our structured `PREVIEW_NOT_SILENT`,
and one asserts the old `SameDocPath` source spelling. The current
update/designator/SDK/relink focused set passed 51 tests with one optional
skip. Live `eda-agent update --status --fetch
--from upstream --json` reported the remote, checkout, editable package,
main script folder and compiled `.160` session current.

Comparing public async function argument names in changed tool modules
across 112 cached fork refs found 24 distinct donor-only name/argument
pairs. The list includes renamed tools such as `obj_zoom_to_xy` and
policy differences such as `lib_rotate_footprint(save)`; the other
candidate arguments still require behavior review.
One functional omission was `vincent-himpe`'s `kinds` on
`lib_get_footprint_primitives`: the current Pascal handler already used
that field to skip unrequested filtered walks, but Python did not expose
it. The public tool now accepts validated `track|arc|region|fill|text|via|body`
selections. A disposable library with one added overlay track returned
one track for the full read and `kinds=track`, zero for `kinds=via`, and
one for `kinds=track|via`. The exact library path matched each reply;
closing with discard left the scratch source unchanged. Fifteen focused
tests passed with one optional skip.

The same argument scan found `courtyard_layer`, `assembly_layer` and
`tolerance_mm` missing from the public `lib_compare_footprints` signature.
Its count-only primitive comparison could call two shifted outlines
identical. The wrapper now uses the existing `model_from_live` and
`compare_live` path to add `geometry` and makes `identical` account for
that result; the old pad and per-layer count fields remain. Mechanical
layer kinds are read from each returned PcbLib path, with explicit layer
names as fallback. On two disposable libraries with one overlay track
shifted by 0.508 mm, native readback returned equal primitive counts but
`geometry.layers_differing.silk` contained the two distinct boxes and
`identical=false`. Both libraries closed with discard; 32 focused tests
passed.

## 2026-10-28 refresh after script `.155`

`python -m eda_agent fork-status --fetch --cached-forks
--verify-fork-branches --json` refreshed `origin`, `upstream`, and
`morembedded` and checked the GitHub branch tips. At local and remote
`main=63532c09171accdf6cf85f5ea709e8b458eaace1`, the exact
`upstream/main=ee7589c9fc543d0b99bb142dc8ca12b618fffeab` is an
ancestor and the sole merge base, with zero commits pending from upstream.
All 62 fork default tips and all 117 branch tips match the cached refs.
`MOREmbedded/main=032fb4b2088d9cfa8d95daad9572c9f1f49f3d41` is
unchanged. Fifty-four cached branch refs have commits outside `main` by
ancestry; this is a review queue, not a count of missing features.

The `vincent-himpe/feature/board-via-pad-properties` and
`vincent-himpe/fix/filter-allobjects-walks` changes are present in the
current Pascal sources and their regression tests. The `cad435` managed
placement dirty-document fix is also present. The `andrzej-sikora-elte/elte`
component DbLib flags and footprint-model reads were present; script `.156`
now adds the useful generic writes and passed save/reopen acceptance on a
disposable component. See `RELEASE_VERIFICATION.md` for the field values.
This source-level comparison does not prove complete behavioral equivalence
of all divergent branches.

## 2026-10-28 async tool-surface comparison after `.156`

A source scan compared `async def` names under `src/eda_agent/tools` in
current `main` with 57 nonancestor remote-tracking refs (forks plus the
direct MOREmbedded fork). Two refs, `rabihnd/integration` and the
`james-martinez` Windows-binary branch, retain an older all-in-one Altium
tool module with dozens of pre-split names. Those names need semantic
comparison against the current split tool modules. Among the other 55
refs, the only async names
absent from `main` were `_live_footprint`, `_open_project_paths`, and
`lib_list_vault_libraries`.

`_live_footprint` is a private read helper; current render and audit paths
already read pads, primitives and mechanical-layer kinds with the explicit
PcbLib path. `_open_project_paths` is a private checkpoint helper; the
current checkpoint path reads `project.get_open_projects` inline.
`lib_list_vault_libraries` is the earlier name for the available-library
diagnostic, now `lib_list_available_libraries`, which also lists
uninstalled libraries and reports the Workspace seen in an open design.
The scan is a way to find missing tool surfaces; it does not compare
arguments or semantics in shared functions, so the behavioral review
remains open.

`xthanhn91/main`'s `ensure_loop.py` adds automatic relaunch. The current
CLI already has a supervised `relaunch` command and keeps outstanding
requests, but its default sought a separate installed script project that
does not exist in this main-only checkout. The default now uses the bundled
project in `main`; the live `--dry-run` printed that path and 25 related
tests passed. The donor's request-file purge and shell-built command were
not needed for this behavior.

The older `rabihnd/integration` names checked individually here have
current paths: `lib_diag_footprint` maps to `lib_probe_footprint` for live
3D-body diagnostics; `lib_set_label_format` to `lib_set_label_formats`;
`diag_workspace` to `app_diag_workspace`; and its Win32 screenshot of a
focused PcbLib can be requested through the general `app_screenshot`
tool. The older screenshot captures the whole Altium window and does not
guard an exact library path, so the current general capture is the more
explicit way to inspect the editor view. This is a four-command sample,
not a completed audit of the older all-in-one module.

## 2026-10-28 live refresh and plane-read repair

`git fetch upstream main` returned
`ee7589c9fc543d0b99bb142dc8ca12b618fffeab`; it is an ancestor of
`Rouniy/eda-agent/main`, with zero missing upstream commits. The live
fork inventory matched all 62 cached default tips and all 117 branch
tips. The inherited internal-plane reader was present but unusable through
the public tool because its native reply omitted exact-board identity and
pad count. Script `.145` repairs that contract and passed a native read
on the CW308 baseboard with one internal plane; see `CURRENT-STATE.md`.

## 2026-10-28 MOREmbedded large fab snapshot

The exact-board fab-facts handler read 8355 drilled vias on the
pi-radio antenna board in one native call, matching the board's
independent via statistics and exceeding the former 5000-hole window.
No generated package was present beside that board, so >5000-hole
Gerber/Excellon comparison and package revision provenance still need
separate checks. See `CURRENT-STATE.md`.

## 2026-10-28 MOREmbedded multi-body bulk acceptance

Native `lib_set_3d_body` bulk writes on a disposable two-body footprint
persisted Mechanical16 and opacity 0.65 for both an extruded body and a
STEP body. A second bulk write persisted 0.1-mil standoff on the
extruded body and 0.1-mil STEP model Z offset while preserving the
model's 90-degree rotation. All 41 footprints in the copied PcbLib had
zero unsupported primitives in dry-run rotation plans; the polygon and
dimension refusal still needs a suitable footprint. See
`CURRENT-STATE.md`.

## 2026-10-28 integrated-library completeness

The imported `lib_build_integrated_library` now checks the compiled
IntLib's actual SchLib/PcbLib streams. A fresh Altium compile from a
copied SchLib with an obsolete footprint link omitted its requested
PcbLib; the tool correctly refused that package after the change.
Rebinding the copied symbol's model and rebuilding produced both
streams and passed. This closes the native LibPkg build gate and
prevents a nonempty but incomplete output from being reported as
complete. See `CURRENT-STATE.md`.

## 2026-10-28 mooreaa parameter and port property acceptance

On a disposable schematic copy, native reads and writes of extra
parameter and port properties passed in memory. Parameter
`ReadOnlyState` and `AllowLibrarySynchronize`, and port `AutoSize`,
survived exact save/reopen. Port `OverrideDisplayString` and
`HarnessColor` reverted on an ordinary port; their fields were absent
from its saved SchDoc record. The generic modify reply now warns when
either is written. The 105-test related suite passes. See
`CURRENT-STATE.md`.

## 2026-10-28 mooreaa IntLib relink and DbLib preflight

On a disposable project and IntLib copy, `sch_relink_components` linked
one placed component to an IntLib symbol and the source-library,
library-reference and design-item fields persisted after save/reopen.
The DbLib path now refuses duplicate keys and capped lookups before
any write; 15 focused tests pass. No DbLib file was present in the
local `Z:` corpus, so native DbLib acceptance remains open. See
`CURRENT-STATE.md`.

## 2026-10-28 two-board net-colour acceptance

The upstream `pcb_net_display(from_project=True, nets=None)` path was
checked natively with 229 copied-project board nets beside an unrelated
74-net board. A call while the other board was selected refused the
target path; after `pcb_focus_board`, the 229-row project-colour plan
matched the copied board's exact net inventory and read five colours.
The copied project closed without saving. The wrapper descriptions now
make the multi-board focus requirement explicit.

## 2026-10-28 project-generated CrossRef qualification

The `mooreaa` port-reference fix was exercised on an Altium-generated
CrossRef in a disposable two-sheet project with `AutoCrossReferences=1`.
After deliberately moving the generated reference to the wired end,
dry run and apply moved it back with one exact native readback. Altium
regenerated the correct position after reopening and compiling both
sheets. Compiling with only one of the linked sheets loaded yielded no
CrossRef despite reporting success, so the no-reference hint now says
to load linked sheets before compilation. See `CURRENT-STATE.md`.

## 2026-10-28 mooreaa CrossRef native qualification

The CrossRef planner read Altium `ConnectedEnd=1`, made a reviewed move
on a disposable sheet, and confirmed the new position after exact save,
close and reopen. Its first live apply exposed a string-format readback
bug (`8420.0` versus Altium's `8420`); the Python tool now verifies
coordinates numerically and the focused suite passes. The test used a
manually placed CrossRef parameter. The separate project-generated
qualification above closes that acceptance gap. See `CURRENT-STATE.md`
for the geometry.

## 2026-10-28 mooreaa live-pin native qualification

The `mooreaa` visible-pin filter was checked on a disposable SchLib and
sheet with two display modes and two symbol parts. Ordinary ePin queries
excluded the inactive mode and part copies; explicit `OwnerPartId`
queries exposed them. Counts 8/10/2 persisted after exact save,
close and reopen. See `CURRENT-STATE.md` for the pin positions and
source-copy hash comparison.

## 2026-10-28 xSignal class and HTTP restart correction

The upstream xSignal class option now creates or reuses a Signal-kind
board class and verifies the newly created pair in its indexed members.
Two pairs were added to one class across two save/close/reopen cycles on
a disposable populated board. The Python MCP wrapper rejects an
unverified class assignment. The HTTP MCP self-restart now preserves
`serve-altium-http.py` instead of switching to stdio; live port 14701
and `app_ping` recovered after its own restart. See `CURRENT-STATE.md`
for the native evidence and original-board hash.

## 2026-10-28 cad435 Workspace exact search

The `cad435` Workspace resolver's first-fuzzy-result limitation is fixed
in script `.131`: it checks all returned candidate revisions for an exact
Component Item name, rejects duplicate exact-name Items and identifies a
full 100-result page as incomplete. The installed SDK exposes the list
methods used; Pascal lint/build and eight focused tests passed. This
session lacks a Workspace connection, so a live exact-match case remains
unqualified. See `CURRENT-STATE.md` for the native refusal and scope.

## 2026-10-28 populated-board xSignal qualification

The upstream xSignal create/delete family now has native AD26 evidence
on a disposable populated board. `R16.2` and `R15.1` formed one routed
`NetR15_1_PP1` pair, which survived save/close/reopen; targeted deletion
also survived save/close/reopen. The owner board hash stayed unchanged.
See `CURRENT-STATE.md` for the exact counts and length.

## 2026-10-28 cad435 pad-name qualification

`cad435/c7d55bb`'s pad-name read/write and PCB batch routing are already
in `main`. On a disposable CW308 board, one pad was renamed through
`obj_modify` and then through `obj_batch_modify`; exact save/close/reopen
retained the final `Name` and `Designator`. The source board hash stayed
unchanged. See `CURRENT-STATE.md` for the exact filter and readback.

## 2026-10-28 schematic menu qualification

The `mooreaa` `Sch:DeSelect` alias behind `app_run_menu('Edit|Deselect All')`
now has an independent native readback: a selected component's schematic
`Selection` flag changed from true to false on a disposable sheet. The
project was closed without saving. See `CURRENT-STATE.md` for the calls.

## 2026-10-28 live synchronization check

`eda-agent fork-status --fetch --cached-forks --verify-fork-branches --json`
refreshed origin, upstream and the direct MOREmbedded fork. At local
`5620c27`, origin matched `main`; upstream tip and exact merge base were
`ee7589c9fc543d0b99bb142dc8ca12b618fffeab`, with zero upstream
commits outside `main`. All 62/62 live fork default tips and 117/117
branch tips matched local cached refs. MOREmbedded tip remains
`032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`; its 33 commits outside
our Git ancestry are tracked by the behavior-level integration audit.

## 2026-10-28 placed footprint-stamp qualification

The `mooreaa` placed-component `Footprint` stamp now has AD26 native
persistence evidence on a disposable sheet. Two existing library models
were selected in one `sch_set_components_parameters` call; both survived
exact save, close, and reopen. The public registry exposes that bulk tool
for one or more stamps and `sch_place_components` for one or more placements.

## 2026-10-28 placement-model qualification

The `mooreaa` bulk placement model chooser now has native persistence
evidence on a disposable project copy. An available nondefault PCB model
was selected on `RES`, while a missing model produced an explicit issue
and kept the default. Both states survived exact sheet save, close, and
reopen. See `CURRENT-STATE.md` for the names and readbacks.

## 2026-10-28 mooreaa placed-part qualification

The `mooreaa` current-footprint pin-map write now has native persistence
evidence on a disposable two-pin placed component: a swapped mapping
survived exact save/close/reopen. Its out-of-range display-mode write was
refused without changing the component. A separate copy with a two-mode
library symbol accepted `DisplayMode` 0 to 1 on a newly placed part,
and the mode survived exact save/close/reopen. See `CURRENT-STATE.md` for
the readbacks and scope of the graphic check.

## 2026-10-28 polygon-read qualification

The upstream `pcb_pours_at` port passed a populated-board native check:
on CW308 baseboard its polygon at `(6500,4000)` mil and two overlapping
GND pours were reported, while `(0,0)` returned none. Both it and
`pcb_board_options` refused a wrong expected board path. On a disposable
copy, its polygon-name template write from 0 to 1 survived exact save,
close and reopen; the original board hash stayed unchanged. See
`CURRENT-STATE.md` for exact results.

## 2026-10-28 checkpoint follow-up

The `vincent-himpe` footprint-primitive-selection and selected-pad/drill-type
branch tests each pass 10/10 against current `main`; both capabilities are
already present. The `mooreaa` port-cross-reference and placement-cleanup
tests pass 35/39 when run from the fork: two port tests use a fake bridge
that omits the active-document path our exact-sheet guard requires; two
placement tests assert older source spellings instead of behavior. The
current tools retain the port planner, per-part pin query and cleanup
functions. Native CrossRef sheet acceptance remains open.

The fork's `Sch:DeSelect` with `Action=All` was already used by
`obj_deselect_all`. The display-side `app_run_menu('Edit|Deselect All')`
still mapped to the old `Sch:DeSelectAll` process that left selections
standing on AD25.8. Script `.130` sends the same corrected action through
both routes. The 12-unit Pascal bundle built and the loaded Altium script
reports `.130`; the selected-object native readback is recorded above.

`main` includes upstream tip `ee7589c9fc543d0b99bb142dc8ca12b618fffeab`
as its exact merge base; `main..upstream/main` has zero commits. The live
fork check matched all 62/62 default tips and 117/117 branch tips to local
refs. `MOREmbedded/main` remains `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.

Running `mooreaa`'s Rosen small-fixes tests against our source exposed one
remaining behavioral gap: `app_checkpoint` treated Altium's synthetic
`Free Documents` entry as a second open project and refused an unnamed
checkpoint when exactly one real project was open. Commit `0614d73` filters
that entry before deciding whether the project is ambiguous. The focused
checkpoint tests passed 8/8, and the HTTP MCP server was restarted from
`main`; Altium script `.129` still answers on port 14701. The other Rosen
test failures in that external test run were response-contract differences
or its temporary location making relative Pascal source paths invalid.
Rerunning with the source path corrected passed 15/18: the remaining
three are the two PDF error-shape assertions and an assertion for the
fork's `SameDocPath` spelling. Our close handler performs the same
canonical-path comparison before `Client.CloseDocument`; those three
failures do not identify a missing behavior.

## 2026-10-28 public-tool-name cross-check

An AST inventory compared public function names in `src/eda_agent/tools`
across 120 cached remote refs with `main`. Twenty-two refs have names
that do not appear literally in today's modules. This is a lead list,
not a feature-gap count: several old forks predate the `app_*` and
`lib_*` names, and nested helper names are also counted.

The four apparent stackup gaps in `MOREmbedded/main` are renamed tools:
`design_list_fab_vendors` is `design_list_stackup_vendors`,
`design_fab_vendor_profile` is `design_stackup_vendor_profile`,
`pcb_check_stackup` is `pcb_check_vendor_stackup`, and
`pcb_apply_stackup_template` is `pcb_apply_vendor_stackup_template`.
The fork's `lib_list_vault_libraries` is covered by
`lib_list_available_libraries` and `lib_get_vault_name`; the latter
separates Workspace identity from Altium's available-library **type**
ordinal. On the loaded `.117` script, the available-library reader
returned five file libraries, all with their actual types, and no
Workspace identity from the open design. That is a valid empty
Workspace observation, not proof that none is connected.

The two `vincent-himpe` branch commits `b05ac10` (via-mask bottom
follows top) and `530db39` (filtered PCB object walks) are also present
in adapted source and their focused tests already exist in `main`.
The via-mask, filtered-walk and available-library focused suites passed
19/19 checks in this review.
This name scan does not prove complete behavioral parity across the
120 refs; remaining differences require source and native checks.

## 2026-10-28 additional branch behavior audit

Across 111 cached external fork refs, six Python test paths are absent
from our tree. This is a path inventory, not a missing-feature count.
The original 11 `vincent-himpe/fix/decimal-mils-leftovers` length tests
all pass against `main`. The custom-pad test's six `eCustomShape`
mappings are present in our Pascal readers and covered by
`test_library_and_board_reads_writes_2026_10_23.py`. EasyEDA extension
nonempty-destination behavior is covered by
`test_easyeda_extension_packaging.py`; the fork's CLI was adapted into
our existing `easyeda_extension.py`. The other missing test paths are
security-policy format, an empty benchmark package, and the
`bblacklock3` designator-batch refusal.

The last is a deliberate behavioral difference: upstream commit
`6486ac1` removed `SetWritesDesignator` to retain bulk renaming, and
our `obj_batch_modify` describes the partial-write/netlist risk. The
separate `sch_batch_rename_designators` now checks collisions and a
project snapshot before writing, uses temporary unique names and reads
the project back after each phase. Its native acceptance is recorded in
`TODO.md`; this test-path review did not make a CAD edit.

## 2026-10-28 native parameter-scope follow-up

The `mooreaa` template Value reconciliation led to a first-level
parameter scope fix in `Generic.pas`. A prior native stamp on an
installed `CAP` symbol had modified a nested model `VALUE`, revealing
that `SetCompParamText` traversed implementation children. Loaded
script `.115` created a direct component `VALUE` and then updated it
to `33nF` together with Comment, while the model `VALUE` stayed put.
The disposable sheet was saved and closed; 15 focused tests and the
12-unit Pascal lint/build passed. A fresh fork-tip check still found
62/62 default tips and 117/117 branch tips cached. `upstream/main`
remains the exact ancestor `ee7589c`.

## 2026-10-28 mooreaa behavioral test reconciliation

The fork's original `test_placement_cleanup.py` was run against our main:
19 checks passed and three failed. Two failures asserted old source
spellings; the current live-pin filter is deliberately query-only and
port width keeps fractional mils. The third revealed that
`sch_draw_template` had missed the fork's `Value` stamp and still sent
`Comment`; our native handler uses `Value` to update both Comment and
the component Value parameter. The adapted fix is in our Python tool.
Forty-two related tests pass with 19 optional skips. Native end-to-end
placement and visible Comment readback passed for two symbols on
disposable SchDocs. An existing component-level Value parameter still
needs native readback; the available `CAP` symbol's `VALUE` is a nested
model parameter.

## 2026-10-28 optional battery lab branch

The self-contained `research/battery-ai-comsol-lab` tree and its scoped
CI workflow were imported from fork branch
`yniantongtian-oss/feat/battery-ai-comsol-lab` at `0f7c73f`. This is an
optional research package, not an Altium bridge dependency. Its own
Python 3.12 environment installed PyBaMM 26.10.1.1; Ruff and six tests,
including a short electrothermal solve, passed. The COMSOL/MPh adapter
still needs a licensed native run. We intentionally did not import the
branch's unrelated root documentation, dependency and submodule changes.

## 2026-10-28 live fork-tip audit

`fork-status --verify-fork-branches` matched all 62/62 live default tips
and 117/117 live branch tips to cached refs. The direct MOREmbedded fork
is at `032fb4b`. Its two commits after the old `b48f970` checkpoint,
`789cabb` (SDK property coverage) and `032fb4b` (NPI phase gates), are
already adapted in our `ef78bd5` and `87eb0f3`. Their substantive source
diffs are the deliberate DFM gate manual classification in `f95c232`
until a specific board can be compared with a fab package, and a stale
SDK resolver test threshold. The current resolver finds 37 schematic and
31 PCB types, so the upstream test's stronger >30/>20 guard is restored.
The 66 SDK/NPI focused tests pass. The fork's two commits need no second
copy.

## 2026-10-28 upstream main advance

`upstream/main` advanced from `f3bd57f` to `ee7589c`. The latter is merged
by ancestry into our `main`. Its `sim_get_probes` change uses the counted
`ProjectSheet` lookup so the reply reports sheets seen and skipped; its
layout regression test compares the courtyard point by point for pytest
9.2 compatibility. The merge kept our broader Pascal implementation and
bumped the bundled script to `2026.10.28.114`. Thirty-six focused tests
passed and `scripts/altium/build.py` linted all 12 units with zero errors
or warnings. The Altium bridge restarted on `.114` with zero cast errors.
On the isolated Simulation Quick Start copy, `generic.get_probes` returned
`sheets_seen=7, sheets_skipped=7, count=0` with no sheet loaded, then
`sheets_seen=7, sheets_skipped=6, count=1` after opening one sheet. The
sheet and copy project were closed without saving.

## 2026-10-28 MOREmbedded package-audit routing

Native script `.113` ran `lib_audit_footprint_vs_package` for
`FP-53261-0771-MFG` in inactive `PCB1.PcbLib` while
`Spirit_Level_Project.PcbLib` was focused. The audit resolved the exact
target library path, read 21 tracks, one arc and one text, and had no
wrong-library note. Both libraries were closed without edits. A diagnostic
custom package based on [Molex drawing 532610001-SD, sheet 2](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/532/53261/532610371_sd.pdf)
found seven 0.8 mm signal pads versus 0.6 mm recommended land width.
Pad-centre offsets in this diagnostic came provisionally from the footprint;
the native run proves correct multi-library routing and width comparison,
not an independent package signoff. Full drawing transcription remains open.

## 2026-10-28 MOREmbedded two-library read

The adapted `lib_render_footprint` path was checked live on script
`.113` with two PcbLibs open. `Spirit_Level_Project.PcbLib` was focused,
but the render targeted `FP-51021-0700-MFG` from inactive `PCB1.PcbLib`.
The target's Mechanical5/2/3/16 kinds became Assembly, 3D Body,
Courtyard and Center roles (four/four/four/two primitives). The
focused library had no such kinds. Both libraries were closed without
edits. The package-audit path was subsequently checked live as above.

## 2026-10-28 fractional PCB batch placement

The fork's fractional batch placement and bottom-side flip were tested
in loaded script `.113` on a disposable board. `pcb_place_components`
placed two `CC1608-0603` footprints from Altium's installed example
PcbLib. Top and bottom origins, sides and rotations matched after
exact save/reopen. The bottom X readback was 1500.6248 mil for a
1500.625-mil request, within one native PCB coordinate step. The
source PcbLib was read only and closed; no managed board was edited.

## 2026-10-28 fractional schematic native fix

The fork's fractional-coordinate port preserved batch wire vertices
after save/reopen, but the text-frame placement reply rounded all four
coordinates and the generic query returned empty `Corner.X/Y`. Script
`.113` uses decimal JSON in the reply and typed `ISch_TextFrame.Corner`
for generic read/write. Altium loaded `.113` and returned exact
fractional placement and corner-edit coordinates after save/reopen on
a disposable SchDoc. Pascal lint/build passed 12 units with zero
errors or warnings, and 12 related source tests passed. The native
`pcb.delete_xsignals` conflict guard also refused `names` with
`all=true` before resolving any board. DbLib fractional placement is
still unverified.

## 2026-10-28 continuation: native simulation and live fork tips

The merged `.112` runtime placed a voltage probe on the `out` wire of
an isolated Altium Simulation Quick Start copy. The probe survived exact
save/reopen with `SimulationProbe=V`; a sheet run saved numeric SDF
results. An op-only request nevertheless ran op, DC, transient and AC,
and reopening with an op-only saved setup did not change this. The
Python tool now reports that observed limitation. Its focused 53-test
simulation suite passes, and the HTTP/MCP process was restarted from
`main` so its live descriptions match the corrected code.

Fresh `git fetch` found `upstream/main` still at
`f3bd57ff87b915d5cfe72579fa501bfea85c3511`, the exact merge base
of `main`, with zero upstream commits to import. GitHub's fork listing
returned 61 forks. `git ls-remote --heads` checked all 109 live branch
tips: 60 external forks' 107 branches already matched the cached refs.
The two differing refs belonged to our own fork: `main` had advanced,
and `agent/sync-upstream-d6823d5` was not cached. The latter is already
an ancestor of `main` (`main..branch=0`). Both own-fork cache refs were
updated to their live tips, giving 109/109 matching branch refs. The
MOREmbedded default branch remains `032fb4b`.
The repository's `fork-status --verify-fork-branches` includes upstream
alongside those forks and independently reported 62/62 default tips
and 117/117 branch tips matching local refs.

## Native fork free-text acceptance on `.112`

The merged runtime placed `sch_add_text` as one `eLabel` on a disposable
free SchDoc at 125.125, 200.25 mil with 90-degree orientation. Exact
save, close and reopen preserved its text and geometry. Altium's font
table normalised `FontId` 1 to 2; both records are Times New Roman 10,
and ID 2 carries the 90-degree rotation. An unloaded exact sheet was
refused. The QA file was closed and deleted. The later simulation check
is recorded above.

## Live merged bundle `.112`

Altium 26.11.1.5 was restarted after the source merge. The loaded main
script project now answers `application.ping` with `.112` and zero cast
errors. The restarted HTTP/MCP server on 14701 lists 757 tools, including
the fork's exact-sheet `sch_add_text` and upstream's `sim_get_setup`.
TCP 14700 remains listening. Subsequent native checks are recorded above.

## Vincent decimal helper reconciliation

The `vincent-himpe` decimal-mil source carried a second module-level
`library._mils` definition. It silently overrode our later finite-value
check, so `NaN` could become an Altium coordinate string. The duplicate
is removed: the retained helper keeps four decimal mil places and
refuses nonfinite inputs. Thirty focused tests pass. A separate comparison
of `rabihnd/integration`'s footprint diagnostics found the current
`lib_get_footprint_primitives` already includes each 3D body's identifier,
layer, `has_model`, model file, type, rotation, height and standoff. Its
window capture is covered by `app_screenshot` after focusing the PcbLib.

## Upstream `f3bd57f` simulation merge

`upstream/main` advanced from `c45ca0a` to
`f3bd57ff87b915d5cfe72579fa501bfea85c3511`. This is one commit:
Altium-native voltage probe parameters, probe inventory, simulation setup
readback, sheet-run analysis selection and `.simcfg` reload. It was merged
as a true second parent; the native script version is `.112` because the
main fork already contained `.111` and its exact-sheet free-text handler.
The main fork's selected-project flags remain in `Main.pas`.
Upstream's scratch-project Altium acceptance is recorded in the merged
release verification; local source tests and Pascal lint/build pass.
Native acceptance of this exact merged bundle is recorded above.

## Fresh live inventory after `1d093a2`

Fetched `upstream/main`, `morembedded/main` and `origin/main`, then ran
`python -m eda_agent fork-status --verify-fork-branches`. The exact upstream
tip and merge base are `c45ca0a537ad5afe0cda4ce1951e6bfb6be4ff3d`;
zero upstream commits remain outside `main`. The live check matched 62/62
fork default tips and 117/117 branch tips to local refs.
`MOREmbedded/main` is still `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.
Its separate `via_loop_inductance` function is the already registered
`pcb_calc_via_inductance` in our broader calculator module. The Johnson
formula agrees, but the shared calculator accepted `NaN` as a successful
result; the fork's input guard refused it. The shared calculator now rejects
nonnumeric and nonfinite values. The GitHub Actions API returned zero
runs for `build-windows-binary.yml`; the local exe smoke test remains the
only build evidence for that workflow.

## Legacy wrapper suite reconciliation

The seven remaining stale calls in `test_added_altium_tools.py` were
reconciled with exact-board and preflight wrappers. Obsolete direct-send
assertions were removed where focused tests cover read, plan, write and
identity guards. Native Pascal assertions with distinct coverage remain.
The combined legacy and focused suites pass: 129 tests. This is source
qualification; the shared Altium runtime still has the older loaded script.

## Fractional-mil annotation follow-up

The residual decimal-mil audit found that `Proj_Annotate` converted
component positions to whole mils before sorting. Source `.106` keeps
native TCoord integers as its sort keys, preserving the relative order of
components with sub-mil spacing. Native annotation acceptance remains
pending. Five related tests and Pascal lint/build passed. Direct
`CoordToMils(` calls remain only in utility/self-test code in the split
Pascal units; other decimal conversions still require behavior review.

## Reviewed fork names with existing behavior

`rabihnd/integration`'s `ApplySetPropertiesEx` adds a call-site catch and
returns skipped names. Our `ApplySetProperties` preflights unsupported
properties, `SetSchProperty` records failed and unknown writes, and
`ModifyOutcomeJson` returns that diagnostic. A second parser would duplicate
this behavior. `cad435/main`'s `Lib_ListVaultLibraries` maps to
`lib_list_available_libraries` plus `lib_get_vault_name`; the current code
uses `TLibraryType` correctly and reports Workspace identity separately
from the available-file list. No donor API was copied here.

The sole child fork's NPI and SDK reflection modules are present on main.
The NPI criteria file differs by nine lines: the fab-capability DVT gate
is manual until a complete same-snapshot export comparison is proven, and
the impedance gate names the current fab-vendor tool. The NPI and SDK
reflection suites passed 66 tests. This confirms source and test coverage,
not native Altium acceptance of the SDK-derived tools.

## Schematic source-library cleanup

The `wizd/edev` clear command also unpinned every PCBLIB model's datafile
Location. Source `.105` adds that as an explicit option to the existing
`sch_clear_source_library` tool, shares the clearing helper with
`sch_relink_components(footprint_library="Any")`, and counts successful
link clears and failed readbacks. It also refuses an unloaded exact sheet
instead of falling through to the focused sheet. Twenty-four related tests
and Pascal lint/build passed. Native verification awaits a controlled
Altium reload.

## Follow-up source verification

The footprint/relink suites now pass 48 tests with one optional skip.
One old test assumed read and write branches for `DisplayMode` had the
same text; both are guarded by `eSchComponent` in the current source.
The refusal-only `proj_export_pdf` handler now has read-only metadata.

## Placed footprint name mirror

`wizd/edev` mirrors the selected PCBLIB ModelName onto the placed part's
`Footprint` parameter. Source `.104` adds this to our existing guarded
`SetPlacedFootprintName` helper for both choosing an existing model and
renaming one, with parameter readback before success. Native persistence
and ECO checks remain pending while the shared Altium session stays on
compiled script `.96` with 16 projects open.

## Placed footprint library links

`wizd/edev` provides an explicit `Any` or `*` action to clear stale
PCBLIB datafile Locations and creates a link when a footprint model lacks
one. Source `.103` adapts both behaviors to the existing guarded
`sch_relink_components` path. The relinker retains its file-name-only
Location because a full PcbLib path wedged Altium 26.11 in earlier native
testing. Native persistence and ECO acceptance remain pending.
Eighteen related tests and Pascal lint/build passed.

## Multipart graphic ownership follow-up

After restoring line ownership, an interface review found that
`lib_add_symbol_rectangle` did not expose the `owner_part_id` its native
handler already accepted. Source `.102` exposes it and also carries the
field through `lib_add_symbol_arc`, whose native handler now uses the
same part-aware helper. Polygon and batch line writers share nonnegative
owner validation. Seventy-seven related tests and Pascal lint/build pass;
native multipart-library acceptance remains pending.

## Schematic frame type names

Current upstream and `MOREmbedded/main` both map schematic polygons, arcs,
elliptical arcs, ellipses and Bezier curves back to readable `sch_*`
names. Our `SchTypeName` had lost those five cases, making
`app_get_sheet_frame` emit numeric `type_<id>` fallbacks. Source `.101`
restores the cases and adds names for five more accepted schematic types.
Seventy-one related tests and Pascal lint/build passed. Native verification
remains pending.

## Multipart symbol line ownership

The `rabihnd/integration` single-line tool exposed an explicit
`owner_part_id` (including 0 for a graphic shared across sub-parts). Our
batch `lib_add_symbol_lines` had no such parameter even though
`Lib_AddSymbolLines` already parsed it. Source `.100` now sends an optional
owner for each line and makes the common Pascal owner helper honor 0.
Three symbol writers now also use the existing `AddLibSymbolPrim` route to
show new graphics immediately on the active symbol and preserve their
specified owner. The batch path retains its one-call editing behavior.
Sixty-nine related tests and Pascal lint/build passed; one pre-existing
reverse schematic-name assertion remains outside this change. Native
save/reopen verification remains.

## Recovered fork helpers

The 119-ref name inventory exposed a real merge loss beneath the apparent
tool coverage. `Generic.pas` still called the `mooreaa` No ERC property
helpers and `Project.pas` still called `SaveProjectFile`, but their
definitions were gone. Source `.99` restores all three in declaration
order. It also pins `app_create_document` to its preselected project,
refuses an existing file path and writes the project membership after a
successful file save. The project save result now requires a changed disk
timestamp; a same-second write can be conservatively reported unverified.
Fifty-one related tests and Pascal lint/build passed. Native execution
awaits a controlled Altium restart.

## Saved No ERC parity follow-up

On two project copies, both named single-pin-net ERC rows stayed suppressed
after deleting their No ERC marker, saving the exact sheet and explicitly
compiling. Closing and reopening that saved sheet before another compile
made each row active. The originals stayed byte-identical across all 59
files. This proves the markers suppress the rows and that Altium's compiled
model can retain their old state beyond a save and `DM_Compile`.

Python's `proj_run_erc` accepted but discarded `project_path`, allowing a
caller to believe it ran ERC on a named project when Altium compiled the
focused one. The native run and violation reader already resolve an exact
project path; both Python wrappers now pass it. The run reads and returns
the filtered/pageable violations, merging its compile action. Script `.98`
also makes a confirmed-save reload clear the bridge's tracked edit before
the document close. Native qualification of these source changes is pending.

## ERC in-memory edit follow-up

Two Altium 26.11.1.5 ERC checks found that deleting a No ERC marker in
memory did not change the target row's `suppressed=true` status after a
reported recompile. The bridge also reported `dirty_doc_count=0` after
an edit it had acknowledged. Source `.97` now invalidates the cache on a
tracked edit, counts that edit as dirty independently of Altium's
`Modified` flag, and clears its record after a confirmed discard/close.
Native execution of `.97` and Altium's treatment of unsaved No ERC edits
remain to be checked on disposable documents. A fresh fetch still puts
`upstream/main` at `fbf72a78254cb0573fb75e71600f5850e38421a0` and
`MOREmbedded/main` at `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.

## Refreshed Git and function inventory

The `redbird98` AD25 Chinese-locale bridge used the system GBK codepage for
response files. Our current request path already supplies a UTF-8 BOM to
`TStringList.LoadFromStream`; the Python response reader now tries UTF-8
first and uses the system codepage only when UTF-8 decoding fails. Both
the BOM and a CP936 Chinese reply decode in the focused test; 37 bridge
and session checks passed. A live AD25 zh-CN session is still needed to
verify the fallback end to end. Six unrelated assertions in the older
`test_unicode_and_detach_transport.py` initially failed against the current
main script and detach API; the audit below resolved them.

The `redbird98` AD25 source-encoding and detach checks revealed two real
merge losses. Script units and installed copies are now ASCII without a BOM;
the generated `Altium_MCP.pas` was rebuilt from the current sources. The
native detach path now honours `SaveScope='edited'`, leaving clean open
documents untouched, and clears tracked edit marks after a confirmed save
for every document kind. The stop reply separates confirmed writes
(`edited_saved`) from attempts (`edited_attempted`); a failed Python
`app_detach` reports `stopped=false` and its reason. The remaining legacy
assertions were updated to the current hex helper, timestamp-verified save
contract and registry key name. Seventy related tests passed; Pascal
lint/build found zero errors or warnings across 12 units. Script `.96`
was reloaded in Altium 26.11.1.5; `eda-agent doctor` confirmed the same
version with zero critical failures. Disposable-document detach/save
acceptance remains pending.

The `yniantongtian-oss` release verifier checked both wheel and sdist
payloads and the wheel's package metadata. Our existing verifier already
installed the wheel in a clean environment; it now also requires one sdist,
checks its Altium and EasyEDA sources, and compares the wheel's version,
Python requirement and console entry point with `pyproject.toml`. A fresh
`python -m build` produced both artifacts. The verifier passed their payload
and metadata checks, then installed the wheel and ran `--version`,
`scripts-path` and `easyeda-extension path` from the isolated install.

The `mooreaa`/`rhsvekon` library body read returned saved STEP model
rotations and Z offsets alongside the live body properties. Our stricter
`lib_set_3d_body` now includes `saved_bodies` on read, dry-run and verified
edit replies when saved body count matches the live count. The reply labels
these records as coming from the file on disk, since unsaved editor changes
can differ. Fifteen body-model checks passed, with one optional dependency
skip; native readback remains to be checked on a disposable PcbLib.

The `abed-amraie` footprint preview used Altium's mechanical-layer kind
and returned courtyard/assembly roles plus silk-on-copper findings. Our
existing `lib_render_footprint` now adds those findings while keeping its
SVG format and existing fields. The SVG colors a mechanical layer from
its native kind (or an explicit caller override), rather than its number
or incidental name. Both `TopOverlay` and `Top Overlay` classify as silk;
the latter was lost by the prior live-model converter. Thirty focused
render/live-model tests passed. Native library acceptance remains pending.

The `rabihnd/integration` fork's one-pin-per-pad designator guard was
missing from our batch library writers. `_pins_payload`, `_pads_payload`
and the single footprint-pad tool now reject grouped names such as
`A4,A6,B1` before sending any batch to Altium. Blank designators retain
their existing handling for unplated mounting holes and skipped pins.
The batch grammar and cross-validation checks passed (42 passed, 19
environment-dependent skips). Native library acceptance remains pending.

After a fresh fetch, `upstream/main` is still
`fbf72a78254cb0573fb75e71600f5850e38421a0`. That exact commit is the
merge base with `Rouniy/main`, and `main..upstream/main` contains zero
commits. `MOREmbedded/main` remains
`032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`. The live fork verifier
found 62/62 default tips and 117/117 branches matching cached refs.
An AST scan of changed Python source in 111 cached fork refs found 21
function names absent from `main` before the bridge port below. Most are
equivalent methods with other names (the singular `lib_add_pin` and
`lib_add_symbol_line` versus our batch writers, and the donor's
`via_loop_inductance` versus `pcb_calc_via_inductance`). The donor's
`_prjscr_is_ad25_safe` rejects headers present in this AD26 script project,
so importing it would make this main-directory installation fail. Name
coverage is a triage aid, not proof of behavioral parity.

## MOREmbedded bridge reply and view recovery

The donor's `_with_outdated_note` had been lost while the surrounding
version tracking remained. Both sync and async native replies now refresh
the compiled script version on ping and periodically warn when a long-lived
Python server predates the compiled script. Async calls also restore a
hidden Altium frame after a reply, as sync calls already did. The optional
`EDA_AGENT_KEEP_BOARD_IN_VIEW` action was unreachable after the async
refactor; it now fits the board after a successful edit when enabled.
Forty-three restart, session-document and fit-view tests passed. This is
Python bridge code; native acceptance is pending a controlled session.

## MOREmbedded ECO verification and hidden menu window

The shared-file review found two MOREmbedded behaviors missing from `main`.
`verify_eco` now compares every physical copy of a repeated pad name,
including split thermal pads, so a later bound copy cannot conceal an
unbound or mismatched one. If either the compiled pin list or board pad
list is empty, it reports `nothing_compared=true` and `complete=false`.
The existing report field names and direct single-net comparison inputs
remain accepted. The menu's existing hidden-frame recovery called
`windows.show_without_focus`, which had been dropped in a merge; the
wrapper is restored. Thirty-two ECO, project-sync and hidden-window tests
passed. Native ECO and hidden-frame acceptance remains pending.

## MOREmbedded rotation audit integration

Compared `MOREmbedded/main`'s multi-pad `rotation_audit` with the fork's
existing two-pad advisory. The current audit now scores each connected net
once while rotating all of a component's pads together, recognizes power,
ground and explicit plane nets for nearest-return scoring, skips locked
parts, and records candidate turns blocked by a known courtyard or 3D body.
Courtyard collisions are checked only between parts on the same board side,
matching `placement_audit`; the donor checked both sides together. The
existing `suggest_rotations` response, two-pad per-pad terms and advisory
`counts` remain compatible, with `blocked` and `courtyard_checked` added.
The audit is offline geometry advice; native board placement still needs a
DRC before applying a suggested turn. Thirty-nine rotation, placer, model
and autoplace tests passed, including shared-net scoring, multi-pad nets,
blocked turns and opposite-side courtyards.

## Upstream `fbf72a7` integration

The fresh `upstream/main` tip is
`fbf72a78254cb0573fb75e71600f5850e38421a0`, four commits after the
previous merged tip `40814badc695813157fd8c50d24feafc5a553fcd`.
`MOREmbedded/main` remains
`032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.

The upstream merge brings two-sided mask expansion for a lone via value,
filtered object walks, remaining decimal-mil conversions, deletion of vias
on any layer, optional deferred polygon pours, and footprint-body selection
by identifier. The merge retained our exact-board contracts, component
source IDs, paste-disabled guard, fractional placement, and selected
project controls. A conflicting duplicate footprint-selection handler was
removed: the retained handler filters its iterator by supported primitive
kinds and supports body identifiers. The old duplicated Python wrapper was
also removed. Script `.93` loaded in Altium 26.11.1.5 with zero cast
errors; ping and ten unit stamps returned. Native read/write acceptance of
the newly merged commands is still pending.

Pascal lint/build scanned 12 units with zero errors or warnings. Focused
upstream tests passed 19/19 for decimal mils, filtered walks and via masks;
four current-tip behavior tests and 64 adjacent fork tests also passed.
The broad older `test_added_altium_tools.py` contains assertions for the
unscoped upstream API (for example calls without our required `board_path`),
so it is not a valid whole-file gate for this fork until reconciled.
After the merge, `eda-agent fork-status --verify-fork-branches --json`
compared all 62 direct/child fork default tips and all 117 branch tips
with live remote refs; every cached tip matched. This is branch freshness,
not proof that all divergent behavior has already been ported.

## MOREmbedded update-status integration

The child fork's `ff4d7e8` and `43457f4` added a four-layer update
diagnostic: Git checkout, installed Python package, script files on disk,
and the version compiled by Altium. Our existing `update --yes` already
provides the apply path, so this port adds the read-only `update --status`
mode, with optional `--fetch`, `--from` and `--json`. It reports the
editable checkout as the script source when no copy or registry entry is
present, matching this workspace's main-directory setup. A responsive
Altium ping also supplies the loaded script-project path for comparison;
when Altium is busy, the session is explicitly unknown. Ping extensions
are disabled for this report so a queued command cannot delay it for
minutes. Twenty-one focused update tests passed. The current live run
reported Git/package/script source current, and the unresponsive Altium
session and loaded path unknown.

## Fork source-file inventory and EasyEDA build guard

The 119 cached direct and child fork branch refs were compared by tracked
Python source path against `main`. After the MOREmbedded update report was
ported, the sole path absent from `main` was
`yniantongtian-oss/main:src/eda_agent/easyeda_extension_cli.py`. Its
`path`/`build` operations already exist in our `easyeda-extension` CLI.
The fork additionally refused a nonempty destination without `--force`
and checked that the build produced a nonempty `.eext`; these safeguards
are now adapted into our existing builder. The checkout still builds in
place, and wheel builds still use the configured writable directory.
Seven EasyEDA packaging tests passed, including the new refusal and
artifact checks. A real isolated build with Node produced a 55,115-byte
`.eext`. The source-file scan detects file-level omissions, not every
behavior difference in shared files; behavioral review continues.

## Later upstream tip in this session

The fork tool-name scan also exposed a real feature removed from our
current EasyEDA backend: `4pplet/main` had a two-pass automatic DesignPlan
emitter. It now coexists with our hand-template route as
`easyeda_emit_plan` plus `easyeda_emit_connections`, using the shared
layout and wiring rules. The first pass reports pending nets; the second
uses supplied real pin positions and blocks any net with a missing pin.
Offline tests passed; no live EasyEDA editor result is claimed.

The 119 cached fork/default/feature refs were scanned for async tool names.
Most apparent missing names were old aliases for existing tools. One
substantive difference was `rabihnd/integration`'s custom pad-list
footprint creation, which our standard-family and package-drawing
generators did not offer as a single call. Script `.85` ports that
capability with exact-library preflight, dry run, count precondition and
readback. On a disposable PcbLib copy, two pads and 13 tracks, one pin-1
arc and one designator text survived save/reopen. A shape constant in the
fork made an oval pad octagonal on AD 26.11; the adapted port uses the
measured round/elongated shape. The fork's vault-list, footprint
diagnostic, screenshot and STEP-body tools have existing equivalents in
`lib_list_available_libraries`, `lib_probe_footprint`,
`lib_render_footprint` and the exact-library body/model tools.

Script `.83` completes the saved STEP standoff read on a named clean
PcbLib even when another document is the active tab. The native footprint
read reports whether that exact library's unsaved state is known and whether
it is modified. Python only substitutes a matching saved model when the
target is known clean. Native `AD_FE38` readback returned 0.254 mm from
the saved STEP record. Unknown or dirty state stays unverified.

Script `.82` corrects a source-level omission in the adapted upstream
`pcb_pours_at` and `pcb_board_options`: `expect_file` had reached the bridge
but the native handlers ignored it. They now refuse a different board and
report the actual board path, which Python checks. Disposable-board native
reads and wrong-path refusals passed. A previously pending PcbLib read was
also accepted on a disposable 38-footprint library (`AD_FE38`: 493 tracks,
38 regions, 12 vias, one STEP body); wrong-path lookup was refused. The
saved STEP standoff resolver remains conditional on a known clean PcbLib.
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
| Upstream `ed4ef59` (library build) | Verify stored Altium checksums before extracting embedded 3D model bytes; compile an integrated library only with an explicit package path and fresh, complete SchLib/PcbLib content | Native LibPkg build and missing-footprint refusal on disposable sources; focused tests and Python compile pass |
| Upstream `5d79657` through `ce53d6e`, `ed4ef59` (footprint read) | Restore the native `library.get_footprint_primitives` handler, including body metadata, region shapes and layer names; restrict saved STEP extraction to a named footprint's live model files | 33 focused tests, Pascal lint/build, loaded `.3` runtime and no-target native dispatch; real PcbLib read still pending |
| Upstream `ce53d6e` (PCB pours/options) | Look up polygon outlines at a board point and read/set the new-polygon name template; include board identity and require an expected file for writes | 28 related tests, Pascal lint/build, loaded `.4` runtime, and no-target native refusals; real-board acceptance pending |
| `mooreaa` `ad8d5fa`, also in upstream by `ce53d6e` (font safety) | Guard generic `FontId` by actual schematic object type and expose `TextFontId` through typed sheet/harness entries | 22 related tests, Pascal lint/build, loaded `.5` runtime; native entry readback pending |
| `mooreaa` `dc36b7e`-`fc22136` (port cross-references) | Plan CrossRef positions from a port's read-only `ConnectedEnd` and wire geometry; require an exact sheet, a reviewed plan digest and per-reference readback for writes | AD26 disposable-sheet plan/apply persisted and read back after numeric-format fix; project-generated CrossRef was also moved and read back; 21 focused tests pass |
| `mooreaa` through `fc22136` (live pins) | Filter hidden part/display-mode copies from schematic ePin queries, preserving explicit `OwnerPart` inspection; use visible pins in CrossRef planning and its digest | 21 focused tests and Pascal lint/build; AD26 native two-mode/two-part sheet returned visible and explicit-owner counts 8/10/2 after save/reopen; CrossRef planner tested separately |
| `mooreaa` `64a71c3` through `fc22136` (part properties) | Read and write a placed part's display mode and current PCB model pin map, with type guards and readback | 22 related source tests, Pascal lint/build; both writes persisted after exact save/close/reopen on disposable AD26 sheets; visual mode-graphic comparison pending |
| `mooreaa` `053aff9` through `fc22136` (placement model choice) | Select a named PCB model the library symbol already carries on placement, verify all current flags and restore them on failure | Focused source tests and Pascal lint/build; AD26 placement accepted and persisted an available nondefault model, reported a missing model and kept the default; public tool accepts one or more placements |
| `mooreaa` `3d5817f` through `fc22136` (Footprint stamps) | Choose an existing model on Footprint parameter writes before fallback rename; refuse unloaded explicit batch sheets | 52 related tests, Pascal lint/build; AD26 two-model bulk stamp persisted after exact save/close/reopen; public tool accepts one or more stamps |
| `mooreaa` `dc36b7e`-`fc22136` (multipart placement and tidy) | Place an explicit sub-part, verify its sheet state and report issues; link the library, hide inherited model parameters and adopt the sheet designator font | 65 related tests, Pascal lint/build and loaded `.11` runtime; native multipart-sheet acceptance pending |
| `mooreaa` `dc36b7e`-`fc22136` (placement styling and Value) | Inherit or set fonts on new schematic objects, hold fixed port width, normalize text-frame line breaks, update existing Value parameters and hide new ones | 70 related tests, Pascal lint/build and loaded `.12` runtime; native disposable-sheet acceptance pending |
| `mooreaa` through `fc22136` (port AutoSize getter) | Return the native port AutoSize flag through generic queries, with a port-only type guard | Native `.12` query exposed the omission; loaded `.13` ePort query read back false, font 1 and width 400 on an isolated sheet |
| MOREmbedded through `032fb4b` (`pcb_check_fab_output`) | Rework fab comparison around one exact-board, uncapped native snapshot and require all three core comparisons | 23 focused tests, Pascal lint/build, loaded `.14`; disposable PCB facts and wrong-path refusal passed; full export comparison pending |
| Upstream `0a9ccd4`, `bb06837` (xSignals) | Read, create and delete xSignals on an exact PcbDoc; use count preconditions and verify native pair deltas | AD26 populated-board create/delete persisted; script `.137` also created and reused a Signal-kind class with indexed member readback across saves; 117 related tests and Pascal lint/build passed |
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
mismatch. The separate 8355-hole acceptance is recorded below.

## Next integration blocks

The October 28 live fork-tip check returned 61/62 fresh defaults and
116/117 fresh branches. The sole move was `mooreaa/main` from `4cbae2a`
to `a4be7fc` (three commits). Its new `pcb_adjust_designators` function
has been ported with a dry-run token, exact-board validation and native
top/bottom save/reopen acceptance on a disposable board; the optional
SVG designator labels are distinct and off by default. The two newly
reported layer-tab view-staleness issues are tracked in `TODO.md`.
After fetching that tip, the cache again matches all 62 default branches
and 117 branch heads.

| Source | Remaining block | Integration check |
| --- | --- | --- |
| Upstream `0a9ccd4`, `bb06837` | The named net, project-library, pin/pad property and shared-package source handlers are present; xSignal create/delete is now natively accepted, while less-used operations remain | Verify per-document targeting and property readback on disposable designs |
| Upstream `5797fc0`, `bff741b`, `ce53d6e` | Find a persistent Altium API for numeric differential-pair impedance rule fields, plus broader project STEP export; placed-component STEP export, editor preferences, pours-at-point, board options and per-net jumper display are now present | Keep numeric writes disabled until exact save/reopen proves they survive; port other families with source tests, script build and disposable-board native checks |
| MOREmbedded `84b682c`, upstream `5db72f2` | Two-body bulk layer, opacity and standoff edits are natively qualified; rotation refusal on a footprint containing unsupported polygon/dimension primitives remains | Preserve exact library/footprint identity, dry run and readback before a save |
| Upstream `ed4ef59` | Use body height/standoff in footprint previews; restored footprint reader and STEP model association are natively qualified below | STEP model Z offset is now resolved from a matching clean saved PcbLib; compare further body types |
| MOREmbedded `pcb_check_fab_output` | The native 8355-via snapshot, a fresh >5000-hole Gerber/Excellon comparison and an export-time integrity manifest are accepted | The large legacy package matches all three required checks, while an earlier GerberX2 production-review package retains a genuine outline mismatch. The manifest binds saved board and export bytes; unsigned external packages cannot establish who generated them. |

The >5000-hole comparison is now accepted on an isolated copy of
`FR1_Antenna_Array.PrjPcb`. Its OutJob had Gerber and NC Drill outputs
disabled; they were enabled only in the copy. Altium exported `Main.TXT`
(312 hits), `Main.TX1` (18) and `Main.TX2` (8025). The old parser silently
read only `Main.TXT`; the legacy OutJob reader now includes every numbered
drill-pair file. The fresh package and native board both have four copper
layers, a 406.4 x 124.46 mm outline and 8355 holes. Comparison ran all
three required checks and passed with no findings. The 26 focused fab tests
pass. `proj_run_outjob(seal_manifest=True, board_path=...)` now hashes the
saved board and OutJob before running a GeneratedFiles container, confirms
their bytes stayed unchanged, then seals every output file in
`eda-fab-manifest.json`. `pcb_check_fab_output(require_manifest=True)`
verifies the board and all package hashes before geometry checks. On the
same isolated project, a repeat native export wrote 25 files and sealed 27
files in the output directory; the exact-board checker passed all three
geometry checks with a verified manifest. The focused export, comparison
and manifest tests pass. The manifest is an unsigned integrity record: it
does not prove an external party's identity or rule out editor changes that
Altium did not mark modified before export.
| `mooreaa` `dc36b7e` through `fc22136` | DbLib relink and persistent alternatives for two port display fields remain; SchLib and IntLib relink, multipart placement, pin properties, parameter properties and port AutoSize are natively checked | Use final corrected handlers; verify remaining exact-sheet targeting, native readback and disposable-sheet safety |

The previous audit has the other fork branches and older upstream work. This
table tracks next implementation batches, not a claim that the listed source
commits are absent in full: some of their smaller changes are already here.

The source audit found one cross-board flaw in that upstream block:
`pcb_net_display(from_project=True, nets=None)` read its net names via
unscoped `pcb.get_nets` before addressing an exact PcbDoc. With two boards
open it could take the current board's names for the requested one. Source
`.109` adds an optional exact board path to the inventory handler, returns
the resolved path, and refuses a mismatched inventory before any display
write. Eight focused tests and Pascal lint/build pass; native two-board
acceptance is recorded above.

Reviewing the older upstream xSignal checks exposed a conflicting delete
selector: `pcb_delete_xsignals(names=[...], all=true)` passed through to
Pascal, whose `all` branch deleted every xSignal. Source `.110` refuses
the combination before the bridge and again in the native handler. The
related focused tests pass (17) and Pascal lint/build has no findings;
native disposable-board acceptance is pending. The source-side `doctor`
check saw loaded `.96`, while `.110` is now bundled, in a shared Altium
session listing 181 open documents.

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
The repository's EasyEDA extension build already covers the fork's builder
through the `eda-agent easyeda-extension` command; the fuller distribution
check is recorded above. A
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

The `rabihnd/integration` STEP-body creation is now adapted as
`lib_add_3d_body` on script `.87`. It requires an exact saved PcbLib,
footprint, existing STEP and old body count, and plans by default. Its
native path selects the named footprint before creating the body; native
testing found that creation on an inactive footprint otherwise looked
correct in memory but shifted by -50,000 mil after save/reopen. On a
disposable PcbLib copy, adding `LTC3895EFE.STEP` to the SOIC footprint
preserved the older SOIC body, Mechanical13 layer, (1, -1) mm centre,
90-degree Z rotation and 10-mil model Z offset after exact save/reopen.
No owner design was written.

The MOREmbedded multi-body STEP edit candidate is qualified on script
`.88`. The earlier Python guard compared a saved basename with a field
missing from `library.set_3d_body`'s snapshot; the native guard compared
that basename with the live model's full path and could change the layer
while skipping the Z offset. Python now obtains the exact footprint's live
body models, and Pascal checks saved/live model identity before any write.
On a disposable two-body footprint, only body 2 moved from Mechanical13
to Mechanical15 and its saved Z offset from 10 to 19.685 mil; the first
body and 90-degree rotation survived save/reopen. A wrong saved model name
was refused with neither body's layer changed. Other body types and
multi-body bulk edits remain unqualified.

A 2026-10-27 tool-name scan of 110 cached `forks/*` branch refs found 15
names absent from `main`. They are naming/surface candidates, not 15
missing features. The following existing tools provide the corresponding
operations, subject to the behaviour-level review still in progress:

| Fork name(s) | Current `main` operation |
| --- | --- |
| `lib_add_pin`, `lib_add_symbol_line` | `lib_add_pins`, `lib_add_symbol_lines` with one item |
| `pcb_move_component`, `pcb_place_track`, `pcb_place_component` | `pcb_move_components`, `pcb_place_tracks`, `pcb_place_components` with one item |
| `sch_attach_spice_model`, `sch_attach_spice_primitive`, `sch_attach_spice_primitives`, `sch_get_simulation_readiness` | `sim_attach_model`, `sim_attach_primitives` with one item or batch, `sim_get_readiness` |
| `lib_set_label_format` | `lib_set_label_formats` with one operation |
| `sch_add_net_label` | `sch_place_net_label` |
| `sch_add_text` | `sch_add_text` now places a native `eLabel` on an exact SchDoc; notes and text frames remain separate object types |
| `lib_diag_footprint`, `lib_screenshot_footprint` | `lib_get_footprint_primitives`/`lib_probe_footprint`, `app_screenshot` |
| `lib_list_vault_libraries` | `lib_list_available_libraries` plus `lib_get_vault_name`; the fork's `is_vault` inference from `AvailableLibraryType` was not carried because that ordinal is a library type, not a reliable Workspace source |

The pending table formerly listed upstream `184301d` as a separate source
candidate. It is already an ancestor of `main`; its `SchExtraOwner` and
`SchExtraFits` test dependencies are present. The focused test file passed
9 cases with 1 optional Free Pascal case skipped. Six source/qualification
groups remain in that table, not a count of individual missing features.

Script `.89` restored the pin-property helpers lost in an earlier merge.
The retained `generic.query_objects` call sites raised Altium's modal
`Undeclared identifier: IsSchPinProp` when a schematic object was read.
After rebuilding and reloading the main script, two parts of the three-part
`EDA_AGENT_QA_TRIPLE` were placed on the disposable
`eda-agent-create-object-20261027.SchDoc`. An exact-path query returned
`CurrentPartID` 1 and 2, `PartCount` 3, the same `U_QA1` designator, and
the requested 1000/2000-mil positions. Both parts survived exact save,
close and reopen. On the disposable SchLib, pin `CMP-001-2897-1:1`
returned its typed text properties; setting `ShowName=true` survived exact
save, close and reopen. The multipart QA symbol itself has no pins, so pin
properties were checked on that separate symbol. Pascal lint/build passed
12 files with zero errors/warnings; the focused suite passed 17 cases with
one optional case skipped. Remaining `mooreaa` relink and parameter paths
still need native acceptance.

The same loaded `.89` runtime also qualified the existing SchLib relink
path on the disposable two-part sheet. The exact sheet and SchLib paths
matched both `U_QA1` sections. Changing their links to the existing
`EDA_AGENT_QA_DUAL` returned `matched=2`, `changed=2`, `failed=0`;
`LibReference` and `DesignItemId` survived exact save/close/reopen on both
parts. Restoring `EDA_AGENT_QA_TRIPLE` survived a second save/reopen. A
wrong sheet path returned `SHEET_NOT_OPEN`, and a missing symbol returned
`LIB_REF_NOT_FOUND`; readback after the latter still showed both original
links. This checks link metadata only: the drawn symbol intentionally
remained three-part throughout. DbLib/IntLib relinks and model/parameter
updates still need their own native cases. A fresh upstream fetch still
gives merge base `40814badc695813157fd8c50d24feafc5a553fcd` and zero
unmerged upstream commits.
The live `fork-status --verify-fork-branches` rerun also found all 62
default fork tips and all 117 branch tips still equal to their local refs.

The first later `application.get_unit_stamps` request exposed two more
merge-loss faults: `UnitStamp_Utils` and `UnitStamp_PCBGeneric` were called
but not defined, and `install-scripts` called a missing
`_stamp_deployed_unit`. These are restored on script `.90`. A fresh Altium
26.11.1.5 session returned all ten unit stamps, `dev` for this source
checkout, without a modal. The bridge's session document pin had also
been dropped from the sync response path and async request/response path;
both paths now carry and update it. The focused 32-test suite passes,
including a new async document-continuity check; Pascal lint/build found
zero errors/warnings across 12 units.

The later branch-level audit checked these independent fork commits against
the current `main` source. Their implementation is already present, so no
second copy of the feature was merged:

| Fork branch / commit | Evidence in current `main` |
| --- | --- |
| `vincent-himpe/feature/primitive-net-write` (`8399eea`) | `PCBGeneric.pas` has `PCBSetNet` and accepts `Net`/`Net.Name` on copper primitives, updating net membership both ways. |
| `vincent-himpe/feature/add-footprint-fills` (`bf31274`) | `lib_add_footprint_fills` is registered in `tools/library.py` and handled by the library script. |
| `vincent-himpe/feature/keepout-restrictions` (`65e19b9`) | `PCBGeneric.pas` reads and writes the five `IsKeepoutFor*` restrictions on track, arc, fill, and region. |
| `vincent-himpe/feature/region-name` (`c3adf7f`) | `pcb_place_region` accepts a name; `PCBGeneric.pas` reads and writes a region's `Name`. |
| `yanivbi1/lib-set-3d-body` (`a54fa8c`) | `lib_set_3d_body` is registered in `tools/library.py`; its saved-model identity and native qualifications are described above. |
| `malteheringorgatex/wsl-process-detection` (`d57df64`) | `bridge/process_manager.py` enumerates Windows processes from WSL via `tasklist.exe`, with an explicit unavailable-interop state. |

This is a source-level equivalence check, not native acceptance of the
currently bundled script `.106`. The live Altium session is still running
`.96`; restarting it while other projects are open remains pending.

The `james-martinez/add-windows-binary-workflow-15064193229940641520`
branch (`1ccf16c`) had a distinct distribution feature: a Windows exe
artifact. Its GitHub Actions job is adapted in `build-windows-binary.yml`:
build and install the release wheel first, bundle that package's data and
modules with PyInstaller, then run the exe and make it copy its embedded
DelphiScript project to a disposable directory. A local Windows build passed:
the exe reported version 0.7.1 and copied 15 script files including
`Altium_API.PrjScr`, `Main.pas` at `.106`, and `StatusForm.dfm`. The GitHub
Actions run on this branch remains to be observed after push.

The `yniantongtian-oss/main` maintenance commit `e7fd6f1` adds a separate
useful repository capability: weekly Dependabot proposals for the root
Python manifest and GitHub Actions. Its two entries are carried in
`.github/dependabot.yml`, with five open version-update PRs per ecosystem.
This configuration does not approve or merge dependency changes. The file's
keys and `directory: /` for workflows were checked against GitHub's current
Dependabot configuration documentation.

Further branch-level source comparisons found these already integrated
behaviours; their divergent commit IDs alone do not signal missing features:

| Fork commit | Current source evidence |
| --- | --- |
| `bblacklock3/oxos/pinned` `c666912` | `PCBGeneric.pas` reads and writes arc `LineWidth` for the generic `Width` property, retaining fractional mils. |
| `terrencehenry/fix/altium-property-access-crashes` `89c017f` | `Generic.pas` preflights unsupported schematic property/type pairs before creation or modification and reports unreadable properties. |
| `darshp848/altium-bridge-sch-repair-tools` `63b0fef` | `kicad_local.py` searches per-user KiCad under `LOCALAPPDATA` and orders version directories numerically across install roots. |
| `viknandala-eng/main` `d4a259b` | `lib_resolve_workspace_component` and `sch_place_workspace_components` are registered, with matching native handlers. |
| `prototrace/runo/read-only-unicode-polyline` `961e6c3` | `Generic.pas` recognises `ePolyline`; `Utils.pas` escapes full Unicode code units. |
| `pieterpotgieter/fix/ad23-paste-flag` `3e7369b` | `Library.pas` gates the top-paste flag by Altium major version. |

The `lda-audiotech` UTF-8 response/pointer-file change (`22bb2df`) is not
copied verbatim: `altium_bridge.py` now accepts UTF-8 with a BOM and falls
back to the system ANSI codepage for older DelphiScript replies, while
`diag/health.py` reads the pointer in the same encoding used to write it.

Fresh `git fetch upstream main` advanced the tip to
`c45ca0a537ad5afe0cda4ce1951e6bfb6be4ff3d` (issue #142, suppress
unwanted console windows for child programs). Two-parent merge `bb3c404`
records the new sync point. Its new source test exposed four fork-only
subprocess starts; `fork_status.py`, `diag/update.py` and `pcb_toolkit.py`
now pass `no_window()`. The focused suite passed 27 tests, and
`git rev-list --count main..upstream/main` returned 0 after merge.

The child fork's private `_live_footprint` helper is the sole async
function name in `morembedded/main`'s tool modules absent from current
`main` (998 fork names compared with 1104 in `main`). Our render and audit
tools already perform the same reads but had omitted its explicit PcbLib
path on the mechanical-layer call. Both now pass the path returned by the
pad/primitive read. Forty-three related tests pass; the name comparison is
only a surface check, and native multi-library acceptance is still needed.

The MOREmbedded bottom-side placement fix (`be21eb3`) and rotation audit
(`2cabd7b`) are present in `main`; its `pcb_modify_layer` already accepts
fractional thickness. Inspecting the shared placement path found a separate
precision loss in our newer batch wrapper: Python cast X/Y to `int`, and
`PCB_PlaceComponents` assigned parsed floats into integer locals. Script
`.107` keeps the values as decimal mils through `MilsToCoordF`. Nineteen
focused tests and Pascal lint/build pass; native placement is pending.

A neighboring schematic placement audit found three more fractional-mil
losses. `sch_place_wires` and `sch_place_dblib_component` cast caller
coordinates to integers before the native handlers; `Gen_PlaceTextFrame`
stored parsed floats and its corner-swap temporary in integers. Source
`.108` preserves decimal mils to `MilsToCoordF`. Forty-three focused tests
pass; native save/reopen checks remain pending.

## Refreshed fork-tip and branch audit after source `.108`

After fetching `upstream`, `morembedded` and `origin`, `main` and
`origin/main` both point to `f6a6d5d497612b050ad8df9bfb856ab62245033e`.
`upstream/main` is still `c45ca0a537ad5afe0cda4ce1951e6bfb6be4ff3d`:
it is the exact merge base and `main..upstream/main` contains zero commits.
`morembedded/main` remains `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.

The live GitHub fork inventory and `git ls-remote` check now match 62/62
default branch tips and 117/117 branch tips in cached refs. The recently
updated `RHSvekon/main` still points to `9ee593e`, already in upstream
history. This freshness check proves which remote commits were inspected;
it does not prove every fork behavior is natively accepted.

Rechecked the individually named `vincent-himpe` fixes for PCB zoom, via
mask following, keepout restrictions, region arcs, primitive net writes,
polygon pour settings and decimal-mil handling. Their current source and
focused tests are present in `main`; 72 related tests pass. The donor's
`2c0a56d` decimal conversion lines are present in the current Pascal and
Python sources apart from two response-building lines whose structure has
since changed. This is a source comparison, with native acceptance still
tracked separately.
