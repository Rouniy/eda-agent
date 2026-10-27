# Fork integration TODO

## Fork behavior audit, 2026-10-28

- [x] Preserve fractional-mil widths through the Python keep-out
  outline and board-pour edge-clearance wrappers. On a disposable
  arched board, three tracks and one arc persisted at 20.625 mil on
  KeepOutLayer after save/reopen; repeat calls added zero.
- [x] Qualify `pcb_place_polygon_board` copper creation on a disposable
  arched board with GND: the exact 20.625-mil keep-out was reused,
  and the poured polygon's five copper pieces persisted after reopening.
- [x] Explicitly repour the new arched-board GND polygon on a disposable
  copy: one rebuilt, two skipped, zero failed, and five copper pieces
  before and after.
- [x] Independently inspect the saved polygon's arc geometry. New
  `pcb_get_polygon_outline` under script `.117` read the same four
  segments as the board: three lines and a 500-mil half-circle arc.

- [x] Compare the offline SchLib reader to the same native library:
  39 primary names match; Altium's 40th row is the `ADXL210` alias.
  Normalize saved header-key casing so library reference, description
  and alias metadata are no longer lost on this Altium-generated file.

- [x] Compare native and offline PcbLib footprint names on the same
  copied library. Fix a sanitized OLE storage name (`SO-G5_P.95`)
  leaking as the footprint name instead of its `PATTERN` (`SO-G5/P.95`).
  All 33 names now agree; offline primitive geometry is still not
  implemented.

- [x] Native-read footprint primitives from a copied 33-footprint
  PcbLib under script `.115`: `PQ208` and `CC1608-0603` returned the
  exact library identity and non-pad geometry; separate pad reads
  returned 210 and two pads. Full independent primitive parity remains
  a separate validation task.

- [x] Native-qualify the MOREmbedded integrated-library build path on
  copied Altium example libraries. Script `.115` compiled a LibPkg with
  exact SchLib and PcbLib members into a 123,392-byte IntLib containing
  both library streams; a second build of the existing package kept
  exactly two members and refreshed the IntLib. The QA project closed.
  Installation of that
  IntLib into Altium's global library list was not part of this check.

- [x] Run the 11 `vincent-himpe` decimal-length tests against `main`;
  all pass. Confirm six custom-pad shape readers already name
  `eCustomShape`, and the EasyEDA extension delivery guards have adapted
  coverage. See the sync checkpoint for the six absent test-path audit.
- [ ] Design and qualify a safe preflight/verification path for bulk
  designator rewrites. The `bblacklock3` fork refused them because a
  partial batch can leave duplicate designators and merge nets;
  upstream restored the bulk capability. Preserve useful bulk editing
  while closing that failure mode on disposable projects.
- [x] Qualify `vincent-himpe`'s fractional circular board outline in
  Altium `.115`: exact centre and radius were returned as four closed
  quarter arcs and persisted after save/close/reopen on a disposable
  PcbDoc. See `docs/CURRENT-STATE.md` for coordinates.
- [x] Qualify a fractional polygon board outline with a true arc in
  Altium `.115`: three lines and a 500-mil half-circle persisted after
  save/close/reopen on the same disposable PcbDoc.

## mooreaa template value reconciliation, 2026-10-28

- [x] Run the fork's placement-cleanup source tests against `main`.
  The live-pin filtering and decimal-width cases already have adapted
  implementations. `sch_draw_template` still stamped `Comment` instead of
  `Value`, which leaves the component's Value parameter stale. It now
  sends `Value`; the native handler updates both the visible Comment and
  the Value parameter. Forty-two related tests pass (19 optional skips).
- [x] Verify a disposable `sch_draw_template` placement and visible
  Comment readback in Altium. The `RES` and `CAP` symbols both produced
  the requested visible value after save/reopen.
- [x] Verify an existing *component-level* Value parameter readback.
  On a disposable `CAP` placement, script `.115` created a direct
  `VALUE=direct-old`, then a `Value=33nF` stamp changed both that parameter
  and the visible Comment after exact save/close/readback. The nested
  model `VALUE` stayed unchanged. The first `.114` check had mistakenly
  updated the model parameter; `.115` confines component parameter lookup
  to first-level children.

## Battery research branch, 2026-10-28

- [x] Import the standalone PyBaMM/COMSOL research lab from
  `yniantongtian-oss/feat/battery-ai-comsol-lab` without changing core
  `eda-agent` dependencies. Ruff and six isolated tests pass, including
  a short electrothermal solve.
- [ ] Observe the path-scoped hosted GitHub Actions workflow after Actions
  is enabled for the fork. GitHub's repository Actions page explicitly says
  "Workflows on this fork have been disabled" and offers a re-enable
  button; the workflow API reports zero runs. The workflow now supports
  manual dispatch and limits its token to `contents: read`.
- [ ] Exercise the optional MPh adapter against a licensed COMSOL install
  when one is available; PyBaMM validation does not qualify COMSOL.

## Live `.113` fractional text-frame correction, 2026-10-28

- [x] On a disposable free SchDoc, batch wire vertices retained
  0.125/0.375/0.625-mil fractions after exact save/reopen.
- [x] Fix `sch_place_text_frame`'s rounded response and expose
  `Corner.X/Y` through `obj_query` and `obj_modify` for `eTextFrame`.
  Pascal lint/build found zero errors or warnings. Loaded `.113`
  returned exact fractional corners, modified one corner and preserved
  both frames after save/reopen.
- [x] In native `.113`, `pcb.delete_xsignals` rejected a request that
  combined a name with `all=true` before looking for a board.

## Live `.112` runtime, 2026-10-27

- [x] Restart Altium with the main script project, confirm `app_ping`
  reports `.112` with zero cast errors, and restart the HTTP/MCP process
  on 14701. A client listed 757 tools; TCP 14700 stayed live.
- [x] Native save/reopen acceptance of `sch_add_text` on a disposable
  SchDoc: type, text, coordinates and rotation persisted. Altium
  normalised the rotated font from ID 1 to ID 2; the family/size stayed
  Times New Roman 10. A missing exact sheet was refused.
- [x] Run disposable-project acceptance of upstream's simulation probe,
  setup and sheet-run changes in the merged `.112` bundle.
  On an isolated copy of Altium's Simulation Quick Start project,
  `sim_get_setup` read operating-point, DC, transient and AC settings
  and 14 stored runs. `proj_load_sheets` loaded all seven sheets;
  `sim_get_probes` returned a complete empty inventory with no unloaded
  sheets. `sch_place_probe` then placed `SimulationProbe=V` at
  (4250,10200) mil on `out`; save/reopen preserved it. `sim_run`
  produced and saved real results for the focused sheet. Its
  `analyses=['op']` selection did not hold: Altium returned op, DC,
  transient and AC, even after reopening with an op-only saved setup.
  The copy closed without saving after each run.
- [ ] Find a native Altium mechanism that reliably limits a sheet run
  to selected analyses. Until then, report the actual `ran_analyses`
  and `selection_applied=false` when the simulator ignores the request.

## Combined fork decimal guard, 2026-10-27

- [x] Remove a duplicate `_mils` definition that bypassed the finite
  coordinate guard after the `vincent-himpe` decimal-mil port. Thirty
  library/decimal/free-text tests pass.

## Upstream simulation tip, 2026-10-27

- [x] Merge upstream `f3bd57f` as a true parent, preserving local script
  flags and free-text placement. Source `.112` passes Pascal lint/build
  and the focused simulation/bridge suite.
- [x] Load `.112` after restarting the shared Altium session; probe and
  sheet-run behavior were checked on a disposable copy above.

## Fork schematic free text, 2026-10-27

- [x] Port `rabihnd/integration`'s `eLabel` free-text placement as
  `sch_add_text` with exact sheet targeting and readback. Script `.111`
  passes source tests and Pascal lint/build.
- [x] On disposable SchDoc with `.112` loaded, place a rotated free-text
  label, save/reopen, and verify type, text, font family/size and position.

## Fresh fork parity check, 2026-10-27

- [x] Refresh all live fork refs: 62/62 default tips and 117/117 branch
  tips match local refs; fetched upstream `c45ca0a` remains an ancestor of
  `main`.
- [x] Compare MOREmbedded's `via_loop_inductance` with our registered
  `pcb_calc_via_inductance`. The formula was present, but our input guard
  returned `ok=true` for `NaN`; it now refuses nonnumeric and nonfinite
  values. The calculator, NPI and SDK suites pass (222 tests).
- [ ] Observe a hosted run of `build-windows-binary.yml`; GitHub Actions
  reports zero runs so far.

## xSignal selector and legacy source checks, 2026-10-27

- [x] Refuse `pcb_delete_xsignals` with both names and `all=true` in
  Python and native Pascal. Script `.110` passes 17 related tests and
  Pascal lint/build. The old behavior would select all despite names.
- [x] Qualify the refusal in loaded `.113` against the native handler.
  It returned `BAD_PARAM` for `names` with `all=true` before any board
  lookup, so no disposable board was needed for this refusal case.
- [x] Reconcile the seven remaining stale cases in
  `test_added_altium_tools.py` with the exact-board/preflight wrappers.
  The combined legacy and focused suites pass (129 tests).

## Exact-board net inventory, 2026-10-27

- [x] Scope `pcb_get_nets` to an optional exact PcbDoc and make
  `pcb_net_display(from_project=True, nets=None)` require a matching board
  path before choosing nets. Source `.109` passes eight focused tests.
- [x] With two disposable PcbDocs open on loaded `.114`, `pcb_get_nets`
  refused the nonfocused board with `TARGET_CHANGED`. The focused empty
  QA board returned zero nets; after `pcb_focus_board` selected a temporary
  copy of Altium's Spirit Level board, the exact-path read returned 126
  nets. Both boards closed without saving and the extra copy was removed.
- [x] Check project colour planning from an exact copied project and board
  without saving. On the Mini PC SODIMM example, `pcb_net_display` returned
  a dry-run plan for GND, VDD, VPP, VREFCA and VTT, with five project BGR
  colours and no missing colour. The board and project closed without a
  dirty document or a save. Temporary-directory cleanup was rejected by
  automatic approval review, so the isolated 9.9 MB copy remains in Temp.

## Fractional schematic placements, 2026-10-27

- [x] Preserve fractional mils in batch wires, DbLib component placement,
  and text-frame corners. Source `.108` passes 43 focused tests, including
  exact bridge parameter checks.
- [x] On a disposable schematic with `.112` then `.113`, batch wires and
  a text frame kept fractional mils through save/reopen. Text-frame
  reply/readback was corrected in `.113` as recorded above.
- [ ] Place a DbLib component at fractional-mil coordinates on a
  disposable schematic, then save/reopen and read back its position.

## Fractional PCB batch placement, 2026-10-27

- [x] Preserve sub-mil X/Y coordinates through Python batch serialization
  and Pascal's `pcb.place_components` parser. Script `.107` passes 19
  focused tests and Pascal lint/build.
- [x] In loaded `.113`, place two `CC1608-0603` footprints on a
  disposable free board at fractional-mil coordinates. After exact
  save/reopen, `QA_TOP` retained (1000.125,1200.375), TopLayer and
  45 degrees; `QA_BOT` retained (1500.6248,1600.875), BottomLayer and
  90 degrees. The requested 1500.625 mil is represented at native PCB
  coordinate resolution as 1500.6248 mil. No owner board was changed.

## MOREmbedded footprint layer identity, 2026-10-27

- [x] Pass the footprint's exact PcbLib path to both mechanical-layer reads
  in the existing render and package-audit tools. Forty-three focused tests
  pass, including call-parameter assertions.
- [x] With two installed example PcbLibs open, render
  `FP-51021-0700-MFG` from inactive `PCB1.PcbLib` while
  `Spirit_Level_Project.PcbLib` is focused. The target library's
  Assembly, Courtyard, 3D Body and Center roles read back with counts
  4/4/4/2; the focused library had no such layer kinds. Both libraries
  were read only and closed.
- [x] Repeat the two-library native routing check through
  `lib_audit_footprint_vs_package` with a Molex drawing. The exact inactive
  PcbLib path and its mechanical layer kinds were used; no wrong-library
  note appeared. Seven signal pad widths differed from the drawing.
- [ ] Independently transcribe the complete Molex pad centres and body
  geometry before treating that diagnostic audit as package signoff; its
  first run provisionally aligned pad centres to the existing footprint.

## New upstream point and distribution, 2026-10-27

- [x] Merge upstream `c45ca0a` as a true two-parent merge and cover
  fork-specific console subprocesses with the new `no_window()` helper.
  The focused 27-test suite passes; upstream is again an ancestor of `main`.
- [x] Adapt the `james-martinez` Windows binary workflow; a local exe build
  and bundled-script installation passed. Add `yniantongtian-oss`'s weekly
  Python and GitHub Actions dependency monitoring.
- [ ] Observe the new Windows binary workflow in GitHub Actions. Its workflow
  is active, but the API reported zero runs after push; local validation does
  not substitute for the hosted runner.
- [ ] Complete native acceptance of script `.106` after the shared Altium
  session can be safely restarted; the last doctor check found loaded `.96`.

## Fractional-mil annotation order, 2026-10-27

- [x] Remove whole-mil rounding from project annotation sort keys by using
  native TCoord integers. Source `.106` passes five related tests and
  Pascal lint/build. Direct `CoordToMils(` calls are now confined to
  utility/self-test code.
- [ ] On a disposable sheet, annotate two same-prefix components whose
  sort positions differ by less than 1 mil; confirm exact order after
  save/reopen.

## Fork behavior review, 2026-10-27

- [x] Compare `rabihnd/integration`'s `ApplySetPropertiesEx` with the
  current property diagnostic path, `cad435/main`'s vault-library list
  with the current available-library/Workspace pair, and MOREmbedded's
  NPI/SDK modules. No additional public tool was needed; 66 NPI/SDK
  tests passed. See the dated sync ledger.
- [ ] Continue behavioral review of other fork differences and native
  acceptance of already ported SDK-derived tools.

## Schematic source-library cleanup, 2026-10-27

- [x] Port `wizd/edev`'s footprint-library clearing into the existing
  `sch_clear_source_library` tool as an explicit option. Count confirmed
  link clears and refuse an unloaded exact sheet before any edit. Source
  `.105` passes 24 related tests and Pascal lint/build.
- [ ] On a disposable multi-model placed part, save/reopen after clearing
  both source and footprint library links; verify the PCB model search and
  compiled ECO state.

## Footprint and export source checks, 2026-10-27

