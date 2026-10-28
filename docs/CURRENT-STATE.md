# Current integration state / agent handoff

## Layer visibility truthfulness, 2026-10-28

Script `.139` and the Python tools now accept an optional exact `board_path`
for reading and setting layer display. Readback preserves `visible` for
compatibility and adds `visibility_setting` and `in_physical_stack`. A true
visibility setting on an unused copper layer does not create a view tab.
The setter refuses copper layers absent from the board stack with
`LAYER_NOT_IN_STACK`. On a disposable four-layer PcbDoc, MidLayer2 read
`visibility_setting=true`, `in_physical_stack=false`, and the setter
rejected it. The board was closed without saving. Build linted 12 Pascal
files with zero findings; 30 focused Python tests passed. Altium and MCP
were restarted; ping matched `.139`.

## `mooreaa` designator fitting, 2026-10-28

Fetched new fork tip `a4be7fc` (previously `4cbae2a`): it adds
`pcb_adjust_designators` and records two layer-tab view-staleness cases.
The designator planner, exact-board native handler and optional SVG overlay
labels are now in `main` source, script `.138`. Apply requires a fresh dry-run
plan token; native code refuses missing board paths, invalid layers and
duplicate designator items before editing. Pascal build linted 12 files with
zero findings. The 16 planner/handler tests and six SVG tests pass.

Native acceptance used a disposable copy of the 96-component FR1 antenna
board. A dry run saw 46 top and 50 bottom parts. A stale token made no edit;
the exact two-part plan moved `W_RX_7` to Mechanical10 and `R34` to
Mechanical11. Apply reported `applied=2`, no property mismatches and one
expected off-centre warning because Altium centres on the entire part.
After exact save, close and reopen, both layer, size, stroke, rotation,
mirror, visibility and centre-autoposition values persisted. The copied
board was closed.

## MOREmbedded uncapped fab snapshot above 5000 holes, 2026-10-28

The native `pcb_get_fab_board_facts` path was run on
`Z:\pi-radio\rfsoc-fr1-beamformer\03_Altium_Antenna\Main.PcbDoc` with
script `.137`. It returned the exact board path, four copper layers,
406.3999873 by 124.46 mm outline, zero drilled pads, 8355 drilled
vias and `hole_count=8355`. The independent board statistics read
`via_count=8355`, so the snapshot passed the former 5000-hole concern
without truncation. The PcbDoc was closed without saving. No matching
Gerber/Excellon package was present in that source folder. An OutJob copy
subsequently produced a full package: all 8355 holes, four copper layers
and the outline matched, and its export-time hash manifest verified.

## MOREmbedded two-body bulk STEP edit, 2026-10-28

The existing `lib_set_3d_body` bulk path was checked on a disposable
4,140,032-byte PcbLib copy. `TEST PAD` had an extruded body on
Mechanical13 and a STEP body on Mechanical15. A dry run planned both
bodies; the native write moved both to Mechanical16 and set opacity to
0.65 (`changed=2`, no skips). Exact save, close and reopen retained both
layers and opacities. The saved STEP file and its 90-degree Z rotation
were unchanged.

A second bulk dry run and write set standoff to 0.1 mil. After exact
save/reopen, the extruded body's standoff was 0.1 mil and the STEP
model's saved Z offset was 0.1 mil, with the same 90-degree rotation.
Altium's live `ComponentBody.StandoffHeight` still returned its unrelated
negative value for STEP; the saved model record supplied the persistent
offset. The test copy closed. Dry-run rotation plans for all 41
footprints in this PcbLib had `not_turned=0`; no footprint here exercised
the unsupported polygon/dimension guard.

## Integrated-library completeness guard, 2026-10-28

`lib_build_integrated_library` was exercised on a disposable LibPkg
containing a SchLib and PcbLib extracted from a small IntLib. Altium
returned compile success and wrote a fresh 5,632-byte IntLib, but its
compound file contained only `SchLib/0.schlib`: the symbol's footprint
model still linked to an obsolete `C:\altium-converter\...` PcbLib path.
After the copied SchLib model was rebound by name to the supplied
footprint, a fresh 22,528-byte IntLib contained both `SchLib/0.schlib`
and `PCBLib/0.pcblib`.

The builder now inspects the compiled IntLib and requires each requested
SchLib/PcbLib kind to be present before reporting `built=true` or
installing it. Against two fresh Altium builds, the stale-link case
returned `artifact_written=true`, `built=false`, missing `pcblib`; the
relinked case returned `built=true` with both kinds. Five focused tests
pass. The scratch libraries were closed without unsaved changes.

## Schematic parameter and port extra properties, 2026-10-28

On an isolated copy of `Multipart_QA.PrjPcb`, a document parameter
`QA_PROP` and port `QA_PROP_PORT` were created on a copied SchDoc.
Native `obj_query` read `ReadOnlyState=0`,
`AllowLibrarySynchronize=true`, `AutoSize=false`, the empty
`OverrideDisplayString` and the port's initial `HarnessColor` with no
unknown or failed properties. `obj_modify` wrote
`ReadOnlyState=1`, `AllowLibrarySynchronize=false`, `AutoSize=true`,
`OverrideDisplayString=QA_ALIAS` and `HarnessColor=123456` with one
match for each object and immediate readback. `AutoSize` recalculated
the port width from 400 to 875.1763 mil.

After exact-sheet save, close and reopen, both parameter changes and
`AutoSize=true` with the new width persisted. `OverrideDisplayString`
had reverted to empty and `HarnessColor` to 15187117. The saved
SchDoc's port record contained `AutoSize=T` but neither of those two
fields. `obj_modify` now reports this AD 26.11 persistence limit when
either is written, while retaining the live setter for contexts where
it is useful. The scratch project was closed.

## IntLib relink persistence and DbLib uniqueness guard, 2026-10-28

The `mooreaa` `sch_relink_components` IntLib path was checked on an
isolated two-sheet project copy. A 21,504-byte IntLib was copied from
the corpus, and Altium's `Extract` dialog produced one SchLib and one
PcbLib in the scratch folder. The extracted SchLib named one symbol,
`ABM8G-14.31818MHZ-B4Y-T`. Relinking copied `RQA1` to that IntLib
passed the dry run, changed one part and read back `LibReference`,
`SourceLibraryName` and `DesignItemId` with no `not_applied` fields.
After exact-sheet save, project close and reopen, the same three fields
still pointed to the IntLib. The scratch project was closed.

The DbLib preflight previously accepted any `found=true` record, even
when `match_count>1` meant the key was duplicated or `scan_capped=true`
left uniqueness unknown. It now requires exactly one match and an
uncapped lookup before writing. The focused 15-test suite covers both
refusals. No DbLib file was found in the local `Z:` corpus for native
DbLib acceptance.

## Two-board project net-colour targeting, 2026-10-28

Native script `.137` was tested with a disposable SODIMM project and its
PcbDoc open beside a different DCDC board. The DCDC board held 74 nets;
the SODIMM board held 229. While DCDC was selected, the direct
`pcb_net_display(from_project=True, nets=None, dry_run=True)` call refused
the SODIMM path with `Selected PCB path differs from board_path`. After
`pcb_focus_board` selected the copied SODIMM PcbDoc, exact `pcb_get_nets`
returned 229 names. The dry-run returned 229 rows with precisely the same
name set and five project colours. No board was written; the copied
project was closed without saving. The tool descriptions now state the
focus requirement for multi-board sessions.

## Project-generated CrossRef native qualification, 2026-10-28

On a disposable two-sheet `Multipart_QA.PrjPcb` copy with
`AutoCrossReferences=1`, Altium 26.11.1.5/script `.137` generated a real
`CrossRef` for matching `QA_REAL_CROSSREF` ports after both sheets were
opened and the project compiled. On `Template_Value_QA.SchDoc`, its text
was `Template_Value_Param_QA[2B]`. With a wire from `(7800,4000)` to the
port at `(8000,4000)`, `ConnectedEnd=1` and Altium placed the reference
at `(8420,4000)`, justification 3. The test moved that generated
parameter to the wrong end `(7980,4000)`, justification 5, in memory.
`sch_fix_port_crossrefs` planned one move and applied it with exactly
one matching readback at `(8420,4000)`, justification 3, and no failures.

Saving and reopening the sheets did not leave a visible CrossRef until
both sheets were reopened and the project was compiled again. Compiling
with only the first sheet open returned success but no CrossRef. With
both sheets open, Altium generated the reference at the correct end and
the planner found no move. The missing-reference hint now describes this
loading condition. The QA project was closed after the check.

## Port CrossRef native apply and readback, 2026-10-28

The `mooreaa` CrossRef planner was exercised on a disposable project copy
under Altium 26.11.1.5, script `.137`. A horizontal 400-mil port at
`(8000,4000)` had a wire from `(7800,4000)` to its origin and a test
`CrossRef` parameter at `(7980,4000)`, justification 5. Altium's
`ConnectedEnd` read 1. The dry run planned the unwired-end position
`(8420,4000)`, justification 3, with no off-sheet warning. The reviewed
plan digest was accepted and the parameter was changed in Altium.

The first apply reply incorrectly said `failed=1`: its readback filter
used `Location.X=8420.0`, while Altium returned `8420`. The Python tool
now rereads named references and compares numeric X/Y within 0.01 mil,
requiring one matching row and the expected justification. After the
HTTP MCP restart, the same plan returned `applied=1`, `failed=0` and a
separate `obj_query` read X=8420, Y=4000, justification 3. Exact-sheet
save, project close and reopen left the plan with zero moves and one
`ok` reference. The source QA sheet remained SHA-256
`fa9931bba40abed643e1ae0093843419d106200473d32f2c0cc20b7d307e5661`.
The reference was a deliberately created test parameter; the separate
project-generated qualification above covers that case. Twenty-one
focused tests pass, including normalized coordinate readback.

## mooreaa live-pin filtering on two modes and parts, 2026-10-28

The corrected `mooreaa` ePin query filter now has native acceptance under
Altium 26.11.1.5, script `.137`. On a disposable copy of
`Multipart_QA.PrjPcb`, `RQA2` uses an empty display mode 1 while `RQA1`,
`RQA3` and `RQA4` use mode 0. The normal ePin query returned their six
visible pins and none at `RQA2`'s X=5000 mil. Adding the explicit filter
`OwnerPartId=1` returned eight, including the two mode-0 copies at
X=5000 mil.

The copied `RES` SchLib symbol was then expanded to two parts and gained
pins 3 and 4 with `OwnerPartId=2`. `sch_place_components` placed `RQA5`
at X=10000 mil as `CurrentPartID=2`, `PartCount=2`, with no part issues.
The normal ePin query returned eight pins total, including only 3 and 4
from `RQA5`. An explicit `OwnerPartId=1` query returned ten, including
the hidden part-1 pins 1 and 2 from `RQA5`; `OwnerPartId=2` returned only
its two visible pins. Exact save, project close and reopen reproduced
counts 8/10/2. The copy and SchLib were closed. The source QA SchLib and
sheet hashes remained `01cabf700eacff508214983414e06edf80e58a95ae735c0a36d6f2ace258d848`
and `80becf723a68fb78053c99160a81240d1039ed7985d4af21ce8ec9b4fa76ae19`.

## xSignal class membership and HTTP restart, 2026-10-28

Script `.137` repairs the upstream xSignal class path. On a populated
disposable CW308 board, the former handler reported `class_assigned=true`
after `AssignPinPairClass`, but no named class existed on the board. The
first repair created a Signal-kind board class, which persisted, yet the
string overload of `IsMember` returned false even when `MemberName[0]`
was `NetR15_1_PP1`. The final handler creates or reuses the class, checks
its indexed `MemberName` entries before adding the pair's primitive, and
returns `class_membership_verified` only after that readback. Python now
requires this field when `class_name` was requested; an unverified write
is returned as `ok=false` with the native partial state.

On a new clean copy, `R16.2` to `R15.1` created
`NetR15_1_PP1` in `QA_XSIG_MEMBER` with `class_created=true` and
`class_membership_verified=true`. Exact save/close/reopen retained the
pair and class. A second pair, `J3.4` to `J3.6`, entered the same class
with `class_created=false` and verified membership; after another exact
save/close/reopen the board had both xSignals and the class. Creating a
pair with no class still succeeded. The owner board SHA-256 remained
`c4e1c9ab5b3a48931e2b57e1229ee9b652438579e2656d51c645c467f428cf85`.

`app_restart_mcp_server` also now preserves the current Python entrypoint.
Its old hard-coded `python -m eda_agent` restart dropped the HTTP 14701
listener because this installation runs `serve-altium-http.py`; the
existing supervisor recovered the listener. The updated tool reported
the HTTP script command, restarted it, and `app_ping` then returned
loaded/bundled `.137` with port 14701 listening. TCP 14700 stayed up.
Pascal lint/build passed with zero errors and warnings; 117 related
Python tests passed.

## Workspace exact-result search, 2026-10-28

Script `.131` repairs the `cad435` Workspace component resolver. Altium's
`SearchItemRevisions` is a fuzzy search: the old handler used only
`GetFirstItemRevision`, so a valid exact Component Item later in the
result list was wrongly rejected. The handler now reads the returned
`IInterfaceList`, scans up to 100 candidate revisions for the requested
name, resolves the latest revision, and refuses distinct exact-name
items as ambiguous. A full 100-result page is reported as truncated
instead of silently claiming uniqueness. The installed SDK reflection
confirms `IULB_ItemRevisionsResult.GetItemRevisions`,
`IInterfaceList.GetCount/Get`, and `IULB_ItemRevision.GetComment`.
The 12-file Pascal lint/build passed with no errors or warnings, and
eight Workspace tool tests passed. Altium reloaded `.131` from the main
script project; `app_ping` reports a matching bundled version and zero
cast errors. The current Altium session has no Workspace server manager;
the live call returned that existing explicit error and the polling loop
remained responsive. Exact-match behavior
still needs a connected Workspace for native acceptance.

## Populated-board xSignal create/delete acceptance, 2026-10-28

On a disposable copy of the CW308 baseboard PcbDoc under Altium
26.11.1.5, script `.130`, `pcb_get_xsignals` initially returned zero.
`pcb_create_xsignals` with `expected_count=0` and pins `R16.2`,
`R15.1` created `NetR15_1_PP1`: two nodes, one track, 69.0071 mil
length, and no unrouted span. The pair survived exact-board save,
close and reopen. `pcb_delete_xsignals` then deleted that exact name
with `expected_count=1`; a second exact save/close/reopen returned zero
pairs. This confirms both writes on a populated board, their count
preconditions and persistence. The owner PcbDoc SHA-256 remained
`c4e1c9ab5b3a48931e2b57e1229ee9b652438579e2656d51c645c467f428cf85`.

## cad435 PCB pad-designator native acceptance, 2026-10-28

The `cad435/c7d55bb` pad-name feature was compared with current source
and tested on a disposable copy of `CW308_PCB.PcbDoc` under Altium
26.11.1.5, script `.130`. `obj_query` found exactly one pad with
`Name=M1|X=1600|Y=4700`. `obj_modify` changed `Name` to `QA_PAD1` and
`obj_batch_modify` then changed its `Designator` to `QA_PAD2` with the
same three-condition filter. The final active-board query read both
`Name=QA_PAD2` and `Designator=QA_PAD2` after exact save, close and
reopen. This verifies the generic single and batch PCB routes and their
multi-condition filters. PCB objects must be queried with `active_doc`
scope; `doc:<PcbDoc>` is explicitly refused. The owner PcbDoc remained
SHA-256 `c4e1c9ab5b3a48931e2b57e1229ee9b652438579e2656d51c645c467f428cf85`.

## Deselect All menu native readback, 2026-10-28

The `mooreaa` corrected schematic deselection alias was checked in
Altium 26.11.1.5, script `.130`, on a disposable four-component SchDoc.
`obj_select(eSchComponent, Designator=RQA3)` reported one selected;
`obj_query` read its schematic `Selection=true`. Calling
`app_run_menu("Edit|Deselect All")` dispatched `Sch:DeSelect` with
`Action=All`, and a second `obj_query` read `Selection=false`. The
temporary project was closed without saving. Schematic selection uses
the `Selection` property; `Selected` is the PCB property. The generic
menu dispatcher still returns `outcome_verified=false`, so the separate
property readback is the evidence that this specific action worked.

## Placed footprint-stamp native persistence, 2026-10-28

The `mooreaa` placed-component `Footprint` stamp passed native acceptance
on the same disposable four-part QA sheet under AD26.11.1.5, script
`.130`. `sch_set_components_parameters` switched `RQA3` from
`CC1608-0603` back to `CR2012-0805` and `RQA4` from `CR2012-0805` to
`CC1608-0603` in one call. It reported `updated=2`, `failed=0`,
`footprints_applied=2` and an empty `footprints_not_applied` value.
`obj_query` read both selected `FootprintModel` names immediately and
again after exact-sheet save, project close, and reopen. The copy was
closed without another save. The public MCP registry exposes only the
bulk parameter-stamp tool; a list of one stamp covers a single part.

## Placement footprint-model native persistence, 2026-10-28

The `mooreaa` placement model chooser was accepted on a disposable copy of
`Multipart_QA.PrjPcb` in Altium 26.11.1.5 with script `.130`. The `RES`
library symbol carries eight PCB models and defaults to `CR2012-0805`.
`sch_place_components` placed `RQA3` with requested `CC1608-0603` and
`RQA4` with nonexistent `QA_NO_MODEL`. It reported `placed=2`,
`failed=0`, `footprints_chosen=1`, and a `FOOTPRINT_NOT_ON_SYMBOL` issue
for `RQA4` with the unchanged default. `obj_query` read `RQA3` as
`CC1608-0603` and `RQA4` as `CR2012-0805`. After exact-sheet save,
project close without another save, and reopen, both readings persisted.
The disposable copy was then closed without saving again. This qualifies
the existing-library-model choice and missing-model reporting for bulk
placement on AD26. The public MCP registry exposes one placement tool,
`sch_place_components`, which accepts lists of one or more parts.

## Placed-part display-mode native persistence, 2026-10-28

The remaining `mooreaa` `DisplayMode` write was accepted on a disposable
copy of `Multipart_QA.PrjPcb`. A copy of its `RES` SchLib symbol gained an
empty second display mode and was saved; placing a new `RQA2` on the copy
of `Template_Value_QA.SchDoc` read back `DisplayModeCount=2` and
`DisplayMode=0`. `obj_modify` changed it to 1 with no failed properties.
Exact-sheet save observed a disk write, and after project close without
another save and reopen, `obj_query` returned `DisplayMode=1`, count 2.
The original QA sheet retained SHA-256
`2d67b03d144a515e9b69dfed309a9eda0f95e5bd57c772a44b3b3d510b2ce3b9`.
The temporary project and SchLib were closed. This checks the mode index
and persistence; the second mode was intentionally empty, so no rendered
graphic difference is claimed.

## Placed-part pin-map native persistence, 2026-10-28

The `mooreaa` placed-component `FootprintPinMap` port was exercised on
`RQA1` in a disposable copy of `Multipart_QA.PrjPcb` under Altium
26.11.1.5, script `.130`. Its old map `(2:2),(1:1)` changed to
`(2:1),(1:2)`, read back immediately, and persisted after exact-sheet
`app_save_document`, project close without another save, project reopen,
and sheet reopen. The source QA sheet stayed at SHA-256
`25e7c99c611c4ab62a0c3de6c393b8a89c25356b35ef1c255725f679ddc6545b`.
The same component has one display mode. Writing `DisplayMode=1` returned
`success=false`, identified `DisplayMode` as failed and left mode 0 and
the old pin map intact. A successful switch between two available modes
still needs a separate native case.

## Polygon point and board-options native reads, 2026-10-28

