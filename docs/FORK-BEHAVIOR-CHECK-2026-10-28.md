# Fork behavior checkpoint, 2026-10-28

The current synchronization point is reported by `eda-agent fork-status
--fetch --remote upstream`: `0bb1b3154cca6e58a517b23edee3d7a108f1c232`,
merged by `63f7c16ab8dd7c703ba9a82ca17b7f06cee1e370`, with zero upstream
commits pending at the latest fetch. The original checkpoint below was made
at `main` / `origin/main` `52d3b8c8126109e12d2f08e0bc0a18d837874409`,
when the point was `ee7589c9fc543d0b99bb142dc8ca12b618fffeab` via merge
`338f615`. `MOREmbedded/main` was
`032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.

The package-install update hint, package repository/issue URLs, and README
clone command now point to `Rouniy/eda-agent`; package metadata also names
the original upstream. This prevents a wheel user following the update hint
from replacing this fork with the upstream package. Update/status/fork tests
passed 26/26.

`yniantongtian-oss` commit `491555d`'s Pascal bundle fix is now present:
`scripts/altium/build.py` reads each source with `utf-8-sig`, so an input
BOM cannot be embedded in the middle of `Altium_MCP.pas`. An isolated build
with BOMs in all 12 inputs produced none in the output; 16 focused tests
passed and the actual 12-file bundle build reported zero lint findings.
This qualifies the bundle builder, not an AD25 compile of the active
multi-file `Altium_API.PrjScr` project.

`malteheringorgatex`'s WSL process-detection commit `d57df64` is covered
by the current `process_manager.py`: it reads the Windows `tasklist.exe`
CSV when WSL interop works and lets IPC diagnose reachability when it does
not. The focused WSL bridge tests passed 10/10. Its fork-specific five-second
poll timeout (`80ebe59`) is a tuning choice; the current ten-second default
is retained for long CAD calls, and callers can configure it.

`rabihnd/integration`'s `setup-mcp.ps1` capability is adapted into the
tracked `scripts/` directory. The helper can dry-run, add or remove the
Claude MCP entry, backs up configs, preserves unrelated JSON and writes
UTF-8 without a BOM. Its launcher is discovered from the active machine
instead of a donor-specific Python 3.12 path. An isolated temporary Claude
Code config passed dry-run/add/remove; no real client config was touched.
`lda-audiotech`'s Unicode pointer and BOM-response fixes were already
covered by `config._pointer_encoding`, the health check and
`_read_response_json`; their focused tests passed 3/3.

The issue-template security link now opens this fork's `SECURITY.md`
(HTTP 200). GitHub's public private-vulnerability-reporting setting for
`Rouniy/eda-agent` returned `enabled:false`; a fork-controlled private
contact is still needed before the policy's upstream email can be changed.
GitHub's Actions API showed no hosted runs for `build-windows-binary.yml`
and no `tests.yml` runs on the latest commits at this check, so local tests
remain the verification for those changes.

The four-layer `update --status` now tracks fetch success independently for
the push remote and the named upstream remote. A failed refresh can no
longer present a cached zero-behind ref as freshly current; it reports
`unknown`. Both fetches use `--no-tags` so status checks do not import
third-party release tags. Seventeen focused status/fork tests passed; a live
`update --status --fetch --from upstream --json` showed both fetches true,
zero upstream commits pending, and Altium compiling the main script `.167`.

The child fork's single-command reconciliation is now adapted as explicit
`update --reconcile`. Its fast-forward is `--ff-only --no-tags` on a clean
tracking branch; script deployment uses the validated installer and the
already checked folder, so the loaded main project is not copied into a
second runtime. An external folder cannot overwrite the active main
checkout's script sources: its changes must be merged into the checkout.
`--check` never applies a change, JSON stays parseable
after deployment, and a compiled-script mismatch remains a separate
`relaunch --restart` action. Thirty-eight local update/status tests passed.
The unchanged donor test file now passes 42/50; its remaining failures are
older action text or source-spelling checks, the old `cmd_update(as_json)`
entry point, a raw copier that accepts a source lacking a `.PrjScr`, and
an Altium-version mock of the older ping path. The current API checks the
loaded project path as well as the compiled version.

`eda-agent fork-status --fetch --cached-forks --verify-fork-branches --json`
matched all 118 live branch tips to cached refs. Fifty-four cached refs
are not ancestors of `main`; that count measures divergent commits, not
missing functionality. No new branch tip appeared since the previous
118-branch check.

A fresh repeat after `4da2cc4` again matched 118/118 live branch tips to
cached refs, with `MOREmbedded/main` still at `032fb4b` and upstream still
at `0bb1b315` (zero commits pending). The child fork still has 33 commits
outside `main` ancestry; their feature behavior is tracked separately below.

The following branch-tip behaviors were rechecked in the current source.
The named tests check source or offline behavior; the native Altium
acceptance already recorded in `CURRENT-STATE.md` and
`RELEASE_VERIFICATION.md` remains the separate evidence for CAD writes.

| Fork branch or commit | Current capability | Recheck |
| --- | --- | --- |
| `MOREmbedded/claude/determined-gould-ebb38e` `cbff5f9` | Doctor trusts a live bridge ping over an invisible process table; the earlier `8ec0cd9` lint guards are adapted | `test_doctor_trusts_the_bridge_over_the_process_table.py` and live `.163` ping |
| `mooreaa/main` `5329cfe` | Ordinary copper, loss tangent and guarded stale-manager reset | `test_pcb_build_stack.py`; disposable AD26.11 insert, dielectric write and stale-model rebuild |
| `MOREmbedded/main` `032fb4b` | Direct Altium 365 route and its schema tool, library operations and NPI phase gates | `test_a365_direct_workspace.py`; previously recorded library and NPI tests |
| `vincent-himpe/fix/decimal-mils-leftovers` `2c0a56d` | Fractional-mil reads and writes | `test_lengths_are_decimal_mils.py` |
| `vincent-himpe/fix/filter-allobjects-walks` `530db39` | Filtered PCB and library object walks | `test_no_unfiltered_object_walks.py` |
| `vincent-himpe/fix/via-mask-bottom-follows-top` `b05ac10` | One-sided via mask setting follows onto the other side | `test_via_mask_bottom_follows_top.py` |
| `yanivbi1/lib-set-3d-body` `a54fa8c` | Exact footprint 3D-body edit | `test_lib_set_3d_body.py` |
| `vincent-himpe/feature/library-select-primitives` `9070755` | Select primitives inside a footprint | `test_library_select_primitives.py` |
| `vincent-himpe/feature/region-true-arcs` `4d93cc6` | True arcs in board-region outlines | `test_board_region_true_arcs.py` |
| `vincent-himpe/feature/keepout-restrictions` `65e19b9` | Five keepout restriction flags | `test_keepout_restrictions.py` |
| `vincent-himpe/feature/polygon-pour-settings` `b3bd0f9` | Polygon-pour settings through the generic layer | `test_polygon_pour_settings.py` |

The eight Vincent/Yaniv test files passed 61 tests; the direct-fork,
doctor and stack files passed another 61. The checks above found no
missing capability in these branches. They do not establish behavioral
parity for every other nonancestor ref. Continue auditing the remaining
branches by distinct capability and verify native differences on copies.

The adapted `build-windows-binary.yml` workflow is in `main` and its local
wheel/one-file exe smoke test is recorded in `TODO.md`. GitHub's Actions
API reported zero hosted runs for that workflow at this check; a hosted
result remains outstanding.

## Additional divergent-branch review

At `7901939`, a fresh `eda-agent fork-status --fetch --cached-forks
--verify-fork-branches --json` again found `upstream/main=ee7589c9` with
zero commits behind, and all 118/118 live fork branch tips matched local
refs. The following distinct capabilities were then compared with the
current source. These are behavior matches, not claims that the donor
commits themselves were merged.

| Divergent source | Result in `main` | Evidence |
| --- | --- | --- |
| `bblacklock3` `c666912`, `78791d3` | Arc `Width` reads `LineWidth`; fractional mil coordinates are retained | `PCBGeneric.pas` getter; `test_lengths_are_decimal_mils.py` |
| `cad435/main` `4f57311`, `2a916c2` | The managed-part resolver probes `SchServer.LoadComponent`, and successful placement marks the sheet dirty | `Lib_GetVaultComponent`, `Gen_PlaceWorkspaceComponents`; `test_workspace_component_placement.py` |
| `mityafoxy` `bba6811` | Request reads use `FileOpen` and `THandleStream`, avoiding the AD26 sharing-violation modal from `LoadFromFile` | `LoadTextFile`; `test_ipc_integration.py` |
| `prototrace` `961e6c3` | UTF-16 code units are JSON-escaped without truncation; schematic `ePolyline` is queryable | `CodeUnitToHex4`, `Generic.pas` object resolver; `test_unicode_and_detach_transport.py`, `test_symbol_writes_on_screen.py` |
| `redbird98` `1ff554f`, `f3c2a5c`, `0b6433a`, `f293e80` | Fab statistics classify vias by `LowLayer`/`HighLayer`; DRC re-focuses the board; focus and exact-board resolution verify the selected document | `PCB_GetFabStats`, DRC and focus handlers, `ResolvePCBBoard`; `test_fab_stats_via_spans.py` and existing native batch DRC acceptance |
| `redbird98/main` `a563269` | OutJob is activated before its container runs | `Project.pas`; `test_outjob_activation.py` |
| `redbird98` `35ff5e0` | AD25-compatible Unicode transport uses UTF-8 request files with a BOM, Pascal stream decoding, and escaped Unicode in replies. This retains characters outside the GBK repertoire while avoiding `TEncoding.UTF8` in DelphiScript. AD25 runtime acceptance is still unverified on this AD26 host. | `altium_bridge.py`, `Main.pas`, `Utils.pas`; Unicode transport tests passed 24/24 |
| `redbird98` `9874d21` | `proj_run_erc` returns the compiled violation rows by reading `generic.get_erc_violations` after the native compile, with paging and suppressed/No Report counts. Print-path exports are classified modal. | `generic.py`, `Generic.pas`, `metadata.py`; ERC/Unicode/print checks passed 38/38 |
| `redbird98` `56118aa`, `e521249` | Chinese dialog captions and button roles are recognized, and batch DRC checks both the requested report and AD25's `Project Outputs for <project>` location before declaring success. These are source and test confirmations; a live AD25 check remains open. | `dialog_driver.py`, `dialog_report.py`, `PCB.pas`; locale/dialog/DRC checks passed 31/31 |
| `xthanhn91` `fc08cf1` | `eNote` and `eTextFrame` are addressable through the schematic object resolver, with placement and typed font access; `eda-agent relaunch` pings first and starts the existing script project only when needed. The separate `ensure_loop.py` script is not needed for those behaviors. | `Generic.pas`, `generic.py`, `cli.py`; object/font/placement/relaunch/supervisor checks passed 47/47 |
| `tisn1678065900-dot/boardquality` `21f0412` | The quality skill and all five `docs/pcb-quality` artifacts are already tracked | `skills/boardquality/SKILL.md`, `docs/pcb-quality/` |
| `pieterpotgieter` `3e7369b` | Paste-enabled reads and writes have a product-version guard; current source extends measured support to AD25.8 | `PadPasteFlagSupported`; `test_pad_paste_flag_version_gate.py` passed 3/3; AD23 compile remains unverified here |
| `mooreaa/main` placement-cleanup test | Font inference, placement tidy, live-pin filtering and port properties are present | 20/22 donor source tests pass; the two failures require an old exact source spelling: the current pin filter also checks query mode and non-library scope, while the public port width now forwards a decimal rather than an integer |

The six focused test files for fractional mils, via spans, OutJob,
Workspace placement, Unicode transport and IPC passed 77/77; the schematic
object-spelling file passed another 8/8. This source
and test review does not prove parity for every commit in those forks or
settle the remaining divergent branches; continue by distinct behavior.

A file-inventory comparison across divergent refs found no unmatched
production path in most forks. The donor's separate
`easyeda_extension_cli.py` is replaced by the tracked
`eda_agent.easyeda_extension` module and `eda-agent easyeda-extension` CLI;
its packaging tests pass 7/7 and the CLI resolves the source directory.
`wizd/edev` has a distinct `StatusFormStub.pas` for an AD25 headless
script project. Its minimal `.PrjScr` header has now been adapted into
the one main `Altium_API.PrjScr`, preserving all 14 current source
documents. The 12-file Pascal lint/build and 16 project consistency
tests passed, and a native AD26.11 restart answered ping with script
`.167` from that same main project. This removes the donor-observed
PCB-project metadata that AD25 rejected as `Invalid Constant`, but it
does not establish a successful AD25 compile.

The old headless stub itself cannot simply replace `StatusForm.pas`:
the current `Dispatcher.StartMCPServer` delegates to `StartMCPPump`, and
the timer event and request dispatch now live in that form's unit. The
donor stub only supplies logging no-ops and has no pump. A new headless
dispatcher would require separate design and native AD25 verification.

The other `wizd/edev` tip (`6d6cb62`) adds footprint writes and
component-origin recentering. Both routes are already in `main`;
`test_footprint_writes_land_where_asked.py` and `test_recenter_origins.py`
passed 18/18. The donor's `6603c0a` replaces the script project with a
minimal project and `StatusFormStub.pas`, and `9a9ed84` keeps that
headless replacement during deployment. That is an AD25-specific
compatibility route, not a direct replacement for the AD26 status form
currently loaded from the main script project. Native AD25 acceptance is
still needed to decide how to expose it without changing the AD26
runtime's dashboard.

## Additional branch-tip checks

| Divergent source | Result in `main` | Evidence |
| --- | --- | --- |
| `mooreaa/main` Rosen small fixes | Fifteen of eighteen donor tests pass unchanged. Both print tests expect the fork's string `PRINT_DIALOG_NOT_SILENT`, while the current tools return a structured `PREVIEW_NOT_SILENT` error and still refuse unattended modal printing. The close test expects a literal `SameDocPath` call; the current `App_CloseDocument` compares both canonical paths and returns `PATH_MISMATCH` before closing. | Temporary donor test run: 15 passed, 3 exact-contract/source failures; current `project.py` and `Application.pas` inspected. The temporary test file was removed. |
| `darshp848/altium-bridge-sch-repair-tools` `d89589b`, `63b0fef` | Net-label conflict audit, pin explanation, schematic UniqueId repair, component replication, pin-owner editing and per-user KiCad discovery are present. | Tool and Pascal symbol comparison; schematic spatial, DelphiScript and agent-facing checks passed 87/87. |
| `vanlong2109/feat/dblib-placement` `476d75e` | Single and batch DBLib component placement are present. | `test_place_dblib_components.py`, `test_dblib_tools.py` and KiCad local part-family checks passed 35/35. |
| `terrencehenry` property-access and TextColor guards `89c017f`, `ee5a455` | Unsupported property preflight, `IsHidden` and typed `TextColor` access are present. | `test_sch_properties_match_their_interface.py` and `test_sch_textcolor.py`: 31 passed, 3 skipped native-only checks. |

These checks add no source change. The three Rosen failures do not show a
missing behavior; they compare an older error shape or literal Pascal source.

The `yniantongtian-oss/improve/0.5.0-ci-metadata` branch exposed a current
gap: the package advertised Python 3.11 and 3.12, but the full Windows
test job ran only on 3.12. The `test` job now uses a 3.11/3.12 matrix
with independent results. The existing 3.11 compile/import smoke job
remains as a fast diagnostic. Package metadata now names the KiCad and
EasyEDA Pro backends documented in the README. Local TOML and matrix
checks and 13 metadata/version tests passed; a hosted matrix result is
still needed for native CI acceptance.

After merging upstream `0bb1b315` (the second parent of `63f7c16`), a
fresh `git fetch upstream` showed zero upstream commits pending. Two
more divergent fork branches were reviewed by their distinct changes:

| Divergent source | Current behavior and decision | Evidence |
| --- | --- | --- |
| `rabihnd/integration` `9c3fc81` | Multipart SchLib queries expose `OwnerPartId`; component graphics establish owner before insertion; label aliases, guarded property writes, delete/active-part tools, exact live part counts and batch rename reasons are present. Its forced `DoFileSave` during a component-list read is deliberately adapted: the current list identifies saved names and separately reports `unsaved_symbols` and stale saved names without writing the library. The donor's panel-cache issue remains unresolved in its own tracker. | Current `Generic.pas`, `Library.pas`, `library.py`; multipart, SchLib, catalogue checks: 40 passed, 2 skipped. |
| `andrzej-sikora-elte/elte` `91d66fb`, `06fffff` | DbLib table and link flags and footprint model reads/writes are present. The current footprint writer selects an existing implementation and verifies its current flag, avoiding an unchecked model-name rewrite; fractional mil footprint pad placement is also present. | Current `Generic.pas`, library handlers; DbLib, footprint-model and decimal-mil checks: 50 passed, 1 skipped. |

The skipped checks require a native editor or an optional local fixture;
these offline runs do not establish native acceptance for every path.

The direct child fork was refreshed again: `MOREmbedded/main` remains
`032fb4b`, and `MOREmbedded/claude/project-thread-6aorpk` remains
`5954a6f`. The latter branch's STEP/LibPkg/backup/footprint-file tools,
rotation audit, fractional PCB layer thickness, registered-script-folder
lookup, stackup templates, calculators, replacement-part review, profile
seeding, fab-package check and performance command all have their source
paths and public routes in `main`. Its focused library-file, rotation,
stackup, replacement-part, calculator and performance tests passed 198/198.
This establishes the checked behavior in those groups, not a blanket
equivalence of every historical commit or a native CAD acceptance claim.

An AST inventory of public tool functions in both `MOREmbedded/main`
`032fb4b` and its `project-thread` branch found zero command names absent
from our current source. The `MOREmbedded/main` bottom-side placement fix
is represented by the current top-first load followed by a separate
`PCB_FlipComponent` transaction; bottom-side parts participate in the
rotation audit. Direct Altium 365, NPI phase-gate, and rotation-audit
checks passed 91/91. This is an API and focused-behavior check; it does
not prove that every implementation detail of the 27 divergent commits
has the same result on every CAD design.

## Public-name inventory across cached fork branches

An AST pass across 111 cached fork refs found 14 distinct prefixed tool
names absent from the current public surface. They are legacy spelling
or narrower entry points, rather than 14 missing capabilities:

| Fork names | Current route |
| --- | --- |
| `lib_add_pin`, `lib_add_symbol_line`, `lib_set_label_format` | `lib_add_pins`, `lib_add_symbol_lines`, `lib_set_label_formats` |
| `pcb_move_component`, `pcb_place_component`, `pcb_place_track`, `sch_add_net_label` | `pcb_move_components`, `pcb_place_components`, `pcb_place_tracks`, `sch_place_net_label` |
| `sch_attach_spice_model`, `sch_attach_spice_primitive`, `sch_attach_spice_primitives`, `sch_get_simulation_readiness` | `sim_attach_model`, `sim_attach_primitives`, `sim_get_readiness` |
| `lib_diag_footprint`, `lib_screenshot_footprint`, `lib_list_vault_libraries` | `lib_get_footprint_primitives(kinds="body")`, `app_capture_window` or `lib_render_footprint`, `lib_list_available_libraries` |

The focused footprint, simulation, and catalogue tests passed 51/51
with two environment skips. The loaded `.164` bridge read four available
libraries and four installed libraries through
`library.list_available_libraries`; its response includes library type
and a separate Workspace name from an open design when available.
No missing public operation was established by this name inventory.

The `rabihnd` footprint diagnostic was checked beyond its name. Its body
array reports identifier, layer, `has_model`, bounding-box width/height and
overall height. The current `lib_get_footprint_primitives(kinds="body")`
reports those fields plus model source/type/rotation/standoff and the full
four-corner box. The donor's screenshot uses Win32 `BitBlt`; current
`app_capture_window` captures the actual editor window when given its
handle, while `lib_render_footprint` provides a separate 2D footprint render.
Footprint primitive/3D model tests passed 14 with one optional fixture skip.
The donor-only names remain convenience spellings, not missing body data.

Nine more `vincent-himpe` feature/fix tips were checked against current
source: board via/pad properties (`ab85b30`), selected-pad drill type
(`e6713dd`), region polygon outlines (`f662898`), primitive net writes
(`8399eea`), region names (`c3adf7f`), custom pad shape (`40ba903`),
decimal rectangle corners (`ca9b0c7`), board zoom (`23b1837`) and
footprint fills (`bf31274`). The eight tracked focused test files passed
62/62. The donor's separate custom-pad source test is not tracked in
this fork, so its six shape readers were checked directly: `PCB.pas`,
`Generic.pas` and `Library.pas` all name `eCustomShape` rather than
falling through to round/other. This is source and offline-test parity;
the individual native CAD write paths were not all rerun in this audit.

## Batch designator safety from `bblacklock3`

The donor's `test_batch_refuses_designator_rewrites.py` exposed a real gap:
the generic `obj_batch_modify` still accepted designator assignments, while
a failed batch can leave only some parts renamed. The public wrapper now
refuses either `Designator` or `Designator.Text` (case and whitespace
insensitive) before sending *any* operation. The Pascal handler also skips
such an operation for direct or older clients. The planned
`sch_batch_rename_designators` path is exempt: it checks a project-wide
snapshot and collisions, uses unique temporary names, and reads back both
phases. Single-object `obj_modify` is unchanged.

The fresh fork-status check found all 118 branch heads current in the cache.
`upstream/main` remains `0bb1b3154cca6e58a517b23edee3d7a108f1c232`, an
ancestor of `main` with zero commits behind. The new `.166` script built with
zero lint errors or warnings; 78 focused tests passed, one optional test was
skipped. A live Altium 26.11.1.5 call with `Designator=R8` returned
`operations_processed: 0`, `operations_skipped: 1` and the refusal note;
the mixed-case second-assignment form did too. The internal bypass returned
`unknown_object_type` on a deliberately invalid object type, confirming
dispatch without changing a design.

## Child-fork update command and merge shape

After the two-parent merge of `032fb4b`, a fresh fetch found a newer direct
child tip, `d495c4d`, eight commits ahead. Two new source modules,
`sdk/symbols.py` and `sdk/generate.py`, are now adapted. `sdk-symbols`
extracts the local engine's registered names; `sdk-generate` prints filtered
Pascal candidates for review without editing the active script. On this
AD26.11 installation the extraction found 44,094 names, and a component
read plan offered 24 candidates while skipping 15. Sixty-seven focused
SDK, source-header, fork-status and style checks passed. The donor's live
probe handler and generated Pascal block have not yet been deployed, and
its per-request perf attribution is also ported. Two consecutive live ping
calls from the same bridge process produced distinct trace keys
`da93ff10-00000001` and `da93ff10-00000002`; the report joined them to
separate Altium handler times (16 ms and 0 ms). Sixty-two focused bridge,
perf, source-header and style checks passed. Type-scoped coverage accounting
is also adapted: a delegated Pascal accessor counts
only for the object type whose branch calls it. The fixture checks passed,
and the current SDK report still reads 650 of 2,176 declared properties
because the generated block is not deployed. The live SDK probe still needs
review; the later merge `ce7aab8` records `d495c4d` as a parent of `main`.

The live SDK probe and generated component read block are now adapted in
script `.168`. The main Altium bridge restarted and answered a native
`DescriptionString` read (`Part J_TX_1`) and a `not_in_probe` case. The
sheet was closed without saving. Type-scoped coverage rose from 650 to
678 of 2,176 declared properties. A later attempt to reopen that sheet
timed out when the Altium process exited before handling the request;
the process was relaunched and `.168` answered ping. The cause of that
exit and the other generated accessors still require native review.
Windows event 1000 places the crash in `ADVPCB.DLL` (`c0000005`, offset
`0x3c1728`), rather than in the request handler.
After adaptation, merge `ce7aab8` records `d495c4d` as its second parent.
Fresh fetches report zero commits pending from `MOREmbedded/main` and
`upstream/main`. The upstream sync point remains `0bb1b315`.
The follow-up live fork audit found one newly created fork,
`betamoojw/eda-agent`, at exactly `0bb1b315`; its main ref was cached.
The repeated check then matched 63/63 fork defaults and 120/120 live
branches to cached refs. Fifty-three of the 112 cached `forks/*` refs
still have divergent ancestry, which is not a count of missing features.

The direct child fork's `test_update_command.py` was run unchanged against
the current source in a temporary test file: 38 passed and 12 failed. The
current `eda-agent update --status --from <remote-or-folder> --json` already
reports the checkout, installed package, deployed scripts and compiled
Altium version. `eda-agent update --yes` separately updates the primary
checkout. The donor failures include its older exact action text, its
single-command `run_update` interface and a different `--check` exit-code
contract. The distinct deploy-from-folder operation is now available as
`eda-agent install-scripts --from <checkout> --force`: it validates the
source and every `DocumentPath` in its `.PrjScr` before copying into the
existing Altium destination, and treats a
source that is already the destination as a no-op. This does not create a
second runtime script project. Focused install/update checks passed 35/35.
No claim of full CLI contract parity is made.

The status command now follows the donor's distinction between an unknown
Altium state and a step that needs action: unknown remains visible in the
report but exits 0; a real action exits 1. Two focused regression cases
cover both outcomes, and the update/status slice passed 26/26.

`git merge-tree --write-tree HEAD morembedded/main` reported 62 conflicts
(45 content, 15 add/add, 2 modify/delete). The child fork's 33 unique
commits had no zero-conflict merge into this tree. A two-parent merge now
records its tip `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`. Resolution
keeps the current implementations of the 28 paths that an automatic merge
would change, imports the donor's 12 passing SDK-tool checks, and carries
forward the useful ERC count documentation. The working `eda-agent vote`
route was integrated just before this merge. Source and behavior audits
above explain why other donor implementations were already present or
superseded; the ancestry link does not claim every AD25-only behavior was
natively qualified here.

A fresh path inventory on 2026-10-28 compared all 227 paths changed since
the child fork's merge base `84b682c` with this `main`: 225 paths exist here.
The two absent paths are donor test files, `test_sdk_found_tools.py` and
`test_update_command.py`, not production modules. The former ran unchanged
as a temporary test file and passed 12/12 checks for symbol parts, STEP model
export, impedance profiles and STEP export guards; the test is retained in
the merge. The current placement flip, rotation audit and impedance profile
tests passed 27/27. These are feature checks, not proof that every behavior
in the 33 commits has been reconciled; continue the semantic audit.
An in-memory `git merge-tree --write-tree -X ours main morembedded/main`
reduced the unresolved set to two modify/delete paths, but the resulting
tree is **not** suitable for committing: it adds a second
`PCB_GetImpedanceProfiles` implementation to `PCB.pas` beside the current
AD26-tested implementation and interleaves incompatible calculator code in
`cli.py` and `calc.py`. Automatic `-X ours` therefore cannot stand in for
the logical merge. The child also adds a `vote` CLI parser without a matching
dispatch branch; importing that parser alone would advertise a dead command.
The useful part is now wired in `main`: `eda-agent vote --plan ...` forwards
to the existing pairwise web application, with optional offline symbols and
host/port settings. A CLI-to-app test loaded a real DesignPlan fixture and
verified that the local server received the requested port; the backend
startup slice passed 8/8 with this route present. No live vote was written
by that check. A separate local process started the real command with a
fixture plan and empty offline symbol list; `GET /stats` returned HTTP 200
and `n_votes: 0`. The process was then terminated and its temporary fixture
removed. The focused CLI, source-header, documentation-style and update
checks passed 28/28 after four older tests received their missing SPDX
headers. The merge-resolution slice passed 54/54, and the Pascal bundle
lint/build scanned 12 files with zero errors or warnings. A larger optional
Python suite was stopped after 13% with no failure observed to that point;
it is not counted as a passing full-suite gate.
By contrast, `git merge-base main upstream/main` is exactly
`0bb1b3154cca6e58a517b23edee3d7a108f1c232`, which is the second parent
of the completed upstream merge `63f7c16`.

## Complete remote-path and public-name inventory

A fresh inventory of 121 cached remote refs found only three production
paths absent from `main`: `src/eda_agent/easyeda_extension_cli.py` (the
current `eda_agent.easyeda_extension` module and CLI provide its build
route), `scripts/ensure_loop.py` (the current bridge supervisor and
`eda-agent relaunch` cover loop renewal), and `StatusFormStub.pas` (an
AD25 headless script-project alternative, not yet qualified on AD25).
The AST inventory of public tool names found the same 14 donor-only
spellings listed above, with no new name from the refreshed branch refs.
These inventories establish file/name coverage, not full behavioral
equivalence of every divergent commit.

## Fresh large-branch review

The live fork inventory again matched 62/62 default heads and 118/118 branch
heads. `slatyb/main`'s seven feature commits have current routes for the
calculator CLI and optional pcb-toolkit cross-check, fab vendor/stackup data,
replacement-part evaluation, profile templates, fabrication-package readback
and performance reporting. Their focused test slice passed 166/166.

All seven tracked Python files in
`yniantongtian-oss/feat/battery-ai-comsol-lab` match the donor after removing
only the leading SPDX line from our copy. The lab was installed into an
isolated Python 3.12 environment with its declared `dev` dependencies on
2026-10-28. Its own `ruff check src tests` passed and `pytest -q` passed all
six tests, including the short PyBaMM electrothermal simulation with
PyBaMM 26.10.1.1. This qualifies the imported research code locally; COMSOL
itself and the optional `MPh` bridge were not run. The current distribution
verifier additionally checks an sdist and wheel metadata, while retaining
the donor's EasyEDA payload checks.

The `yniantongtian-oss` commit `717efec` pinned six external COMSOL/AI
repositories as Git submodules, without wiring their code into `eda-agent`.
This repo's battery lab already implements an optional MPh session adapter.
The other five external projects remain documented as possible adapter
sources; importing the donor's Git links would add checkouts but no callable
backend feature. The lab's reference page previously said those submodules
were present here; that inaccurate statement has been corrected.

The `jah-yee` `afa13696` Win32 `wintypes` import is already present in
the current UI module through later upstream code. Its direct import had
left a duplicate after the fork merge; the duplicate was removed while
retaining the working import. Fifty-one foreground-guard, control-shape
and dialog-automation checks passed.