- [x] Recheck the two failures in the extended footprint suite. The
  component property test used a stale identical-branch assumption;
  `proj_export_pdf`'s metadata incorrectly labeled its refusal-only
  handler as a writing operation. Updated both; 48 pass, one optional skip.

## Placed footprint name mirror, 2026-10-27

- [x] Adapt `wizd/edev`'s `Footprint` parameter mirror when choosing or
  renaming a placed PCBLIB model; require parameter readback for success.
  Source `.104`.
- [ ] After a controlled Altium reload, verify the model and `Footprint`
  parameter agree after both paths and persist after save/reopen.

## Placed footprint library links, 2026-10-27

- [x] Adapt `wizd/edev`'s `Any`/`*` unpinning and absent-datafile-link
  creation to `sch_relink_components`, retaining the proven PcbLib basename
  format required by Altium 26.11. Source `.103` and focused tests pass.
- [ ] On a disposable placed multi-model part, verify unpin and new-link
  persistence after save/reopen and confirm ECO resolves the named PcbLib.

## Multipart graphic ownership, 2026-10-27

- [x] Expose explicit `owner_part_id` for rectangle and arc creation;
  keep 0 as the shared-part value and reject invalid owners before IPC.
  Source `.102` passes 77 related tests and Pascal lint/build.
- [ ] In a disposable multipart SchLib, verify a rectangle, arc,
  polygon and line assigned to part 2 and shared part 0 after save/reopen.

## Schematic object type names, 2026-10-27

- [x] Restore upstream/MOREmbedded's five `SchTypeName` graphic names
  lost during a merge. Name another five schematic types already accepted
  by `ObjectTypeFromString`, so sheet-frame output is readable.
- [ ] Verify the ten names on a disposable schematic after source `.101`
  is loaded in Altium; compare the frame inventory with native objects.

## Multipart symbol lines, 2026-10-27

- [x] Port `rabihnd/integration`'s explicit line `owner_part_id` through
  `lib_add_symbol_lines`. The native batch handler already read it; the
  Python wrapper dropped it. Accept 0 as a shared graphic in the common
  native owner helper. Route rectangle, polygon and batch line insertion
  through `AddLibSymbolPrim` so newly written graphics appear on the active
  symbol. Source `.100` passes 69 related tests and Pascal lint/build.
- [ ] In a disposable multipart SchLib, add lines to part 2 and shared
  part 0, save/reopen, and verify their owner and visibility in each part.
- [x] Reconcile the older `test_symbol_writes_on_screen.py` schematic-name
  assertion: the reverse names were lost from `Generic.pas` in a merge.

## Lost helpers in fork reconciliation, 2026-10-27

- [x] Restore `ReadNoErcProp`, `WriteNoErcProp` and `SaveProjectFile`,
  whose live call sites survived earlier merges without their definitions.
  Guard No ERC reads/writes by object type, verify a project-file disk
  write, and pin `app_create_document` to its selected project. Source
  `.99` passes 51 focused tests and Pascal lint/build.
- [ ] Reload `.99` in Altium when the shared session can be restarted.
  On disposable projects, verify No ERC property reads/writes and exact
  document creation, save and reopen, including the project's persisted
  member list. A source test cannot prove DelphiScript runtime behavior.
- [ ] Continue behavior-level comparison of the remaining fork changes.
  A 119-ref name scan found 20 Python and 35 Pascal names absent from
  `main`; many are aliases or superseded helpers, and absence of a name
  alone is not a feature gap.

## Project-scoped ERC and stale No ERC model, 2026-10-27

- [x] Prove on separately saved project copies that the specified No ERC
  markers suppress `NetU1_A2` and `NetIC44_1`. Both rows become active
  only after the saved sheet is closed/reopened and the project compiled.
  Original folder hashes remained unchanged.
- [x] Pass `project_path` through Python's ERC run and violation-read
  wrappers, and return the filtered violation page from the run. Repair
  tracked-edit cleanup for confirmed-save document reloads in source `.98`.
  Forty-two focused tests and Pascal lint/build passed.
- [ ] Load `.98` and restart the Python bridge when the shared Altium
  session can be cycled without interrupting other clients. Native-check
  that an explicit project path reads that project while another project
  is focused, and that `app_reload_document` refreshes the saved No ERC
  model. Do not silently reload or save an unsaved sheet.

## ERC edits and compiled model, 2026-10-27

- [x] Count bridge-tracked edits as dirty for compile freshness and cache
  invalidation, and clear tracked records after confirmed discard/close.
  Source `.97` passes Pascal lint/build and 51 focused tests.
- [ ] Load `.97` in a controlled Altium session. On disposable sheets,
  verify that a no-save No ERC delete reports a dirty document and that
  a later compile reflects the in-memory marker state. Altium 26.11.1.5
  returned `suppressed=true` before and after deleting markers in two
  owner projects, despite `compile_action=compiled`; those projects were
  closed with `save=false`. Do not infer the suppressing object yet.

## Library preview fork parity, 2026-10-27

- [x] Restore Altium mechanical-kind coloring and courtyard/assembly role
  reporting in the existing footprint preview; report silk over copper.
  Thirty focused tests pass.
- [ ] Verify a real PcbLib preview with a Courtyard Top mechanical layer
  and a silkscreen line crossing a pad on a disposable Altium library.
- [x] Return saved STEP Z offsets and rotations from `lib_set_3d_body`
  alongside live body values, labeling the saved-file source.
- [ ] Check that combined read on a disposable multi-body PcbLib in Altium.

## MOREmbedded bridge reply parity, 2026-10-27

- [x] Restore stale-server reply warnings and the optional fit-board call
  after async edits; add hidden-frame recovery to async replies. Forty-three
  focused tests pass.
- [ ] Verify those behaviors in a controlled native Altium session without
  interrupting another client's active command.

## MOREmbedded ECO and UI recovery, 2026-10-27

- [x] Check every copy of a repeated pad name after ECO and refuse to call
  an empty schematic/board comparison complete. Restore the menu's
  hidden-window helper. Thirty-two focused tests pass.
- [ ] Native-check the repeated-pad ECO case and hidden-window menu
  recovery on a disposable Altium session.

## MOREmbedded rotation audit, 2026-10-27

- [x] Integrate multi-pad per-net scoring and courtyard collision reporting
  into the existing advisory. The port also avoids double-counting two pads
  of one net and ignores courtyards on the opposite board side; 39 focused
  tests pass.
- [ ] Compare this advisory on a disposable Altium board against real
  rotations and its placement DRC before using a suggestion to move parts.

## MOREmbedded updater parity, 2026-10-27

- [x] Port the child fork's four-layer update diagnostic as a read-only
  `eda-agent update --status` mode. It checks the source checkout, package,
  script directory and compiled Altium session; the current workspace's
  source-directory runtime is recognized. Twenty-one focused tests pass.
- [ ] Recheck the loaded script-project path on a responsive Altium session;
  the present process is hung, so only source/deployment state was verified.
- [x] Compare tracked Python source paths across 119 fork branch refs.
  The sole remaining path, `easyeda_extension_cli.py` in the
  `yniantongtian-oss` fork, duplicates our EasyEDA path/build CLI. Port its
  nonempty destination and `.eext` artifact guards into the existing CLI;
  seven packaging tests and an isolated real Node build pass.
- [ ] Continue behavior-level review of shared source files; matching file
  names and tool names alone do not prove feature parity.

## Upstream `fbf72a7` source merge, 2026-10-27

- [x] Reconcile the four new upstream commits after `40814ba` into the
  source tree, preserving the fork's exact-board and paste safety checks.
  The merge contains decimal-mil, filtered-walk, via-mask, via-delete,
  deferred-pour and 3D-body identifier improvements. Focused source tests
  and Pascal lint/build pass; see the dated sync ledger.
- [x] Load script `.93` in Altium: ping and all ten unit stamps returned on
  Altium 26.11.1.5 with zero cast errors.
- [ ] Run native reads and guarded writes against disposable designs for
  the newly merged paths. Verify persisted
  geometry after exact save/reopen, especially decimal schematic placement,
  via mask state, deferred pours and footprint body selection.
- [ ] Reconcile legacy `test_added_altium_tools.py` cases that still call
  unscoped upstream API wrappers without this fork's required board path.
- [ ] Diagnose the recurring Altium 26.11.1.5 UI hang during another
  client's `pcb.run_drc` / `application.set_active_document` sequence.
  It occurred with both loaded scripts `.92` and `.93`: no modal was
  reported, the window stopped responding, and subsequent bridge calls
  timed out while the Altium process continued using CPU. Capture the
  offending stack or a reproducible disposable-project case before
  attributing it to a source change.

## Refreshed after `.68`, 2026-10-27

- [x] Restore per-unit stamps, script-install stamping and the session
  document pin lost across merges. Script `.90` returned all ten unit stamps
  natively after an Altium restart; sync and async pin tests pass. The
  supervisor restarted HTTP 14701 into the new Python source and a live
  MCP handshake listed 754 tools; TCP 14700 remained listening.

- [x] Native-qualify the `mooreaa` multipart placement and existing SchLib
  relink path on disposable SchDoc/SchLib files. Script `.89` restored the
  missing pin-property helpers. Both placed sections and their later link
  changes survived exact save/reopen; wrong sheet and missing symbol were
  refused. DbLib/IntLib relink and parameter/model paths still need checks.

- [x] Add `rabihnd/integration`'s STEP body creation on an exact PcbLib.
  Script `.87` preserved the existing body, centre, layer, rotation and
  saved Z offset after save/reopen on a disposable library.
- [x] Fix and native-qualify the MOREmbedded multi-body STEP edit path.
  Script `.88` changes only the selected body's layer and model Z offset;
  a stale saved-model name refuses before any change.
- [x] Recheck tool names across 110 cached fork branch refs. The 15 names
  absent from our surface map to existing single/bulk or diagnostic tools;
  behaviour differences still need feature-by-feature review. Remove the
  already merged upstream `184301d` test fix from the pending table.

- [x] Restore `4pplet`'s automatic EasyEDA DesignPlan emission as an
  optional path alongside hand templates. Seven offline tests cover
  placement, real-pin wiring, refusal of missing positions and registry.
- [ ] Run the emitted plan and its second-pass connections in a disposable
  EasyEDA design through the live extension; current evidence is offline.

- [x] Adapt `rabihnd/integration`'s custom pad-list footprint creator to
  one guarded native call. Script `.85` plans against an exact PcbLib,
  reads back pad and outline geometry, and persisted the corrected oval
  pad and 15 non-pad primitives after save/reopen on a disposable copy.

- [x] Resolve saved STEP Z offset for a named clean PcbLib even when a
  separate PCB tab is active. Script `.83` reads the exact library's
  known/modified state natively; `AD_FE38` returned its saved 0.254 mm
  offset in Altium. Unknown/dirty libraries remain unverified.

- [x] Enforce board identity for the upstream-adapted pour lookup and
  board options. Script `.82` rejects a wrong `expect_file` natively and
  echoes the actual board; the Python wrappers verify that identity.
- [x] Native-read the ported footprint primitive handler on a disposable
  PcbLib. `AD_FE38` returned tracks, arcs, regions, text, vias and STEP
  body metadata; a wrong library path was refused. Saved STEP standoff
  substitution now uses the exact library's native clean-state report.

- [x] Reconcile upstream `40814ba` net-colour and project-colour options
  with exact-board, expected-state `pcb_net_display`. Script `.81` changed
  GND on a disposable board to `#123456`, planned the loaded project's
  colour, then restored it from the project in one guarded write. Native
  readback and 10 focused Python tests passed.
- [x] Reconcile upstream's coarse visible-grid factor and grid units with
  our exact-board `pcb_set_grids` contract. Script `.79` changed and
  restored factor 5/6 and visible unit mm/mil on the disposable PcbDoc;
  a stale expected factor was refused before writing.
- [x] Expand PCB editor preference and paste-array wrappers for the new
  font, colour, confirmation and pan settings, with exact-board preflight.
  Script `.78` read all properties and changed/restored board-area colour
  and paste repeat count; stale expected state was refused.
- [x] Merge the `40814ba` upstream tip with a two-parent commit, add its
  Gerber/print setup, paste-array preferences, Testpoint Style rule fields
  and schematic reference zones. Script `.77` compiled and answered native
  reads on an isolated board and the loaded schematic.

- [x] Port decimal-mil paste-grid dimensions and gaps from
  `vincent-himpe/fix/decimal-mils-leftovers`; confirm six fills and the
  disabled top-paste flag persist on a disposable PcbDoc under script `.76`.
  Fix DNP apply/restore persistence with the same side-specific flag.
- [ ] Confirm the resulting Top Paste output geometrically with a fresh
  native Gerber/export from the same disposable board snapshot. The pad
  flags, primitive counts and save/reopen checks establish persisted PCB
  state, not the fabrication file geometry.

- [x] Establish an exact upstream merge point: `9ee593e` is an ancestor
  of our current `main`, and there are zero upstream commits behind it.
- [x] Recheck every fork branch against its cached ref: 62 default tips
  and 117 total branch tips matched after fetching 20 previously missing
  branch refs. The `fork-status --verify-fork-branches` command repeats
  this live check.
  Recheck periodically; this is a dated inventory, not a permanent claim.
- [x] Port the child fork's via-tenting write with exact-board dry run,
  reviewed token and Altium save/close/reopen acceptance on a disposable
  board (`6b08ff4`). Bottom-side placement also passed native mirror,
  rotation and persistence checks (`63f1d6c`).
- [x] Port useful generic DbLib reads from `andrzej-sikora-elte/elte`.
  Script `.62` returned flags and current footprint models from two
  placed parts on a live DCDC schematic without property diagnostics.
- [x] Port another decimal-mil tranche from `vincent-himpe`:
  snap-grid context reads, off-grid audits, stub lengths, Workspace placement
  and library label coordinates. The 0.3-mil audit passed a live read on
  the loaded DCDC sheet with script `.64`; other write paths still need
  disposable-document acceptance.
- [x] Keep decimal coordinates in schematic symbol lookup, distance
  measurement, component placement and pin reads. Script `.65` compiled
  and answered native distance/pin queries. The expanded fork audit still
  lists PCB geometry and audit/reply conversions, plus the fractional
  placed-pin acceptance gap.
- [x] Keep decimal corners and pitch in via arrays. A four-via array
  persisted at exact fractional coordinates on a disposable PcbDoc after
  save/close/reopen. The stitching-via wrapper and outline grid also
  preserve fractional inputs; their native placement still needs separate
  acceptance.