The earlier upstream `pcb_pours_at` and `pcb_board_options` ports now have
read-only native acceptance on `CW308_PCB.PcbDoc` under Altium 26.11.1.5,
script `.130`. The board had seven polygons. The saved outline of
`1V2_HEATSINK` includes `(6500,4000)` mil; `pcb_pours_at` at that point
examined seven and found that pour plus `GNDBOT` and `GNDTOP`. At `(0,0)`
it found none. An incorrect expected board path was refused. The board
options read returned `polygon_name_template=0` and
`automatic_split_planes=true`; its wrong-path read was also refused.
The original PcbDoc was closed without saving, with `discarded=false`.
On a standalone temporary copy of the same board,
`polygon_name_template` changed from 0 to 1, read back immediately,
and survived `app_save_document` (which observed a disk write), close,
and reopen. The original board SHA-256 remained
`c4e1c9ab5b3a48931e2b57e1229ee9b652438579e2656d51c645c467f428cf85`.
The copy was closed after the persisted readback. This qualifies the
exact-board write on AD26.11.1.5; it does not assign meaning to the
numeric template choices beyond Altium's stored value.

## Fresh DRC active versus waived totals, 2026-10-28

`pcb_run_drc` now reads the summary header from its confirmed, per-request
batch HTML report and returns `report_counts` separately from the board's
stored `violation_count`. It also returns `violations_returned` and
`violations_truncated`, because the native inline array stops after 100
entries; `pcb_get_clearance_violations` pages through all stored types.
The parser was checked against two live Altium 26.11 reports: MB2222 has
zero active and one waived Room violation, while Nordic 400432 has zero
active and no waived header. Five focused tests passed. The Python MCP
server must be restarted after this source change; no new native DRC was
run for the wrapper itself.

## Populated-board stack builder acceptance, 2026-10-28

Partial-failure recovery was also exercised on the same temporary,
project-backed board. A plan demanding two dielectrics in a gap that
Altium provided only one failed after eight native copper edits. The
tool returned `ok=false`, `partial_unsaved=true`, `applied=8` and the
specific insufficient-dielectric error. `proj_close(save=false)` left
the saved PcbDoc hash unchanged; reopening restored the saved stack.
This proves the deterministic planner-failure path. The Python wrapper
also now treats an unacknowledged native edit or failed post-edit
readback as an uncertain in-memory state: it returns
`native_state_unknown=true` and `partial_unsaved=true` even if the first
edit reply was lost. The failure-path test passed; no real transport
loss was induced in Altium.

The refreshed fork check matched 62/62 default tips and 117/117 branch
tips; `upstream/main` is still the exact ancestor `ee7589c9` with zero
pending commits. On a temporary copy of the CW308 baseboard project,
`pcb_build_stack` refused a two-layer plan that would remove occupied
`Ground Plane` and `Internal Signal 3`, both as a dry run and when apply
was requested. The copied PcbDoc hash remained unchanged. A plan that
kept all four occupied copper layers applied 14 native edits with zero
readback mismatches. Exact save/close/reopen retained the three planned
FR-4 dielectric layers (core 12.6 mil, prepreg 5 mil, core 10 mil) and
copper order. Offline `pcb_stack_from_file` found no V9/legacy issues
and no mismatches against the plan. The copied project was closed.
An ambiguous transport failure now carries an explicit state warning.

## Sheet-symbol and sheet-entry geometry, 2026-10-28

Script `.129` repairs the `mooreaa` sheet-entry placement issue. A
sheet symbol's positive YSize grows down from its Location, so its
requested bottom/top corners now anchor at the top-left. After Altium's
`AddAndPositionSchObject`, the handler writes each entry's Location
from the actual symbol geometry and tests both coordinates as well as
side/distance before claiming `positioned_as_asked`. On a disposable
two-sheet project, immediate and saved/reopened positions agreed for
left `(6000,2900)`, right `(7000,2800)`, top `(6300,3000)` and bottom
`(6400,2000)` mil. Before the fix, immediate positions lay outside the
symbol and changed only after reopen. The temporary project was closed.

## Exact-board rule queries, 2026-10-28

Script `.128` fixes `pcb_find_dominant_rule` and `pcb_check_rule_scope`.
The Pascal handlers now reject a mismatched `board_path` and return the
verified path with their Altium rule results, so the Python MCP wrapper
accepts valid answers. Build lint: 12 units, zero errors or warnings.
After reopening `Dispatcher.pas` and starting it with F9, native MCP
returned the 7 mil Clearance rule for MH6.MOUNT on `CW308_PCB.PcbDoc`,
reported true scope flags, and rejected a different board path. The
board was closed without saving. Source SHA-256: `Main.pas`
`8880d8cfcb08fe889637ed2d57c12c7c21929b8aceeca1f51aa84ed56d469673`,
`PCB.pas` `3a86710cfc86f15c1fe8c3f3c3afbcbd577284cd4106fd1a58acbeef831cc09d`,
generated `Altium_MCP.pas`
`cb12dc84b81750ec18c4e85f7cb75838002864e8aa3a44be053886a62049b68f`.

## Silent per-variant schematic PDFs, 2026-10-28

`proj_print_all_variants` no longer sends direct `project.export_pdf` for
each variant. It stages the saved project and schematics separately per
variant, configures the OutJob's variant choice and physical-document
source, publishes silently, verifies the PDF and moves it to the requested
folder. The original project variant is read back but never switched.
Native QA on a disposable two-sheet project produced `AllFitted.pdf` and
`NoJ10.pdf`, both two pages, without a modal. Rendered page 1 matched
exactly; page 2 changed 12,000 pixels and red pixels increased from 1855
to 2810 for the not-fitted variant. The source project was closed without
saving. Variant lookup now uses the persisted Description when AD26
reopens variants with the generic `DM_Name="Variant"`; script `.127` and
HTTP MCP match. Pascal lint had zero findings; 136 focused tests passed.
The deployed script source hashes (SHA-256) are `Main.pas`
`8b6fabf4f10cab6aee01ae42eb2bab7bccd555f4549b2d67e0d348e7eb9146ce`
and generated `Altium_MCP.pas`
`59aed1ccec00e319e90cf4ca4e3ae305533770bd022e1ca8dc4e36c06cb9800a`.

Altium's [OutJob documentation](https://www.altium.com/documentation/altium-designer/preparing-for-manufacture/output-jobs)
confirms that variant choice belongs to the OutJob. The separate
`proj_set_active_variant` process still failed native readback on AD26;
this PDF workflow does not depend on it.

## Project-scoped save and PIC24 read-only parity, 2026-10-28

Script `.126` restricts `proj_save` and `proj_close(save=true)` to modified
project members or documents marked edited by the script. On a disposable
two-sheet project, a clean save left both file hashes unchanged; editing A
then saving changed only A, and a second edit followed by `proj_close`
again changed only A. Pascal lint passed (12 files, zero findings), the
project closed, and `app_ping` confirmed `.126` after F9 restart.
The HTTP MCP service was restarted on 14701; TCP 14700 remained listening.
`eda-agent doctor` passed 8 checks with zero critical failures. The focused
save/close test suite passed 34 cases.

The PIC24 curiosity board's native batch DRC had `UnRoutedNet` enabled
(All/All) and reported 63 total violations, zero Un-Routed Net rows.
J105-6/7/8/9 are MultiLayer/SHIELD, J212-6/7/8/9 are
MultiLayer/SHIELD2, and all eight carry `JumperID=123`. Neither net has
connection lines or separate track/via/arc/fill/region objects. The T1
project's compiled J10-A41 row has `net="?"`, and Altium lists it among
the 84 unconnected pins. Both source projects were closed without saving.

## Explicit direct-print opt-in, 2026-10-28

The remaining `mooreaa` print-dialog correction is adapted into both
legacy PDF entry points. By default `proj_export_pdf` and
`proj_export_image(format="pdf")` return `PREVIEW_NOT_SILENT` without
touching Altium. `open_print_dialog=True` permits the native path,
refuses an existing output file, and validates a claimed PDF by its
`%PDF-` header. Both tools are catalogued as potentially modal.

After restarting only HTTP MCP, a disposable SchDoc test confirmed the
default refusal and that the explicit `proj_export_pdf` call opened
Altium's Preview SCH dialog. The bridge correctly reported a modal
instead of pretending that a PDF was written. `app_send_keys(escape)`
closed the dialog, `app_ping` resumed at `.125`, no PDF existed, and the
copy closed without a save. The `proj_export_image` PDF path was not
opened separately in native QA. Export/metadata tests: 87 pass.

## Native Description persistence and capture QA, 2026-10-28

The prior PIC24 batch DRC stalled Altium's UI and bridge. After its run
ceased to respond, Altium was restarted; the bridge and HTTP MCP resumed.
The script was later detached with no loaded or modified documents and
Altium restarted again to load source `.125`. `eda-agent doctor` reported
the native script responding at `.125`, a version match, and no critical
failures. Ports 14701 (HTTP MCP) and 14700 (TCP relay) listen.

On an isolated copy of `Docking_Connection.SchDoc`, bulk stamping J10's
`Description` wrote `ComponentDescription` to the saved SchDoc, but
`obj_query` returned empty because `GetSchProperty` had no component
description read case. Script `.125` adds `Description` and
`ComponentDescription` getters for components and wraps the bulk write
in a component undo change. Native `obj_query` read the new value both
immediately and after save/close/reopen. The independent saved-file
parser agreed. The original schematic was not saved.

`app_screenshot` completed on responsive Altium and wrote a 1936x1048
PNG of the native main-window frame. The corresponding visible content
capture was 1920x1032; this is consistent with the 16-pixel frame and
confirms the exported PNG was not the former 2x OCR image.

The focused UI test suite also exposed a missing `_KEYS_HELP` constant:
invalid keystrokes would raise `NameError` while formatting a refusal.
The fork's concise supported-key guidance is restored; 120 related
tests now pass.

## Additional `mooreaa` stack and description fixes, 2026-10-28

The legacy `pcb_apply_stackup_template(dry_run=False)` path now requires
explicit `legacy_stack_write=True`, like the other V7 stack writers; its
successful reply directs the caller to inspect the saved physical stack.
The bulk schematic parameter writer routes `Description` and
`ComponentDescription` to the component's native `ComponentDescription`
field rather than a transient parameter. Script `.124` rebuilt with zero
Pascal lint errors or warnings, and 62 related Python tests pass. Native
description save/reopen acceptance and `.124` VM reload are pending while
the currently running Altium command is active. The HTTP MCP endpoint
continues to answer protocol checks, but script ping is unavailable.

## Additional `mooreaa` corrections, 2026-10-28

`app_checkpoint` now requires an exact project path whenever zero or
multiple projects are open, and sends that path to the project's save
operation. A two-project fake refused an unqualified checkpoint and
accepted the explicitly named project; the prior success/failure save
tests still pass. The schematic template now points GND-named ports down
by default even when their style is `bar`; three focused fixtures pass.
`capture_png` defaults to native pixel size and only the OCR path asks
for 2x scaling; 35 screenshot/dialog source tests pass. A direct live
`PrintWindow` attempt on Altium's main window did not return before it
was cancelled, so native pixel-size QA is still open. Bridge trace shows
another client had started `pcb.run_drc` and pressed Run in the modal
checker; the native DRC remained active while Altium showed
`Responding=false` and its CPU time increased. The screenshot attempt
overlapped that run, so it does not establish a screenshot defect. No
restart was attempted during the DRC.

## `mooreaa` UI corrections, 2026-10-28

Source `.123` includes the fork's schematic deselection process and full
sheet zoom. On a disposable free SchDoc, `generic.select_objects` made its
wire's `Selection=true`; `generic.deselect_all` changed it to false, and
`generic.zoom` with `action=document` dispatched to `Sch:Zoom`. The copy
was closed with its temporary selection state discarded. The native
close handler now refuses a path that Altium resolves to a different
document; the normal exact-path close was accepted, while the phantom
path condition still needs a separate reproduction. The Python zoom
wrapper also returns a clear pointer to `obj_zoom_to_xy` for `point`
instead of referencing undefined local coordinates. Altium 26.11.1.5
pinged with `.123`; the 12-unit Pascal build/lint passed.

## Fresh fork tip and full-stack builder, 2026-10-28

Fresh fetches leave upstream `main` at
`ee7589c9fc543d0b99bb142dc8ca12b618fffeab`, still the exact merge
base and ancestor of our `main` (zero upstream commits pending).
`MOREmbedded/main` remains `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.
The live 62-default/117-branch audit found one advanced fork:
`mooreaa/main` moved from `fc22136` to `4cbae2a`. Fetching it restored
62/62 and 117/117 fresh refs. Its new `pcb_build_stack` feature is being
integrated with exact-PcbDoc identity checks rather than active-tab writes.

Source `.122` now carries the planner and native MasterLayerStack edits.
On an isolated Temp copy of `Rules.PcbDoc`, the public tool planned and
built a two-layer stack, then a four-layer stack with one inserted signal
layer, one inserted plane and three configured dielectrics. The saved
four-layer board was closed and reopened; Altium returned the same layer
order, names, thicknesses, dielectric types and internal-plane layer ID
39. The copy was closed. Twenty-five planner tests pass, and the Pascal
12-unit build/lint has zero errors or warnings. `app_ping` confirms
Altium 26.11.1.5 loaded `.122`. The wrapper leaves failed partial edits
unsaved for explicit inspection and discard; it never silently closes a
project-backed board. Broader board fixtures and failure recovery remain
to be qualified before calling this a general stack migration guarantee.

The fork's `pcb_stack_from_file` saved-file reader now parses the V9
physical stack and legacy copper chain without Altium. Against the saved
four-layer QA file it found four copper layers, three dielectrics, no
findings and no expected-stack mismatches. The parser refuses an absent
V9 stack or absent legacy chain instead of reporting an empty file healthy.
Legacy `pcb_add_layer`, `pcb_remove_layer`, dielectric fields of
`pcb_modify_layer` and the batch stack configurator now require explicit
`legacy_stack_write=True`; accepted replies direct the caller to saved-file
verification. The metadata catalog was reconciled with the static
`proj_export_pdf` refusal, two new EasyEDA emitters and current simulator
coverage. The 204 related stack, metadata and simulator tests pass.

## MOREmbedded library checker and footprint export QA, 2026-10-28

On a separate Temp copy of `SpiritLevel_2E.SchLib`, the public
`lib_check_schlib` wrapper invoked Altium's library rule checker and
read its `.ERR` report. A description check returned `SN74AHC1G04DBVR`
and `TestPin` as missing descriptions; a pin-duplication check returned
zero, and a repeated description check returned the same two. The
report's modification timestamp advanced on each run. The copied
library was closed without a CAD save.

On a separate Temp copy of `Spirit_Level_Project.PcbLib`, the public
`lib_save_footprint_library` wrapper exported `PQ208` into a new
336,896-byte PcbLib. The source had 33 footprints, the output had one.
Altium read 210 pads from each `PQ208`, with identical pad records;
tracks, arcs, regions, fills, texts, vias and 3D body-model lists also
matched exactly. Both libraries were closed. No source library was
modified.

## MOREmbedded symbol alias collision guard, 2026-10-28

The integrated `lib_set_symbol_aliases` feature was tested on an
isolated copy of `SpiritLevel_2E.SchLib`. A new alias on `RES` survived
save/close/reopen, removal survived the next save/reopen, but Altium
also accepted `CAP` as an alias of `RES` while `CAP` was a primary
symbol. That bad edit was discarded. Script `.121` now scans the open
library's primary names and aliases before any alias write. Native
checks refused primary `CAP`, existing alias `ADXL210`, a duplicate
within the add request, and an alias added unsaved to another symbol.
A unique `RES_GUARD_QA` was still accepted and persisted. The tested
library copies were closed, and the example source library was not
changed. The 12-unit Pascal build/lint had zero errors or warnings;
105 related Python tests passed. Altium ping reported loaded `.121`.

## Upstream pre-route and paste opening QA, 2026-10-28

The follow-up tested the existing `pcb.lock_net_routing` on the same
QA board. Its netted track changed from `Locked=false` to true and
remained true after exact save/close/reopen, while `IsPreRoute` remained
false. A read of `pcb.editor_options` showed
`ProtectLockedPrimitives=false` and `LockPreRoutes=false` in the current
editor. Altium's protection preference must therefore be enabled for
the persistent lock to govern subsequent editing/autorouting; the
global preference was only read, not changed. Public guidance now
recommends this workflow.

On a new free Temp PcbDoc, `generic.modify_objects` set `IsPreRoute=true`
on a track and `generic.query_objects` read true immediately. After exact
save/close/reopen it read false. A second experiment set
`UserRouted=false` first; the pre-route flag still reverted. A track
assigned to the new `QA_NET` also reverted to false after save/reopen.
This native setter is usable only as an in-memory state in the tested
AD 26.11 path; its persistent implementation remains open. Both
`obj_modify` and `obj_batch_modify` now attach a persistence warning
when the property is written.

For a standalone SMD pad, writing `PasteMaskUsePercent=true` and
`PasteMaskPercent=50` while `PasteMaskExpansionMode=1` returned a success
but read false/zero. Setting mode 2 exposed those values. A second pad
received `PasteMaskExpansionMode=2|PasteMaskUsePercent=true|PasteMaskPercent=45`
in one `generic.modify_objects` call; all three values, and
`PasteMaskEnabled=true`, persisted after exact save/close/reopen.
The public wrappers and guidance now name mode 2 and advise readback.
The QA board was closed. The 105 focused added-tool tests passed.

## Upstream rule-setting QA and empty-write guard, 2026-10-28

On a new free Temp PcbDoc, `pcb.set_rule_properties` wrote Height
10/900/450 mil, ComponentClearance vertical gap 12.5 mil,
RoutingCorners setbacks 75.5/125.5 mil and NetAntennae tolerance
15.5 mil. All four native replies had empty `settings_not_applied`;
after exact save/close/reopen, `pcb.get_rule_properties` descriptors
contained those values. An exploratory native setter call with only
`name` returned `properties_updated=0` but dirtied the board. The
public Python wrapper now refuses that empty write before transport;
its description also correctly says `properties_updated` counts
successful groups, not individual fields. The free QA board was closed
with its empty-call dirty state discarded. Twenty-six focused tests pass.

## Upstream wire optimizer QA, 2026-10-28

Fresh fetches left `upstream/main` at `ee7589c9fc543d0b99bb142dc8ca12b618fffeab`
and `MOREmbedded/main` at `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.
The former is still the exact upstream ancestor of our `main`.
On a new free Temp SchDoc, `generic.place_wires` placed three contiguous
collinear segments. `generic.optimize_wires` returned 3 to 1 wires and
6 to 2 vertices. `generic.query_objects` read the resulting endpoints
as `1000,1000;2500,1000` mil before and after save/close/reopen;
a second optimize returned 1 to 1 wires. The test sheet was closed.

## MOREmbedded symbol part and display mode QA, 2026-10-28

The integrated `library.set_symbol_parts` handler was exercised in Altium
on a separate Temp copy of `SpiritLevel_2E.SchLib`. `ADXL202E` went from
one part to two, and `library.get_components` still read two after
save/close/reopen (including its `ADXL210` alias row). Adding a second
display mode and removing the empty second part both returned
`complete=true`; another save/reopen showed one part, one populated part,
and eight pins. Removing the second display mode, saving, and reopening
then gave a final no-op readback of one part and one mode, again with
`complete=true`. The QA copy was closed; the original example library
was not edited.

## Structured schematic refusal details, 2026-10-28

Script `.118` fixes three `BuildErrorResponseDetailed` call sites in
`Generic.pas`: they had passed a bare `"candidates":...` or
`"symbols":...` field where the response builder requires a complete
JSON object. A native `generic.set_component_unique_id` refusal on a
disposable two-sheet project previously caused an unparseable response
file twice. After rebuilding and reloading `.118`, the same call
returned `WRITE_REFUSED` with structured `details.symbols` containing
the actual location (5000, 2000) mil and unchanged UniqueId `XUEYHPIV`.
The bridge stayed responsive. The generated monolithic script was
rebuilt from the 12 units; lint reported zero errors or warnings.

