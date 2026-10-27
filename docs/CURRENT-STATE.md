# Current integration state / agent handoff

## Refreshed handoff, 2026-10-27

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
and unmodified. Creating and deleting an actual xSignal on a populated
disposable board still needs native acceptance. TCP 14700 and MCP 14701
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
`fpc` is unavailable here. Pascal lint/build passes. Native component
acceptance is pending.

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