- [x] Keep decimal component positions through PCB align, distribute and
  snap-to-grid operations. All three passed live save/reopen readback on
  the disposable PcbDoc; script `.68` also echoes decimal distribution
  endpoints. Remaining fork audit categories are in the integration ledger.
- Continue native acceptance of the already integrated multipart,
  rigid-flex, library and manufacturing paths listed below. A Git-divergent
  fork commit alone is not evidence that its feature is absent.

## Upstream merge qualification, 2026-10-27

- The two-parent merge includes upstream `9ee593e`; follow-up work should
  reconcile legacy upstream tests that assume implicit active-board writes
  with the exact-board contracts retained here. The broad suite previously
  reached 7419 passing tests; focused fixes after that run passed.
- Continue native checks on disposable Altium documents using script `.68`.
  Bottom-side component placement and flip readback passed on an isolated
  PcbDoc; other operations in this section retain their own acceptance gaps.
- Keep reviewing the latest MOREmbedded tip `032fb4b` for behavior that
  needs additional native qualification. Its NPI/SDK/3D features are ported.

## Upstream layer-stack remainder, 2026-10-27

- Complete the remaining `172d254` rule-setting, wire-tidy, pre-route and
  paste-opening review. Pour growth is ported and persisted on an isolated
  PcbDoc; repour and final copper acceptance remain separate.
- Test `pcb_plane_connections` on a disposable PcbDoc with a real internal
  plane and known connected/isolated pads. The current owner board has no
  internal-plane layers, so `.40` only proves the property read path.
- Qualify relative movement of a populated copper layer and rigid-flex
  stack-region edits from upstream `642e6a8` and `9ee593e` on isolated
  PcbDocs with exact save/reopen checks. The exact-board rigid-flex reader
  passed on a single-region rigid board; a multi-region flex sample is
  still needed. Empty-layer ordering, stack-style writes, impedance
  profile lifecycle and per-copper-layer settings are ported and checked.
- Continue reviewing upstream `172d254` and the remaining direct/child
  fork features against the sync ledger for native acceptance gaps.

## Exact document save, 2026-10-27

- [x] Add an exact-path save command that reports a verified disk write
  without closing/reopening the document (`app_save_document`, `.20`).
- Investigate why `MarkDocDirtyByPath` does not make the modified flag true
  for free PcbDocs after grid changes. Do not infer that modified=false
  means native changes have been saved.

## Package equality acceptance, 2026-10-27

- On a disposable populated PCB, compare two geometrically equal packages
  whose `PackageSpecificHash` is unavailable, and confirm that
  `pcb_find_same_package` groups them without comparison errors.

## xSignal acceptance, 2026-10-27

- On a disposable populated PCB, read an initial xSignal count, create a
  pair through a series part, verify its returned path/length/class, delete
  it with the new expected count, and independently read back the original
  count. Do not exercise the write on an owner's board.

## Fab-output acceptance, 2026-10-27

- Run `pcb_check_fab_output` on a disposable PcbDoc and its freshly exported
  Gerber/Excellon package from the same saved revision. Confirm copper,
  outline and drill-hit checks all ran.
- Exercise the native uncapped hole counter on a disposable board with over
  5000 drilled pads and verify the count against an independent export.

## Overnight corpus bridge, 2026-10-21

- Capture the native Script IDE diagnostic or Windows crash event at the
  moment `StatusFormClose` follows `project.run_outjob`. The 00:05 activity
  log shows `_session_end` after a successful print, but no visible error
  dialog or script diagnostic remained when inspected. Do not attribute the
  script exit to the Python PDF concurrency without further evidence.
- Qualify repeated color PDF exports over the full corpus after the
  same-server serialization change. If more than one MCP process will run PDF
  exports concurrently, add a cross-process Altium UI transaction lock.

## US-Plus-CPM statistics crash, 2026-10-20

- Instrument `PCB_GetBoardStatisticsForBoard` in a disposable runtime to
  locate the native access violation seen after `pcb_get_board_statistics`
  on antmicro US-Plus-CPM `PCB.PcbDoc`. Avoid that tool on the board until
  native acceptance passes. Other isolated reads that succeeded are logged
  in CURRENT-STATE.md; do not infer all `pcb_*` tools are safe.
- Remove the outline invalidate/rebuild/validate cycle from the statistics
  *read* once its effect on result freshness is measured. Altium documents
  that it refreshes outline and internal plane state; the current wrapper
  performs it even though the core function is read-only.

## ERC and DRC follow-up, 2026-10-19

- [x] Deploy native script `2026.10.19.1` after a coordinated bridge stop
  and Altium close. Exact-path ERC for tl-tx-booster-cbp returned 12
  violations, matching `proj_get_messages` on 2026-10-20.
- Reproduce the transient Place Line report from `pcb_run_drc` on a stable
  focused board. Qualify DRC completion against the configured report format
  and output path; the current `.DRC`-beside-board timestamp check cannot
  confirm HTML/XML or redirected TXT reports.

## Runtime menu catalog, 2026-10-17

- Find and natively qualify a read-only enumeration of the merged menu tree
  and View|Panels entries before adding `include_runtime` or claiming a
  complete live panel catalog. The documented GUI manager only supports
  lookup by known launcher/panel ID, and the Windows accessibility tree
  exposes dynamic submenu entries after the menu is opened.

## Installed RCS catalog follow-up, 2026-10-17

- `app_dump_menu_tree` and `app_read_resource_file` expose factory menu
  definitions without focus. To claim live menu completeness, add a read-only
  GUI manager query for user customisations, extension entries and dynamic
  menus. `app_list_panel_catalog` currently returns only statically discoverable
  panel launchers; default dock and editor filters remain unknown.

## External 3-D comparison request, 2026-10-16

- Qualify multi-designator and net selection after native PCB selection passes
  readback. `pcb_select` now accepts both selectors and returns read-only
  target bounding boxes, but truthfully reports `selected=false`. The
  documented `SetState_Selected(True)` setter also failed live FD4 readback.

- Natively validate the new PCB `generic.zoom_to_xy` rectangle zoom on a
  disposable board after the hung Altium is restarted. Source tests and
  Pascal lint pass; the old modal `PCB:Jump` call is gone from main.
- Repair PCB selection: on the owner's board `pcb_select("FD4")` reported one
  match but read-back returned `Selected=false`. The tab showed `*` while
  `app_get_active_document` said `modified=false`; the cause of the star is
  uncertain because the owner was active. The live Python wrapper is disabled.
  Candidate `2026.10.16.3` introduces `pcb.select_component` and two-stage
  read-back. After the owner authorized discarding disposable test edits, native
  tests on FD4, C126 and C128 returned `SELECTION_FAILED`; separate reads showed
  `Selected=false`. Find another native selection mechanism and qualify it
  before enabling this tool for 3-D zoom workflows.
- Design and qualify a bridge lifecycle that releases the scripting engine
  between calls. `app_detach` stops the worker while retaining HTTP, and
  `app_attach` now restarts it through the local URI launcher; a live
  detach/attach/ping sequence passed. Per-call or idle release remains open.
- Find and natively qualify an absolute 3-D camera API before promising
  get/set, arbitrary-angle rotate, orientation-preserving fit, or repeatable
  image scale. `pcb_render_2d` now writes a deterministic selected-layer PNG
  from live geometry for a requested rectangle; compare its pixels only with
  a renderer using matching geometry, palette, fonts and rasterizer settings.
  Keyboard-based `pcb_3d_set_view` now supports 30-degree angle steps and
  discrete zoom relative to Fit Board; `pcb_3d_center` preserves the current
  angle on the tested editor. These controls have no camera readback.
- Validate `pcb_3d_capture` against multiple windows and view modes; current
  capture is a current-canvas PNG with `view_mode_verified: false` and Altium's
  floating canvas toolbar may be visible.

## Local integration follow-up, 2026-10-14

- Qualify project close/reopen invalidation and the optional edit modes before
  enabling them in a deployed runtime. The read-only UI and sample PCB reads
  passed in a separate native test profile.
- Direct Altium quit with the integrated timer pump exited without a Windows
  crash or hang event. MCP detach, dashboard close, Detach button, and
  stop-file shutdown passed locally. Investigate the missing `_session_end`
  record on direct host quit before claiming graceful logging for that path.
- The companion PLT-hw shared-projects runbook is not present in this local
  workspace, so any shared-runtime deployment remains outside this check.


Updated 2026-09-09. Base `1b60105cbe0c4bd557007b87bc04dda2fd4ef9a1`,
package 0.5.0. Named profiles remain `2026.09.08.1`; shared source/runtime is
`2026.09.08.2` plus recorded UI patches. The `.1` shutdown observations below
are historical evidence, not a claim that `.2` fixes direct quit.
Focused Altium/PLT integration backlog, not a full upstream audit.
Distinguish reproduced Python behavior, source-level risks and native acceptance.
These items do not authorize CAD writes or enabling additional tools.
Current deployment/test evidence and agent memory: [handoff](docs/CURRENT-STATE.md).