The attempted native multipart fixture was not a valid shared package:
Altium gave its two placed parts different UniqueIds, and also reminted
a replicated same-sheet part. The safe designator batch correctly
refused the two `UQA1` symbols with distinct UniqueIds before a write.
The disposable project was closed without saving; native multipart
acceptance remains open.

## Project-sheet discard cache, 2026-10-28

A fresh project-backed scratch sheet kept an unsaved placed `UQA1`
visible after `app_close_document(discard_changes=True)` and reopen,
although its SHA-256 stayed
`25e7c99c611c4ab62a0c3de6c393b8a89c25356b35ef1c255725f679ddc6545b`
before placement, after tab close, and after reopen. Closing the whole
project with `save=false` and reopening it returned only the original
`RQA1`. A free scratch SchDoc discarded an unsaved `RQA99` edit normally
and returned to `RQA1` on reopen with the same disk hash. Thus the
project's in-memory sheet state, not a disk write, caused the difference.
Script `.120` now detects that the closed sheet remains a member of an
open project and reports `discarded=false`, `project_retains_sheet=true`
with the required project-close step. Native checks confirmed that
reply for a project sheet and `discarded=true` for a free sheet. The
generated script rebuilt and all 12 Pascal units linted cleanly.

## Collision-checked project designator batch, 2026-10-28

`sch_batch_rename_designators` is an additional path for a use case the
`bblacklock3` fork refused and upstream later restored generically. It
requires an explicit PrjPcb path and UniqueId-to-designator map. Its
default dry run loads project sheets, queries every component, refuses
existing or proposed duplicate names, and returns a snapshot hash.
Execution requires that hash and writes distinct temporary designators
before final names, with project-wide readback after each phase. A
partial first phase stops without sending final names. No save is
automatic; the generic `obj_batch_modify` remains available.

On a disposable two-sheet project in Temp, two one-part components with
UniqueIds `VTNURPGL` and `SMNYQOWP` swapped `RQA1` and `CQA1`.
Altium reported two matched edits and no skipped operation in each
phase. Readback after each phase and after save/close/reopen showed the
planned values, and the QA project was closed. On a second disposable
two-sheet project, a proxy sent only the first native final edit and
then raised a simulated transport error. The tool's readback reported
one final name and one unique temporary name. A new dry run planned
only the remaining component; applying it and saving/closing/reopening
left both final names persisted. Twenty-seven focused tests passed,
including the simulated partial second phase. Multi-part native
behavior remains to be qualified. Multiple bridge calls are not
atomic against another client editing the same project concurrently.

## Fractional keep-out outline and polygon-pour clearance, 2026-10-28

The native `.115` keep-out-outline handler already accepted decimal-mil
widths, but Python's `pcb_keepout_board_outline` and
`pcb_place_polygon_board(edge_clearance_mils=...)` cast them to integers.
Both now serialize finite decimal mils; the latter doubles the exact
requested edge clearance. Eleven focused source tests pass. On the
disposable arched PcbDoc, `pcb_keepout_board_outline(20.625)` added
three tracks and one arc, then returned `added=0, already_there=4` on a
second call. After exact save/close/reopen, `obj_query` found exactly
three KeepOutLayer tracks and one arc with `Width=20.625` and
`IsKeepout=true`; another outline call still added zero. On this same
disposable board, `pcb_place_polygon_board(net="GND", layer="TopLayer",
edge_clearance_mils=10.3125, pour=True)` reused all four keep-out
primitives (`added=0, already_there=4`) and created `Top Layer-GND 1`
with four vertices and `poured=true`. `pcb_get_polygons` read five
copper pieces and 68.7101666882369 mm² copper area; the same values
remained after save/close/reopen. The QA board was then closed.
An explicit `pcb_repour_polygons(names=["Top Layer-GND 1"],
board_path=<that copy>)` rebuilt exactly one polygon, skipped the other
two and failed none. It reported five copper pieces and
68.7101666882369 mm² both before and after. The copy was saved and
closed after the repour. Script `.117` adds `pcb_get_polygon_outline`,
which reads the saved segment records. On the reopened copy it read
four closed segments matching the board outline exactly: three lines
and a half-circle arc starting at (8000.125, 7500.375) mil, centred at
(7500.125, 7500.375) mil, radius 500 mil, angles 0..180 degrees. Native
Pascal lint passed all 12 units without warnings; Altium reloaded `.117`
and returned this result from the active script project.
The supervised HTTP MCP child on 14701 was restarted from this `main`
checkout after the Python edit. A new MCP session listed 757 tools,
the keep-out width schema is numeric, and `app_ping` reported loaded
script `.115` with `version_match=true`. TCP 14700 remained listening.

## Offline SchLib header and alias parity, 2026-10-28

On the same disposable Spirit Level library copy, Altium listed 40
component rows: 39 primary symbols and the `ADXL210` alias of
`ADXL202E`. The offline SchLib reader found the 39 storages, but
initially returned empty `lib_reference` and `description` because this
file stores header keys as `LIBREFERENCE` and
`COMPONENTDESCRIPTION`. The reader now folds header keys to uppercase,
uses the stored library reference as the canonical name, exposes the
OLE `storage_name`, and returns raw `ALIASLIST`. The offline 39 primary
names and alias now match the native list; `ADXL202E` reads its actual
description. Focused SchLib/provider/PcbLib tests: 16 passed and six
local-fixture skips. The copied SchLib was closed without saving.

## Offline PcbLib footprint identity parity, 2026-10-28

Comparing the native 33-footprint list from the copied Spirit Level
PcbLib with `read_pcblib_footprints` found one real name mismatch:
Altium reports `SO-G5/P.95`, while its OLE storage is `SO-G5_P.95`.
The saved `PATTERN` field has the editor name. The offline reader now
uses `PATTERN` as `name` and exposes `storage_name` separately so callers
can still identify the OLE stream. A regression test covers the
sanitised-storage case. After the fix, the 33 native and 33 offline
names matched exactly. The copied PcbLib closed without saving.
Focused file-reader tests: 22 passed, six local-fixture skips. This
compares identity and count; offline pad/primitive geometry remains
outside this reader's scope.

## Native footprint-primitives read on copied PcbLib, 2026-10-28

Loaded script `.115` opened the copied
`C:\Users\Alex\AppData\Local\Temp\eda-intlib-qa-20261028\Spirit_Level_Project.PcbLib`
and enumerated 33 footprints. `lib_get_footprint_primitives` with that
exact path returned `PQ208` with 209 body records, four tracks and
three arcs; independent `lib_get_pad_geometry` reported 210 pads
(including two fiducials). `CC1608-0603` returned one body, three
tracks and two pads. The library path and footprint name in the
replies matched the requests. The copied library closed without a save.
This qualifies a real native read and routing to the named PcbLib; it
does not compare every primitive against an independent file parser.

## Native integrated-library build from MOREmbedded path, 2026-10-28

With loaded script `.115`, `lib_build_integrated_library` created
`Spirit_QA.LibPkg` in `C:\Users\Alex\AppData\Local\Temp\eda-intlib-qa-20261028`
from copies of Altium's installed `SpiritLevel_2E.SchLib` (186,880 bytes)
and `Spirit_Level_Project.PcbLib` (715,264 bytes). Both exact paths appear
as members in the saved LibPkg and `project.get_documents` returned both.
Altium's `project.compile` returned success and wrote a fresh
`Project Outputs for Spirit_QA\Spirit_QA.IntLib` (123,392 bytes).
The OLE container has `SchLib/0.schlib` and `PCBLib/0.pcblib` streams,
not merely a nonempty placeholder. The exact LibPkg closed successfully
with no other project closed. Its isolated outputs remain in Temp; the
installed source libraries were only copied. Re-running the same tool
against the existing package returned `created=false`, compiled a fresh
123,392-byte IntLib, and `project.get_documents` still listed exactly
the same two members rather than duplicate entries. The package closed
again successfully.

## Hosted Actions on the fork, 2026-10-28

The public GitHub API lists `battery-research-lab` as active but with
zero runs; all repository runs stop at 2026-10-26. The signed-in
repository Actions page supplies the missing explanation verbatim:
"Workflows on this fork have been disabled." It offers a button to
re-enable them. The imported battery workflow now has
`workflow_dispatch` and explicit `permissions: contents: read`; no
hosted run can be claimed while the repository-level setting remains
disabled. A request to enable Actions is pending with the owner because
that setting permits workflow code to execute on the fork.

## Native fractional polygon outline with arc, 2026-10-28

The same disposable PcbDoc used for the circle check was then given a
four-vertex arched polygon through `pcb.set_board_shape`. Vertices were
(7000.125,7000.375), (8000.125,7000.375), (8000.125,7500.375) and
(7000.125,7500.375) mil; the third-to-fourth edge is a counter-clockwise
half-circle centred at (7500.125,7500.375) mil, radius 500 mil. Loaded
script `.115` returned one arc, three lines, `closed=true`, and bounding
box (7000.125,7000.375)..(8000.125,8000.375) mil. Exact save, close
and reopen retained those four vertices and the arc's 0..180-degree
angles. The copy then closed. Its current Temp contents are the polygon;
the earlier circle check remains an observed test result, not the copy's
current shape.

## Native fractional circular board outline, 2026-10-28

Loaded script `.115` set a circle on disposable
`C:\Users\Alex\AppData\Local\Temp\eda-circle-qa-20261028.PcbDoc`, copied
from the installed Spirit Level example. `pcb.set_board_shape` accepted
centre (7000.125, 7500.375) mil and radius 500.625 mil. Before the
edit the copied board had an eight-vertex rounded rectangle; after the
edit `pcb.get_board_outline` returned four 90-degree arcs at that exact
centre, bounding box (6499.5, 6999.75)..(7500.75, 8001) mil, and
`closed=true`. Exact save, close and reopen preserved the four arcs and
bounds. The disposable board then closed. The installed example was
read only; the modified copy remains in Temp.

## Component parameter scope and native Value readback, 2026-10-28

The fork template-value reconciliation exposed a native scope defect:
`SetCompParamText` could match a nested model `VALUE` when the caller
intended a parameter on the placed component. Script `.115` restricts
that lookup to `eIterateFirstLevel`, matching the existing `Value` update
helper. Pascal lint/build passed all 12 units with zero warnings or
errors; 15 focused Python tests passed with one optional skip. On a
disposable placed `CAP`, a direct `VALUE=direct-old` was created and
persisted, then `Value=33nF` updated it and the visible Comment after
save/close/readback. The nested model `VALUE=old-component-value`
remained unchanged. The bridge reloaded `.115` from the main script
project without an Altium restart.

## mooreaa template Value fix, 2026-10-28

Running the fork's 22 placement-cleanup source checks against current
`main` exposed one real regression: `sch_draw_template` sent a plan value
as `Comment`, while the native `Value` key intentionally updates both
`Comp.Comment.Text` and the existing component Value parameter. The
template drawer now emits `Value`. The other two fork-test failures were
source-shape assumptions superseded by our query-only live-pin filter
and fractional-width serialization. The template, multipart and cross-
validation suites pass: 42 passed, 19 optional skips. On disposable
SchDocs, `RES` and `CAP` placements both set the visible Comment to the
requested value after save/reopen (`4k7` and `47nF`). The installed
`CAP` library's `VALUE=0.1uF` is nested under a model, not owned by the
component, so an existing component-level Value parameter still needs
native readback. Altium crashed twice during the first `CAP` attempt;
after a restart the same copy opened and the placement succeeded.
`app_ping` then confirmed `.114` and the script project in the main
source directory. The scratch documents and library were closed.

## Exact-project PCB net-colour plan, 2026-10-28

The installed Mini PC SODIMM example project and board were copied to
`C:\Users\Alex\AppData\Local\Temp\eda-netcolor-qa-0c37065137df4fc5a5a80d63db2c3f87`.
Native script `.114` read 229 board nets. With exact copied PrjPcb and
PcbDoc paths, `pcb_net_display(from_project=True, dry_run=True)` planned
the project BGR colours for GND (16777070), VDD (48640), VPP (16740095),
VREFCA (7274350) and VTT (7237375). All five matched existing board
colours; no project colour was missing. No document became dirty. The
board and project closed without saving. Automatic approval review
rejected recursive removal of the isolated copy, so it remains in Temp.

## Optional battery research lab from a fork, 2026-10-28

The self-contained `research/battery-ai-comsol-lab` package and its
path-scoped GitHub Actions workflow were imported from
`yniantongtian-oss/feat/battery-ai-comsol-lab`. The core `eda-agent`
dependency set and CLI were not changed. In an isolated Python 3.12
environment with PyBaMM 26.10.1.1, Ruff passed and all six package tests
passed, including the short electrothermal smoke run and CSV/manifest
output. COMSOL/MPh was not installed or natively exercised; its adapter
remains optional and requires a local COMSOL installation and license.
GitHub registered the new workflow as active but reported zero runs after
the push, so hosted acceptance is still pending.

## Exact-board net inventory native read, 2026-10-28

Script `.114` opened two disposable PcbDocs. `pcb_get_nets` with the
nonfocused Spirit Level copy's exact path raised `TARGET_CHANGED` while
the empty QA board was focused. The focused QA board returned zero nets.
After `pcb_focus_board` selected the Spirit Level copy, its exact-path
inventory returned 126 nets. Both boards were closed without saving and
the extra copied PcbDoc was removed. Project net-colour planning still
needs its own exact-project check.

The local SDK reflection produced 1,946 interfaces and 2,332 properties
from the running installation's `Altium.SDK.Interfaces.dll`; 1,913 types
were unresolved and 37 methods skipped. `sdk-coverage` reported 662 of
2,207 properties reachable by its *generic chain* model. That model does
not count all dedicated handlers, so the percentage is not total tool
coverage or a claim that the remaining properties are safely writable.

## Latest upstream ancestry merge, 2026-10-28

Upstream `ee7589c` is a true merge parent of our `main`, moving the exact
sync point forward from `f3bd57f`. Its counted `sim_get_probes` sheet lookup
and pytest 9.2 courtyard assertion were adapted with script `.114`. Thirty-six
focused tests and the 12-unit Pascal lint/build passed. Live Altium `.114`
returned `sheets_seen=7, sheets_skipped=7, count=0` with no Simulation Quick
Start copy sheets open, then `7, 6, 1` after one sheet opened. That sheet and
the copied project were closed without saving. The script ping returned zero
cast errors.

## MOREmbedded package-audit path, 2026-10-28

With `Spirit_Level_Project.PcbLib` focused, `lib_audit_footprint_vs_package`
targeted `FP-53261-0771-MFG` in the inactive `PCB1.PcbLib` by its exact
`library_path`. Native script `.113` read nine pads, 21 tracks, one arc and
one text from the target; the audit returned that target path and no
wrong-library layer note. Both PcbLibs were closed without edits. This
accepts the multi-library routing of the audit path.

The diagnostic `custom` PackageSpec used the 7-circuit 1.25 mm pitch and
recommended 0.6 by 1.6 mm signal lands and 2.1 by 3.0 mm hold lands from
[Molex drawing 532610001-SD, sheet 2](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/532/53261/532610371_sd.pdf).
Its pad-centre offsets were provisionally registered from the Altium
footprint, so position checks are *not* independent vendor verification.
The audit found seven signal pads 0.8 mm wide against the drawing's 0.6 mm
recommendation, plus courtyard and assembly warnings. Do not treat this
diagnostic as footprint signoff; independently transcribe and verify all
pad centres and body dimensions from the drawing before that claim.

## MOREmbedded multi-library render check, 2026-10-28

Two installed Altium example PcbLibs were opened read only.
`Spirit_Level_Project.PcbLib` was focused while
`lib_render_footprint` targeted `FP-51021-0700-MFG` in inactive
`PCB1.PcbLib`. The target library's mechanical layers were explicitly
`Assembly Top` (Mechanical5), `3D Body Top` (Mechanical2),
`Courtyard Top` (Mechanical3) and `Component Center Top`
(Mechanical16); the focused library had none of those kinds. The render
reported roles with counts 4/4/4/2, no wrong-library note, and an SVG.
Both PcbLibs were closed without edits. This qualifies the render path
of the MOREmbedded layer-path adaptation; the package-audit routing check
is recorded above.

## Native fractional PCB placement on `.113`, 2026-10-28

The original `Spirit_Level_Project.PcbLib` was read only to choose its
`CC1608-0603` footprint. A disposable free PcbDoc received two batch
placements. `QA_TOP` read back at (1000.125,1200.375) mil, 45 degrees
on TopLayer. `QA_BOT` was flipped to BottomLayer and read back at
(1500.6248,1600.875) mil, 90 degrees; the requested X was 1500.625
mil and Altium's PCB coordinate resolution accounts for 0.0002 mil.
Both values, sides and rotations survived exact save/close/reopen.
The test board and source PcbLib were closed without further edits.

## Live fractional schematic acceptance on `.113`, 2026-10-28

An isolated free `Fractional_QA.SchDoc` showed batch wire vertices at
2000.125/2100.375 to 2200.625/2100.375 mil after exact save/reopen.
On `.112`, a text frame's actual fractional geometry persisted but
`sch_place_text_frame` rounded its reply and `obj_query` returned empty
`Corner.X/Y`. Script `.113` uses decimal JSON for the reply and typed
`ISch_TextFrame.Corner` for generic read/write. Altium was restarted
with the main script project; `application.ping` returned `.113` and
zero cast errors. A second text frame returned exact 1700.125/1800.375
and 1900.625/1950.875 mil corners. `obj_modify` changed the first
frame's `Corner.X` to 1600.75 mil. Both frames and that edit survived
exact save, close and reopen. No managed project was modified. DbLib
component placement remains a separate fractional-coordinate check.

## Fresh sync and service check, 2026-10-28

After a fresh fetch, `upstream/main` and the exact `main` merge base
are both `f3bd57ff87b915d5cfe72579fa501bfea85c3511`; zero
upstream commits are outside `main`. All 109 branches exposed by the
61 live GitHub forks matched local cache refs after refreshing our own
fork's `main` and `agent/sync-upstream-d6823d5` refs. That agent branch
is already an ancestor of `main`. The built-in live verifier, which
also includes upstream, reported 62/62 default tips and 117/117
branch tips matched. The HTTP/MCP process was restarted
from the corrected Python source on 14701; TCP 14700 stayed listening,
and Altium answered `.112` with zero cast errors before the later
`.113` restart described above.

## Native simulation reads on `.112`, 2026-10-27

An isolated copy of Altium's installed Simulation Quick Start project
opened in the restarted bridge. `sim_get_setup` read operating-point,
DC, transient and AC analyses, including their stored settings and 14
prior runs. `proj_load_sheets` loaded all seven SchDocs, after which
`sim_get_probes` returned `count=0` and `not_loaded=[]`. The project
closed with `save=false`; the installed original was never opened.
Probe placement and a new simulation run were verified the next day.

## Native simulation write and run on `.112`, 2026-10-28

On the same isolated Quick Start copy, `sch_place_probe` put a voltage
probe at (4250,10200) mil on the `out` wire. `sim_get_probes` returned
one simulation probe with `SimulationProbe=V`, `ProbeVoltage=True` and
custom name `QA_OUT`, both before and after saving/reopening the copied
sheet. A sheet-scoped `sim_run(analyses=['op'])` saved an SDF with
numeric outputs and correctly reported `selection_applied=false`:
Altium actually ran operating point, DC, transient and AC. Reopening
the copied project with `sim_get_setup.enabled=['op']` and running the
same sheet again still produced all four. The prior claim that
reopening makes the selection apply was wrong; the tool's note and
documentation now report the observed behavior. The copy closed
without saving after the run. Analysis selection needs a separate
native solution.

## Native free-text acceptance on `.112`, 2026-10-27

On a disposable free `FreeText_QA.SchDoc`, `sch_add_text` placed native
`eLabel` `QA_REV_A` at (125.125, 200.25) mil, rotation 90 degrees.
`obj_query` returned one label with those fields. `app_save_document`
observed a disk write; exact close/reopen returned the same text,
coordinates, object type and orientation. Altium changed `FontId` 1 to 2
on reopen: both specs are Times New Roman 10, with rotation 0 and 90
respectively. A missing exact SchDoc was refused with
`SHEET_NOT_LOADED`. The disposable document was closed and removed.
The simulation additions from upstream were subsequently checked on a
disposable project copy, with the analysis-selection limitation above.

## Live `.112` runtime after restart, 2026-10-27

The user-authorized Altium restart replaced the `.96` VM with source
`2026.10.27.112` from the main `Altium_API.PrjScr`. Before restart,
`application.get_open_documents` listed 181 project documents, but only
`PCB.pas` had `loaded=true` and none reported modified. Altium restarted
as PID 25392; the main-directory `start-altium-bridge.ps1` launched its
polling loop. `application.ping` returned `.112` and `cast_errors=0`.
The Streamable HTTP MCP service on 14701 was restarted as PID 18400; a
real MCP client listed 757 tools and found `sch_add_text` and
`sim_get_setup`. The TCP relay on 14700 remained listening. This proves
load and reachability, not native save/reopen behavior of the new tools.

## Combined fork decimal guard, 2026-10-27

`library.py` accidentally defined `_mils` twice. The later definition
from `vincent-himpe`'s decimal-mil port overrode a newer finite-value
check, allowing `NaN` to be serialized into library coordinates. The
duplicate was removed; one helper now preserves 1e-4-mil precision and
rejects nonfinite values. Thirty relevant tests pass. A live bridge read
found Altium `.96` responsive, 181 project-listed documents but only one
loaded editor document (`PCB.pas`), with no modified flag. The modified
flag is not a reliable proof of no unsaved state; full `.112` reload and
native acceptance are separate work.

## Upstream simulation merge, 2026-10-27

Upstream advanced one commit to `f3bd57ff87b915d5cfe72579fa501bfea85c3511`.
The true merge carries native voltage-probe parameters, `sim_get_probes`,
`sim_get_setup`, sheet-scoped `sim_run` analysis selection and the `.simcfg`
reload change. Script `.112` preserves our exact-sheet free-text handler
and shared-mode flags. The combined Pascal lint/build found zero errors or
warnings; 59 focused simulation, free-text and bridge tests passed.
Upstream ran the simulation changes on a scratch project in Altium 26.11;
our merged `.112` bundle has not yet been loaded in the shared session.

## Fork free-text primitive, 2026-10-27

The `rabihnd/integration` branch's `sch_add_text` creates an `eLabel`.
The earlier name-only audit mapped it to notes/text frames, which are
different schematic primitive types. Source `.111` adds an exact-sheet
`sch_add_text` handler using a native `ISch_Label`, font inference,
document dirtying and readback. Python refuses malformed coordinates and
mismatched-sheet replies. Source tests and Pascal lint/build pass; native
save/reopen acceptance is pending until the shared Altium session can load
the new script.

## Fresh fork audit after `1d093a2`, 2026-10-27

At the start of this audit, `main` and `origin/main` pointed to `1d093a2`;
the validation fix is now on `main` as `e6ef3db`. The fetched upstream tip is
`c45ca0a` and is an ancestor of `main` (`main..upstream/main` is empty).
The live verifier matched 62/62 fork default tips and 117/117 branch tips
to local refs. `MOREmbedded/main` remains `032fb4b`. Its
`via_loop_inductance` is already exposed here as `pcb_calc_via_inductance`
using the same Johnson loop formula. Comparison found that the older
shared calculator accepted nonfinite values, while the fork refused them;
the shared calculator now refuses nonnumeric and nonfinite inputs too.
The Windows binary GitHub Actions workflow still has zero
recorded runs, so its hosted build remains unverified.

## xSignal selector and live runtime, 2026-10-27

`pcb_delete_xsignals` now rejects conflicting `names` plus `all=true`
in both Python and Pascal. Previously Pascal ignored the names and
deleted all xSignals. Source `.110` passes 17 related tests; Pascal
lint/build scanned 12 units with zero errors or warnings. The legacy
`test_added_altium_tools.py` and the focused suites for its migrated
wrappers now pass together (129 tests). A live `eda-agent doctor --json` check found Altium responsive
with loaded `.96` and source `.109` before this change. A subsequent
open-document read listed 181 documents and zero reported modified
flags, so `.110` has not been loaded or natively checked.

## Exact-board net inventory, 2026-10-27

`pcb_get_nets` now accepts an optional PcbDoc path. Its native read
checks that path against the selected board and includes the board path
in the reply. `pcb_net_display(from_project=True, nets=None)` sends the
same path for its net inventory and rejects a mismatched reply before
planning any colour write. Previously it read whichever PCB was current.
Eight focused tests pass; Pascal lint/build scanned 12 units with zero
errors or warnings. Native two-board acceptance on script `.137` is
recorded above. The broader legacy `test_added_altium_tools.py` has been
reconciled with the exact-board wrapper contracts.

## Fractional schematic placements, 2026-10-27

Source `.108` carries decimal mils through `sch_place_wires`,
`sch_place_dblib_component`, and `sch_place_text_frame`. The text-frame
Pascal handler now keeps parsed corners and its corner-swap temporary as
`Double` before `MilsToCoordF`; the wire and DbLib handlers already did so.
Forty-three focused tests pass. Native save/reopen acceptance is pending
until `.108` can be loaded in the shared Altium session.

## Fractional PCB batch placement, 2026-10-27

Source `.107` preserves fractional-mil X/Y positions in
`pcb_place_components`: Python serializes mils to four decimal places and
the native batch parser keeps X/Y as `Double` until `MilsToCoordF`.
Previously the Python wrapper called `int()` and the Pascal batch handler
stored `StrToFloatDef` in `Integer` variables, so a sub-mil request was
rounded twice before placement. Nineteen placement/decimal tests pass;
Pascal lint/build reports 12 units with zero errors or warnings. Native
save/reopen acceptance of a fractional placement remains pending.

## MOREmbedded mechanical-layer targeting, 2026-10-27

`lib_render_footprint` and `lib_audit_footprint_vs_package` now ask the
native `library.get_mech_layers` handler for the same PcbLib path used for
the footprint's pads and primitives. Previously they sent no path, so
multiple open PcbLibs could give the correct footprint geometry with layer
kinds from the focused, unrelated library. This adapts the child fork's
`_live_footprint` behaviour into our existing tools. Forty-three focused
tests pass. Native multi-library acceptance remains pending on script `.106`.

## Upstream no-console merge, 2026-10-27

`upstream/main` advanced to `c45ca0a537ad5afe0cda4ce1951e6bfb6be4ff3d`.
Merge `bb3c404` records that exact sync point in `main`; zero upstream
commits remain unmerged. The upstream `no_window()` helper now covers
console subprocesses launched by the original package. Three fork-specific
call sites in `fork_status.py`, `diag/update.py` and `pcb_toolkit.py` also
use it. The focused suite passes 27 tests. This is Python source behavior;
the loaded DelphiScript `.96` versus bundled `.106` gap is separate.

The `james-martinez` Windows exe workflow was adapted and locally built
from a release wheel. The exe reported 0.7.1 and installed all 15 bundled
DelphiScript files into a disposable directory. GitHub Actions recognises
the workflow, but had not created a run at the latest check. Weekly
Dependabot config from `yniantongtian-oss/main` is also in `main`.

## Fractional-mil annotation order, 2026-10-27

Source `.106` sorts project annotation by native TCoord positions instead
of rounding components to whole mils first. Distinct imported placements
less than 1 mil apart therefore retain their order within a sheet. The
wire reply and annotation numbering contract are unchanged. Native
acceptance on a disposable schematic with fractional positions remains
pending. Five related tests passed; Pascal lint/build found zero errors or
warnings. The only remaining direct `CoordToMils(` calls in split Pascal
units are utility/self-test definitions and assertions.

## Fork behavior review, 2026-10-27

The remaining-name audit checked `rabihnd/integration`'s extra property
catch and `cad435/main`'s vault-library list against current equivalents;
neither needs a duplicate public tool. The MOREmbedded NPI and SDK
reflection modules are present; their focused suites pass 66 tests.
The NPI fab-capability DVT criterion stays manual until a complete
same-snapshot export comparison is natively verified. Details are in the
dated sync ledger.

## Schematic source-library cleanup, 2026-10-27

Source `.105` adapts `wizd/edev`'s optional footprint-library cleanup to
`sch_clear_source_library`. With `clear_footprint_library=true`, the
command clears datafile Locations across every PCBLIB model of each
matched placed part, counts confirmed clears and reports failed readbacks.
The default stays false for existing callers. An explicitly named sheet
that is not loaded now returns `SHEET_NOT_OPEN` instead of silently
editing the focused sheet. Twenty-four related tests passed; Pascal
lint/build found zero errors or warnings. Native save/reopen acceptance
remains pending.

## Footprint and export source checks, 2026-10-27

The extended footprint/relink verification now passes 48 tests with one
optional skip. Its older component-property test was updated to inspect
the separate read and write guards actually used by `Generic.pas`.
`proj_export_pdf` is classified read-only because its current handler only
returns `PREVIEW_NOT_SILENT`; the working PDF exporter remains
`proj_export_schematic_pdf`.

## Placed footprint name mirror, 2026-10-27

Source `.104` adapts the `wizd/edev` model-name mirror: choosing an
existing PCBLIB model or renaming the current one also writes the placed
component's `Footprint` parameter. The helper reads the parameter back
before claiming success, so the Properties panel and model cannot silently
diverge. Native save/reopen and ECO acceptance remain pending. Altium
26.11.1.5 currently has 16 open projects and 181 listed documents; the
running script is `.96`, so this source has not been loaded into that
shared session.

## Placed footprint library links, 2026-10-27

Source `.103` adapts `wizd/edev`'s explicit `Any`/`*` action in the existing
`sch_relink_components` path: it clears pinned datafile Locations on every
PCBLIB model of the named placed component. Assigning a PcbLib to a model
with no datafile link now adds that link before readback. The existing
Altium 26.11 finding that a full path in Location wedges the editor is
respected: the relinker writes the PcbLib file name. Native save/reopen and
ECO verification are pending on a disposable schematic. Eighteen related
tests passed, and Pascal lint/build found zero errors or warnings.

## Multipart graphic ownership, 2026-10-27

Source `.102` exposes optional `owner_part_id` on the public
`lib_add_symbol_rectangle` and `lib_add_symbol_arc` tools. The native
rectangle handler already read it; the arc handler now does too. Explicit
0 shares the graphic across all parts, while omission uses the current
part. Polygon and batch line writers use the same validation, refusing a
negative or fractional owner before a bridge command. Seventy-seven
related tests and Pascal lint/build passed. Native save/reopen acceptance
on a disposable multipart SchLib is pending.

## Schematic object type names, 2026-10-27

Source `.101` restores five schematic graphic names in `SchTypeName`
that upstream and MOREmbedded already return. Without them,
`app_get_sheet_frame` reported `type_<id>` for polygons, arcs,
elliptical arcs, ellipses and Bezier curves. Five more accepted schematic
types now receive readable names instead of numeric fallbacks. Source
tests passed (71 related tests), and Pascal lint/build found zero errors
or warnings; native sheet-frame acceptance
requires a controlled Altium reload.

## Multipart symbol lines from `rabihnd/integration`, 2026-10-27

Source `.100` carries the fork's explicit `owner_part_id` on schematic
symbol lines through the existing batch tool. The native batch handler
already accepted the field, but Python had omitted it. Native
`SetOwnerPartFrom` now treats 0 as a shared graphic instead of falling back
to whichever sub-part is current. Omitting the field still uses that current
part. Three native symbol writers (rectangle, polygon and batch lines) now
use `AddLibSymbolPrim`; the earlier direct component insertion could leave
the new graphic invisible until a library view refresh. Sixty-nine related
tests passed, with one unrelated existing schematic-name assertion excluded;
Pascal lint/build passed. Native
save/reopen acceptance on a disposable multipart SchLib remains pending.

## Fork helper recovery, 2026-10-27

A declaration-name comparison over 119 cached fork refs found 20 Python
and 35 Pascal names absent from `main`. Most named helpers have equivalent
implementations under other names, but three live call targets had no
definitions: `ReadNoErcProp`, `WriteNoErcProp` and `SaveProjectFile`.
Script source `.99` restores the guarded No ERC property helpers and an
exact-project save helper that reports an observed project-file write.
`app_create_document` now pins the chosen project path before creation,
saves the project membership after adding the file and refuses an existing
file path. Fifty-one related tests and Pascal lint/build passed. The shared
Altium session still runs the earlier compiled script; native acceptance
of `.99` is pending a controlled restart.

## Saved No ERC copies and project-scoped ERC, 2026-10-27

Two separately opened project copies proved that deleting a No ERC at
`Main.SchDoc` (1400,6100 mil) activates `NetU1_A2`, and deleting one at
`I2C.SchDoc` (7850,2300 mil) activates `NetIC44_1`. Both rows remained
`suppressed=true` immediately after exact sheet save and explicit
`DM_Compile`; after close/reopen of the saved sheet and another compile,
both became `suppressed=false`. The other I2C marker at (7850,2400 mil)
remained. SHA-256 manifests confirmed all 29 and 30 files in the respective
original folders unchanged. Full call results are in
`D:\ai\alterc7-calls.jsonl` (local evidence, not a repository artifact).

The Python `proj_run_erc` wrapper had silently ignored `project_path`,
although the native run and violation reader accept it. Both wrappers now
pass that exact path; the run also reads and returns the filtered violation
page rather than only a raw count. Script source `.98` repairs tracked-edit
cleanup when `app_reload_document(save_before_close=true)` confirms a disk
write. Forty-two focused tests passed (one optional skip); Pascal lint/build
found zero errors or warnings. Runtime loading of `.98` and native testing
of the updated Python wrapper remain pending.

## ERC edit tracking and close lifecycle, 2026-10-27

Script source `.97` makes the bridge's tracked schematic edits invalidate
the compile cache and count as dirty even when Altium's `Modified` flag is
false. Exact document close now refuses an unacknowledged tracked edit and
clears its marker only after confirmed close; project close with
`save=false` clears markers for documents confirmed gone. Pascal lint/build
found no errors or warnings, and 51 focused tests passed (one optional
skip). This source change is not yet loaded in Altium. Two no-save ERC
experiments removed one No ERC marker each in memory, but `DM_Compile`
still returned both original rows as suppressed. Whether Altium compiles
those unsaved edits or holds a separate stale model remains unresolved.

## Fork source scan and EasyEDA build, 2026-10-27

Across 119 cached fork branch refs, the only tracked Python source path
absent from `main` after the updater port was
`yniantongtian-oss`'s `easyeda_extension_cli.py`; its path/build commands
already have our `easyeda-extension` equivalent. Its nonempty build-folder
refusal and nonempty `.eext` result check are now integrated into that
existing command. Seven focused packaging tests and a real isolated Node
build (55,115-byte `.eext`) passed. Shared-file behavior still needs
review beyond this file inventory.

## Child-fork update report, 2026-10-27

The source now includes a read-only `eda-agent update --status` mode
adapted from MOREmbedded's four-layer updater. It checks the tracked Git
remote, installed Python package, script source/deployment and compiled
Altium version; `--from upstream` adds the original project, `--fetch`
refreshes refs, and `--json` emits the same findings for automation.
This machine's main-directory script setup is recognized without creating
a second script copy. The current Altium process is unresponsive, so its
compiled version and loaded project path correctly report as unknown.
Twenty-one focused tests passed. Existing `update --yes` behavior remains
the apply path.

## New upstream source merge, 2026-10-27

The current source candidate is script `.93`. It reconciles upstream
`fbf72a78254cb0573fb75e71600f5850e38421a0` with our exact-board
contracts and earlier fork ports. The previous exact merge point was
`40814badc695813157fd8c50d24feafc5a553fcd`; see the dated upstream
sync ledger for the feature list and focused checks. Pascal lint/build and
87 focused tests passed. Altium 26.11.1.5 then loaded `.93` from the main
script project: `application.ping` returned `.93` and `cast_errors=0`, and
`application.get_unit_stamps` returned all ten modules. Native execution of
the newly merged feature commands remains unverified. `MOREmbedded/main`
remains `032fb4b`.

## Refreshed handoff, 2026-10-27

Script `.90` is now loaded after an Altium restart. The former `.89`
script raised an undeclared `UnitStamp_Utils` error when another client
requested unit stamps; `Utils.pas` and `PCBGeneric.pas` had lost their
stamp functions. The same merge had dropped the CLI's
`_stamp_deployed_unit` helper, so `install-scripts` also failed. Both are
restored, and `Running` now lives in the `StatusForm` unit that uses it.
Live `application.get_unit_stamps` returned all ten unit names with no
modal; ping reported Altium 26.11.1.5, `.90`, and zero cast errors.
The Python bridge again carries each session's document on both sync and
async calls and updates it from response focus changes; the focused
32-test suite passes. The supervisor restarted HTTP 14701 into the new
Python source and a real MCP initialize/list-tools exchange returned 754
tools. TCP 14700 still listens. The main script project remains
`D:\AI\eda-agent\scripts\altium`.

Script `.89` previously loaded in Altium 26.11.1.5 with zero cast errors. It restores
the pin-property helpers lost in an earlier merge; without them a generic
schematic query raised a modal undeclared-identifier error. On disposable
SchDoc/SchLib files, two sections of a three-part symbol survived exact
save/reopen, as did a pin `ShowName` change. The existing
`sch_relink_components` handler was then checked on that disposable SchDoc:
both sections switched from `EDA_AGENT_QA_TRIPLE` to `EDA_AGENT_QA_DUAL`
and survived save/reopen; both were restored to `EDA_AGENT_QA_TRIPLE` and
survived another save/reopen. A wrong sheet path and nonexistent library
symbol were refused without changing the links. The upstream merge base
remains `40814badc695813157fd8c50d24feafc5a553fcd`, with zero upstream
commits pending after a fresh fetch. Other fork acceptance gaps remain in
the dated upstream-sync table.

Script `.88` fixes STEP standoff editing for multi-body footprints.
`lib_set_3d_body` now matches a saved model name against the basename of
the live model's full path; the native handler checks that identity before
changing any property, so a stale record cannot leave a partial layer edit.
On disposable `TEST PAD` with an extruded body and a STEP body, only body 2
changed Mechanical13 to Mechanical15 and model Z offset from 10 to
19.685 mil. Both bodies, the unchanged first layer and the STEP's 90-degree
rotation survived exact save/reopen. A deliberately wrong model name was
refused before the layer changed. Nine related Python tests and Pascal
lint/build passed; Altium 26.11.1.5 loaded `.88` with zero cast errors.

Script `.87` adds `lib_add_3d_body`, adapting the `rabihnd/integration`
STEP-body feature to an exact PcbLib and footprint, a default dry run, an
old-body-count precondition and native readback. The selected footprint is
made current before the body is created: a native test found that adding to
an inactive footprint otherwise moved the body by 50,000 mil after save.
On a disposable PcbLib copy, the new STEP body joined an existing SOIC STEP
body on Mechanical13. Its (1, -1) mm centre, 90-degree Z rotation and
10-mil model Z offset survived exact save, close and reopen. The original
model remained. Pascal lint/build had zero errors or warnings, and eight
related Python tests passed. The library file is test data, not a release
artifact. The exact save remains a separate operation.

The `4pplet` EasyEDA auto-layout emission path is restored alongside the
hand-template workflow: `easyeda_emit_plan` computes placements from a
validated DesignPlan and `easyeda_emit_connections` emits wires, labels or
flags only from real pin positions supplied in mils. Neither tool writes
to CAD; the returned calls are reviewable data. Seven focused auto/template
tests passed, including missing-pin refusal and backend registration.
Live EasyEDA extension acceptance remains pending.