Execution order: [read/write delivery gates](docs/PROJECT-SELECTION-AND-WRITES.md#delivery-plan-and-release-gates-2026-09-09).
First target is qualified metadata editing (Gates 0-3), then values/footprints and
annotation/variants separately. Missing Start report resolved: the screenshot was
the Projects panel, not Run Script; operator started the candidate and live
ping/discovery passed. The expected-22p full-read test stopped before content
reads when selection changed to cyber80. Complete candidate read/visual/stop
acceptance; do not enable writes or overwrite loaded scripts. Subsequent 22p
generation-4 checks passed all eight tools; see the current-state handoff.

## P0: Native shutdown qualification

2026-09-09 update: operator confirms the short close/reopen and
Detach/quit/restart checks completed. Exact cycles/logs not supplied; remaining
matrix items below are not closed by that confirmation. See current-state handoff.

Progress: 22p live reads on `2026.09.08.1`, no-save stop acknowledgement and one
operator-confirmed normal quit after stopping passed. **Quit while running FAILED
on that same patched revision**, with `ScriptingSystem.DLL` access violation at
read address `0x78` and no end/abort log. Details are in the shutdown log below.

**2026-09-23  -  reproduced on `2026.09.23.1`, and this time the CALL SITE is
known.** Operator quit Altium with the bridge still attached. Identical fault
(`ScriptingSystem.DLL`, read of `0x78`), and the debugger stopped on
`Dispatcher.pas` **`If Client.IsQuitting Then`** inside `MCPHostAvailable`.
Three things follow:

- **`Client` is already destroyed when we ask it whether it is quitting.**
  `0x78` is a field/vtable offset off a nil-or-freed interface, so the guard
  dereferences the very object whose death it exists to detect. It cannot work
  in its current form.
- **The surrounding `Try/Except` does not catch it.** That call is already
  wrapped, and the process still died  -  an access violation raised inside a
  native DLL is not recoverable by DelphiScript's exception handling. The
  source comment directly above the call predicted exactly this: *"These checks
  cannot recover a VM destroyed inside that native call."* The prediction is
  now measured rather than assumed.
- **The shutdown guards deployed since 09-09 did not fix it**, which the
  matrix should stop implying.

**This re-frames §8 of `docs/DESIGN-event-driven-dispatch.md`**, which worried
that a live timer at quit "may be a *new* crash surface, where today the answer
is the blunt but effective stop-the-bridge-first". Quit-while-running already
crashes today, so it is an *existing* surface, not a new one. **P3's bar is
therefore "no worse than today", not "clean"**  -  and the operator rule stands
either way: stop the bridge before quitting Altium.

- [ ] **P0 CONFIRMED live interference: Ctrl+Z swallowed while attached,
  REPLAYED as a burst on detach (operator, 2026-09-14).** With the
  bridge attached, Ctrl+Z does nothing (Edit-menu Undo works); when the
  bridge detaches, the queued Ctrl+Z presses all fire at once. The
  attached/detached A/B is the operator's own observation - this is
  bridge-correlated, unlike the exonerated ratsnest case. DANGER: the
  deferred undo burst can silently revert edits made after the ignored
  presses - CAD-corruption class. Source-level analysis (2026-09-15)
  excluded three candidates: no KeyPreview/TMessageFilter/WM_KEYDOWN
  handler exists in any scripts/altium/*.pas, so nothing in our code
  intercepts keys; the status form never calls SetFocus or Activate, it
  only Shows (StatusForm.pas:682), so pure focus-steal cannot explain
  the detach burst because keys typed into a form control would die
  there; and loop cleanup does not pump UI events
  (Dispatcher.pas:540-557), so the burst is not our final pump. Two
  mechanisms remain, both Altium-side: (H1) Altium defers
  accelerator-key processing while a script owns the message loop and
  flushes at script end, which also explains why Edit-menu Undo works
  because menus dispatch commands directly; or (H2) the script-context
  Application.ProcessMessages only drains VCL-form messages, so
  editor-bound keystrokes back up in the queue and flush when Altium's
  normal loop resumes after detach. The attached loop is a tight
  UI-thread pump (Dispatcher.pas:367, 477-531). Discriminator for the
  next bench window: with the bridge attached, press harmless editor
  keys (arrows/space to pan). If they respond immediately, only
  accelerators are deferred (H1) and form/focus tweaks cannot fix it;
  if they also lag until detach, the backlog is general (H2) and the
  TTimer-based event-driven dispatch already deferred in SHUTDOWN.md
  becomes the fix path. Remaining fix candidates for the next dev
  window: make the bridge form non-focusable or windowless-timer based;
  explicitly return focus to the editor after every handled command; on
  shutdown, FLUSH (discard) queued keyboard messages instead of pumping
  them. Operator
  guidance until fixed (also in SHARED-PROJECTS.md): never Ctrl+Z while
  attached (use the Edit menu); if pressed anyway, after detach check
  the board and Ctrl+Y back any unwanted reverts before continuing.
  - **⚠ OPERATOR EVIDENCE 2026-09-23 (Stefan): Ctrl+Z fails with the bridge
    IDLE too. That settles the starvation question  -  it is not starvation.**
    Idle pumps `ProcessMessages` about every 6 ms (see the rates below), which
    is effectively continuous, and the keystroke still does not land. The
    message queue is being drained; the problem is **dispatch**, not backlog.
    Every yield-tuning and poll-interval fix is therefore excluded, and the
    idle-vs-active discriminator below is answered without needing the bench.
  - **The remaining ambiguity, and the experiment that ends it.** On detach
    **two things change at once**: the polling loop exits *and*
    `HideStatusForm` runs (`Dispatcher.pas`, shutdown path). No test so far has
    changed only one, which is the whole reason "running script" vs "the form"
    has stayed open. `ShowStatusForm` takes a `Dummy` parameter, so it is
    hidden from the Run Script dialog and the form could not be shown without
    starting the loop.
    **Added `ShowStatusFormDiagnostic` (parameterless, so it lists next to
    `StartMCPServer`): shows the form and returns immediately  -  no loop, no
    script left running, no CAD touched.** Then press Ctrl+Z in the editor:
    - **Still broken → the FORM is responsible.** VCL `Show` activates the
      window, making it `Screen.ActiveForm`, and shortcut dispatch resolves
      against a form that has no Undo. Fix is activation: show without
      activating (`SW_SHOWNOACTIVATE`), or return activation to Altium.
    - **Fine → the form is exonerated**, the running script owning the thread
      is the cause, and flush-on-shutdown / TTimer dispatch is the path.
    - If the form vanishes when the call returns, that is its own finding.

  - **✅ P1 ANSWERED 2026-09-23 (operator, live on the 22p): UNDO WORKS.**
    `ShowStatusFormDiagnostic` run with no bridge attached; the form was up and
    the script had returned; a silkscreen nudge in the PcbDoc was undone by
    **Ctrl+Z normally**. Also settles the sub-question: **the form DID outlive
    the call that showed it**, so the script VM survives a return  -  the
    prerequisite P2 depends on.

    **Two consequences, both load-bearing:**
    1. **The form is exonerated, and every activation-based fix is DEAD.** Do
       not build `SW_SHOWNOACTIVATE`, do not hand activation back to Altium, do
       not touch `FormStyle`/`fsStayOnTop` for this. The form is shown,
       activated and on top during the passing test. That whole branch is
       closed  -  it was the cheap fix, and it is not available.
    **Honest weighting of what P1 added** (operator raised it, and it is a fair
    challenge): undo has always worked with nothing attached, so the *new*
    state here was narrow  -  the form shown, activated and on top **without the
    script running**, which had never been possible before because
    `ShowStatusForm`'s `Dummy` parameter hides it from the Run Script dialog.
    And the activation theory was already implausible from the earlier
    minimized result, since a minimized window is not the active one. So the
    Ctrl+Z half of P1 converted a strong inference into a direct measurement
    rather than discovering anything. **The half that was genuinely
    load-bearing is the other one: the form outlived the call**, which was a
    listed open outcome and is the precondition P2 would have been meaningless
    without.

    2. **The running script owning the main thread is CONFIRMED as the cause**,
       now by direct elimination rather than inference. The discrimination is
       complete:
       fails idle (not starvation), fails minimized (not focus), menu undo
       works (not the action system), presses replay on detach (buffered, not
       swallowed), and **the form alone is harmless (not the form)**. Nothing
       is left but "a script holding the thread defers keyboard-to-command
       dispatch", and the only cure is not holding it.

    **This makes P2 the whole ballgame.** The redesign is no longer one of
    several candidate fixes; it is the only remaining one that addresses the
    cause, with the untested `OnMessage` hook as the sole fallback.

  - **✅ P2 ANSWERED 2026-09-23, SAME SESSION: THE TIMER FIRES. The redesign is
    buildable and `docs/DESIGN-event-driven-dispatch.md` §3-§7 are unblocked.**
    `ShowStatusFormTimerProbe` armed a 1 s `TTimer` and returned; it kept
    ticking with no script running. Measured **externally** rather than by eye,
    by sampling the form's window caption  -  `GetWindowText` against another
    process reads the cached caption without sending a message, so the probe
    could not be perturbed or hung by the act of measuring it:
    - **1.00 ticks/s**, 40 ticks over 40.0 s of wall clock  -  exactly the
      configured interval, not merely "firing".
    - **While MINIMIZED**, which is the state Ctrl+Z fails in, so the timer
      path is unaffected by the thing that breaks the keyboard path.
    - **No drift or starvation:** the form's own elapsed counter advanced 40 s
      against 40 s external. Had it fired but been starved, this is where it
      would have shown, and it is why the probe reports elapsed beside count.
    - **Self-bounding verified:** stopped exactly at the 120-tick cap and the
      caption stayed frozen across a further 25 s.

    **Both P0s now have one shared fix with its prerequisite met.** Keyboard
    dispatch is deferred because a script holds the thread (P1), and a timer
    can carry the work without holding it (P2). The `OnMessage` fallback
    (Mitigation A′) is no longer needed and should not be built.

    **Still required before merging the rework**, and not excused by P2: the
    §6 re-entrancy guard, §8's consecutive-failure counter, the
    `StatusFormClose` teardown ordering (already landed), and a full native
    acceptance pass  -  every existing acceptance result was obtained against the
    polling loop, so this is a new execution model, not a diff.

    **P3 is the only prerequisite left.**

  - **✅✅ 2026-09-24: THE Ctrl+Z P0 IS FIXED. Operator-verified live on script
    `2026.09.24.2`.** Both halves of the acceptance criterion recorded on
    2026-09-23 before any code was written:
    - **"a press must undo at that moment"**  -  operator: *"ctrlz works!"*
    - **"detaching must produce no burst at all"**  -  operator: *"nothing moved
      when detatching, no queded undos since they happen"*

    Nothing was softened. The second half is the one that killed every earlier
    candidate fix, and it passed clean.
    - **The ordering question is SETTLED, and the rule does not apply.**
      `StatusForm.pas` is document 11 of the deployed runtime and
      `Dispatcher.pas` is 14; the forward call compiled and ran, logging
      `_tick_first` 67 ms after `_session_start`. So "a callee must come
      earlier than its caller" is real **only** for `build.py`'s concatenated
      `Altium_MCP.pas`, never across PrjScr documents. Two earlier answers to
      this were wrong in opposite directions; the live test cost 30 seconds
      and should have been run on 2026-09-23.
    - **Pacing is not a regression.** `pcb.get_object_classes` took 4281 ms
      under timer dispatch against 3985/3922/3922/4125 ms on the blocking
      loop  -  one sample against four, with a dirty board. The runbook's
      "well under a second" expectation was simply wrong; this read is ~4 s on
      both runtimes.
    - **The caption warning is REMOVED** (`KeyboardWarningSuffix` now returns
      empty, kept as a function so restoring it is one line). An operator who
      learns the caption lies about one thing stops trusting it about the
      others. Script bumped to `2026.09.24.3` for that change.
    - **Guards that earned their place.** `_tick_first` is what turned "is it
      running?" into a one-line answer, and the DFM-binding test would have
      caught the silent failure that cost a cycle. Keep both.
    - **NOT closed by this:** the shutdown crash (quit-while-attached still
      AVs), and `Library.pas`'s three `Application.ProcessMessages` calls
      inside handlers, which this test did not exercise.
    - **Gate 4 read re-qualification: PASSED 2026-09-24** on script
      `2026.09.24.2`, board saved (`dirty_doc_count: 0`). Every stable metric
      matches its baseline exactly: `erc` **187**, `bom` **172**, `rooms`
      **0**, `rules --expect` **1 matched / 3 mismatched / 8 missing**,
      `objectclasses` **18 classes, 11 counts_unreliable**,
      `nets --designator R404` PA0/LNSW[0]. All six `audit` checks ran in
      78-1437 ms - that is the one exercising `Library.pas`, the path this fix
      does NOT touch, so it was the one that mattered.
      - Three audit numbers moved against the **2026-09-14** checkpoint, all
        downward: via_antennas 16 -> 12, signal_vias_without_return 72 -> 53,
        pads_near_edge 2 -> 0. That baseline is ten days and a lot of layout
        old, so these are near-certainly real board changes, not read
        differences. **A strict A/B - the same board read through the old
        runtime - was NOT done**; it costs a full script swap. The case rests
        on every stable metric matching.
    - **Shutdown, 2026-09-24: the AV did not reproduce, and that is one
      observation, not a fix.** Operator quit Altium with the bridge attached
      (*"closing altium with mcp running now also seem to work"*), and
      confirmed on follow-up that there was **no error dialog at all**
      (*"no error when closing altium"*). That distinction was asked for
      deliberately: "no dialog" and "a dialog I dismissed" are different
      results. **0 orphan IPC files** left behind.
      - **But `FinaliseMCPServer` never ran.** Session 2 opened 12:10:24, last
        entry 12:12:09, then the log simply stops - no `_session_end` and no
        `_session_aborted`. Altium exited and took the script with it before a
        tick could finalise. So the state moved from "AV + no end log" to "no
        AV + no end log": the crash symptom is gone, graceful teardown is not
        achieved.
      - **QUIT #2, 2026-09-24, script `2026.09.24.3`: same result.** Operator
        confirmed the bridge was active at exit and there was no error dialog
        (*"no error and MCP was active when exiting"*). The session log again
        stops mid-stream - last entry a `pcb.get_clearance_violations` at
        13:13:06 - with no `_session_end` and no `_session_aborted`. So the
        signature is stable across two runtimes and two quits: **no AV, no
        graceful finalise.**
      - **Do not close this P0 on one quit.** The AV is a race against
        Altium's teardown ordering and a 10 ms tick can miss the window on any
        given run. Repeat the quit 2-3 times before claiming anything.
      - **✅ QUIT #3, 2026-09-24, script `2026.09.24.4`: THE SHUTDOWN P0 IS
        CLOSED.** Operator confirmed no error dialog (*"was there an error
        dialog when Altium exited? - no"*). Session opened 14:08:52 with
        `_tick_first` 38 ms later, served requests until 14:26:54, then the log
        stops. **0 orphan IPC files.** Three consecutive quits, on three
        runtimes, against a baseline that reproduced the AV reliably. The bar
        set two entries above - "repeat the quit 2-3 times" - is met.
      - **The missing `_session_end` is explained and is NOT a defect.**
        Altium tears the script engine down without granting a final tick, so
        the finaliser cannot run on exit. It runs on every Detach
        (`reason=stop-requested`, observed the same day at 14:08:30). Nothing
        leaks: zero orphan `request_`/`response_`/`progress_` files across all
        three quits, which is the property the marker would have been evidence
        *for*. Graceful teardown on exit is not achievable from inside the
        script and is not worth further work.
      - The reason it holds is the one predicted: the script no longer holds
        the main thread through teardown - the same root cause as the Ctrl+Z
        P0, fixed by the same change, which is what
        DESIGN-event-driven-dispatch.md section 1 meant by "two P0s, one piece
        of work".
      - **Residual risk, recorded not hidden:** "did not reproduce over three
        trials" is weaker than "fixed". The native object lifetime behind the
        original AV was never identified, only avoided. If it returns, look for
        something reacquiring a host object after teardown begins.
    - **P3 is still NOT done** - closing the *form* with its X while ticks run
      is a narrower case than quitting Altium and has not been exercised.
    - **Qualification is INCOMPLETE.** Gate 4's compiled reads (`nets`,
      Gate 4 has now passed (above), but P3 has not run and the shutdown
      result needs repeating. `ACTIVE-RUNTIME.txt` therefore still points at
      `selected-readonly-classes-20260923`.
    - **The genuine finding from the earlier wrong turn.** There are TWO
      `Altium_API.PrjScr` files with different orders and the repo's is not
      the one that compiles. `lint.py`'s `PAS_FILES` matches the DEPLOYED
      order, so its cross-file rule was validating the right thing all along.
      `test_manage_shared_runtime.py::DeployedCompileOrderTests` pins the
      deployed sequence and fails if the two lists drift apart.
    - **Guards added, because rule 3 fails SILENTLY.**
      `test_pas_project_consistency.py` now fails if any `StatusForm.dfm`
      handler names a procedure `StatusForm.pas` does not define  -  verified to
      fail when deliberately broken. `MCPTimerTick` logs `_tick_first`, so
      "armed but never fired" is distinguishable from "fired and something
      else broke". `test_dispatcher_shutdown.py` asserts `Dispatcher.pas`
      contains **zero** `Application.ProcessMessages`.
    - **`MCPYield` deleted.** Nothing called it under timer dispatch, and it
      wrapped the file's only message-pump call  -  an unused helper for the
      exact operation that causes this P0 is a landmine, not dead weight.
    - **Residual, NOT fixed and not to be forgotten:** `Library.pas` calls
      `Application.ProcessMessages` three times inside handlers. Those run
      *during* a tick and can still defer keyboard dispatch for the duration
      of a library command. The acceptance test below exercises PCB reads, so
      **a pass does not clear the library path.** Separate item.
    - **Follow-up, deliberately not bundled:** `StatusFormClose` still leaves
      `tmr_MCP` running for one tick and lets that tick finalise, rather than
      calling `FinaliseMCPServer` directly. Direct calling would now compile  -
      the scope argument that ruled it out was the false one  -  but finalise
      calls `HideStatusForm`, so it would hide the form from inside that
      form's own `OnClose`. Untested re-entrant path; bundling it would
      confound the one test this deploy exists to run.

  - **BEFORE-baseline recorded on `2026.09.23.1` (operator, 2026-09-23), the
    revision the rework will be compared against.** With the bridge attached:
    **Ctrl+Z does nothing; on detach every buffered press fires at once, and
    the keyboard works normally again immediately afterwards.** Unchanged from
    the 09-14 observation, so the new runtime altered nothing here  -  which is
    what makes it a usable baseline rather than just a re-confirmation.
    - **Acceptance criterion for the rework, stated now so it cannot be
      softened later:** with the bridge attached, a Ctrl+Z press must undo
      *at that moment*, and detaching must produce **no burst at all**. "Fewer
      undos on detach" is a fail, not progress.
    - **How the test was driven, and a correction to an earlier reading of
      it.** The operator used a via moved back and forth as the undoable
      action  -  a good choice, since a moved via is obvious on sight and
      trivially reversible. The 22p `PcbDoc` did go from clean-in-git
      (`pcb_modified: false` at 18:16) to modified on disk at 19:13, but
      **that was the deliberate via manipulation, not the undo burst.** An
      earlier draft of this entry implied the burst had silently altered the
      board; it did not, and no instance of that has actually been observed.
    - **The hazard is still real, just unwitnessed:** a burst firing into a
      board followed by a save is the mechanism by which deferred keypresses
      would become persistent changes, and nothing about the measured
      behaviour rules it out. Keep CAD committed before a bridge session  -
      cheap insurance, and it is what made this test safe to run at all.
  - **✅ RESOLVED TO A CAUSE CLASS 2026-09-23 (operator bench, current
    runtime). The minimize test came back: still dead.** Combined with the
    other observations, the hypothesis space is now closed:

    | Observation | Eliminates |
    |---|---|
    | Fails while **idle** (~6 ms pumping) | Message-queue starvation. Yield tuning, poll intervals  -  all dead |
    | Fails while the form is **minimized** | Form activation / `Screen.ActiveForm`. `SW_SHOWNOACTIVATE` and focus-returning fixes  -  all dead |
    | **Menu** undo works throughout | The undo command, the action system, and Altium's UI generally. Nothing is frozen |
    | Presses **replay on detach** | "Swallowed" / consumed. They are **buffered**, faithfully, and flush when the script ends |

    **Cause class: the script owning the main thread defers keyboard-to-command
    dispatch.** `Application.ProcessMessages` is not a substitute for Altium's
    own message loop for this path. Nothing about the form, the focus, or the
    poll rate can fix it  -  **only not blocking the thread can.**

  - **Feasibility checked 2026-09-23 before scoping the redesign.**
    `StatusForm.dfm` is a real Delphi form resource and the form already binds
    handlers by name (`StatusFormClose`), so **a TTimer can be added as a form
    component with its `OnTimer` bound the same way**  -  which matters, because
    creating a timer and assigning an event handler purely at runtime is not
    something DelphiScript can be relied on to do. There is no `TTimer`
    anywhere in the project today, so this is new ground.
    **Consequence for scoping: the redesign touches the .dfm, not only Pascal**,
    and every local the loop carries across iterations (`IdleCount`,
    `CurrentSleep`, `LastActivityMs`, `ActiveTickCount`, `HadRequest`,
    `LoopFailed`) has to become module state that survives between ticks. The
    post-loop shutdown block becomes a separate finalise path triggered when
    `Running` goes false. **Design it before coding it**  -  the shutdown path is
    the delicate part and already has its own P0 section above.
  - **DESIGN WRITTEN 2026-09-23:
    [docs/DESIGN-event-driven-dispatch.md](docs/DESIGN-event-driven-dispatch.md)**
     -  architecture, the state-migration table, re-entrancy guard, finalise
    order, and what could make it worse. **Gated on a staged prerequisite: P1
    (does a form outlive the call that showed it) is free and already rides
    this deploy window via `ShowStatusFormDiagnostic`; P2 (does a TTimer on
    that form still FIRE after the return) is the real gate.** If P2 fails the
    timer bridge is dead and the honest fallback is the blocking loop plus
    flush-on-shutdown. Do not code past the gate.
  - **So the real fix is the event-driven redesign, not a tweak.** Replace the
    blocking `StartMCPServer` loop with **TTimer-driven dispatch** (already
    deferred once in SHUTDOWN.md): the script returns, Altium's own message
    loop runs continuously, and the keyboard behaves normally because nothing
    is blocked. This is the only option the evidence leaves standing as an
    actual fix. It is real work  -  the whole poll/yield/stop/auto-shutdown
    structure moves into timer ticks, and the shutdown path is the delicate
    part  -  so scope it deliberately.

  - ~~**Mitigation A, flush queued input on shutdown.**~~ **DEAD as specified  -
    unbuildable, established 2026-09-23 from the repo, no bench time needed.**
    The mitigation was `PeekMessage`/`PM_REMOVE` over the key messages before
    the script ends. Every one of those lives in **user32**, and
    `Project.pas:2145` already records the blocker from the screenshot work:
    *"DelphiScript blocks `external` DLL imports, so user32/gdi32 calls aren't
    reachable from a script."* `GetKeyState` is out for the same reason. So the
    flush cannot be written in this environment at all  -  it was never gated on
    *where* the buffering lives.
    - **Consequence: the 5-press count is demoted from a decision to a
      curiosity.** It existed only to choose whether to build Mitigation A, and
      that choice is gone. Do not spend bench time on it. **P2 is now the only
      thing standing between us and knowing whether this is fixable.**
    - **Its logic was also weak, worth recording so it is not revived
      unexamined.** "Exactly 5 means command-level" does not follow: five raw
      `WM_KEYDOWN` sitting in the thread queue also dispatch as five undos. The
      "exactly 5" branch is consistent with *both* levels and discriminates
      nothing. Only *fewer* than 5 would have been informative, by showing
      coalescing.

  - **Mitigation A', the surviving candidate if P2 fails  -  `OnMessage` hook,
    UNTESTED.** Recorded now so a failed P2 does not leave an empty page.
    VCL's `Application.OnMessage` fires *before* dispatch and takes a `Handled`
    var param, so swallowing the press is possible without ever removing it
    from the queue by hand  -  no user32, no `external`.
    - **Why it is plausible:** the Ctrl state does not need `GetKeyState`
      either. The hook sees `WM_KEYDOWN`/`WM_KEYUP` for `VK_CONTROL` ($11) go
      past, so it can track a `CtrlDown` boolean itself and swallow `VK_Z`
      ($5A) while that flag is set. Constants as literals, since an undeclared
      identifier is fatal here.
    - **Why it may still die:** it needs `TApplicationEvents` to load from the
      DFM the way `TTimer` does  -  wiring `OnMessage` at runtime means assigning
      a procedure reference, which DelphiScript handles badly. The DFM route is
      the proven one (`tmr_Spinner`, and now `tmr_Probe`), so probe it that way
      or not at all.
    - **Do not build this before P2 reports.** If P2 passes, the redesign fixes
      the keyboard properly and this is unnecessary work on a dead end.

  - **Mitigation B, make the hazard visible  -  trivial, do it regardless.** The
    failure mode needs the operator to *forget* that a press was ignored. The
    status form already updates every tick; a permanent, prominent line like
    "KEYBOARD UNDO DISABLED WHILE ATTACHED - use Edit menu" converts a silent
    trap into a visible constraint. It does not fix anything and should not
    delay the redesign, but it costs almost nothing and addresses the half of
    the failure that is human.

  - ~~**A test available TODAY, no deploy needed  -  run this first.**~~ **DONE,
    result above.**
    `ShowStatusFormDiagnostic` needs the new runtime, but activation can be
    changed on the CURRENT build without it. **Do not close the status form to
    try this: `StatusFormClose` sets `Running := False`, so closing it stops
    the bridge and changes both variables again.** Minimizing does not.
    1. Bridge attached and **idle**. **Minimize** the status form.
    2. Click into the PCB canvas so Altium certainly has focus.
    3. Press Ctrl+Z.
    - **Undo works while minimized → activation is the mechanism.** The form
      was holding it. Fix is `SW_SHOWNOACTIVATE` / returning activation, and
      `ShowStatusFormDiagnostic` then just confirms it.
    - **Undo still dead → the form is NOT holding focus**, since a minimized
      window is not the active one. That kills the activation theory without
      a deploy and leaves the running script owning the thread  -  build
      flush-on-shutdown and skip the activation work entirely.
    - Also worth recording: whether Ctrl+Z fails when the PCB canvas was
      *just clicked*. If it does, the form is demonstrably not where focus is.
  - **Pump rates measured from the source, 2026-09-23  -  and they argue the
    obvious fix is a dead end.** `MCPYield` is exactly
    `Application.ProcessMessages` plus stop checks, and the loop calls it at
    two very different rates (defaults from `Main.pas InitDefaultConfig`):
    - **Idle:** `PollIntervalIdleMs` 30 split across `YieldIterations` 5, so
      **ProcessMessages roughly every 6 ms**.
    - **Active:** `PollIntervalActiveMs` 10 with `YieldEveryNActive` 5, so
      **ProcessMessages roughly every 50 ms**.
    An 8x difference  -  but **starvation at either rate would delay a keystroke
    by tens of milliseconds, not hold it until detach.** Queued input drains on
    the next `ProcessMessages`; it does not accumulate for minutes. So
    "yield more often" is very unlikely to be the fix, and building it would
    spend a deploy-and-qualify cycle to learn that.
  - **An inference that narrows it without a bench, stated with its
    assumption.** Auto-shutdown is 10 minutes, so an attached bridge sits
    **idle** for most of any CAD session  -  i.e. pumping every ~6 ms, which is
    effectively continuous. If Stefan's Ctrl+Z presses mostly land in that
    idle window (they almost certainly do; he is editing, not driving the
    bridge), then keys are being swallowed *while the message queue is being
    drained constantly*. That is not starvation. It points at **H2**:
    `ProcessMessages` drains the VCL queue, but Altium dispatches Ctrl+Z
    through its own accelerator/action path, which is not running while the
    script owns the thread.
  - **So sharpen the discriminator**: the arrows/space test above tells
    accelerator-vs-general, which is useful, but the cheaper and more decisive
    one is **idle vs active**. Press Ctrl+Z with the bridge attached and
    quiet, then again while a long read is running. **Same behaviour in both =
    pump rate is irrelevant = H2**, and every focus/yield-tuning fix is
    excluded in one test. Different behaviour = starvation after all.
  - **This also promotes flush-on-shutdown from one candidate among several to
    the mitigation worth building first**, because it is the only one that
    works whichever hypothesis wins: discarding queued key messages as the
    loop exits turns a silent undo burst into keystrokes that were already
    lost. Losing a keypress the operator knows was ignored is strictly safer
    than replaying it into a board minutes later. Verify `PeekMessage` with
    `PM_REMOVE` is reachable from DelphiScript before committing to it.
- [ ] **Suspected live interference: stale ratsnest during CAD with the
  loop running (reported by operator 2026-09-10 ~09:45).** Connection
  lines with break markers not following component moves in the first
  real PCB-editing session with a bridge loop active; operator suspects
  onset coincides with MCP adoption. Candidate mechanisms: (a) the
  polling loop starving the interactive engine's connection recalc,
  (b) the compiled reads' DM_Compile at 09:31 pushing net updates into an
  open PcbDoc (known Altium stale-line trigger), (c) native Altium
  ratsnest staleness, coincidental. Connection DATA was self-consistent
  at 09:26 (unrouted read validated). **A/B RESULT (~10:00): issue
  persists after a full Altium restart with NO bridge running: the
  polling loop is exonerated as the live cause.** Stale lines also
  survived PcbDoc close/reopen and Clean All Nets, so the state is in
  the saved file or is a native bug. Remaining bridge-related suspect is
  one-time: the 09:31 compiled-read DM_Compile into the open PcbDoc,
  saved shortly after. Interim guidance stands and is now precautionary:
  prefer PCB reads over compiled reads during active board editing;
  compiled reads at operator save points only. Next: ECO-dialog probe
  (Import Changes, read-only inspection) to see whether board nets
  desynced; known-good PcbDoc exists in git (yesterday's commit) as the
  bounded fallback.
- [ ] **Idle-timeout pin anomaly (observed 2026-09-09 16:16):** the bridge
  session started 16:05:56 idle-timed-out after exactly 600.0 s (last request
  16:06:36.8, `_session_end reason=idle-timeout` 16:16:36.9) despite the
  60-minute pin; `mcp_config.json` on disk held `3600000` (mtime 15:11:47,
  the connect-time re-pin). The earlier 15:11 session survived 53 min idle
  before a clean `stop-requested` end at 16:05:47, so the pin worked at least
  once. Hypotheses to check on a non-CAD day: does the Pascal side re-read
  the config on client connect and race the wheel's default rewrite against
  `apply_auto_shutdown`'s re-pin, or does a bridge restart read something
  other than the pinned file? Evidence: batch-20260909 `workspace/activity.log`.
- [ ] **2026-09-09 wind-down evidence (positive):** deliberate stop at
  16:05:47 (`reason=stop-requested`, 9 s later a fresh session served reads),
  first live helper-stop data point; and after the 16:16 idle-timeout exit,
  Altium was closed with **no crash in the Windows event log** (contrast the
  11:50:51 heap-corruption signature that followed an idle-timeout exit).
  Only unrelated LiveKernelEvent WER entries (P1 124/1cc, 15:49:56):
  machine-level, not Altium. Count toward the shutdown matrix rows.
- [ ] Complete [the shutdown matrix](docs/SHUTDOWN.md) on disposable CAD:
  new-version ping/read, explicit no-save stop, native Detach/Close, repeated
  restart cycles, paused/active/idle stop and timeout. Test quit while running
  only after a separately reviewed lifecycle change; do not repeat the known failure.
  Require fresh session-end evidence and no native crash. Source checks are
  not native Pascal execution. Do not call the candidate a proven quit fix.
- [x] Capture patched failure location: operator screenshot shows deployed
  `Dispatcher.pas:325`, `If Client.IsQuitting Then`, with Dispatcher left under
  Free Documents. This is the new host-state check, not the old Sleep line.
- [ ] Investigate the reproduced direct-quit failure: obtain native stack/object
  lifetime evidence, check debugger exception behavior and supported earlier
  shutdown/lifecycle/event-driven dispatch.
  Do not assume the interpreter's exact failure point from its address, or add
  arbitrary sleep delays. Current post-yield guards are insufficient.
- [x] Prepare a separate no-CAD/no-MCP [shutdown probe](diagnostics/shutdown-probe/README.md)
  with local-stop-first ordering and form-close/yield event logs. No production
  bridge code changed by this experiment.
- [x] Run probe A (Stop button baseline), inspect its log, then probe B (normal
  Altium quit with only the diagnostic running). A recorded clean loop completion;
  B left Altium open, source under Free Documents and Run > Stop disabled. Last
  log event was `before_yield`; operator force-closed. No AV dialog was captured
  for B. See [probe evidence](docs/SHUTDOWN.md#standalone-probe-results-2026-09-08).
- [ ] Deferred while qualifying stop-first use: prepare a separate timer-only lifetime probe: startup returns, no polling
  loop/manual UI pump, no CAD/MCP. Verify callback survival first, then explicit
  Stop and normal quit. Timer support alone does not establish safe lifetime.

## P1: Trustworthy read responses

- [x] Validate BOM/net response schemas at the normal tool boundary, not only
  in the smoke test: required lists/row fields, count/list consistency and
  truncation/completeness. Treat unexpectedly empty known-populated designs as
  failed extraction; support genuinely empty projects explicitly.
  **Isolated fake reproduction:** the PLT wrapper accepts empty BOM/net lists
  and even `{"count":172}` without a component list. Native Altium was not used.
  The wrapper lives in companion PLT-hw `tools/eda-agent/project_server.py`;
  coordinate changes to its installed client snapshots.
  **Implemented/deployed client-only update:** reject malformed rows/counts,
  truncation/limit hits and unexpected emptiness. Genuine empty designs need an
  explicit local profile expectation; installed PLT profiles have none. Blank
  metadata/unconnected net strings remain visible. 48 combined offline tests and
  both nine-tool startup checks pass. Updated 22p live reads passed at 21:55-21:56
  with 172 components/559 pin entries and valid schemas. This does not
  fix native enumeration omissions or the separate offline extractor.
- [x] Return compile outcome and physical-versus-logical enumeration mode.
  **Candidate 2026.09.09.1 NATIVELY QUALIFIED 2026-09-09** (runtime
  `selected-readonly-extraction-20260909`, session 20260909125934012, live
  22p reads): extraction block physical/4 docs/zero skips/limit_hit false/
  compile_action delegated on both BOM and nets, strict validation enforcing
  (extraction_checked true), counts 172/559 in parity with the previous
  runtime. Implemented in f285621 + PLT-hw 9f11328. BOM/net responses carry an extraction block
  (enumeration mode, doc_count, skipped-nil counters, limit_hit,
  compile_action); the Python wrapper rejects nonzero skips, truncation,
  logical-multisheet fallback and unrecorded compiles; INCOMPLETE_DOCUMENTS
  now names the identityless document (closes the draft-diagnosability note
  at source). Lint 12/0; all source tests pass including the two previously
  failing wheel force-include checks (SelectedProject.pas added). Remaining:
  create a new dated shared runtime at the next stopped-Altium window
  (create_shared_runtime), native startup + 22p reads verifying the block,
  and a draft test confirming the named-document error. compile_action
  records call completion, not Altium's compile verdict - ECO/ECC stays
  authoritative.
- [x] Fix offline BOM extraction returning a successful empty result
  (fixed 2026-09-09, commit 93f5f4a). Root cause was input handling, not the
  SchDoc reader: a nonexistent path, a non-.SchDoc/.PrjPcb input or a missing
  .PrjPcbStructure returned [] with exit 0, and the offline review turned the
  same cases into a silent clean pass. bom_from_file/review_project_file now
  refuse those (allow_empty/--allow-empty states a genuinely empty design
  explicitly); eight regression tests. Verified against the real project:
  refusals exit 2, 66 lines / 172 parts on the .PrjPcb. Native exports remain
  authoritative for sign-off; the reader itself matched the live BOM count.
- [x] Automate same-snapshot designator and connected-pin/net comparison with
  native exports: companion PLT-hw `tools/eda-agent/compare_native_export.py`
  (commit c00957e) diffs bridge BOM/net dumps against native Protel v1/v2
  exports, reporting missing, mismatched and additional entries separately.
  First snapshot-verified run against the 2026-09-08 Protel2 bundle export:
  172/172 designators, 550/550 shared pins identical, 9 additional single-pin
  bridge entries, 0 mismatches. Content agreement only, not connectivity or
  electrical acceptance. **ODB++ leg landed 2026-09-09**: companion
  `odb_parity.py` (PLT-hw 1173560) parses the ODB++ step and checks
  alias-tolerant net partitions (splits/merges reported separately); first run
  reproduced audit A2 (172/172, 550/550, zero splits/merges, nine single-pin
  nets correctly no-net on the PCB). CI wiring remains open.
- [x] Bulk parameter read - **NATIVELY QUALIFIED 2026-09-09** (runtime
  `selected-readonly-batch-20260909`, session 20260909143632721): full
  172-designator batch matched=172/not_found=[] with byte-equivalence to the
  single-call loop on parameters/footprint/comment for every component; a
  bogus designator correctly returned in not_found. Prepared via the guarded
  cross-version manage_shared_runtime prepare (receipt written). Original
  scope note: shared mode now exposes the reviewed upstream
  `Proj_GetComponentInfoBatch` (uncompiled, parameters-only flags) as ninth
  tool `proj_get_component_info_batch`; the client validates 1-500 unique
  designators and requires every one back as matched or not_found
  (validate_component_batch). Whole-project baseline = two calls (BOM +
  batch). Deploy a new runtime at the next stopped-Altium window and qualify
  live (172-designator batch equals the dump_parameters.py loop output).
  `dump_parameters.py` remains the fallback meanwhile.
- [ ] **Candidate: read-only PCB-document reads: IMPLEMENTED 2026-09-10,
  native qualification pending.** First tranche built the same day it was
  requested: the five upstream read functions split into `...ForBoard` cores
  (wrappers preserve upstream behavior; the shared outline core drops the
  Invalidate/Rebuild/Validate mutation), `ResolveSelectedBoard` in
   SelectedProject.pas resolves the selected project's OWN PcbDoc only,
   exactly one PcbDoc member, already open (fail-closed `PCB_NOT_OPEN`,
   no auto-open/focus change, PCBServer touched only after an open .PcbDoc
   proves the server is loaded), and the dispatcher splices `pcb_doc` +
  `pcb_modified` (live-state honesty) into every result. SCRIPT_VERSION
  `2026.09.10.1`; companion clients grew five `pcb_*` tools with
  `validate_pcb_read` shape checks, `bridge_read.py` subcommands
  placements/outline/stackup/diffpairs with mm companions.
  **Tranche 2 same day (2026.09.10.2, replacing the undeployed .1 runtime):**
  four more reads for copper-policy validation - pcb_get_vias,
  pcb_get_polygons, pcb_get_unrouted_nets (all upstream pure-read splits)
  and pcb_get_layer_primitive_counts, a NEW native reader (primitive counts
  per layer+type via TStringList keyed buckets - the fixed-array return-slot
  bug is documented at PCB_GetUnroutedNets - answering "do the internal GND
  layers hold any routed copper" in one tiny payload). Validators enforce
  bucket/total reconciliation and per-net unrouted sums. 141 companion tests
  pass; fork failed-set diff vs baseline empty. Runtime
  `selected-readonly-pcb-20260910` recreated at .2 (23 files), workspace
  seeded. **PCB reads NATIVELY QUALIFIED 2026-09-10** (deployed at the
  morning Altium start, session 20260910092249830, 22p working project,
  live/dirty PcbDoc): all nine tools returned validated results first run.
  Placement parity vs the 09-08 ODB baseline: 172/172 designators, exact
  positions except three genuinely-moved parts (R427 large move+rotate,
  R423/S101 small nudges - real CAD deltas, not read errors);
  **rotation convention confirmed: bridge reports Altium CCW degrees,
  ODB stores the negation - 171/172 satisfy alt=(360-odb)%360, the one
  exception being the really-rotated R427.** pcb_modified=true correctly
  reported throughout (the dirty guard simultaneously refused compiled
  schematic reads - both honesty paths exercised live). Live findings the
  reads surfaced immediately: current CAD stackup is not the JLC 7628
  values (28 mil core / 10.2 mil prepreg vs 8.3), the single
  DiffPairsRouting rule is placeholder geometry (0.381/0.254 mm, not the
  100R MIPI numbers), six pairs defined (D0-D3, CLK, USB D) all unrouted,
  113 nets / 439 unrouted connections, internal layers hold only the two
  GND pours, and all four GND polygon pours report net='' (operator to
  check pour net assignment - possible real defect or nil-net read quirk).
  **COMPLETE 2026-09-10: compiled bom/nets/parameters regression on the
  saved state matched the 172/559/111-blank baseline exactly;
  ACTIVE-RUNTIME.txt flipped to selected-readonly-pcb-20260910;
  check_install 13/13.** The doctor also caught the idle-timeout pin
  regressed to 600000 on the new runtime's workspace (seeded 3600000,
  wheel rewrite won the race after apply_auto_shutdown) - re-pinned
  manually, and the companion shared_server now ALSO re-pins at process
  exit (atexit) so the file is left pinned for the next bridge start;
  that fix rides in the next runtime, the deployed copy is untouched
  (hash-manifested). New evidence for the timeout-anomaly item: the
  wheel's config rewrite can land after the connect-time re-pin.
  **Race lost AGAIN same day (~10:10 bridge start read 600000; operator
  hit the 10-minute auto-off mid-layout).** Root cause now settled as
  the config-file race; mechanism confirmed twice. Mitigation deployed
  (PLT-hw 68abebe): bridge_read re-pins in its finally block after every
  client run, so the file is pinned whenever no client is running -
  which is when bridge starts happen. Verified live post-run at 3600000.
  The 2026-09-09 600s observations are explained by the same race. The
  remaining proper fix (Pascal-side floor or per-request config re-read)
  rides with the next runtime alongside the atexit hardening.
  **Tranche 3 same day (2026.09.10.3, runtime
  selected-readonly-pcbreads3-20260910, commit 8d7f989):** six more
  purity-reviewed reads - design_rules (all kinds), net_classes,
  trace_lengths (optional net filter), component_pads (placed-pad
  geometry), selected_objects (operator-cooperative), board_statistics
  (flat summary; its core and the outline core drop the upstream
  Invalidate/Rebuild/Validate mutation). Twenty-four tools total; 144
  companion tests pass; fork failed-set diff vs baseline identical; lint
  0/0; the atexit timeout re-pin rides in this runtime's client. Deploy
  at the next natural bridge restart; qualify the six live; flip the
  pointer.
  **Tranches 3-5 NATIVELY QUALIFIED 2026-09-10 midday** (runtime
  selected-readonly-pcbreads3-20260910, script 2026.09.10.5, session
  20260910113737461, live 22p board): all seven new reads first-run valid
  (rules 36, netclasses 1, tracelengths, boardstats, selected 0,
  placements 172, pads U301 48 - the pads read immediately caught U301
  placed 90 deg off the recommended orientation); compiled bom/nets
  regression matched 172/559 on the saved state; **first ERC pull via
  proj_get_erc_messages returned 197 violations in 6 classes, triaged in
  PLT-hw reviews/2026-09-10-erc-triage.md (191 cosmetic/convention, 6
  need operator eyes)**. ACTIVE-RUNTIME.txt flipped; check_install 13/13.
  Known limitation recorded: short-descriptor only (no per-object detail,
  no severity); tracelengths' empty-net bucket includes silk/mech lines
  (AllLayers iterator upstream).
  Original scoping note kept below for the record.
  The shared bridge previously had no PCB-side tools: no component
  X/Y/rotation/layer, no tracks/vias/polygons, no differential-pair or rule
  objects. Layout-phase validation currently goes through the operator-run
  ODB++ OutJob (components + per-layer copper geometry; authoritative but
  only as fresh as the last export) or partial offline PcbDoc parsing.
  Candidate scope, same gate discipline as the schematic reads: selection-
  scoped, read-only `pcb_get_component_placements` (designator, X/Y, rotation,
  layer, footprint), then `pcb_get_diff_pairs`/rules enumeration, then track
  geometry last (large payloads; needs limits + honesty reporting like the
  extraction block). Implement on a non-CAD day; qualify against a
  same-snapshot ODB export before use.
  **Survey 2026-09-10: the native functions already exist upstream**:
  PCB.pas carries PCB_GetComponents, PCB_GetComponentPads,
  PCB_GetDifferentialPairs (pair objects) + PCB_GetDiffPairRules (rules),
  PCB_GetTraceLengths, PCB_GetLayerStackup, PCB_GetBoardOutline,
  PCB_GetPolygons, PCB_GetVias, PCB_GetUnroutedNets,
  PCB_GetClearanceViolations, PCB_RunDRC, PCB_GetBoardStatistics. The real
  adaptation work is (a) **selection scoping**: upstream functions target the
  current/focused board, which our rules forbid: resolve the board from the
  operator-selected project the way SelectedProject.pas does for schematic
  commands, and refuse if the selected project's PcbDoc is not it; (b)
  reviewing each exposed function read-only end-to-end (PCB_RunDRC is a
  compute that touches document state, exclude it from the first pass);
  (c) allow-list + Python validation + version bump + stopped-Altium deploy
  + live qualification vs a same-snapshot ODB export. Comparable in shape
  and effort to the 2026-09-09 item-3/item-4 batch.
- [x] **Audit tranche NATIVELY QUALIFIED 2026-09-10 (2026.09.10.6,
  runtime selected-readonly-audits-20260910, session 20260910121336748,
  pointer flipped, doctor 13/13).** Six/six audits ran and validated on
  the live board; findings coherent (outline/edge/mirrored clean, 2
  mixed-silk pairs = rough-stage noise, 10 via antennas = the known
  not-yet-poured stubs incl. the U207 VCC5V pair, 6 return-via flags =
  the U205 island vias, exempt once the net is renamed VEE_IBB_LOCAL -
  the power-name matcher covers VEE*). One client-side validator bug
  found and fixed (mixed-rotation counts pairs, items list contributors;
  regression test added); the deployed runtime's client was patched
  surgically with backup/manifest/provenance per the selector-patch
  precedent. Bonus: audit data exposed a shorting hazard in the PLT-hw
  floorplan DOCS ("PowerPAD vias to L2" - U205's pad is -3.3V; docs
  corrected, CAD was right).
- [ ] **Phase 2 kickoff candidate (agreed with operator 2026-09-10):
  approval-gated OutJob generation + report parsers.** Solves all three
  documented read limitations at once: an ERC report output carries the
  per-violation detail/severity the DM_ShortDescriptorString API cannot;
  an UNCAPPED DRC report output gives DRC access without exposing the
  state-mutating PCB_RunDRC as a read (the mutation happens inside a
  deliberate generation); and the same trigger refreshes the Validation
  ODB bundle, closing the export-freshness gap. Design: NOT a read -
  Proj_GenerateOutput/Proj_GetOutJobContainers behind a NATIVE
  confirmation dialog in Altium (operator clicks Allow at the machine;
  selector form is the precedent) - Gate-2-lite, never ambient. Operator
  side: add ERC + uncapped-DRC report outputs to 22p-adapter.OutJob
  (one-time). Client side: gated tool + parsers for the two report
  formats + freshness/hash recording per the evidence discipline.
  **Scope extension (agreed 2026-09-10): plan TWO OutJobs.** Validation
  job (ERC + uncapped DRC + ODB + Protel netlist - cheap, every
  checkpoint; the netlist feeds compare_native_export automatically) and
  a Release job (variant-aware BOM CSV closing the not-a-purchasing-BOM
  caveat, pick-and-place/CPL cross-checkable against the live placements
  read, Gerbers/NC drill, schematic PDFs - the order package as one
  dated hashable artifact set). Same approval gate, per-container.
- [ ] **Wider upstream survey (2026-09-10): further read-side candidates**,
  same caveats as above (unreviewed, mostly focused-document targeting,
  each needs read-only verification + selection scoping):
  1. **Audit.pas suite (~30 prebuilt checks)**: highest value; maps
     directly onto the 22p layout-completion checklist and open passes:
     Audit_FindSignalViasWithoutReturn (return-path review),
     FindViaAntennas, FindBadConnections, FindFloating/UnmatchedPorts,
     FindSinglePinNets, FindComponentsOutsideBoardOutline,
     FindPadsNearBoardEdge, FindDesignatorCollisions,
     FindMixedDesignatorRotation, FindMirroredPcbText,
     **FindMissingDatasheets + FindMpnInconsistencies** (the 111-blank MPN
     entry pass), ValidateComponentParams, PowerPortOrientation,
     VariantNotFitted. Verify each is pure-read (no select/highlight side
     effects) before exposure.
  2. **Library geometry reads**: Lib_GetFootprints, Lib_GetFootprintPads,
     Lib_GetLibraryGeometry: native footprint pad geometry, replacing the
     offline olefile binary parsing for footprint-vs-datasheet checks
     (R218 Kelvin lands, FH58SA pin-1 location for the pinout session).
  3. **Proj_GenerateOutput / Proj_GetOutJobContainers**: could automate
     the ODB checkpoint refresh that PCB-side validation depends on. NOT
     read-only (writes output files, may compile): if exposed, behind an
     explicit per-call approval, never ambient.
  4. **Proj_CrossProbe**: cooperative review aid (agent names a component,
     Altium highlights it for the operator). Verify it cannot modify.
  5. **Generic filtered primitive queries** (Gen_QueryObjects /
     ProcessPCBBoardObjects): general fallback for object reads without
     dedicated tools; large-payload limits + honesty reporting required.
- [ ] **Read-side gaps hit during the 2026-09-14 CAD session** (operator
  asked to log improvements while using the tool; all read-only, all
  ForBoard-pattern candidates for the next script deploy window):
  1. ~~**Rooms read (`pcb.get_rooms`)**~~ **WIRED 2026-09-23  -  it turned out to
     need no new Pascal at all.** `PCB_GetRoomRules` already existed and was
     already an MCP tool; what was missing is that it had **no `...ForBoard`
     variant and no entry in `SelectedProject.pas`**, so the shared dropdown
     path  -  the only path the runbook sanctions  -  could not reach it. Split out
     `PCB_GetRoomRulesForBoard` the same way as the other reads, registered it,
     and added the `rooms` client subcommand (extents in mm plus width/height,
     `--designator` filters by name and refuses by listing what is present).
     **Lesson worth keeping: this item was logged as a missing capability when
     it was actually an unrouted one.** Check the shared dispatcher before
     concluding a read does not exist.
     - Caveat carried from the existing tool's own docstring: these are room
       **rules** (confinement constraints), not physical `IPCB_Room` objects,
       and the extents come from the rule's bounding rect.
     - Still needs the same deploy/qualify window as the object-classes read.
  2. ~~**Object-classes read**~~ **WRITTEN 2026-09-23, NOT YET DEPLOYED OR
     QUALIFIED.** `PCB_GetObjectClassesForBoard` in `scripts/altium/PCB.pas`,
     registered on both dispatch paths, exposed as `pcb_get_object_classes`,
     with the client subcommand `objectclasses` in companion PLT-hw
     (`--designator` filters by class name and refuses with the list of
     classes present).
     - **Two DelphiScript constraints drove the design, both verified against
       the existing file rather than assumed.** `MemberCount`/`MemberName[]`
       are unavailable  -  but `IsMember(Obj)` is, and
       `PCB_AddTestpointsForNetClass` already uses it, so membership is
       **probed** rather than asked for. And only `eClassMemberKind_Net` is
       referenced anywhere in the script: `eClassMemberKind_Component` and
       `..._DifferentialPair` are **not**, and an undeclared constant is a
       **compile-time failure that would take the whole dispatcher down**. So
       the declared kind never decides what to probe  -  every class is probed
       against all three object sets (all three proven in-file) and reports
       what actually came back.
     - **What qualification must check, since none of this is testable
       offline** (the simulator does not model object classes, so only the
       client-side summariser has unit tests  -  5 of them): that the script
       still **compiles**; that `pcb.get_object_classes` returns the five MIPI
       pairs once that class exists; that a board with **no** classes returns
       `count: 0` rather than erroring; and the per-class probe cost on a real
       board, since it is O(classes x objects)  -  172 components and 114 nets
       should be trivial, but measure rather than assume.
  3. **Component bounds in placements**: centers-only today; adding
     per-component bounding boxes would enable client-side overlap and
     zone-fit checks (e.g. cap-vs-connector-body during compaction).
  4. Client-side `placements --diff` shipped in companion PLT-hw
     2026-09-14 (338393c), no Pascal change needed.
- [ ] **Expose the DRC RUNNER, and report which rules a run actually checked.**
  Two halves, and the second is the one that matters.
  - **The runner.** `PCB_RunDRCForBoard` was split on 2026-09-24 and then
    REVERTED unbuilt, deliberately: the split alone does nothing, and
    committing it would have made source `2026.09.24.4` differ from the
    deployed `2026.09.24.4`, which is precisely the stale-compile hazard the
    version pin exists to catch. Redo it as one complete change - split, both
    `SelectedProject.pas` gates, `PCB_READ_COMMANDS` (cap is **100** here, not
    the reader's 200), the tool and a `rundrc` subcommand - when it is
    actually going to be deployed. Honesty is already fixed: `drc_confirmed`
    is report FRESHNESS as of `2026.09.24.4`.
  - **Policy note to settle first:** a DRC run writes a `.DRC` report into the
    project folder and **marks the PcbDoc modified** (measured 2026-09-24:
    `pcb_modified` went true after the operator's native run). That is the
    same class as `erc`, which compiles and is already permitted, but it does
    stretch what "selected-project-read-only" covers. Operator call.
  - **THE RULE-COVERAGE GAP, and it is the more valuable half.** MEASURED
    2026-09-24: a fresh native DRC returned 220 violations and **`RoutingVias`
    appeared ZERO times in the report** - it was not enabled in the run. So an
    absent violation means "not checked", not "compliant", and the violation
    objects alone cannot tell the two apart. This is the same shape as the
    `zero_is_not_a_pass` trap one level up: a clean-looking result that is
    actually silence.
    - **Baseline from that run, 220 total, for comparison after stage 6:**
      95 Minimum Solder Mask Sliver, 89 Silk To Solder Mask Clearance, 15 Net
      Antennae, 12 Un-Routed Net (GND, expected - pours not started), 7 Hole
      Size, 1 Silk To Silk, 1 Board Outline Clearance. Clearance, Width,
      Short-Circuit, Hole-To-Hole, Power Plane, Modified Polygon and Height
      all returned 0.
      - **The 7 Hole Size violations (3.5mm > 2.54mm) are the PCB MOUNTING
        HOLES** (operator, 2026-09-24). Expected, not a defect; the stock
        2.54 mm max is what is wrong, not the holes. Either scope a rule
        exception or accept them as known - do not chase them.
      - **1 Board Outline Clearance collision is NOT explained** and is worth
        a look before the order.
    - The `.DRC` report DOES list every rule processed with its count
      (`Processing Rule : Clearance Constraint (Gap=0.15mm) (All),(All)` then
      `Rule Violations :0`), so the fix is to parse it alongside the violation
      objects and return `rules_checked`. Until that exists, **never read a
      zero from `violations` as a pass without checking the report by hand.**

- [x] **Native DRC violation read  -  BUILT 2026-09-24, awaiting its deploy
  window.** Shipped as `pcb.get_clearance_violations` / `bridge_read violations`
  in script `2026.09.24.3`. It turned out to be **wiring, not new code**:
  `PCB_GetClearanceViolations` had been in `PCB.pas` all along with no
  `...ForBoard` split and no dispatcher entry  -  exactly the rooms-read pattern,
  and exactly what the memory note warns to check before writing anything.
  **The reader is exposed and the runner is NOT**: `PCB_RunDRC` calls
  `RunProcess('PCB:DesignRuleCheck')`, which raises the Design Rule Checker
  modal and once wedged the bridge for 30+ minutes; a modal is unrecoverable
  from the Python side. The operator runs DRC natively, the bridge reads what
  it left behind. Three tests hold that line, one of them reading `PCB.pas`
  itself so the reader stays a read. Original entry follows.
- [x] ~~**Native DRC violation read (`pcb.get_drc_violations`)  -  the gap that bites
  next.**~~ `erc` covers compiled ERC and `audit` covers our six surfacing checks,
  but **nothing reads native DRC**, and the 22p is about to enter the phase where
  DRC is the check that matters: the rules ritual is 1/12 entered, room
  `MIPI_CROSS` is new, and the (b1) lane crossing is routed against clearance,
  width and via-style rules we can only read *as rules*, never as violations.
  Today the loop is "operator runs DRC, reads the panel aloud". Pair it with the
  already-logged **rooms read**, which the same work needs  -  rule 10 scopes to two
  rooms now and no tool can confirm either exists.

- [ ] **Parameter WRITES: BUILT in source 2026-10-03, operator-approved; native
  qualification open, not deployed.** The Ctrl+Z P0 below was closed 2026-09-24 (timer
  dispatch). Scope and implementation: [PROPOSAL-2026-09-28](docs/PROPOSAL-2026-09-28-metadata-write-increment.md)
  section 7 (`LCSC Part #` and `Instruction` only; the wider field list below stays
  for Gate 4). Next: provision `--param-edits` on a non-CAD day and run T1-T17 on a
  disposable copy. History of the item follows.
- [x] **Parameter WRITES: the right first write capability, but gated on P0**
  (operator asked 2026-09-23 whether the bridge should write parameters).
  **Why this class specifically is defensible**, where geometry writes are not:
  parameters are **non-topological**  -  they cannot change a net, a footprint, a
  placement or any copper, so a wrong value cannot short or disconnect anything;
  they are **verifiable by read-back** with `parameters --designator --fields`;
  and their recovery path is **"write the correct value", not undo**, because the
  intended value always exists in the source CSV. That last point is what makes
  them separable from edits whose recovery genuinely depends on a working undo.
  - **PREREQUISITE: close the Ctrl+Z P0 first.** Adding the first write capability
    while undo is known-broken-and-replaying is the combination this TODO has been
    warning about all along. P0 is the gate, not a parallel task.
  - **Design, if it is built:** whitelist the writable fields (`Value`, `Comment`,
    `LCSC Part #`, `LCSC MFG`, `MRF.Part`) and **refuse `Footprint`, `Library
    Reference` and `Designator`**  -  a footprint change is a land-pattern change and
    stays manual. Input is a **designator-keyed CSV committed to git** (never
    positional, which is the failure mode of Altium's own grid paste). **Dry-run by
    default**: print current -> proposed per field and require an explicit apply
    flag. **Read back and assert** every written field afterwards, reporting any
    that did not take. **Refuse on dirty docs** so a clean git revert point exists.
    Operator-gated through Gates 0-5 as a new capability, never a config toggle.
  - **Not worth building for the 22p BOM itself** (~96 MPNs): a Pascal tool plus a
    runtime version plus qualification costs more than typing them once. It pays
    off across the HDMI board and later spins, which is the case to make when P0
    is closed.

- [ ] **Read-side gaps hit during the 2026-09-22 P00 / BOM session** (operator
  asked again what would make the tool faster). **Items 1-4, 6 and 7 are
  CLIENT-SIDE  -  they need no Pascal and no script deploy window**, because the
  data already comes back in the `nets` and `parameters` payloads. That is the
  cheap half of this list.
  > **1-4 SHIPPED and verified against a live board 2026-09-23** (companion
  > PLT-hw `d74f3ec`, suite 149 -> 161). `nets --designator R404` returned both
  > pins with co-members; `nets --net VEEA` returned all five members;
  > `nets --designator NOPE` refused with the "check against `bom`" message;
  > `parameters --designator R218,R404 --fields Value --blank-report` filtered to
  > two rows while the rollup still covered all 172. **Remaining: 5 (test-point
  > read, needs Pascal), 6 (venv wrapper), 7 (schema discoverability).**
  >
  > Note when reading the rollup: `complete` counts rows with *every*
  > `--check-fields` filled, so it moves with that list  -  62 against
  > `Value` + `LCSC Part #`, 61 once the default `MRF.Part` is included. Not a
  > discrepancy; say which field set a number came from.
  1. **`nets --designator U301`: component pin -> net, with the other members
     of each net.** By far the most-used operation of the session  -  the MCU pin
     map, the CON401 pad table, the strap tracing and the link-pair topology
     were all this one query, hand-rolled in a scratchpad script each time.
     Today's `--designator` only serves `pads` (PCB side); the schematic
     equivalent does not exist.
  2. **`nets --net VEEA`: full membership of one named net.** The `--net` flag
     exists but only narrows `tracelengths`. Membership is the query that
     settles "is this really the rail?" and it is the one the R229/R230
     postmortem tells us to always run.
  3. **`parameters --designator R218,R224 --fields Value,"LCSC Part #"`.**
     `parameters` dumps all 172 components; every use today filtered it
     client-side first.
  4. **A BOM-gap rollup on `--blank-report`**: counts of complete /
     missing-Value / missing-MPN, broken down by designator prefix. The raw
     report has the data; the rollup ("62 complete, 47 missing Value, 96
     missing MPN") was computed by hand and is what actually drives the work.
  5. **Test-point / free-pad read (server-side, needs Pascal).** pcb-design
     requires a labelled probe pad on every strap pin plus RESX, and **no
     current tool can verify that**  -  it stayed "unverified" in the 2026-09-22
     BRINGUP review for want of a read. Free pads and vias not owned by a
     component are invisible today.
  6. **A `bridge.cmd` / `bridge.ps1` wrapper that hard-codes the runtime venv
     interpreter.** Bare `python` fails with `ModuleNotFoundError: mcp`, and
     this is rediscovered every session  -  it is in agent memory precisely
     because the tool does not prevent it. A two-line wrapper removes the whole
     error class.
  7. **Payload schema discoverability.** The `nets` payload keys pins by
     `component`, not `designator` (which `--designator` implies elsewhere);
     three script iterations went into finding that. Either align the naming or
     add a `--schema` flag that prints one example record per subcommand.
- [x] Cross-version runtime management (2026-09-09, companion PLT-hw):
  `SharedRuntime.load_any_version` keeps all integrity checks but tolerates
  another version family, used only by manage_shared_runtime
  inspect/prepare/rollback (which previously could not even validate a
  rollback target from an older family). Clients stay version-strict.
  Verified live against the real 2026.09.08.2 runtime; four new tests.

## P1: Deployment and evidence consistency

- [x] Add guarded shared-runtime check/side-by-side preparation/manual rollback
  instructions via companion `tools/eda-agent/manage_shared_runtime.py`.
  Checks manifests/gate/IPC pointers, requires stopped clients/Altium, creates
  only a new sibling, preserves the old runtime, and returns exact manual launch
  paths. No auto-activation/config changes or in-place overwrites. Nine synthetic
  management tests pass (82 total Python tests); real installed 22-file check passes.
- [ ] Qualify a real side-by-side candidate activation and manual rollback cycle.
  Candidate `selected-readonly-permissions-20260909` was prepared on 2026-09-09
  with Altium/clients stopped: 23-file integrity/pointers and installed eight-tool
  schema pass; previous 22-file runtime preserved. Native startup and all eight
  22p reads now pass; visual/lifecycle and manual rollback qualification remain.
  Add separately reviewed legacy named-profile/package and cross-version support;
  the new helper deliberately handles only its matching shared-version family.
  Never run a generic installer over generated profiles.
- [ ] Align packaged scripts with patched source/named profiles. The installed
  wheel still contains older shutdown code; preserve it before rebuilding.
  Distinguish source, installed package, deployed scripts and loaded script.
- [ ] Verify deployment hashes at startup and expose exact CAD snapshot identity
  in read evidence. Shared startup already enforces all 22 script/client hashes;
  that item is complete for shared mode, not a CAD snapshot guarantee. Legacy
  startup enforcement and exact source/copy revision evidence remain open.
  Detect saved-copy/source drift; do not silently refresh CAD or compare revisions.
- [x] Publish the scoped source fixes, tests and companion runbooks checkpoint.
  Fork `d5b62a0` and PLT-hw `3b7cc66` pushed to origin/main; remote hashes and clean
  worktrees verified. See the current-state handoff for immutable links.
  Keep venvs, copied CAD, IPC logs and workstation runtime artifacts out of Git.

- [x] Draft-state diagnosability - NATIVELY VERIFIED 2026-09-09: with an
  unsaved sheet, the refusal reads "Cannot establish selected-project
  document identity (unsaved/identityless: Sheet1.SchDoc); save or discard
  the named document"; after a deliberate discard, compiled reads recovered
  immediately with healthy extraction blocks, no restart or re-selection. Original note kept for context (noted 2026-09-09, behavior itself
  accepted):
  with an unsaved new sheet in the selected project, ALL project reads refuse
  with `INCOMPLETE_DOCUMENTS - Cannot establish selected-project document
  identity` - correct fail-closed handling, natively verified. But unlike
  DIRTY_PROJECT (where freshness still serves and names dirty_docs), nothing
  names the identityless member. Let proj_get_compile_freshness (or a small
  diagnostics read) list draft/identityless documents - names only, content
  reads keep refusing. Decision: keep fail-closed; new files are supported
  once saved.

## P2: Cancellation, deadlines and usability

- [ ] Define cancellation semantics and a consistent end-to-end deadline.
  **Isolated reproduction:** cancellation releases the PLT reader lock while
  its executor worker continues. The single-worker executor prevents concurrent
  execution through that queue, but later work may wait behind the cancelled
  request. Do not claim cancellation stops native execution. Test queued,
  published, active and timed-out requests; avoid unsafe automatic retries,
  especially before future write access.
- [ ] Reconcile per-send 60-second waits, multiple guard calls, the 90-second
  client tool timeout and upstream heartbeat extensions. Distinguish "still
  running", "client stopped waiting", "paused" and "blocked on dialog".
  A timeout is not evidence that an operation did nothing.
- [x] Add a profile status / **no-save stop** utility. Verify the selected IPC
  workspace, await fresh acknowledgement and report a halted interpreter.
  Native status-window Detach is no-save; API/browser Detach saves dirty CAD.
  Preserve this distinction in labels and instructions.
  Implemented in companion PLT-hw `tools/eda-agent/stop_bridge.py`, deployed to
  both named profiles. Standalone CLI only, no added MCP tool or UI button. Checks
  process/session/IPC identity, unique live ping and fresh stop-file end marker;
  refuses stale/aborted/restarted/ambiguous results. No save/quit/kill/keep-alive.
- [ ] Native-qualify the new stop helper and updated reads; repeat stop-first
  normal quit/restart cycles. Offline synthetic tests are not native acceptance.
  First updated 22p read run and helper stop passed on 2026-09-08, PID 4320:
  `21:56:01.382,0,_session_end,requests=33,reason=stop-file`. No CAD save or
  automatic quit; operator normal-quit confirmation and repeated cycles pending.
- [ ] Enforce one active profile/client and bind diagnostics to a particular
  Altium process/session. Separate IPC folders do not qualify multi-instance use.
  Source now includes a process-lifetime Windows guard shared by the shared read
  server and stop CLI, keyed by canonical IPC workspace. Seven new real Windows
  kernel/temporary-process tests pass (89 Python tests total). Side-by-side
  candidate startup/eight-tool reads pass; remaining native acceptance pending.
  This excludes updated cooperating clients in the same workspace/session,
  not old/custom direct IPC writers or clients of different profiles.
- [ ] Consolidate reusable shared-client/permissions/management code into the
  eda-agent fork/package, retaining PLT-specific wrappers/runbooks as needed.
  Cross-project use should not permanently depend on a hardware checkout. Preserve
  installation compatibility and existing runtime snapshots during migration.
- [ ] Improve smoke-test error reporting: preserve useful tool-error details
  and summarize nested MCP exception groups without hiding the cause. Do not
  confuse permission failures with native script defects or obey returned text.
  Shared helper now preserves bounded tool-error text and supports explicit
  expected-project/token and old-binding rejection checks. Legacy helper and
  outer exception-group presentation still need work.

## Future enhancements: selected-project UI and scoped writes

Design notes: [project selection and controlled metadata editing](docs/PROJECT-SELECTION-AND-WRITES.md).
Project-selection implementation was authorized subsequently; metadata writes
remain proposals. Existing named copy profiles are unchanged. New shared mode
requires native qualification and remains read-only.

- [x] Add an explicit native-panel Project dropdown (name + full path) and
  **Use this project** button for one shared bridge. Do not follow active tabs.
- [x] Implement native/Python binding to project path, session and selection
  generation; invalidate stale queued requests, caches and grants on switches,
  closure or restart. Disable switching during execution. Review focus-dependent
  handlers and startup/stop guards before relaxing single-profile restrictions.
  Implemented in separate `.2` shared runtime with eight read tools and a native
  dispatcher allowlist. Metadata writes are not enabled. 63 Python tests, eight
  native-selection source checks, ten shutdown source checks and changed-Pascal
  lint pass. All 22 deployed file hashes and MCP startup/schema pass; native UI,
  selection lifetime and handler behavior still require the tests below.
- [ ] Native-test two open projects, duplicate names, tab changes, queued requests,
  closure, dirty state and stop/restart; keep writes disabled during this phase.
  Selected-22p smoke pass now observed on `.2` with two projects open: 9 documents,
  dirty count 0, 172 components, 559 pin/net entries and C101 metadata, all bound to
  the same path/session/generation. This is not native export parity or a switch
  test by itself. Subsequent explicit switch to cyber80 advanced generation 2 to
  3; all eight tools passed (8 documents, dirty count 0, 260 components, 616 pin/net
  entries, D201 metadata). Live wrapper rejected old path/token, new path/old token
  and old path/new token before native document dispatch. Queue races and native
  guard in isolation remain untested. Session/binding evidence is in the companion
  shared-mode guide.
- [x] Implement/deploy selected-project confirmation sizing and text fix:
  operator clicked Use
  and backend selection succeeded, but reported no visible indication. Screenshots
  confirm clipping consistent with scaled child controls and an unscaled 166-pixel
  header. Height now derives from scaled control bounds. The committed project
  basename/read-only state appear in the label and window title; hover shows the
  exact path. Draft dropdown changes do not update committed identity.
  Patch `selector-layout-checks-20260908-v1` deployed after verified session end
  and Altium closure, with four-file backup and manifest/provenance update.
  73 Python tests, 12 selection source checks, ten shutdown source checks, changed
  Pascal lint, 22 runtime hashes and eight-tool initialization pass.
- [ ] Native-test the new layout/title after restart, current display scaling,
  hover full-path identity, selection changes and unapplied dropdown drafts.
  On 2026-09-09 the operator confirmed selected-project text is visible, and all
  eight reads passed after restart on the 22p copy (9 documents, dirty count 0,
  172 components, 559 pin/net entries, C101). The prior session's token was
  explicitly rejected with the current selection unchanged. Hover/title details,
  unapplied drafts and closure/reopen still need separate observation.
- [x] Deploy selector contrast fix after session end and confirmed Altium closure.
  Operator reported white-on-white dropdown text in `.2`:
  the native combo inherited the dark form's light font. Source now explicitly
  uses window background/text colors and button text color without parent font
  inheritance; all nine selection source tests pass. Shared runtime updated with
  a three-file backup and revised form hash/provenance; 22-file integrity and
  eight-tool initialization pass without contacting Altium. Script stays `.2`.
- [ ] Finish contrast qualification: collapsed/open/highlighted dropdown and Use
  button are readable in operator screenshots; disabled state remains unverified.
- [ ] Prototype a separate allowlisted metadata-edit capability: approved MPN,
  manufacturer and datasheet fields for explicit components on a copy/branch.
  Require a dry-run diff, exact-batch approval, expected-old-value checks,
  recoverable baseline, read-back verification and separately authorized saves.
- [ ] Design/qualify the proposed GUI permissions panel: read-only default,
  per-capability grants and Revoke edits, disabled unimplemented capabilities,
  and separate edit/save/export scopes. Operator grants are a ceiling, not blanket
  batch approval. Bind permission generation to session/project/selection, clear
  edit grants on switch/closure/restart, reject stale queued approvals and report
  in-flight unknown outcomes honestly. Enforce in Python and native dispatcher.
  First candidate UI increment shows the effective fixed read-only policy and
  unavailable editing/saving/output jobs, with DPI-aware bounds. No configurable
  grant controls or writes added; side-by-side preparation/schema passed, native
  visual/start/read/stop acceptance pending.
  Thirteen selection source checks and changed-Pascal lint pass.
- [ ] Qualify partial-failure recovery and native undo behavior; reject stale
  approvals and never retry uncertain writes automatically. Re-export and compare
  BOM/net evidence; metadata-only changes must not change connectivity.
- [ ] Define parameter ownership and aliases for MFG/manufacturer, MPN, supplier
  SKU, internal part number, datasheet and description. Distinguish missing,
  empty and inherited values; reject conflicting aliases or unsupported managed
  objects. A BOM CSV edit alone is not a schematic correction.
- [ ] Add separately approved value/Comment and typed-parameter edits. Preserve
  units/expressions and verify electrical ratings, approved MPN consistency and
  native export/save-reopen results; do not treat these as cosmetic metadata.
- [ ] Param-edit increment 2 (asked by Stefan 2026-10-05, after the first live write on the HDMI
  board): (a) **multi-part symbols**: write every part's copy of the parameter in one apply, require
  identical old values across the parts and read all of them back (HDMI U501 has six parts on one
  sheet, CON401 two; today refused by design, T14, and set by hand). (b) DONE 2026-10-05 in script
  2026.10.05.1: any existing parameter by exact name, never Designator / Footprint / component properties.
- [ ] **Placement-write increment (approved 2026-10-07, scripts 2026.10.07.1, deployed as runtime
  selected-edits-20261007 the same day; T1 and T14 pass on the live HDMI project, T2-T13 and T15
  open, proposal section 10):**
  [docs/PROPOSAL-2026-10-07-placement-write-increment.md](docs/PROPOSAL-2026-10-07-placement-write-increment.md).
  - A narrow `pcb_move_components_checked`: the selected board only, raw coordinates,
    compare-and-set, refusals for locked, flipped and routed parts, its own session tick, read-back,
    never save.
  - It is fed by PLT `plancheck --emit-moves` from a checked layout plan.
  - The upstream `PCB_MoveComponent` / `PCB_BatchMoveComponents` are not exposed: focused-board
    target, mil rounding, parse-failure-to-zero, locks ignored (audit M1-M10).
  - Learned on the HDMI rough placement (2026-10-07, 4 batches, ~180 moves): the routed-part refusal
    uses `Comp.BoundingRectangle`, which includes the designator / comment text, so a part whose
    LABEL reaches a mounting-hole via is refused (C205, C206, TP206) and the post-apply verify flags
    parts that sit exactly at target. Consider the pads' and body's extent instead of the text.
- [ ] **Silkscreen designator edits (Stefan 2026-10-07, "very low risk"):** hide / show, move and
  resize the designator (and comment) text of placed components on the selected board, as a gated
  batch like the placement write: preview -> approval hash -> its own tick -> compare-and-set ->
  read back -> never save. Only text position, rotation, height / stroke width and visibility; no
  other primitive. Feeds a PLT-side "designator tidy" (outside the courtyard, readable rotation,
  off pads and vias).
- [ ] Add assignment/change of existing library footprints with explicit model
  identity, package and pin-pad/pin-1 checks, library availability and assembly
  review. Preview schematic-to-PCB ECO separately; require approval before
  changing the placed PCB footprint. Footprint geometry editing is a later scope.
- [ ] Add reference-designator annotation/renumbering (distinct from part numbers)
  using stable component identities, uniqueness/multi-part checks and verified
  schematic/PCB/BOM mappings. No blind bulk text replacement.
- [ ] Add separately scoped fitted/DNP/variant edits with variant BOM and assembly
  output checks. Shared-library/managed-source updates need separate impact review.
- [ ] Keep default read-only and use exact-batch, session/project-bound approvals
  for each editing capability. Qualify native undo, partial failure, timeout and
  disconnect recovery, and save/reopen persistence on disposable projects first.
- [ ] Keep footprint geometry, symbols, nets and PCB placement/routing as separate
  later capabilities, not part of a broad write-mode toggle.

## Acceptance discipline

- [ ] Run relevant upstream tests in an isolated test environment. Initial
  coverage: 10 shutdown source checks and 30 PLT helper tests; pytest was not
  installed during patch work. Native observations belong in the shutdown log.
- [ ] Qualify HDMI and each new profile independently; a 22p read pass does not
  transfer to another board or a new script revision.
- [ ] Keep CAD-write tools disabled until an explicitly authorized edit workflow
  has backups, scoped changes, diffs, native checks and operator review.