Script `.85` adapts `rabihnd/integration`'s custom pad-list footprint
creation as `lib_create_pcb_footprint`. It plans by default, requires an
exact existing PcbLib, validates every pad and refuses an occupied name or
stale footprint count before one native creation call. Native creation
reads back pads, silk/assembly/courtyard outlines, a pin-1 dot and
`.Designator`. On a separate disposable PcbLib copy, two pads and all
15 non-pad primitives read back; the corrected oval shape, pad geometry
and primitive layers persisted after exact save and reopen. The fork's
`eRoundedRectangle` oval mapping produced an octagonal pad on AD 26.11;
the port uses `eRounded` with unequal pad dimensions and verifies the
returned shape. Wrong path, stale count and duplicate name were refused.
The owner PCB hash remained unchanged. Pascal lint/build and three
focused Python tests passed.

Script `.83` reports the exact PcbLib document's known/modified state in
`lib_get_footprint_primitives` and resolves saved STEP Z offsets when that
document is clean. The disposable `AD_FE38` library read returned
`standoff_mm=0.254` from its saved model while the active-document API had
reported the scratch PCB. Unknown/dirty cases remain unverified. Altium
26.11.1.5 accepted `.83`; Pascal lint/build had no errors or warnings,
and 14 related Python tests passed (one optional test skipped).

Script `.82` fixes exact-board identity for `pcb_pours_at` and
`pcb_board_options`: the Pascal handlers now enforce `expect_file` and echo
`board_file`; the Python wrappers reject a mismatched reply. On the
disposable PcbDoc, reads named the correct board, and wrong-path pour reads
and option writes were refused in Altium 26.11.1.5. The same runtime read
`AD_FE38` from a disposable PcbLib: 493 tracks, 38 regions, 12 vias and
one STEP body; a wrong library path was refused. Saved STEP standoff was
subsequently qualified in `.83`. Fork branch check: 62/62 default tips
and 117/117 branch tips still match their cached refs.

Script `.81` completes the `40814ba` net-colour adaptation. The exact-board
`pcb_net_display` can set `#RRGGBB` or read colours from an explicitly named
PrjPcb, with default dry run and old flag/colour preconditions before its
single batch write. On the disposable PcbDoc, GND changed to `#123456` and
was restored from the loaded project colour. Native readback confirmed both;
Pascal lint/build found zero errors or warnings and 10 focused tests passed.
Fresh fetches still identify `upstream/main=40814ba` and
`MOREmbedded/main=032fb4b`; the upstream tip is our merge base.

Script `.79` (bundle Git blob `908a03ca1aba89f3fe25825369606b3d556d21dd`)
adds upstream's coarse visible-grid factor and grid-unit controls to the
existing exact-board grid command. In Altium 26.11.1.5, a disposable
PcbDoc's factor changed 5→6→5 and its visible unit mm→mil→mm. A stale
factor precondition was refused with the value unchanged. Pascal lint/build
had zero errors or warnings; 26 related Python tests passed.

Fresh `upstream/main` advanced to `40814badc695813157fd8c50d24feafc5a553fcd`
while this session was running. Merge commit `da566a8` has that tip as
its second parent and is pushed to `origin/main`. Script `.78` (bundle Git
blob `3f69889576501586251f2338430e174a78c4cdac`) is loaded in Altium
26.11.1.5 with zero cast errors. On the disposable PcbDoc, exact-board
Gerber and print setup reads returned units/decimals and scale/fit settings;
a wrong board path was rejected. On the loaded schematic,
`sch_reference_zones` returned 147 component/port locations and their
native border zones. The disposable PCB was refocused after that read.
The merge also brings Testpoint Style rule settings and paste-array
preferences. The expanded PCB editor preferences and paste-array settings
now use exact-board preflight, default dry run and readback. A board-area
colour and repeat count were changed and restored in Altium; a stale
editor-option precondition was refused. The already reviewed exact-board
net-display and grid commands remain in place; upstream's newly added
colour/project sync and grid factor/unit extensions were subsequently
adapted to their preconditioned contracts.
The owner PCB hash remains
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.

The current source candidate is script `.76` (bundle Git blob
`8ddab41edc39cffabf14aac92a2e0d9f339fd61f`); Altium 26.11.1.5
answered `application.ping` with `.76` and zero cast errors. The
decimal-mil paste-grid port from `vincent-himpe/fix/decimal-mils-leftovers`
was checked on a disposable PcbDoc: a 39.37-mil grid with 5.125-mil
minimum gap created six fills at 67.567% reported coverage. The six fills
and disabled top-paste flag survived exact save, close and reopen. A repeat
call was refused with `PASTE_DISABLED`, preventing duplicate fills. A
cache-only negative paste expansion did not survive reopen, so the grid
and DNP exclusion now disable the pad's side-specific paste flag. DNP
apply and restore on both R1 pads each survived a separate save/reopen.
The generic PCB writer now routes supported extra properties to its
existing setter; an exact, single-pad mask-mode write also survived
save/reopen. Pascal lint/build passed with zero errors or warnings and
37 focused Python tests passed. The owner PcbDoc SHA256 remains
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.
Altium PID 29396, HTTP MCP 14701 and TCP relay 14700 are listening.

`f339ee53e2643f1e222015028cb239b9fb9ede58` is the last reviewed
feature/acceptance commit; later ledger commits may advance `main`.
Use `git rev-parse main origin/main` for the live heads.
The earlier upstream synchronization point was
`9ee593ea0dce989bf3bfc97d0c982044ed41badb`; the fresh tip is
`40814badc695813157fd8c50d24feafc5a553fcd`. The direct child
fork `MOREmbedded/main` is `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`;
its 33 divergent commits are Git ancestry, not a count of missing features.

Script source and generated bundle are `.68`; see `git hash-object
scripts/altium/Altium_MCP.pas` for the current exact bundle identity.
Via tenting with an exact-board plan persisted on an isolated PcbDoc after
save, close and reopen in Altium 26.11.1.5. The loaded script answered
`application.ping` as `.68` after the latest restart. An exact-document,
read-only `generic.query_objects` call returned live DbLib flags and current
footprint model names for R13 and U4 with no property diagnostics. Altium,
HTTP MCP port 14701 and TCP relay port 14700 are running at this handoff.
The latest read-only native audit accepted a 0.3-mil schematic grid and
reported 135 off-grid objects among 147 inspected components, with one
unloaded project sheet explicitly excluded from those counts.
The latest native read also returned 397 pins from the loaded DCDC sheet,
and a decimal-mil distance calculation retained all input fractions.
An isolated PCB copy passed fractional via-array placement and exact
save/close/reopen readback; the source board hash stayed unchanged.
The same disposable PCB now also passed fractional component alignment,
distribution and grid snapping with exact save/close/reopen readback.

On this date GitHub listed 61 direct forks of `salitronic/eda-agent` and
one child fork of `Rouniy/eda-agent` (`MOREmbedded`). `git ls-remote`
matched all 62 default-branch tips. An all-branch audit found 20 missing
cached branch refs, fetched them, and then matched all 117 live branch tips.
The API list and tip checks are recorded in `UPSTREAM-SYNC-2026-10-27.md`.

## Upstream merge and live runtime, 2026-10-27

`Rouniy/eda-agent/main` has the two-parent merge `f71a076` with
`upstream/main` at `9ee593ea0dce989bf3bfc97d0c982044ed41badb` as its
second parent. The merge is pushed to `origin/main`. The live Altium bridge
now answers version `.49` from the main directory, and the supervisor reports
`bridge_usable=true`. HTTP MCP port 14701 and the TCP relay port 14700 both
listen. The owner PcbDoc remains byte-identical at SHA256
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.
The post-merge Pascal fixes that led to `.49` are a follow-up commit; see
`RELEASE_VERIFICATION.md`. The MOREmbedded NPI, SDK, Altium 365 and library
tests pass. Bottom-side placement still needs native acceptance on a
disposable PcbDoc.

## Latest native integration, 2026-10-27

Script `.41` on Altium 26.11.1.5 added exact-board polygon-outline growth
with a dry-run preview and required bounds token for writes. On an isolated
PcbDoc copy, polygon index 64 grew by 1 mil on all four bounding edges.
Exact save/close/reopen retained the new bounds, while Altium renumbered
that polygon to index 50. Reusing the old index with its prior bounds was
refused before a write. The pour was not refilled; a separate repour is
needed. Three focused tests, Pascal lint/build and loaded script version
match passed. Generated bundle SHA256:
`B439E99C99D02DB2D28B02759A7B7B7A51730E485AF5938AA3A7C65AEE9E7189`.
The owner PcbDoc remained unchanged at SHA256
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.

Script `.40` on Altium 26.11.1.5 added an exact-board read of each
component pad's internal-plane connection settings. R62 pad 1 on the
owner PcbDoc returned its GND net, native connection style and five
relief/clearance parameters; the board has zero internal-plane layers.
A wrong-board path was refused and the owner file hash remained
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.
Four focused tests and Pascal lint/build pass. Generated bundle SHA256:
`5A959828AAEF5196B357A982A82CE99D60D138A6775A02C6809B6DEAD1B2F90E`.
An actual internal-plane connection still needs native acceptance.

Script `.39` on Altium 26.11.1.5 added an exact-board rigid-flex
inventory: board regions, split lines, bend lines and named layer stacks
with their copper layers. On the owner's PcbDoc it returned one region,
one rigid `Board Layer Stack` with Top Layer, Int1, Int2 and Bottom Layer,
and zero split or bend lines. A wrong-board read was refused. A board
with actual flex splits and bends remains to be checked natively. Two
focused tests and Pascal lint/build pass. Generated bundle SHA256:
`2F6905FB64F751FF340F84D0F670A0607F5D17A753A584B8FA71CF74ADDC42B1`.
The owner PcbDoc remained active with unchanged SHA256
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.

Script `.38` on Altium 26.11.1.5 added exact-board copper order listing,
relative insertion and movement. The list includes visible names and
canonical layer IDs, so a renamed `MidLayer1` is not mistaken for a free
ID. On an isolated PcbDoc copy, `MidLayer3` was inserted above `Int2`
and then moved below it; both orders survived exact save, close and
reopen. The moved layer was empty; moving populated copper layers still
needs native acceptance. Five focused tests and Pascal lint/build pass.
Generated bundle SHA256:
`CFF54CA6E92A2844C55A6AA433E7CA625C3E3C3B33AD3C934EEBA7F8DCAE3B9A`.
The owner PcbDoc was restored active and retained SHA256
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.

Script `.35` on Altium 26.11.1.5 added an exact-board stack-style edit with
old-style/layer-count preconditions and a default dry-run plan. On an
isolated PcbDoc copy, style 0 changed to 1 and remained 1 after exact
save, close and reopen; all 13 physical layers and their 70.0078-mil Z
span remained. A wrong-board write was refused. Four related tests and
Pascal lint/build pass. Generated bundle SHA256:
`33BF9B90CAD6C77805604894545CC9DF4DA2326C6DBE000E7722B7235E734B28`.
The owner's PcbDoc SHA256 remained
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.

`Rouniy/eda-agent/main` is the integration branch. Script `.34` on Altium
26.11.1.5 added exact-board impedance-profile layer reads and edits, with
profile and layer state tokens before writes. On an isolated PcbDoc copy,
Top Layer's enabled flag, width/gap locks, 4/6 mil width/gap, lower and
upper limits, plane clearance and solder-mask settings survived exact save,
close and reopen. Altium automatically changed an unspecified minimum
width from 0 to 4 mil after the first save; the tool reports the refreshed
value. Six related tests and Pascal lint/build pass. The generated bundle
SHA256 is `C6DC4FEA224DB2E62219900A7593D91E066101084D39EC8086DB10BF4D1DF74D`.
The owner PcbDoc was restored active with its SHA256 unchanged at
`F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.
The sibling `PLT-hw/tools/eda-agent/SHARED-PROJECTS.md` runbook referenced
by `AGENTS.md` is absent in this checkout; this native write followed the
user's explicit authorization and used an isolated document copy.

## Source integration, 2026-10-27

The `.26` source ports upstream's two placed-component STEP export APIs.
`pcb_export_component_model` uses the part assembly API and
`pcb_export_component_3d` uses the model API; both require an exact active
PcbDoc path and a new absolute `.step`/`.stp` target. Python verifies an
observed STEP header, size and SHA256. Two focused tests pass; Pascal
lint/build reports zero errors/warnings. Altium 26.11.1.5 loaded `.26`.
U1 on the owner's board exported a 704,493-byte part STEP and a
649,650-byte model STEP under `workspace/native-acceptance/step-exports`.
A wrong board path was refused. The board remained active, modified=false
and its SHA256 unchanged. The exported test files remain in that directory.

The `.25` source ports upstream's three PCB editor preference groups:
display, editing and routing. These are global Altium settings, read with an
exact active PcbDoc path. Writes use old-value preflight, default dry-run and
native readback. Three focused tests pass; Pascal lint/build reports zero
errors/warnings. Altium 26.11.1.5 loaded `.25`. On the owner's board,
show-pad-numbers, auto-pan and auto-via each toggled, read back, and were
restored to their original values. A wrong board path was refused. The
owner PcbDoc remained active, modified=false and SHA256 unchanged.

The `.24` source ports MOREmbedded's complete-footprint quarter-turns.
`lib_rotate_footprint` focuses an exact existing PcbLib, plans the object
counts by default, refuses unsupported primitives unless explicitly allowed,
and leaves saving to `app_save_document`. Three focused tests pass; Pascal
lint/build is clean and Altium 26.11.1.5 loaded `.24`. On the isolated
`BodyEdit_20261027.PcbLib` copy, AD_FE38's 580 objects rotated 90 degrees:
32 pads, 493 tracks, three arcs, 38 regions, 12 vias, one text and one 3D
body. Native pad verification found zero mismatches. After exact save and
close/reopen, pads 14, 38 and 10 retained their rotated coordinates and
90-degree rotations; the saved STEP model retained its 10-mil Z offset and
rotated about Z with the body. Owner PcbLib and PcbDoc hashes were unchanged.

The `.23` source ports MOREmbedded's `lib_set_3d_body`. It reads saved STEP
rotations from the exact PcbLib so a model Z-offset edit can retain them;
the tool requires an existing absolute library path, checks the live body
count, plans writes by default and verifies native results. Three focused
tests pass; Pascal lint/build has zero errors/warnings. Altium 26.11.1.5
loaded `.23`. On an isolated copy of the owner's 38-footprint library,
AD_FE38's STEP Z offset was changed from 0 to 10 mil, saved with
`app_save_document`, and parsed from disk as 10 mil with rotations still
90/0/360 degrees. Opacity read back as 0.7. A separate 50-mil overall-height
edit read back and was discarded on close. Owner PcbLib and PcbDoc hashes
were unchanged. The closed test copy remains under
`workspace/native-acceptance/BodyEdit_20261027.PcbLib`.

The `.22` source ports Altium's dominant PCB rule lookup and rule-scope
evaluation for component, pad and net objects. Both require an exact absolute
PcbDoc path and reject incomplete native replies. Two focused tests pass;
Pascal lint/build reports zero errors/warnings. Altium 26.11.1.5 loaded `.22`.
On the owner's 47-rule board, dominant-rule lookup for R62 returned native
rule data; unary and binary scope queries returned applicability flags. A
binary query lacking its second object and a mismatched board path were
refused. The board stayed active and unmodified; its SHA256 remained the
baseline below.

The `.21` source ports drill layer pair read, flag setting and pair addition.
Writes use exact PcbDoc identity and a full pair-count snapshot; flag writes
also compare the old layer IDs and flags. Three focused tests pass, Pascal
lint/build reports zero errors/warnings, and Altium 26.11.1.5 loaded `.21`
with zero cast errors. On a disposable two-layer PcbDoc, the drawing flag
changed from false to true and an independent read returned true. A duplicate
pair and wrong-board read were refused. On the same disposable board with
MidLayer1 added, a new TopLayer-MidLayer1 pair raised the count from one to
two and an independent read returned both spans. The owner board was restored active and
its SHA256 matched the baseline below. The disposable file remains at
`workspace/native-acceptance/DrillPairs_20261027.PcbDoc`: automatic command
review blocked its exact-path deletion, despite the test document being closed.

The `.20` source adds `app_save_document(file_path)` after the grid-save
investigation. Native code saves only the loaded document whose actual path
equals the caller's absolute path; Python requires an observed disk mtime
or size change before reporting `saved=true`. Nine related tests pass;
Pascal lint/build has zero errors/warnings. Altium 26.11.1.5 loaded `.20`
with zero cast errors. On a disposable PcbDoc, a 16.5-mil snap X was
written, the exact save reported a disk write, and closing/reopening the
file read back 16.5 mil. A nonexistent document path was refused. The
scratch file was closed and removed. The owner's PcbDoc SHA256 before and
after this exact-save acceptance was identical to the post-incident
baseline below (`F19A44DF...EC6FF76D`); it is active and modified=false.

The `.19` source ports upstream's `pcb_set_grids` for six writable grid
sizes and dot/line display, with exact PcbDoc targeting, validation of all
new values before mutation, old-state preflight, a dry-run plan and
readback. The Python reply marks changed settings `save_required=true`:
native grid changes remained in memory when the scratch PcbDoc was closed
without saving, even though `MarkDocDirtyByPath` ran and
`app_get_active_document.modified` reported false. Three grid-tool tests
pass; Pascal lint/build has zero errors/warnings. Altium 26.11.1.5
loaded `.19` with zero cast errors. On a disposable board, snap X changed
from 5 to 12.5 mil, track from 20 to 7.5 mil, component X followed snap,
and dot-grid became false; an independent read matched. A wrong board path
was refused. Exact `app_reload_document(save_before_close=true)` on a
separate disposable board preserved a 14.5-mil snap grid across reopen.
All scratch documents were closed and their files removed.

During the persistence investigation, one `app_save_all` call wrote two
documents, including the owner's `DC-DCmodule_DT11328.PcbDoc`, although
the active-document modified flag was false. That file's write time became
2026-10-27 12:28:19 local; its current length is 8,336,384 bytes and SHA256
is `F19A44DFBFC7D710E43B9C2D758C1F71E0471C857EB9D600DFBA45EFEC6FF76D`.
There is no pre-save hash, so content equivalence to the previous disk
revision is unverified. Use `app_save_document` for later exact-path
persistence checks; avoid broad Save All for this purpose.

The `.18` source ports upstream's batch `pcb_net_display` for connection
lines, loop removal, own net colour and jumper visibility. It requires an
exact PcbDoc; the native handler resolves every net and checks all four
old flags before any write. Python returns a dry-run plan by default and
verifies per-net readback after an explicit write. Six focused tests pass;
Pascal lint/build has zero errors/warnings. Altium 26.11.1.5 loaded
`.18` with zero cast errors. On disposable PCBs, a one-net connection-line
change read back independently; a two-net batch changed the other three
flags on both nets and read back `1010` per net. A missing net and a wrong
board path were refused. The disposable documents were closed with changes
discarded and their saved blank files removed. The owner's PCB is active
and unmodified. TCP 14700 and MCP 14701 listen.

The `.17` source ports upstream's `pcb_find_same_package` with an exact
PcbDoc path and native package comparisons. It groups even parts without
a package hash and reports comparison errors rather than silently skipping
them. Python validates board identity and result completeness. Eight
focused tests pass and Pascal lint/build has zero errors/warnings. Altium
26.11.1.5 loaded/bundled `.17` with zero cast errors. The disposable
PcbDoc returned zero groups, refused a missing component and refused a
different board path; it was closed and its file removed. A read-only run
on the owner's active, unmodified PCB examined 147 parts, found 14 groups
with zero native comparison errors; querying R62 separately found 51
matching parts, consistent with its 52-part group. The board remained
unmodified. Package equality on a deliberately unhashed disposable part
has not yet been accepted natively.

The `.16` source ports upstream's xSignal read/create/delete family with
explicit PcbDoc paths, native path checks, and an expected pair count for
writes. The Python layer verifies complete readback and the count delta.
28 focused tests pass; Pascal lint/build reports zero errors/warnings.
Altium 26.11.1.5 loaded/bundled `.16` with zero cast errors. A disposable
PcbDoc reported zero xSignals; nonexistent pins were refused, a stale count
was refused, and an empty delete left the count at zero. The disposable
document was closed and its saved file removed. The original PCB is active
and unmodified. The populated-board write was accepted on 2026-10-28
as recorded above. TCP 14700 and MCP 14701
listen.

The `.14` source integrates MOREmbedded's fab-output comparison as an
exact-board check. `pcb_get_fab_board_facts` reads the focused PcbDoc path,
copper layer count, outline size and all drilled pads/vias in one native
snapshot, without a 5000-pad response window. `pcb_check_fab_output`
parses Gerber/Excellon with the optional gerbonara extra and refuses an
automatic pass if the board identity or any required comparison is missing.
23 focused parser/tool tests pass; Pascal lint/build has zero errors and
warnings. Altium 26.11.1.5 loaded/bundled `.14` with zero cast errors.
On disposable `workspace/native-acceptance/FabFacts-20261027.PcbDoc`, native
readback reported the exact path, 2 copper layers, 152.4 by 101.6 mm and
zero holes. A different board path was refused. The disposable document was
closed with changes discarded; its file does not exist; the owner's PCB is
active and unmodified. A full generated fab package comparison and a large
board with more than 5000 drilled pads still need native acceptance. MCP
14701 and TCP 14700 listen.

The `.13` source adds the missing read-only generic `AutoSize` getter for
ports and preflights writes on other object types. The earlier `.12` native
check used the isolated `workspace/native-acceptance/PlacementStyle-20261027.SchDoc`
with `add_to_project=false`: `sch_place_port` returned font 1, width 400 mil
and AutoSize false; `obj_query` independently read font 1 and width 400.
The AutoSize field was empty on that read, which led to this getter fix.
`sch_place_text_frame` returned font 1 and a second query read
`LINE_A`/`LINE_B` separated by CRLF. After Altium loaded `.13`, `app_ping`
reported loaded/bundled `.13`, `version_match=true`, Altium `26.11.1.5`
and zero cast errors; a fresh ePort query returned `AutoSize="false"` along
with font 1 and width 400. A power port written with font 1 read back with
font 1. The disposable sheet was closed and its saved blank file removed;
the original PCB is active again and reports `modified=false`. TCP 14700 and
14701 listen. Sheet-entry/font inheritance and multipart placement still
need native acceptance.

The `.12` source ports the remaining `mooreaa` placement styling: new ports,
power ports, text frames and sheet entries use an explicit `font_id` or infer
one from the sheet; a positive port `width` disables AutoSize before writing
the width, with native readback in the reply; text-frame `\\n` and line breaks
are normalized for Altium. A `Value` stamp now updates an existing first-level
Value parameter alongside Comment, and newly created parameters are hidden
at the component location. 70 related tests pass, three FPC-dependent tests
skip, and Pascal lint/build passes. The HTTP child was restarted through its
supervisor and Altium loaded `.12`: `app_ping` reports loaded/bundled `.12`,
`version_match=true`, Altium `26.11.1.5` and zero cast errors. TCP 14700 and
14701 listen. Native disposable-sheet acceptance remains pending.

The `.11` source ports the corrected `mooreaa` multipart placement and tidy
step. `sch_place_components` accepts `part_id` per part and a `tidy` switch
(on by default). The native handler writes the requested part before and
after adding the component to the sheet, reports a post-placement mismatch
in `part_issues`, and leaves that placement visible and counted. Tidy links
the source library, hides inherited model parameters and adopts the sheet's
designator font; it reports each result in `tidied`. The Python placement
encoder now sanitizes designator and footprint fields as well. 65 related
tests pass, three FPC-dependent tests skip, and Pascal lint/build passes.
The HTTP child was restarted through its supervisor and Altium loaded `.11`:
`app_ping` reports loaded/bundled `.11`, `version_match=true`, Altium
`26.11.1.5` and zero cast errors. TCP 14700 and 14701 listen. Native
multipart-sheet acceptance is pending.

The `.10` source routes single/bulk `Footprint` stamps through the verified
model chooser before any fallback rename. A component that already carries
the requested model switches to it rather than duplicating its name and
keeping the previous model's pin map. A failed choice is counted separately.
Bulk parameter stamping now refuses an explicitly named sheet that is not
loaded rather than falling through to the focused document. Pascal lint/build
and 52 related tests pass (three FPC-dependent tests skipped). The HTTP child
was restarted by its supervisor and Altium loaded `.10`: `app_ping` reports
loaded/bundled `.10`, `version_match=true`, Altium `26.11.1.5` and zero cast
errors. TCP 14700 and 14701 listen. Native sheet acceptance remains pending.

The `.9` source ports the `mooreaa` footprint-model chooser to single and
bulk schematic placement. A requested footprint is matched against the
symbol's own PCB models; the helper clears other current flags, sets the
requested one, verifies every flag and restores the originals if it fails.
Placement reports a missing or unapplied model without silently renaming
another one. Pascal lint/build and focused source tests pass. The remaining
model-name stamp handlers were subsequently updated in `.10`; other relink
paths remain under review. Live `.9` loaded with `version_match=true` on
Altium `26.11.1.5`, and native disposable-sheet checks remain pending.

The `.8` source adds `mooreaa`'s placed-component `DisplayMode`,
`DisplayModeCount` and current `FootprintPinMap` property handling. Reads and
writes are gated to `eSchComponent`; mode writes check the available range and
read back, and pin-map writes require an old-map read, check the requested
entries after Altium's merge and restore the old map on failure. The related
source suite passed 22 tests; three FPC-dependent tests were skipped because
`fpc` is unavailable here. Pascal lint/build passes. The later native
pin-map and display-mode persistence checks are recorded at the top of
this handoff.

The `.7` source ports `mooreaa`'s corrected live-pin filter. Schematic ePin
queries omit hidden copies from other parts and display modes unless the
filter explicitly names `OwnerPart`. `sch_fix_port_crossrefs` reads these pins
and includes them in the reviewed plan digest. Pascal lint also exposed an
existing missing local `Pin` declaration in `SetSchProperty`; it is fixed.
The focused CrossRef suite has 21 passing tests and Pascal lint/build passes.
The HTTP child was restarted through its supervisor and Altium loaded `.7`:
`app_ping` reports loaded/bundled `.7`, `version_match=true`, on Altium
`26.11.1.5`, with zero cast errors. TCP 14700 and 14701 listen. The active
document is a PCB and the project schematic sheets are not loaded, so native
multipart-sheet acceptance is pending. A no-target ePin query returned the
expected `Document not loaded` refusal without affecting the bridge.

The `.6` source ports `mooreaa`'s port cross-reference planner and exposes
`sch_fix_port_crossrefs` with dry run by default. Applying a plan requires
an exact sheet path, a matching plan SHA-256 and `confirm=true`; each write
uses the old CrossRef position and is read back. The native property reader
adds read-only `ConnectedEnd`. At that version direct pin fallback was disabled;
geometry and Altium's ConnectedEnd remained available, and ambiguous ports
were not moved.
Focused tests and Pascal lint/build pass. The existing HTTP child was
restarted by its supervisor, then Altium loaded `.6`: `app_ping` reports
loaded/bundled `.6`, `version_match=true`, on Altium `26.11.1.5`. TCP 14701
advertises 627 tools including the CrossRef tool, and TCP 14700 still listens.
A relative-path call was refused before document access. Native
disposable-sheet read/write acceptance remains pending.

The `.5` source guards `Obj.FontId` in the generic schematic reader and
writer by object type. Sheet and harness entries use typed `TextFontId`.
This ports the `mooreaa` AD25 crash fix as refined by the latest upstream.
Focused tests and Pascal lint/build pass. Altium reloaded `.5` from `main`;
restart status reported `running`, script `.5`, Altium `26.11.1.5` and zero
cast errors. A native entry read on a disposable sheet remains pending.

The `.4` source adds `pcb_pours_at` and `pcb_board_options` from upstream
`ce53d6e`. The first reports the actual board file and accepts an expected
file; the second requires that exact file when setting the name template and
checks readback. Python tests and Pascal lint/build pass. Native board
acceptance remains pending. The existing HTTP child was relaunched by its
supervisor and Altium reloaded `.4`; `app_ping` reports loaded/bundled `.4`,
`version_match=true`, on Altium `26.11.1.5`. TCP 14701 advertises 626 tools,
including both new commands, while TCP 14700 still listens. Direct native
calls with invalid parameters reached both handlers and were refused before
accessing a board; a valid disposable-board read/write has not yet run.

The `.3` source now restores the native footprint-primitives reader that was
missing behind the registered Python tool. It includes live 3D body metadata
and a focused-library identity check; embedded STEP extraction can filter by
the model files attached to a named footprint. Pascal lint/build and focused
source tests pass. The existing MCP supervisor reloaded its HTTP child from
`main`, then Altium loaded `.3`: `app_ping` reports both versions `.3` with
`version_match=true` on Altium `26.11.1.5`. TCP 14701 lists 624 tools and TCP
14700 still listens. A no-target call reached the native handler and returned
`footprint_name is required`, then ping remained healthy. Reading a real
disposable PcbLib and comparing its body records is still pending.

The `ed4ef59` library block is partially integrated: embedded model extraction
now checks Altium's stored checksum before writing the original bytes, and
`lib_build_integrated_library` can create/open, populate, save and compile an
exact-path LibPkg. It claims a build only when a fresh, nonempty IntLib is
observed. Source tests pass; no native build or owner-library write was run.
After restarting the existing HTTP child through its supervisor, TCP 14701
advertises 624 tools, including this builder; `app_ping` reports both script
versions `2026.10.27.2` and `version_match=true`. TCP 14700 is listening.

The `main` source now includes SDK coverage and NPI phase gates from
`MOREmbedded/main`, a periodic datasheet reminder from upstream, and a
schematic generic edit response that no longer calls a dirty document saved.
It now also reads the board's impedance profiles from Altium's layer stack.
The `.2` build was loaded from `main`; the HTTP MCP endpoint on TCP 14701
advertises 623 tools including `pcb_get_impedance_profiles`, and `app_ping`
reports loaded/bundled `2026.10.27.2`, `version_match=true`, on Altium
`26.11.1.5`. Native execution of this board read is still pending.
The reviewed upstream and fork tips, true merge bases and remaining merge
work are recorded in `docs/UPSTREAM-SYNC-2026-10-27.md`. The bridge was
reloaded from the same `main` directory. Streamable HTTP on TCP 14701 now
advertises 622 tools, including all three NPI tools; `app_ping` reports
loaded and bundled script `2026.10.27.1`, `version_match=true`, and Altium
`26.11.1.5`. The existing TCP 14700 relay still listens. Focused integration,
documentation and version tests passed; native acceptance of new write paths
remains open.

## Source integration and runtime, 2026-10-26

`Rouniy/eda-agent/main` is the source of truth. The source script is now
`2026.10.26.16`; it adds fractional-mil PCB stitching vias, circular board
outlines, decimal-mil board geometry reads and arc placement, polygon
pour settings, and named board regions with decimal-mil placement, then
regenerates `Altium_MCP.pas`. Focused Python tests and Pascal lint pass.
The remaining fork candidates are listed in
`docs/FORK-INTEGRATION-AUDIT-2026-10-26.md`.

The previously hung X2 (`PID 23836`) was terminated at the owner's request.
Altium was restarted twice, and the bridge was subsequently reloaded from
`main`; `app_ping` confirms loaded and bundled script `2026.10.26.16`,
`version_match=true`, and Altium `26.11.1.5`. TCP 14701
answers MCP and the existing Codex message relay listens on TCP 14700;
its loopback health check reports `ready`. Native acceptance of the new
stitching-via Pascal change and the newer geometry, polygon and region
changes is still pending. Altium has updated to `26.11.1.5`. The separate
`eda-agent-large-integration` worktree is used for conflict resolution,
not as a second runtime.

## Single-main MCP deployment, 2026-10-26 20:49 +02:00

The local `main` now contains the selected fork integrations, the PCB
`pcb_query_region` Owner alias repair, and the previously uncommitted bridge
recovery/PDF serialization fixes. The Python HTTP MCP supervisor, server, and
dashboard were restarted from `D:\ai\eda-agent`. After `app_detach` stopped the
old worker without saving documents, `StartMCPServer` was launched directly
from this checkout's `scripts/altium/Altium_API.PrjScr`; no script copy was
installed. `app_ping` over TCP 14701 reported 580 tools, loaded and bundled
script `2026.10.26.2`, `version_match=true`, Altium `26.10.1.5`.

The previous `eda-agent-large-integration` supervisor and its HTTP/dashboard
children were stopped. TCP 14700 remains without a listener. This live check
establishes startup and version agreement, not native acceptance of every new
tool. The fork audit and its deferred features are in
`docs/FORK-INTEGRATION-AUDIT-2026-10-26.md`.

## Radxa C200 session exit and recovery, 2026-10-21 03:43

Altium exited during the native 3-D pass on `radxa_c200_v1.11.PcbDoc` after
`generic.switch_view(mode=3d)` returned successfully. No matching Windows
Application Error event was found in the checked window, so whether this was
a crash or another exit path is unknown. Altium was relaunched, the bundled
script started in the single live instance, and the session-restored LimeSDR
PDF stage plus the Fastino and RaToPUS free PCB documents were closed without
saving. Final `app_ping` returned `2026.10.20.4`; only the owner's nine projects
and empty Free Documents remained, with no dialog and watchdog usable. The
corpus runner should skip the Radxa C200 native 3-D render pending diagnosis.

## Antenna_base PDF modal and script recovery, 2026-10-21 02:44

During a staged color schematic PDF export of Antenna_base, Altium displayed
an `Error` modal whose OCR text included `Index was outside the bounds of the
array`. The bridge activity stopped after successfully focusing
`01_powersupply.SchDoc`, before `project.run_outjob` returned. The modal was
gone by inspection, but the script remained unresponsive with its MCP form
disabled. `Ctrl+F3` stopped that script, and the bundled `StartMCPServer` was
relaunched in the same X2 process. The Antenna_base stage project was closed
with `save=false`; no corpus project remained. Final `app_ping` reported script
`2026.10.20.4`, and the watchdog reported `bridge_usable=true`. The native
array-index error is not fixed; the corpus runner should record this PDF as a
failure or skip it rather than repeatedly printing the same stage.

The corpus operator correlated the same `STAGING_CLOSE_FAILED` and native
array-index modal with LimeSDR USB, Mini, and Micro PDF exports, and reported
one 300-second PDF handler timeout on gpa-zynq-module. This is a repeated
native PDF path failure, not a single Antenna_base file. The monitor now
recognises a disabled MCP script form after the modal has cleared. After two
failed pings and only when there is one ready X2, no dialog, and no active
native progress marker, it sends `Ctrl+F3` and relaunches the script. Attempts
are bounded, including a separate cooldown for stop attempts. This recovery
path has unit checks; a real recurrence remains to qualify it. The 3-D corpus
pass was active and healthy after monitor deployment, so its current board
was left open for the operator to close normally.

## Radxa 3-D crash and recovery, 2026-10-21 02:32

The visible X2.EXE process crashed at 02:32:33 while the corpus pass viewed
`radxa_cm3s_io_board_V1510.PcbDoc` in 3-D. The last completed native call was
`generic.switch_view(mode=3d)`; this does not establish which later operation
faulted. Windows Application Error 1000 again named `coreclr.dll` 8.0.1525,
exception `0xc0000005`, now at offset `0x26b0d6`. Altium was relaunched,
restoring the owner's projects. The bundled `StartMCPServer` was launched in
the single live instance. A restored LimeSDR PDF stage project and two corpus
free PCB documents were closed without saving. Final `app_ping` returned script
`2026.10.20.4`; open projects were the owner's nine plus empty Free Documents,
no corpus document remained, and the watchdog reported `bridge_usable=true`.

## Corpus crash and bridge recovery, 2026-10-21 01:12

The visible X2.EXE process crashed at 01:12:29 while the corpus pass was
running. Windows Application Error 1000 named `coreclr.dll` 8.0.1525.16413,
exception `0xc0000005`, offset `0x11caf5`; the last completed bridge activity
was `application.get_active_document` on a newae corpus PCB. No script error
dialog remained. A previous, editorless X2 process had survived. It made the
monitor think Altium was running, and the URI script launcher initially
attached to that stale process. The script was detached there and the stale
process exited after a normal WM_CLOSE. A fresh Altium session restored the
owner projects. `StartMCPServer` was selected in its bundled script project
through File > Run Script. `Stabilizer_Pounder.PrjPCB` and two detached corpus
PcbDocs were closed without saving. Final inventory: the owner's nine projects
plus Free Documents (empty), no corpus project; `app_ping` script
`2026.10.20.4`, Altium `26.10.1.5`; visible editor maximized. The 20-second
monitor reports `bridge_usable=true`.

The monitor now refuses URI script launches when more than one X2 process is
present, because the URI handler does not target a PID. It also treats an
editorless status form as unusable instead of reporting a healthy bridge.
This prevents a false recovery, but a repeated native crash with a surviving
X2 process still needs an operator to close the stale process and start the
script in the correct instance. The `coreclr.dll` crash cause is unproven.

## Overnight PDF bridge recovery, 2026-10-21

The corpus pass reported repeated `app_ping` timeouts and two
`STAGING_CLOSE_FAILED` PDF exports. At 00:05 the activity log recorded a
successful `project.run_outjob` followed immediately by `_session_end`; no
error dialog was visible during inspection. The exact native cause of the
script form closing remains unproven. The HTTP PDF wrapper could interleave
two exports: both temporary projects were open during a later mmWave Radar
print, and focus changes could interfere with closing the named stage.
`proj_export_schematic_pdf` now serializes its entire open, focus, print,
close, and cleanup sequence within one MCP server process. This does not
protect against an independent second server process using Altium at the
same time.

The existing watchdog now checks every 20 seconds, distinguishes the live
editor from a windowless old X2 process, and can relaunch `StartMCPServer`
when the script form has exited while the editor remains ready. It still
holds off while a native command is active and will not blindly relaunch
when the form is present or a modal is open. Recovery attempts are bounded
per Altium process. See `altium-mcp-supervisor-status.json` in the bridge
workspace for its current state. The wider corpus pass is still the native
acceptance test for this repair.

## Silent schematic PDF export, 2026-10-20

Direct `proj_export_pdf` and `proj_export_image(format="pdf")` ran
`WorkspaceManager:Print`, which opened Preview SCH and wrote no file. Both
Python wrappers now return `PREVIEW_NOT_SILENT` without invoking that process.
New `proj_export_schematic_pdf(project_path, output_path)` copies only logical
SchDoc members into a temporary project below
`D:\AI\ALTIUM\testprojects\_screens\_pdf_stage`, adds a tested PDF OutJob
there, publishes with `PublishToPDF` / `DisableDialog`, verifies the expected
PDF and its pages, closes the staged project without saving, removes the stage,
and atomically places the result at `output_path` under `_screens`. It returns
the page order from PDF sheet bookmarks. The staged OutJob explicitly sets
`PageOptions1` `PrintKind=0` (Color), and staging fails if that option is absent
or changed. This setting belongs to the OutJob, independently of the printer's
last preset. External SchDoc references outside the
source project directory are rejected until staging them is qualified.

Native pilot on the open antmicro Apalis Smart Vision Baseboard project yielded
`apalis-native-schematics.pdf` (2,265,636 bytes), nine pages for nine SchDocs in
the source project's document order, with no modal. A prior run with the full
project copy and one with only the nine schematic documents had identical
extracted page text. The original project file retained its 2026-10-19 mtime,
no Project Outputs folder appeared in the source project, the staged project
was removed, and the original `Power-Supply.SchDoc` was restored as the active
document. The HTTP MCP was restarted to load the Python tool; Altium itself was
not restarted. This qualifies one project and does not claim that every corpus
project's hierarchy or print settings are compatible.
All nine pilot PDF pages contain non-gray RGB graphics commands, confirming
that the Color setting was applied in this live export.

## Stabilizer Pounder track-read crash and recovery, 2026-10-20

At 16:30 the X-Office operator reported `pcb_get_tracks {"limit":1}` crashing
on `sinara\pounder\pcb\Stabilizer_Pounder.PcbDoc`, an ordinary PCB rather
than a panel. The modal was `TShowException` with a `ScriptingSystem.DLL`
read access violation at `00000001CE4EF32B`. It was dismissed with Escape,
without sending a report. The script did not answer afterward, so Altium was
closed normally and relaunched. `StartMCPServer` was launched, and the corpus
project was closed with `proj_close(save=false)`, discarding its loaded PCB,
schematic and project state. Final checks: the owner's nine projects plus Free
Documents, no modal, `app_ping` successful with script `2026.10.20.4` and
Altium `26.10.1.5`. This ordinary-board failure disproves a panel-only
trigger. The operator is skipping `pcb_get_tracks` on the remaining corpus
boards; the exact failing native operation remains unknown.

## Fastino panel track-read crash and recovery, 2026-10-20

The X-Office operator reported a `pcb_get_tracks {"limit":1}` crash at 16:10
on the second Fastino PCB, `Panel\Panel_Fastino.PcbDoc`. The first Fastino PCB
had read successfully; panel outline, components (zero), nets (zero), layer
stackup, design rules, and used layers completed before the failing tracks
call. Altium showed `TShowException`, `ScriptingSystem.DLL` read access
violation at `00000001CF49F32B`. Escape dismissed the error without sending a
report, but `app_ping` stayed unresponsive. Altium was closed normally. Its
Unsaved Changes dialog named `Fastino.PCBDOC`; `Don’t Save` was invoked via UI
Automation, and Altium exited. After relaunch, a progress marker from the old
process prevented the keepalive from restarting the script. That stale marker
was removed and `StartMCPServer` launched once. The Fastino project then closed
with `proj_close(save=false)`, discarding the two PCB documents, its loaded
schematic, and project state. Final `proj_list_open` shows the owner's nine
projects plus Free Documents, `app_ping` matches script `2026.10.20.4`, and no
dialog is open.

The monitor now ignores progress markers older than the current Altium process
start, preventing this stale-marker recovery failure. Three monitor tests pass;
the restarted monitor reports MCP, script, and bridge healthy. The matching
`...F32B` suffix across crashes is consistent with the same faulting native
ScriptingSystem instruction after DLL relocation, but it does not identify a
single DelphiScript helper. All four failing handlers use native PCB object
iteration or primitive access; `pcb_get_tracks` does not read the layer stack
or board outline. The exact failing operation on the panel remains unknown.

## One-minute bridge and crash monitor, 2026-10-20

The existing `scripts/keep-altium-mcp.py` supervisor now checks every 60 seconds
and publishes its last result atomically to
`<workspace>\altium-mcp-supervisor-status.json`.
It records MCP listener/protocol health, Altium PID, whether a native command is
active, script responsiveness when it is safe to ping, overall bridge usability,
and the full open-dialog diagnostic. It logs a newly observed dialog once and
never dismisses it. The supervisor was restarted with the final code at 15:25
local time as PID 46400; its first status reported the MCP protocol healthy but
the bridge unusable because Altium is blocked by an `Error` dialog:
`ScriptingSystem.DLL` read access violation at `00000001CDCDF32B`.
The last completed native activity before the crash was `pcb.get_design_rules`
at 15:19:38 on the OHWR VME ADC 250k 16b 36ch board; a native progress marker
from that second remains. The X-Office operator identified the failing next
tool as `pcb_get_fab_stats` on `ADC_CARD.PCBDOC`. At their request, the error
dialog was dismissed with Escape without sending a report. The script remained
unresponsive and a script-only restart timed out. Altium was closed normally
and relaunched; its session restored the owner's nine projects plus the VME ADC
project. `proj_close(save=false)` then closed VME ADC, discarding its PCB,
schematic, and project changes. Final `proj_list_open` shows exactly the nine
owner projects plus Free Documents; `app_ping` reports script 2026.10.20.4 and
Altium 26.10.1.5, with no modal dialogs.

## RaToPUS component-read crash and recovery, 2026-10-20

`pcb_get_components` on the corpus RaToPUS-Control PCB raised a modal
`ScriptingSystem.DLL` access violation after the bridge's `pcb.get_board_outline`
read succeeded. The component reader walked every footprint's child primitives
with a nested group iterator to calculate `placement_bbox`. Native script
version `2026.10.20.4` removes that walk. The response retains `placement_bbox`
for schema compatibility, but it now equals the component's visual `bbox` and
sets `placement_bbox_fallback=true` because text may be included. The Python
placement planner rejects this flagged geometry instead of using it for moves.
On the same RaToPUS-Control PcbDoc, the patched native read returned 134
components without a dialog; the project was then closed with `save=false`.
Altium was left with the owner's nine projects and 13 loaded documents, none
reported modified, focused on `tl-hub` PCB. `app_ping` matched loaded and bundled
script version `2026.10.20.4`. The earlier `pcb_get_board_statistics` crash
remains a separate unresolved native issue.

## US-Plus-CPM PCB statistics crash and recovery, 2026-10-20

At 00:30:08 the last completed native command was `project.get_board_info`
for `D:\AI\ALTIUM\testprojects\boards-corpus\antmicro\ultrascale-plus-processing-module\PCB\PCB.PcbDoc`.
The next reported call was `pcb_get_board_statistics`; Altium raised a
`TShowException` access violation in `ScriptingSystem.DLL` (read of -1), with
no native response or completed activity entry. The crash dialog was captured
at `D:\AI\ALTIUM\testprojects\_screens\US-Plus-CPM-statistics-crash-20261020.png`
and closed with WM_CLOSE, without invoking `Send and Close` (which offers to
send a report). The worker was stopped and relaunched; `app_ping` again reports
26.10.1.5 and script 2026.10.19.1. The only corpus project open was US-Plus-CPM;
it was closed with `save=false`, and the original nine projects remained.
`tl-hub` PCB focus was restored. No document was reported modified before
corpus closure.

An isolated read pass on that board succeeded for `proj_get_board_info`,
`pcb_get_layer_stackup` (6 layers), `pcb_get_nets` (415),
`pcb_get_board_outline` (29 points), `pcb_get_components` (274), and
`pcb_get_tracks` (11,262 routed primitives, limit 1). These are single-call
observations, not a blanket guarantee for other tools. No second
`pcb_get_board_statistics` call was made; the precise failing native statement
is unisolated. The stats handler combines an all-object iterator, raw track
casts/coordinates, outline rebuild, and V7 stack traversal. The separately
successful outline and stackup reads narrow the suspect area but do not
identify it. Avoid `pcb_get_board_statistics` on US-Plus-CPM until an
instrumented native test on a disposable copy identifies and fixes the fault.

## ERC deployment and project restoration, 2026-10-20

After the X-Office coordinator's `ready for restart`, the bridge detached
without saving (`_session_end` at 00:05:14), and Altium was closed normally.
Altium 26.10.1.5 was restarted with script `2026.10.19.1`; the HTTP MCP on
port 14701 was restarted separately to load the Python ERC argument schema.
`app_ping` reports matching loaded/bundled versions. `proj_run_erc` with the
explicit `tl-tx-booster-cbp.PrjPcb` path returned 12 violations and
`proj_get_erc_violations` returned 12 (5 requested); `proj_get_messages`
also returned 12. The focused document remained `tl-hub` PCB, demonstrating
the exact-path ERC calls did not follow focus. Nine projects are open:
the seven requested design projects and both Altium_API script projects.
The 13 previously loaded design documents were restored; no document reported
modified. `Free Documents` is empty. Both TCP 14700 and 14701 listen on
`0.0.0.0`. The pre-restart project/document snapshot is at
`D:\AI\ALTIUM\testprojects\_screens\altium-restart-snapshot-20261020.json`.
The combined native source SHA-256 is
`3D04C48C9FC2CC20AE96902FF11B8F6AFF132DE09F9A6CE775E52038E8E1E21E`.

The first URI launch created an extra Altium process because startup update
prompts were open. The prompts were declined/closed, that extra process exited,
and a single Altium process remained. An autonomous supervisor briefly started
the correct native script; a subsequent bridge-restart attempt stopped it.
`app_attach` then started the stable final session. No CAD save or discard
was requested.

## ERC targeting and DRC investigation, 2026-10-19

On the live 26.10.1.5 Altium instance, activating the tl-tx-booster-cbp
schematic did not consistently focus its project: `proj_get_focused` returned
either a different project or `Free Documents`. The old `proj_run_erc` and
`proj_get_erc_violations` both used `DM_FocusedProject`, explaining the empty
or wrong-project results despite target ERC messages. Source now accepts an
explicit `project_path`, compiles that project, returns its path/count/action,
and refuses Free Documents. The Python tools require native script
`2026.10.19.1` before using this behavior. The 2026-10-20 deployment and
native verification are recorded above.

The target PCB screenshot saved at
`D:\AI\ALTIUM\testprojects\_screens\tl-tx-booster-drc-state-20261019.png`
showed `Idle state - ready for command`, with no Place Line operation active.
`PCB:DesignRuleCheck` is the static Tools menu process; Place Line uses the
distinct `PCB:ManualRoute` process. A live menu click did not open a DRC dialog
before another operator changed focus, so the transient Place Line report is
unexplained. Altium's documented batch flow is Tools > Design Rule Check,
Design Rule Checker dialog, Run Design Rule Check button. The native DRC
tool's report confirmation assumes a `.DRC` file beside the board, while
Altium documents configurable HTML/TXT/XML output paths; that confirmation
is not reliable for every configured report format.

## Focus-free menu follow-up, 2026-10-17

`app_list_panels` no longer raises `KeyError: holder_class`: it returns the
actual `button_hwnd` and `content` fields from `ui.panels.list_open`. The
network MCP was restarted and a live no-focus call returned `ok=true` with
the open Messages panel. The installed RCS parser remains a static catalog.
Altium's documented `IGUIManager` exposes lookup of a known process launcher
and panel, but no documented enumeration of the merged runtime menu tree.
The existing accessibility reader sees submenu items only after opening that
submenu, which requires clicks and focus. A complete, focus-free
`include_runtime` or View|Panels catalog remains unqualified.

## Read-only installed resource catalog, 2026-10-17

Python MCP adds `app_dump_menu_tree`, `app_list_panel_catalog`, and
`app_read_resource_file`. They parse the running Altium installation's
`System/*.rcs` text without focusing or clicking the UI. The menu tool resolves
static Tree/TreeCopy/Link entries to PL processes, parameters and shortcuts.
The panel catalog reports only launchers discoverable in factory RCS files;
Altium's `View|Panels` list is generated dynamically, so this is not a complete
live catalog, and RCS does not establish the default dock or editor filter.
User customisations and loaded extensions are not reflected in the static
menu output. The Python MCP on TCP 14701 was restarted from this worktree;
network discovery listed 579 tools including all three additions. Live calls
returned 572 factory PCB menu entries and 22 static panel launchers. Thirty-three
focused parser/toolset tests passed. The loaded native DelphiScript was not
replaced.

## PCB layer visibility, 2026-10-16

`pcb_set_layer_visibility` now uses Altium's `Pcb:DocumentPreferences`
process and a PCB redraw, following Altium's published `pcblayer.pas` example.
The old `Board.LayerIsDisplayed` assignment changed API readback but left the
editor canvas unchanged. Source build/lint passed with zero errors or warnings.
On the open `modem-stm32-2trx-lr2021.PcbDoc` in Altium 26.10.1.5, loaded
script `2026.10.16.12` hid `TOP-L01` and reported its visibility changed; the
document remained `modified=false`. The HTTP MCP on TCP 14701 was restarted
separately. A screenshot changed substantially, but the owner later said they
were independently hiding other layers at the same time. That visual evidence
cannot isolate this command's effect, and one-layer visual acceptance remains
open. The board was reloaded from its clean saved state to restore visibility;
this also reset the owner's unsaved view choices. The active PCB then changed
to `vd-tx-imod-QPA2237.PcbDoc`, so no further toggles were attempted.

## Coordinator 3-D/2-D API follow-up, 2026-10-16

`pcb_3d_capture` now defaults to `D:\shared\xo-altium\compare\` and routes
relative output paths there; it returns the absolute PNG path and pixel size.
`pcb_3d_set_view` accepts integer angles and zoom factors in 0.25..4, reports
the nearest 30-degree/2x step applied, and skips a repeated request in the
same MCP process. Its cached view is invalidated by `pcb_3d_center`; external
mouse camera movements cannot be detected because camera readback is absent.
`pcb_render_2d` accepts spaced Altium layer names, defaults to the whole-board
bbox, and reports `rect_mils` and `mils_per_pixel`. Live tests used the focused
disposable board and wrote only to `D:\shared\xo-altium\compare\`.
`pcb_select` accepts `designators` or `net_name` and returns a read-only
`target_bbox_mils` while clearly reporting `selected=false`; native component
and net selection remain unqualified. The documented `SetState_Selected(True)`
method was tried on FD4 and failed readback exactly like the property setter,
so the experiment was reverted. The board remained `modified=false`.

## 3-D view controls, 2026-10-16

Native script `2026.10.16.11` is loaded in Altium 26.10.1.5. The new
`pcb_3d_center` shows the focused PcbDoc in 3-D and uses the verified
`PCB:Zoom Action=Board` process to center and fit it without resetting the
view angle. `pcb_3d_set_view` shows 3-D, resets to top, applies 30-degree
keyboard rotation steps, fits the board, then applies 0.25/0.5/1/2/4 zoom
relative to the fit. Its pointer anchor is the actual editor canvas center,
which on this host is on the second monitor. `pcb_3d_capture` and `pcb_select`
also request 3-D before operating. A live call set 30/30/1, centered, and
captured `D:\shared\xo-altium\board-3d-center-final.png`; the board was
visually centered and `modified=false`. The camera angles and zoom are
requested shortcut controls, since no absolute camera readback is available.
PCB component selection still fails native selection readback and remains open.

## Main branch handoff, 2026-10-16

Follow-up: Python MCP now includes `pcb_render_2d` for exact mil-coordinate
rectangles and explicit layer lists. On the disposable working board it wrote
an 800x2160 PNG of the full region and a 500x500 `TopOverlay`-only crop;
both were inspected, and the cropped image contained only the requested
silkscreen layer. The network MCP was restarted from `main` and listed 574
tools including `pcb_render_2d`; `app_ping` matched loaded and bundled native
script `2026.10.16.3`. The local raster derives from Altium geometry and
does not claim pixel identity with Altium's editor. The 3-D camera and PCB
native selection limitations below remain open.

`app_attach` now starts the local bundled `StartMCPServer` worker if it was
stopped by `app_detach`. A live network detach/attach/ping sequence succeeded:
the attach response reported `worker_launch_requested=true`, a second attach
reported false, and the focused test PcbDoc remained `modified=false`.

The owner authorized discarding changes to the disposable Altium test project
and restarting components needed for native acceptance. The source changes were
committed to `main`. A follow-up fix removed `SaveAllDirty` from the native
`application.stop_server` dispatch: detach now stops the pump without saving
documents. The 10-minute detach hint now describes the timer pump accurately.
The combined script rebuilt with zero lint errors or warnings; 76 relevant
Python tests passed. Native reload and acceptance are recorded below.

Native follow-up: `application.reload_document` with `discard_changes=true`
reopened the disposable `vd-tx-imod-QPA2237.PcbDoc` from disk. The script was
relaunched from `main`; `application.ping` confirmed `2026.10.16.3` on Altium
`26.10.1.5`. `pcb.select_component` reached the requested board but returned
`SELECTION_FAILED` for FD4, C126 and C128. Separate `generic.query_objects`
reads confirmed `Selected=false`; the document API reported `modified=false`.
This selection API remains unqualified until a native selection mechanism
passes read-back. Python MCP on TCP 14701 runs from `main`; the relay on TCP
14700 remains available.

Network MCP verification after restart listed 573 tools and reported matching
loaded/bundled version `2026.10.16.3`. `pcb_3d_capture` wrote an 800x559 PNG
of the editor canvas; the floating toolbar and Altium's collision overlays are
visible in it, so this is not a clean raster comparison export. `app_detach`
left TCP 14701 listening and the board file's SHA-256 and modification time
unchanged. Starting `StartMCPServer` again and calling `app_attach` succeeded.

## Local Python MCP follow-up, 2026-10-16

The Python Streamable HTTP process on TCP 14701 was restarted from this
worktree after Python-only changes. The loaded DelphiScript remains
`2026.10.14.5`, with no native script replacement. `app_ping` reported Altium
`26.10.1.5`. `app_screenshot` now creates parent directories;
`pcb_3d_capture` captures the current visible `View_Graphical` PCB canvas,
and `pcb_select` supplies an exact PCB component-designator wrapper. On the
owner's board, `pcb_select("FD4")` reported one match but read-back returned
`Selected=false`; the PCB tab showed a dirty `*` while the active-document
API reported `modified=false`. The owner was active, so the dirty marker's
cause is unproven. The live wrapper has been disabled pending native repair. No
save or discard was performed. `obj_zoom_to_xy` refuses a PCB request before the
known modal `PCB:Jump` call; silent coordinate centering is still open.
`app_detach` now reports correctly that the Python MCP transport stays up but
the DelphiScript worker stops and needs an operator relaunch. Focused Python
tests: 22 passed. Live checks: 567 tools listed, ping, nested screenshot,
canvas capture and zero dialogs after the guarded zoom call. See
`D:\shared\xo-altium\reply.md` for the external retest handoff.

Source-only candidate `2026.10.16.1` adds `pcb.select_component`, focused
board path validation and immediate selected-flag read-back. The staged Python
wrapper requires that exact native version and verifies selection in a second
request. Source build/lint and 64 focused tests passed. It is **not loaded in
Altium** at that checkpoint. The open PCB tab had a dirty `*`; the owner later
authorized discarding test changes and restarting components. The companion
shared deployment runbook is absent from this workspace; native acceptance
must record the actually loaded version and board state.

## Local integration check, 2026-10-14

The fork merge is under test in `D:\ai\eda-agent-large-integration` on
`integrate-large-altium-forks`. It is uncommitted and has not been pushed.
The historical deployed-runtime notes below describe the fork's earlier
environment, not this local Altium 26.9.1 test session.

On 2026-10-14 after updating Altium to 26.10.1.5, the local TCP 14701 MCP
server, dashboard and supervisor were switched from `D:\ai\eda-agent` to this
test worktree. A network MCP session listed 565 tools and `app_ping` confirmed
both the loaded and bundled script versions as `2026.10.14.5`. The supervisor
ping succeeded. This is a startup/transport check on the updated Altium, not
native qualification of every imported command.

The combined script keeps the current branch's `StatusForm` timer pump and
its shutdown teardown. The fork's older dispatcher timer was removed because
it would restore previously fixed hang and access violation paths. Native
compilation and PCB reads succeeded in Altium 26.9.1. MCP detach, dashboard
close, Detach button, and stop-file paths stopped the script; `X2.EXE` remained
responsive, and no new Application Error event was found. Selected-project
mode is present but disabled by the source default
(`SELECTED_PROJECT_READ_ONLY = False`). In a separate local test copy with
this flag enabled, the operator selected a project, read its documents,
tracks, vias, and unrouted nets, and saw a write command refused. Altium 26
returns different interface wrappers for the same project on later UI ticks;
the original pointer-identity check dropped valid read-only selections. The
read-only path now verifies that the selected project remains open at its
path, while the optional edit modes keep the stricter identity check and
remain unqualified. A direct Altium quit with the script attached was also
tested: the main `X2.EXE` process exited, and the Windows Application log
showed no new crash or hang event. That quit did not record `_session_end` in
the activity log, so graceful logging on host exit remains unverified.


Updated 2026-09-09. This is the current-state entry point; dated session logs are
historical evidence, not pending-work truth. See [TODO](../TODO.md) and the
[read/write delivery gates](PROJECT-SELECTION-AND-WRITES.md#delivery-plan-and-release-gates-2026-09-09).

Published checkpoint: [eda-agent d5b62a0](https://github.com/4pplet/eda-agent/commit/d5b62a03b20d1c2c6dfa416b4990d7c74fe11ad9)
and [PLT-hw 3b7cc66](https://github.com/4pplet/PLT-hw/commit/3b7cc66f4bd55cffe53a26141abdc85a52e65160).
Both were pushed to `origin/main`; their remote hashes and clean worktrees were
verified before this documentation-only receipt. These are matching source/helper
baselines; no installed package/runtime redeployment accompanied publication.

## What is running

- Fork: `4pplet/eda-agent`, based on `1b60105cbe0c4bd557007b87bc04dda2fd4ef9a1`.
  This publication checkpoint contains the local integration changes; use its
  actual Git revision, not the old base alone, to reproduce them.
- Altium 23.3.1; shared scripts `2026.10.02.1`; 35 bounded read tools (since 2026-10-02:
  `pcb_get_tracks`, copper tracks and arcs in exact coordinates, paged; the violations read
  paged). Natively qualified on the PLT HS and 22p boards.
  Runtime: `%LOCALAPPDATA%\PLT\eda-agent\shared\selected-readonly-tracks-20261002`
  (previous, kept for rollback: `selected-readonly-drc2-20260924`, scripts `2026.09.24.4`).
  For using the bridge, the one page to read first is PLT-hw
  `tools/eda-agent/BRIDGE.md` (commands, rules, blind spots; test-enforced against the
  runtime pointer). Upstream review of 2026-10-02: PLT-hw
  `tools/eda-agent/UPSTREAM-REVIEW-2026-10-02.md`.
- **Source is ahead of the deployed runtime (2026-10-03):** scripts `2026.10.03.1` add the
  first write, checked `LCSC Part #` / `Instruction` edits, approved by the operator and
  gated off by default (`SELECTED_PARAM_EDITS = False`). Not provisioned, not deployed;
  native qualification T1-T17 is open:
  [PROPOSAL-2026-09-28](PROPOSAL-2026-09-28-metadata-write-increment.md) section 7. The
  running runtime above is unaffected.
  **Runtime paths are written with the environment variable on purpose.** An
  absolute path here names one machine's private storage, which
  `test_no_client_design_data.py` refuses. Use the variable in committed docs;
  expand it when pasting a command.
- Historical: scripts `2026.09.08.2` with eight read tools ran from
  `selected-readonly-permissions-20260909`, manifest SHA-256
  `e3dd10e76af730af55700e8e8c9f563c0a24d63ddcf2d382a5c243abff39bd88`
  (23 files). Superseded; kept because the hash identifies that checkpoint.
- The older `shared/selected-readonly-v1` runtime and named `.1` profiles remain
  untouched fallbacks. **Committing source does not update the wheel or
  loaded/deployed scripts**; that separation is the standing trap here.
- **Wheel reinstalled from source 2026-09-24, fixing a real defect.** Its
  bundled `eda_agent/scripts/` had drifted to 14 files while
  `pyproject.toml`'s force-include list names 15: `SelectedProject.pas` was
  never shipped, yet the bundled `Altium_API.PrjScr` referenced it. So
  `eda-agent install-scripts` produced a script project that **could not
  compile**: it pointed at a file the wheel did not contain.
  - The packaging config was correct all along; the wheel simply predated the
    line that added the file. `pip install --no-deps --force-reinstall .`
    fixed it permanently. Python sources were byte-identical before and
    after, so only data files changed.
  - **PLT's deployed runtimes were never affected**: `create_shared_runtime.py`
    copies from the repo checkout and generates its own PrjScr, so it never
    reads the wheel's bundled scripts. This broke the `install-scripts` path
    only.
  - `tests/test_regression.py::TestInstallScriptsIncludesDfm` is what catches
    this, and it was already failing, invisible inside the 276 failures that
    a missing `pytest-asyncio` was producing at the time.
- Generic Python wrappers/provisioning currently live in companion
  [PLT-hw tooling](https://github.com/4pplet/PLT-hw/tree/main/tools/eda-agent).
  Moving them into this package is pending. Until then both checkouts are needed.
  Use the [shared runbook](https://github.com/4pplet/PLT-hw/blob/main/tools/eda-agent/SHARED-PROJECTS.md),
  not the historical named-profile patch recipe or a generic reinstall.

Important: the raw source defaults `SELECTED_PROJECT_READ_ONLY = False` for
upstream compatibility. The reviewed shared generator enables it and installs
matching restricted clients. Running arbitrary source scripts/upstream tools is
**not** equivalent to our read-only runtime. No shared persistent client config
has been enabled; checks use a single short-lived STDIO diagnostic client.

## Latest observed evidence

- Operator confirmed the short project close/reopen and Detach/quit/restart
  checks completed on 2026-09-09. This is operator-reported evidence; exact cycle
  count/session logs were not supplied. It does not close dirty-state, duplicate
  names, native guard bypass, helper-stop or in-flight tests, or fix direct quit
  with the bridge running.

- Missing Start report resolved: user was viewing the Projects panel, not
  File > Run Script. `Dispatcher.pas > StartMCPServer` works; no startup fix needed.
- Candidate live session `20260909084536379-17129109`, Altium PID 3612:
  ping/project discovery passed; 22p generation 2 changed to cyber80 generation 3.
  A test bound to 22p correctly stopped at preflight before content dispatch.
- User selected the 22p disposable copy again, generation 4. All eight tool
  checks passed: 9 documents, dirty count 0, 172 BOM components, 559 pin/net rows,
  C101 metadata. Every scoped response retained the selected path/session/token.
  No CAD edit/save command sent; BOM/net reads use allowed non-forced compilation.
  This is a copy under `projects/plt-22p/design-copy`, not necessarily latest CAD.
- 2026-09-09 continuation (different agent): the same-snapshot export
  comparison is automated in companion PLT-hw `compare_native_export.py`
  (c00957e, ten synthetic tests, suite green in the installed venv). Real run
  with hash-verified snapshot identity (design-copy files == PLT-hw `05d18ab`):
  bridge generation-4 BOM/net dumps versus the 09-08 Protel2 bundle export gave
  172/172 designators, 550/550 shared pins with identical nets, 0 mismatches
  and 9 additional-only single-pin entries (spare pads, TVS NCs, floating U205
  EN, freed PC15, and D302-3 - extra evidence for the open D302 numbering
  dispute). The 15:48 sheet-scoped v1 export carries only 542 of the 550;
  prefer the full-project Protel2 export as comparison input.
- Re-run: 89 companion Python tests, 13 native-selection source checks,
  10 shutdown source checks and 8 standalone-probe source checks pass.
  Full Pascal lint in canonical source order: 12 files, zero errors/warnings.
  Source tests do not execute Altium's VM. Counts/schema are not export parity,
  electrical acceptance or full extraction completeness.

- Native dirty-state read test PASSED (2026-09-09, session
  20260909103901779-23934625, working 22p project, generation 2): with two
  operator-confirmed unsaved documents (22p-adapter.PcbDoc,
  3_22p-adapter_mcu.SchDoc), `proj_get_compile_freshness` reported
  dirty_doc_count=2 and named both files, `proj_list_documents` still served,
  and `proj_get_bom` was refused with `DIRTY_PROJECT - Save intended edits
  manually before compiled reads`. First native confirmation of the dirty-target
  guard: inspection reads work, compiled reads refuse. The full row is now closed
  (2026-09-09, session 20260909113532577): an operator save that did NOT
  reach disk was correctly still refused (file mtimes proved the bridge
  right); after a real Save All, dirty_doc_count returned 0 and BOM/net
  reads succeeded (172/559, byte-identical schematic content to the
  pre-edit baseline). Dirty state also survives a bridge restart - it is
  live Altium state, not bridge cache - and unsaved documents of the other
  open, unselected project (cyber80) never appeared in any response:
  dirty reporting is selection-scoped. Drafts (new unsaved documents in the
  selected project) remain an open matrix row.

- Usability batch (2026-09-09 afternoon, companion PLT-hw, client-side only,
  no deployment needed): shared idle timeout is config-pinned to 60 minutes
  (operator decision; EDA_AGENT_AUTO_SHUTDOWN_MS overrides; seeded for new
  runtimes, re-pinned after every wheel connect, current runtime updated) -
  the 10-minute default forced two mid-CAD restarts. New `bridge_read.py`
  CLI: one-command status/bom/nets/parameters(+blank-report)/documents/
  freshness bound to the live selection, runtime root from the reviewed
  ACTIVE-RUNTIME.txt pointer, DIRTY_PROJECT errors enriched with dirty
  document names; both paths live-verified (2026-09-09 15:11 session: status and the
  full 172-component parameters+blank-report in seconds on the 60-min
  clock). New `check_install.py` drift doctor: 13/13 on the
  current installation. Stop-first at wind-down matters more with the longer
  timeout, not less.
- Batch candidate 2026.09.09.2 QUALIFIED and active (2026-09-09): runtime
  `shared/selected-readonly-batch-20260909`, prepared with the guarded
  cross-version manage_shared_runtime prepare (update-receipt records the
  09.09.1 baseline). Ninth tool proj_get_component_info_batch: full
  172-designator pull matched all, byte-equivalent to the single-call loop,
  not_found honest for unknown designators; eight existing reads regression-
  passed with extraction validation active. Rollback: the 09.09.1 extraction
  runtime, itself falling back to the 09.08.2 permissions runtime.
- Extraction candidate 2026.09.09.1 QUALIFIED and active (2026-09-09):
  new runtime `shared/selected-readonly-extraction-20260909` (23 files
  hashed, integrity check passed offline, eight-tool schema intact) is now
  the operating shared runtime; `selected-readonly-permissions-20260909`
  remains untouched as rollback. Live qualification on the working 22p
  project: version agreement, all reads, extraction block
  physical/zero-skips/delegated with strict client validation enforcing,
  draft refusal naming the offending document, and immediate recovery after
  a deliberate discard. The cross-version guard in manage_shared_runtime
  correctly refused to inspect the old-family runtime (documented
  limitation); create_shared_runtime provisioned the new family directly.

- Foreign-tab invariance, post-crash recovery and drafts recovery PASSED
  (2026-09-09, session 20260909120705744, post-crash relaunch): with a tab of
  a NON-selected project focused, selection stayed 22p generation 2 and all
  eight reads served only selected-project data with the correct binding on
  every response; the tool surface exposes no active-tab query at all. Same
  probe confirmed clean recovery after the 11:50 crash and after the
  identityless draft ceased to exist (dirty 0, BOM 172, nets 559). Drafts row
  closed: fail-closed INCOMPLETE_DOCUMENTS while a draft exists (see TODO
  diagnosability note), clean reads once it is gone; the deliberate
  discard-without-crash variant can be repeated cheaply any session.
  Remaining live matrix work: repeat helper-stop, close/reopen selection
  clearing, duplicate names, dirty-unrelated-document case.

- New shutdown-family crash data point (2026-09-09): X2.EXE 23.3.1.30
  crashed at 11:50:51 with exception 0xc0000374 (heap corruption, faulting
  module ntdll.dll, WER report 541a7215-1b4d-43ec-add6-e7eb165d7dc6) - 1.2 s
  AFTER the bridge loop ended cleanly by idle-timeout at 11:50:49.794
  (_session_end, requests=51). Not the known quit-while-running case: the loop
  had exited first. Either a spontaneous crash right after loop teardown or an
  operator close racing it. Strengthens "do not depend on inactivity timeout
  to quit"; relevant to the P0 lifetime investigation. An unsaved draft sheet
  (part of the drafts matrix test) was open at crash time; saved documents
  (11:37 Save All) were unaffected. Two unrelated LiveKernelEvent reports
  (10:33, 11:21) the same morning are system-level, not X2.

- Wind-down evidence 2026-09-09 evening (positive, plus one anomaly):
  deliberate stop at 16:05:47 (`_session_end reason=stop-requested`; fresh
  session 9 s later served reads), first live helper-stop data point toward
  the "repeat helper-stop" matrix row. After the 16:16:36 idle-timeout exit,
  Altium was closed with NO crash in the event log (contrast 11:50:51:
  the idle-timeout-then-crash signature did not repeat). Anomaly: that final
  session timed out after exactly 600.0 s despite the 60-minute pin
  (mcp_config.json held 3600000, mtime 15:11:47), while the 15:11 session
  had survived 53 min idle, the pin held once and not the other time.
  Logged with hypotheses in TODO.md (config re-read race vs restart-time
  read); investigate on a non-CAD day alongside the deferred crash work.

- P0 Ctrl+Z source-level analysis (2026-09-15, host-side only, no Altium
  run): excluded our own interception paths (no KeyPreview/TMessageFilter/
  WM_KEYDOWN handler in scripts/altium/*.pas; the status form never calls
  SetFocus/Activate, it only Shows; loop cleanup does not pump UI events),
  so the detach burst is not our final pump and pure focus-steal cannot
  explain it. Two Altium-side mechanisms remain (accelerator deferral
  while a script owns the message loop, or VCL-only message draining with
  an editor-key backlog); the one-step bench discriminator and remaining
  fix candidates are recorded in the TODO P0 item. No code change; no new
  native evidence yet.

## Continuation ownership (2026-09-09)

The agent that built this integration has stopped (out of credits) and will not
continue. The plan and evidence here remain the handoff. Stefan's decision:
resume gate work later, **on a day without CAD work**: Gate 0 lifecycle tests
involve repeated Altium quit/restart cycles and the known direct-quit crash,
and must never share a session with real design edits. Read-only use continues
under the operating contract in the shared runbook meanwhile.

- 2026-09-10 END-OF-DAY ROLL-UP (continuation agent): five runtime
  versions in one day, three natively qualified. ACTIVE =
  `selected-readonly-pcbreads3-20260910` (2026.09.10.5, twenty-five
  tools): the nine .2 PCB reads + six tranche-3 reads (rules, net
  classes, trace lengths, component pads, selected objects, board stats)
  + `proj_get_erc_messages` (first native ERC pull: 197 violations in 6
  classes, triaged in PLT-hw reviews/2026-09-10-erc-triage.md - 191
  noise, 6 for operator eyes). ACTIVE since
  the afternoon deploy = `selected-readonly-audits-20260910` (2026.09.10.6,
  thirty-one tools): six layout audits qualified live, one client
  validator bug fixed via surgical runtime patch, and the audit data
  caught a shorting hazard in the PLT-hw floorplan DOCS (U205 PowerPAD
  vias belong on the L4 island, not L2 GND - CAD was right, docs fixed). The pads
  read caught U301 90 deg off the recommended orientation on first use
  (operator fixed; re-verified pin-1-SW). Idle-timeout race ROOT-CAUSED
  and fixed three ways (bridge_read finally re-pin, shared_server atexit,
  and the wheel-proof workspace/idle-timeout-ms.txt sidecar preferred by
  scripts .4+). Ratsnest interference report resolved: full-restart A/B
  exonerated the loop; native Altium preference/N-mode class issue.
  Working rule kept: compiled reads only at operator save points during
  active board editing. Phase 2 kickoff (approval-gated Validation +
  Release OutJobs) and library-read grant design are the next non-CAD
  blocks; the systematic schematic checker
  (PLT-hw tools/eda-agent/schematic_sanity.py) baselined clean after the
  R229/R230 false-floating postmortem.
- 2026-09-10 (continuation agent, earlier detail): **PCB-read tranches implemented during the
  22p layout phase** (operator request: placement/diff-pair validation
  without the OutJob loop, then copper-policy reads in the same
  Altium-closed window). Nine selection-scoped read-only PCB tools
  (placements, board outline, layer stackup, differential pairs with routed
  length/skew, diff-pair rules, vias, polygons, unrouted-net ratsnest
  counts, and a new per-layer primitive-count reader for the
  internal-GND-no-copper check) as SCRIPT_VERSION 2026.09.10.2; the
  focused-board/`GetPCBBoardAnywhere` targeting was replaced with
  `ResolveSelectedBoard` (selected project's own PcbDoc, already open,
  fail-closed) and PCB reads carry pcb_doc/pcb_modified live-state honesty.
  Candidate runtime `selected-readonly-pcb-20260910` created and
  integrity-checked at .2 (the undeployed .1 build was replaced in place);
  deployment + native qualification (incl. placements vs same-snapshot ODB)
  pending at the next Altium start. Companion suite 141 pass; fork
  failed-set diff vs baseline empty. Details in TODO.md
  and PLT-hw `tools/eda-agent/SHARED-PROJECTS.md`.
- 2026-09-09 (continuation agent): offline BOM/review silent-empty defect
  fixed at source (93f5f4a) and the installed wheel rebuilt from that commit
  during a no-Altium window: old wheel preserved as
  wheels/eda_agent-0.5.0-py3-none-any.whl.pre-fix-20260909.bak
  (SHA-256 84fb7109...), current build (b7bd379, guard scoped to
  the .PrjPcb branch after a full failed-set baseline diff came back clean)
  SHA-256 1c15b063... installed, pip check clean, installed CLI verified on
  the real project, shared client eight-tool list-only schema check passes. pytest was added to the runtime venv as dev
  tooling (runtime lock unchanged per pip check). Targeted suites around the
  changed files: identical 15 pre-existing failures on clean tree, +7 new
  passing regressions; full-suite baseline comparison recorded separately.

## Remaining work, in order

The long-horizon sequencing - importing the remaining upstream surface
through the scoped model, phase by phase up the risk ladder with a
never-import list - is planned in [PARITY-ROADMAP.md](PARITY-ROADMAP.md)
(agreed with Stefan 2026-09-10). The numbered items below are the near-term
qualification order within that plan.

This is qualification order, not a strictly sequential implementation queue.
Packaging, documentation and permissions design may proceed alongside native
read/lifecycle testing. Reliable target/baseline reads, approval enforcement,
failure recovery and separate-save safeguards must pass before enabling writes.

1. Finish candidate visual/selection lifecycle tests (draft, tabs, close/reopen,
   duplicate names, dirty documents), native guard tests and repeated no-save
   Detach/helper-stop/quit/restart. Side-by-side manual rollback still needs testing.
2. Expose extraction omissions/compile results and automate exact same-snapshot
   native export comparison. Do not rely on the broken offline BOM extractor.
3. Consolidate packaging and qualify clean installation; improve concise
   diagnostic errors and define cancellation/deadline/unknown-outcome recovery.
4. Implement operator-only capability grants and exact-batch approval with
   native/Python enforcement, baseline checks and audit/recovery records.
5. Qualify existing manufacturer/approved-MPN/datasheet parameter updates on
   copies first. Save separately; test undo, failures and save/reopen persistence.
6. Values and footprint assignments next; annotation/variants separately. PCB
   ECO application, library/geometry and connectivity edits are separate scopes.

## Non-negotiable operating limits

Default to scoped reads. Selection is not CAD-write authority. Keep one Altium
instance/client, exact absolute project and fresh token; never follow focused tabs.
No forced recompile, Save All or automatic retries after uncertain writes.
The named kernel client guard coordinates updated cooperating clients only.

**Detach before closing the script project or quitting Altium.** Direct quit with
the loop running remains a known failure, not a fixed issue. Pause is not Detach.
The idle timeout tracks bridge traffic, including keepalive pings, not general
Altium activity; it is pinned to 60 minutes via mcp_config.json, but the
2026-09-09 16:16 anomaly (a 600 s timeout despite the pin, see TODO.md) means
the pin cannot yet be relied on: treat the effective timeout as possibly ten
minutes until the anomaly is resolved. Never replace loaded scripts or auto-dismiss/save/kill
Altium to complete tests. No write permissions were enabled by this publication.
