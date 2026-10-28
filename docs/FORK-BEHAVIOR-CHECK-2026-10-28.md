# Fork behavior checkpoint, 2026-10-28

The last integrated synchronization point is
`0bb1b3154cca6e58a517b23edee3d7a108f1c232`, merged by
`63f7c16ab8dd7c703ba9a82ca17b7f06cee1e370` and marked by
`upstream-sync-2026-10-28`. At the latest fetch, upstream/main advanced
one direct child to `75df9907a8ece15a2a0d20952fb67edd09e6d46d`;
that new commit is pending review, not part of `main`. The original checkpoint below was made
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

At `7d6045d`, the two donor-only test files were rerun unchanged against
the current checkout. `MOREmbedded/main`'s SDK file passed 12/12. Its
update file passed 43 checks, failed seven old-interface/source-spelling
assertions, and raised one teardown assertion because its test left the
shared bridge keepalive running. The seven expect `--pull` or a manual
File > Run Script instruction instead of the current `update --yes` and
`relaunch --restart` routes, reject the guarded `install-scripts --from`
route, call the former `cmd_update(as_json)` and `_deploy_from` internals,
or inspect `altium_version` instead of its delegated `altium_runtime`
ping/logger guard. A live `eda-agent update --status --from upstream --json`
returned parseable JSON with our remote current, upstream requiring review,
and package, script folder and Altium session current. The process exited
with status 1 for the upstream action step. Temporary donor files were
removed; these results do not claim unchanged donor API spellings.

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
| `MOREmbedded/claude/determined-gould-ebb38e` `cbff5f9`, `b1d0fa1` | Doctor, probe and report routes trust a live bridge answer over an invisible process table; the earlier `8ec0cd9` lint guards are adapted | The branch-tip `test_probe_and_report_ask_altium_not_the_process_table.py` passed unchanged 12/12 on current `main`; earlier doctor test and live `.163` ping |
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

The latest refresh has 112 cached refs after adding
`betamoojw/eda-agent`, which points exactly to the already merged upstream
tip. A repeat over the 49 divergent distinct tips found no new public
capability beyond the legacy spellings and mappings below. Raw Python
function-name comparison also sees the older `rabihnd` and `james-martinez`
unprefixed tool functions (`get_nets`, `open_project`, and similar), which
map to today's `proj_*`, `app_*` and `obj_*` tool names; those are naming
history, not additional absent handlers.

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
export, impedance profiles and STEP export guards; the donor file itself is
not tracked in `main`. The current placement flip, rotation audit and
impedance profile tests passed 27/27. These are feature checks, not proof
that every behavior
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

The `yniantongtian-oss` `733367c` dashboard-port change was a response
to a local conflict on 8766. The current auto-start now accepts
`EDA_AGENT_DASHBOARD_PORT`, and both auto-started and standalone dashboards
publish their bound URL for Altium's Open Dashboard button. A standalone
8877 instance answered HTTP 200 and wrote the correct URL; script `.169`
passed Pascal lint/build and answered a fresh ping. The button click itself
has not been exercised. The default remains 8766 for existing users.

## Missing-path inventory after the 120-branch refresh

Across the 53 divergent cached refs, only 12 tracked paths under `src/`,
`scripts/`, `.github/workflows/` or `tests/` are absent from `main`.
They resolve as follows:

| Donor path group | Decision and evidence |
| --- | --- |
| `src/eda_agent/easyeda_extension_cli.py`, `tests/test_easyeda_extension_delivery.py` | The installed `eda_agent.easyeda_extension` route and distribution verifier cover the builder/payload behavior; the older module name is not needed. |
| `scripts/ensure_loop.py` | `eda-agent relaunch` and the bridge supervisor provide the loop-recovery route. |
| `.github/workflows/sync.yml` | The donor schedules `tgymnich/fork-sync@v1.8` daily with `FORK_SYNC_TOKEN` to sync `main` directly. This repo records upstream merges after review; an automatic direct sync would bypass that decision. Keep the explicit `fork-status --fetch` and merge workflow. |
| `scripts/altium/StatusFormStub.pas` | AD25 headless alternative remains unqualified on this AD26 host; the one main script project is retained. |
| `tests/test_via_soldermask_relief_is_refused.py` | Its refusal describes the old direct `IPCB_Via.SolderMaskExpansion` crash. The current tool writes through `TPadCache` and has native AD26 readback; reverting to refusal would remove working functionality. |
| `tests/test_batch_refuses_designator_rewrites.py`, `tests/test_custom_pad_shape_is_named.py` | The current batch parser refuses raw designator rewrites, and every current pad-shape reader names `eCustomShape`. |
| `tests/test_placement_cleanup.py`, `tests/test_rosen_small_fixes.py` | Their donor behavior was assessed separately above; some exact error spellings differ while the current operation remains available. |
| `tests/test_security_policy_version.py`, `tests/benchmarks/__init__.py` | These are policy/packaging checks, with no production path. The security policy already names the three backends; its private Rouniy reporting channel remains an open maintainer decision. |

The current designator, via-mask, Workspace and DbLib focused slice passed
33 tests. This inventory checks path-level completeness and the named
behaviors; it does not make AD25 native acceptance or every generated SDK
accessor complete.

## Latest live-ref and regression check

### Small-fork behavior audit after the 49-tip inventory

Three divergent tips whose branch names were not called out in the earlier
tables have been compared directly with current source:

| Fork commit | Donor change | Current `main` evidence |
| --- | --- | --- |
| `lda-audiotech/main` `22bb2df` | Read non-ASCII workspace pointers and accept a UTF-8 BOM on bridge responses | `diag/health.py` decodes the pointer using `config._pointer_encoding()` (the same codec used to write it), and `bridge/altium_bridge.py:_read_response_json` decodes UTF-8 with BOM before its legacy-codepage fallback. |
| `jah-yee/fix/wintypes-import` `afa1369` | Import `ctypes.wintypes` for window pointer actions | `ui/windows.py` imports `wintypes` and `byref` together; `wintypes.POINT` is available to the pointer paths. |
| `malteheringorgatex/wsl-process-detection` `d57df64` | Query Windows `tasklist.exe` from WSL instead of trusting Linux `psutil` | `bridge/process_manager.py:_windows_tasklist_rows` reads the Windows process list, and `_scan_running` uses it when Toolhelp is unavailable. It treats unavailable WSL interop as unknown rather than incorrectly reporting Altium absent. |

The three focused files `test_non_ascii_paths_and_bom_responses.py`,
`test_pointer_gestures_reach_win32.py`, and `test_wsl_bridge_reachability.py`
passed 16/16. These are source and local behavior checks, not native AD25
acceptance.

The donor-only `_validate_pin_designator` helper in `rabihnd/integration` was
also compared with `tools/library.py:_single_pad_designator`. Both reject
grouped pin aliases. Current batch builders deliberately count and report
blank designators as skipped, with an exception for unplated mounting holes;
copying the donor's blanket empty-value rejection would remove that behavior.
The donor's `_prjscr_is_ad25_safe` checks only two header strings. The current
script project contains neither, but this is not proof of AD25 native
compatibility; the AD25 runtime check remains open.
The source-selection guard from `wizd/edev` is now adapted into the CLI:
an editable checkout skips a stale bundled `Altium_API.PrjScr` containing
those AD25-incompatible markers when its main source project is safe. The
guard does not claim to validate every script-project setting. Source
selection, relaunch, health and update tests passed 34/34; a live
`eda-agent scripts-path` still resolves to this checkout's single
`scripts/altium` directory.

The `yniantongtian-oss/main` commit `b643cd0` adds portable-checkout and
manifest-syntax checks. Its `.github/quality/check_repository.py` and
cross-platform `repository-integrity.yml` are already tracked in `main`.
Running the checker on this checkout found 1,260 tracked files, two valid
manifests, and zero errors or reviewed exceptions. This confirms the local
check, not a hosted CI run.

An AST inventory against the integrated `MOREmbedded/main` tip `d495c4d`
found no donor Python function names absent from the current corresponding
source files. Five donor-only Pascal helper names remain after excluding
the generated bundle: `CodeUnitHex4` is now `CodeUnitToHex4`, `PinShownOn`
moved to `Generic.pas`, `FrontPCBBoardPath` became the stricter
`GetPCBBoardForMutation` selection path, and the implicit
`SchDocByPathLoading` is now an explicit project-sheet load followed by an
already-loaded document lookup. The donor's `ImpLayerName` helper was inlined
in the impedance profile reader; this comparison exposed an unguarded
`Layer.Name` access. Script `.173` guards that read and counts a failure in
`read_errors` while retaining the other profile rows. The 12-file Pascal
lint/build and 11 impedance-focused tests passed; a live MCP ping after
restarting the one main script project reported `.173`, matching the bundle,
no stale units and no warnings. The ping confirms script load, not a native
impedance-profile read on a board.

The internal helper `_zone_origin_mils` in `rabihnd/integration` exposed one
real placement gap: the old fixed-grid layout shifted a zone by its
`origin_mm`, while the current force-directed and Sugiyama engines ignored
that field. The shared `compute_layout` pipeline now applies the converted,
grid-snapped offset after placement and motif shaping, clamps the whole
group to the declared sheet, and reruns overlap repair. A default zero
offset leaves existing layouts unchanged; `size_mm` remains advisory, as
it was in the donor. Both engines were checked with a 25.4 mm / 12.7 mm
offset (exactly 1,000 / 500 mil in the resulting placements) and with an
oversized offset that stops at the sheet boundary without collapsing the
group. The focused layout tests passed 101 with one skip. This is offline
layout behavior; no schematic document was changed. The full `tests/design`
package then passed 1,973 tests, skipped 11, and had one expected failure.

### Donor-only internal Python names

The 49-tip function-name inventory produced 14 names absent from current
source. Each has now been traced to behavior, rather than counted as a
missing user feature:

| Donor name(s) | Current behavior or decision |
| --- | --- |
| `_altium_process_running`, `_check_save_all_canary` | Doctor uses `_altium_process_scan` and a read-only `_check_command_canary`; a save-all call is not a harmless liveness probe. |
| `_normalise_mpn` | Compatibility alias to the exported `normalise_mpn`. |
| `_coord` | `_read_coord` keeps the SchDoc fraction exactly, including negative coordinates. |
| `_listed`, `schematic_pin_nets` | ECO verification uses `netlist_pin_map` and reports each list's true count, truncation flag and rows directly. |
| `_emit_junctions` | Deliberately omitted: Altium auto-junctions form at the same-net wire geometry; explicit manual dots remain available to callers. |
| `_ends` | Diffpair `_end_options` explores multiple pad couples on different components and retries candidates. |
| `_mst` | Rotation scoring uses `mst_length`. |
| `_copy_extension_source`, `packaged_extension_dir` | `easyeda_extension.source_dir` and `build` choose checkout or packaged source and copy the build payload. |
| `_prjscr_is_ad25_safe` | Adapted into CLI script-source selection, with an editable-checkout fallback. |
| `_validate_pin_designator` | `_single_pad_designator` rejects grouped aliases while batch builders report blank entries as skipped. |
| `_zone_origin_mils` | Integrated as the offset conversion in `_apply_zone_offsets` for both current layout engines. |

The junction, diffpair, SchDoc, ECO, EasyEDA, rotation and doctor-focused
slice passed 104 tests with 11 fixture skips. This closes the name-level
inventory, not the wider behavior audit of divergent commits or AD25 native
acceptance.

### Unchanged donor-test replay from `mooreaa/main`

Four donor test files were run unchanged against the current code from
temporary test paths, then removed. `test_added_altium_tools.py` passed
86/111. Nineteen failures call board tools without the exact `board_path`
(two xSignal writes additionally omit `expected_count`); two use the old
`pcb_grow_pour(name=...)` and `pcb_physical_stack(style=...)` call shapes;
three assert old Pascal source layout rather than the current equivalent
read-only property or rule helper; and one expects no `expect_file` field
on `pcb_pours_at`. The local corresponding files passed 129/129. The
remaining donor assertions do not establish missing board operations.

`test_pcb_stack_from_file.py` passed 21/24. Its three failures are exact
response differences: the current check also reports a missing legacy
chain before `no_dielectric`, describes the stale manager layer as
`Top thickness: ...` rather than `Top: ...`, and requires an expected
PcbDoc SHA-256 before an offline reset. The corresponding local stack
tests pass. Donor PDF-export and port-crossref files passed 41/45. Their
four failures expect an already-existing PDF path to be accepted or a
port-reference edit without the current preview/confirm/hash gate. The
three corresponding local stack, export and crossref files passed 46/46.
None of these 32 donor failures
justifies removing the current exact-board, file or edit guards; the
unmodified tests remain useful evidence of changed call contracts, not
proof of native behavior parity.

At `main` `6cdb3af`, `fork-status --fetch --cached-forks
--verify-fork-branches --json` refreshed origin, upstream and MOREmbedded.
The upstream tip and merge base are both `0bb1b3154cca6e58a517b23edee3d7a108f1c232`;
the last explicit upstream merge is `63f7c16`. MOREmbedded's tip and merge
base are both `d495c4d8802c0b7259068c2f414b7b23bfdf6ee6`. All 63
live fork defaults and 120 live branches matched their cached refs.

An AST pass over the 49 distinct divergent tips found 116 donor-only
`@mcp.tool` function names. Of these, 104 are from the old unprefixed API
in `rabihnd` and `james-martinez`: 65 have an exact suffix match after
the current namespace prefix; 39 require a renamed-route comparison, such as
`compile_project` / `proj_compile`, `query_objects` / `obj_query`,
`get_open_projects` / `proj_list_open`, and `update_pcb` / `proj_sync_pcb`.
All 39 proposed current route names exist in the registered tool source.
The other 12 are the prefixed legacy spellings described above. This
name check does not prove behavior parity; it prevents old API names from
being counted as 116 unimplemented features.

A signature/docstring pass against `rabihnd/integration` checked those
39 renamed routes more closely: 34 retain the donor's input names; five
change their input shape. Single component and wire placement are now
expressed as one-item calls to the bulk placement tools; the bulk
component route adds document/tidy options; document removal adds a
`save_project` option; and PCB sync adds wait and pad-net verification
options. The donor's `execute_menu` claims execution, but the current
`app_run_menu` labels its result as dispatch only and `app_click_menu`
verifies a real menu click. Focused placement, project membership, ECO
guard and post-sync tests passed 49/49 after their mocked ECO test was
isolated from a modal window in the user's live Altium session. This
narrows the compatibility gap to old call shapes, not a missing CAD
operation; it does not prove every old response field is identical.

The full Python suite at `6cdb3af` ran again after six failing tests were
repaired: 9780 passed, 165 skipped, one expected failure, and two failures.
Those two exposed a stale generated tool reference and a via-mask handler
that could fall back to another board after losing focus. The reference was
regenerated, and the handler now uses a focused-board-only resolver;
64 related tests and 9 via checks passed. The generated SDK accessor for
`CompilationMasked` was removed because AD26.11 ignored its write, and
the generator now records it as native-unreliable so a later regeneration
does not restore it. Its focused generator/reflection slice passed 40/40.
The current `.171` script passed lint/build and answered a native restart
ping. The full Python suite after these fixes completed with 9,783 passed,
165 skipped and one expected failure (no failures) in 16:07.

The unchanged child-fork `test_update_command.py` was rerun separately:
42 passed, 8 failed. Three failures assert the donor's old action wording;
two inspect obsolete `altium_version` source strings; one calls the old
`cmd_update(as_json=...)` signature; one expects the donor's raw
`_deploy_from` copier; and one mocks only the old version helper while the
current command checks the loaded script-project path. On the fake state
used by that last test, the live `.171` Altium project was correctly
reported as different from the fake `/home/scripts` folder. These are
specific compatibility differences, not eight proven missing features.

## Generated SDK readback after the child merge

The live `.171` `sdk-probe --doc-path` call exposed an undeclared
`SchDocByPathLoading` identifier before probing any property and stopped
the DelphiScript loop. The handler now uses `LoadedSchDocByPath`, which
only resolves an already open sheet. Script `.172` passed Pascal lint/build,
restarted in AD26.11.1.5, and answered the same probe on IC44 in
`Z:\sinara\eem_fmc_carrier\PCB\I2C.SchDoc`. All 29 names in the generated
`ISch_Component` block returned `exposed=true` across five batches.
The sheet was closed without saving. This qualifies the accessors on that
component and fixes the explicit-path probe; behavior with other component
kinds remains a separate native check.

## Direct-child test replay on current main

Nine changed test files from `MOREmbedded/main` were replayed unchanged
against the current source: 129/129 passed. The initial replay found two
gaps. The release instructions still expected script `.172`; they now name
the active `.173` and put previous full-version references under dated
history headings. The deployed `Generic.pas` block also had two live-proven
DbLib getters absent from a fresh generator render. The generator now keeps
`UseDBTableName` and `UseLibraryName` in the block despite their overlap
with the handwritten property handler, and a local parity test guards the
deployed block. No Pascal code or loaded script changed in this replay.

## WSL pointer write recovered from delivery-fork review

Reviewing `yniantongtian-oss/feat/astra-verify-boost` commit `042abf6`
exposed a cross-platform regression in the current `write_workspace_pointer`:
it selected a non-Windows fallback codec but first insisted that Windows-only
`mbcs` exist. On WSL that returned without writing any pointer. The writer
now validates and uses the same selected codec. A scratch-pointer test checks
the missing-codec path leaves no empty file, while the WSL readback test
checks the Windows-form path and fallback encoding. The pointer, WSL and
Unicode transport slice passed 18/18 on Windows. A real WSL-to-Altium session
has not yet been run for this change.

## Installed-wheel release bundle from delivery fork

`yniantongtian-oss/release/0.5.0-deliverable-hardening` publishes an
EasyEDA `.eext` beside the wheel and sdist, with SHA-256 checksums. The
current package had verified and installed its wheel but stopped there.
`scripts/verify_distribution.py` now builds the `.eext` using the current
`eda-agent easyeda-extension build` command from that clean wheel install,
then writes all three deliverables and `SHA256SUMS.txt` under `dist/`.
The package CI job uploads that verified set under a commit-SHA name.
A local 0.7.1 wheel/sdist build and clean-wheel verification produced a
55,115-byte `.eext`; all three listed hashes matched an independent
SHA-256 calculation. The focused EasyEDA tests passed 17, with two
optional skips. Hosted Actions publication remains unverified because
this fork's workflows have no completed hosted run at this checkpoint.

The separate `viknandala-eng/main` Workspace component test file passed
6/7 unchanged against current main. Its one failure expects placement
immediately after `set_active_document`; current main also reads back the
focused document and refuses placement on a mismatch. The current
Workspace and live-sheet test slice passed 46/46. This is a stricter
selection check, not an absent Workspace placement route.

## Full-suite stabilization after zone-origin integration

The complete Python suite on `df28d1d` finished with 9,789 passed,
165 skipped, one expected failure and one failure. The failure was a
duplicate mil-to-mm literal introduced in the recent zone-origin layout
adapter; the repository requires that factor to come from `eda_agent.units`.
The adapter now uses `MM_PER_MIL`, and the unit-conversion and layout
slice passed 61 tests with one optional skip. No other full-suite failure
was reported; a new full run after this single-line repair remains to be
recorded separately.

The delivery guide from `yniantongtian-oss/release/0.5.0-deliverable-hardening`
is now adapted as `docs/DELIVERY_ACCEPTANCE.md` and linked from the README.
It names the current 3.11/3.12 test matrix, Pascal cross-validation,
installed-wheel EasyEDA build, exact-SHA artifact and native editor check,
without retaining the donor's old 0.5.0 version or separate EasyEDA CLI.

## Newly advanced direct-child diagnostics branch

A live 63-fork/120-branch refresh found one new head:
`MOREmbedded/claude/determined-gould-ebb38e` moved from `cbff5f9` to
`b1d0fa1`. Its added `app_capability_probe` and `app_get_report` behavior
was missing in `main`: both diagnosed Altium as absent when a process-table
scan failed even if the bridge answered. The donor's unchanged test file
initially failed 11/12 against our source. Both tools now try the normal
ping, then an ungated ping if needed; they report the process scan separately
as `process_scan_saw_altium` and time the attempt that answered. The donor
test file and existing capability/doctor tests pass 31/31. A subsequent
cached-ref audit matched 63/63 fork defaults and 120/120 branch heads.
After the Python MCP restart, `app_ping` matched `.173`; live
`app_get_report` returned `altium_running=true`,
`process_scan_saw_altium=true`, `version_match=true` and a 46.7 ms round
trip. With the process scan deliberately hidden in a separate read-only
client, both tools still reached the real Altium bridge: the probe and
report each returned `altium_running=true`,
`process_scan_saw_altium=false`, script `.173`; the report measured
44.2 ms and matched the bundled version.

The complete Python suite on `4b43d58` then passed: 9,803 passed,
165 skipped and one expected failure in 15:18, with zero failures.
The 14 warnings are `PyMakeBuffer` deprecation notices from the Win32 UI
tests. This includes the newly added direct-child diagnostic tests and
the earlier zone-origin conversion repair.

The branch's exact tip `b1d0fa199d6f38438dde2449191248360f70fd95`
was subsequently merged into `main` by `02d6964`, preserving Git
ancestry as well as the adapted behavior. Its extra explanatory comments
were retained; the older duplicate changelog block was not. The donor
probe/report tests and related local tests passed 42/42 after the merge.
The latest 63-fork/120-branch refresh reports 53 nonancestor cached refs.

Script `.179` stabilizes a large-board read encountered during native
fork verification. The former unbounded `pcb_get_vias` response stalled
Altium while serializing 22,617 vias. The current handler scans the board
once, emits at most 1,000 rows by default, and returns a total count,
offset, returned count and truncation flag. It accepts an exact net filter;
the diff-pair audit reads the total count of each net, preserving the
symmetry check on paged boards. A native first/last page and GND-filter
read passed on that same board with the original file unchanged; the
release verification records the numbers.

The `yniantongtian-oss/upgrade/reliability-20261011` donor's EasyEDA
delivery tests use its removed `easyeda_extension_cli.py` entry point.
The current `eda_agent.easyeda_extension` already selects explicit
source files, excludes old `.eext` packages, refuses a nonempty output
folder without `--force`, and builds from a clean installed wheel as
verified above. Its separate security-policy drift guard was absent.
An adapted test now checks that `SECURITY.md` names the package's current
version line and all three shipped EDA backends; the security and
EasyEDA packaging slice passes 9/9.

## Native free-library and footprint acceptance after the fork merge

A fresh `eda-agent fork-status --fetch --cached-forks
--verify-fork-branches --json` at `05ed05b` found `upstream/main`
at the tagged sync point `0bb1b315` and `MOREmbedded/main` at the
merged child tip `d495c4d`; neither has commits pending. All 63 direct
fork default tips and all 120 live branch tips matched the cached refs.
The 53 divergent cached refs still require behavior-level review; their
presence alone does not establish an unported feature.

On AD26.11.1.5, script `.174` created a free disposable PcbLib with
`application.create_document(kind=PCBLIB, add_to_project=false)` and
reported `focused=true`. `application.get_active_document` returned
that exact path and `PCBLIB`. `library.create_footprint` added `FILL_QA`;
`library.add_footprint_fills` added one 100 by 50 mil Top Overlay fill.
`library.get_footprint_primitives` returned the native fill with bounds
`(0, 0, 2.54, 1.27)` mm. After `application.save_document`, close and
reopen, `library.get_footprints` still listed `FILL_QA` and the fill
readback was identical. The library was closed and the scratch file
removed. The earlier asynchronous `ScriptingSystem.DLL` exception did
not recur in this sequence; its original cause remains unproven.

The `.174` focus repair uses the current editor view's owner when the
workspace focused-document pointer is empty. Pascal lint/build passed,
and 38 focused document/context/version checks passed. The main
Altium loop was restarted and answered the live native calls above.

## Native board-region arc acceptance

The `vincent-himpe/feature/region-true-arcs` behavior was exercised on
a disposable free PcbDoc in AD26.11.1.5 with script `.174`. A four-vertex
Top Layer region had one 90-degree arc from `(1000, 1000)` to
`(1100, 1000)` mil. `pcb.place_region` returned `placed=true`,
`arc_edges=1`, `name=ARC_QA`, and the four-vertex `shape` with a
90-degree sweep at its first vertex. After `application.save_document`,
close and reopen, `pcb.get_layout_model(section=copper)` returned the
same shape in native coordinates: `[[10000000,10000000,90],
[11000000,10000000,0],[11000000,11000000,0],
[10000000,11000000,0]]`. This proves the arc survives a disk round
trip as a shape segment, not only as a flattened contour response.
The scratch board was closed and removed.

## Re-running donor placement and Rosen checks on current main

At `b468962`, the unchanged `mooreaa/main` donor tests were run against
this checkout as temporary test files and then removed. The placement
cleanup file passed 20/22 checks. Its two failures compare source text:
the pin query now limits live-pin filtering to schematic queries (and
allows explicit `OwnerPart` filters), and port width now uses a fractional
mil value instead of the donor's `int(width)` spelling. The Rosen small-fix
file passed 15/18 checks. Its three failures expect the old flat
`PRINT_DIALOG_NOT_SILENT` error instead of the current structured
`PREVIEW_NOT_SILENT` refusal, and the donor's `SameDocPath` spelling
instead of `CanonicalPathValue('path', ...)` before `CloseDocument`.
These five assertions do not show a missing operation. The current source
still applies the font, port, text-frame, pin and document-close guards
that those tests exercise. This is a source/contract comparison; it does
not add an AD25 native run on this AD26 host.

## Library edit state after native footprint creation

The free-PcbLib acceptance above exposed that AD26.11 returned
`IServerDocument.Modified=false` immediately after a successful
`library.create_footprint`. The bridge already recorded that edit for
`app_save_all` and safe close, but `app_get_active_document` and
`app_list_documents` reported `modified=false`, concealing the pending
save from `app_context`. Script `.175` now reports a loaded document as
modified when either its native flag or the bridge's edit record says
it changed. `application.save_document` reports that combined state
before and after its confirmed disk write.

On a disposable free PcbLib, `application.create_document` first reported
`modified=false`; `library.create_footprint(name=DIRTY_QA)` succeeded,
and both active and open-document reads reported `modified=true`.
`application.save_document` returned `modified_before=true` and
`modified_after=false`; a fresh active-document read also returned
`false`. The library closed without a prompt and the scratch file was
removed. Pascal lint/build passed and 33 focused tests passed. This
repairs the dirty-state signal needed by clients using the fork's
footprint writers.

## Native keepout restriction persistence

The `vincent-himpe/feature/keepout-restrictions` property path was
checked on script `.175` in AD26.11.1.5. A disposable free PcbDoc
received one netless Top Layer track from `(1000,1000)` to
`(1100,1000)` mil. An initial `generic.query_objects` returned
`IsKeepout=false` and all five restriction flags `false`.
`generic.modify_objects` set `IsKeepout=true`,
`IsKeepoutForCopper=true`, `IsKeepoutForSMDPad=true`, and the Track,
Via and TH Pad restrictions to `false`; it reported one match and no
failed or unreadable properties. A read before save returned those
values and `application.get_active_document` reported `modified=true`.
After save, close and reopen, another query returned the same six
flags. The board was closed and its scratch file removed. This proves
native property read/write persistence on this AD26 build; a polygon
repour or DRC effect was not tested in this run.

## Native keepout effect on a polygon pour

A second disposable PcbDoc closed the repour gap above on AD26.11.1.5.
`pcb.place_polygon_rect` poured one netless Top Layer polygon over
`(1500,1500)` to `(2500,2500)` mil. Before the keepout, the copper
layout model had one poured region. A 20 mil Top Layer track ran from
`(2000,1450)` to `(2000,2550)` mil across it. `generic.modify_objects`
set `IsKeepout=true`, `IsKeepoutForCopper=true`, and
`IsKeepoutForTrack=false`; readback confirmed all three.

`pcb.repour_polygons` rebuilt that one polygon with `failed=0` and
reported `pieces_before=1`, `pieces_after=2`, and copper area dropping
from `645.16` to `618.848052624` square mm. The copper layout model
then contained two poured regions. After an exact save, close and
reopen, it still contained two and the track retained the three flag
values. This verifies the native copper-exclusion effect in addition
to property persistence. DRC treatment of other object kinds was not
measured. The scratch board was closed and removed.

## Fresh changed-tool and path inventory after `.175`

At `192ae5f`, `fork-status --fetch --cached-forks
--verify-fork-branches --json` again found upstream `0bb1b315`
and child fork `d495c4d` with zero commits pending, and matched all
63 direct fork defaults and 120 live branch tips. There are 53 cached
refs whose tips are not ancestors of `main`.

A new AST pass inspected `@mcp.tool` functions in Python tool files
changed between each divergent ref's merge base and its tip. Only six
public spellings were absent from current source:
`lib_list_vault_libraries` in `cad435/main`, and `lib_add_pin`,
`lib_add_symbol_line`, `lib_diag_footprint`,
`lib_screenshot_footprint`, `lib_set_label_format` in
`rabihnd/integration`. Their current plural, catalogue, body-read and
render/capture routes are mapped in the public-name inventory above.
This scan tests names, not argument or response parity.

The same 53-ref comparison found eight changed paths absent from
`main`: `.github/workflows/sync.yml`,
`scripts/altium/StatusFormStub.pas`, `scripts/ensure_loop.py`,
`src/eda_agent/easyeda_extension_cli.py`, and four donor tests
(`test_custom_pad_shape_is_named.py`,
`test_easyeda_extension_delivery.py`, `test_placement_cleanup.py`,
`test_rosen_small_fixes.py`). Their behavior and decisions are recorded
in the missing-path inventory above. AD25 runtime qualification of the
headless stub remains open; this host has AD26.11 but no AD25 install.

## Native one-sided via-mask acceptance

The `vincent-himpe/fix/via-mask-bottom-follows-top` branch behavior now has
a disk-round-trip check in `CURRENT-STATE.md`. On AD26.11.1.5 script `.176`,
setting `SolderMaskManual=true|SolderMaskExpansion=4` on a disposable via
also set `SolderMaskBottomExpansion=4`; both persisted after save/reopen.
The test also exposed a redundant `FoundNet.AddPCBObject` call in
`pcb.place_via` that Altium rejected at compile time. It was removed; the
existing `BindPrimitiveToNet` path remains. The native bridge again answers
ping from the one main script project.

## Shared tool argument review across divergent branches

An AST pass over all 53 cached fork refs outside `main` ancestry compared
the parameters of their `@mcp.tool` functions with current `main`. Only
14 shared tool names had a donor-only parameter in any branch. Twenty-one
refs carried one of these differences, often the same old signature.
This compares call contracts, not the behavior of every function body.

| Donor signature difference | Current operation or decision |
| --- | --- |
| `pcb_calc_wavelength` (`er_eff`, `length_mils`), `pcb_calc_wire_gauge` (`diameter_mils`), `pcb_calc_fusing_current` (`seconds`, `area_sq_mils`), `pcb_calc_padstack` (`vendor`, `copper_layers`, `kind`, `outer_oz`, `tier`) | The donor physics/fab formulas are exposed by the separate `physics_calc_*` tools. The current `pcb_calc_*` spellings retain their earlier geometric calculator contracts. |
| `obj_zoom` (`x`, `y`, `radius`) | Point zoom is `obj_zoom_to_xy`; the general `obj_zoom` keeps its fit/document/selection actions. |
| `lib_rotate_footprint` (`save`) | Rotation leaves the library dirty for inspection; `app_save_document` saves the exact PcbLib separately. |
| `lib_render_footprint` (`path`) | `output_path` selects the SVG destination. |
| `pcb_grow_pour` (`name`) | The current selector requires exact board, polygon index, expected name and layer, then verifies the preview before editing. |
| `pcb_physical_stack` (`style`) | `pcb_set_stack_style` provides the write with exact-board selection and dry-run/readback. |
| `pcb_build_stack` (`pcbdoc_path`) | The same operation takes `board_path`. |
| `lib_delete_component` (`name`) | The same operation takes `component_name` or a verified component index. |
| `easyeda_activate_document` (`uuid`) | `tab_id` is required because EasyEDA's activation API accepts an open tab ID; document UUIDs go through `easyeda_open_document`. |
| `easyeda_cross_probe` (`primitive_ids`) | The current cross-probe uses names; `easyeda_select_primitives` accepts editor primitive IDs. |
| `pcb_set_rule_properties` (`priority`, generic min/max limits, preferred via hole and impedance names) | The current tool has typed, read-back constraint fields for width, length, signal impedance, flight time, differential-pair impedance and via size/hole. Priority is read-only through the Altium scripting interface. The donor's generic `IPCB_Rule` writes are not evidence that all those fields work on native rule subtypes. |

The Length rule limits were added in script `.180` and verified on a disposable
copy of `03-07366_R3.PcbDoc`: `LengthStubFind` (kind 3) read back 10.5 mil
minimum and 50.25 mil maximum after a setter call. The source board was
untouched and the copy was closed with edits discarded. This review leaves
other generic rule-limit candidates and AD25 native checks open rather than
equating a changed parameter name with an absent feature.

Script `.181` also added typed Signal Integrity Impedance limits. On a copy
of `UNG8071_B1-EVB-KSZ9477.PcbDoc`, rule `MaxMinImpedance` (kind 33) read
back 45.5 and 60.25 ohms; Altium's rule descriptor showed the same values.
The copy was closed with edits discarded and the bridge still answered ping.

Script `.182` adds creation and read-back updates for the Signal Integrity
Flight Time Rising/Falling Edge rules. No existing flight-time rule appeared
in the `Rules6` streams of 614 corpus PcbDocs, so the native check created
both kinds on a disposable copy of `CW308T_AVR.PcbDoc`: Altium's descriptors
showed 2/3 ns at creation and 4/5 ns after updates. Both setter replies
confirmed the values in seconds. The copy was closed with edits discarded;
the source design was unchanged. This confirms the API path and storage,
not an actual flight-time DRC violation on a signal-integrity design.

A fresh `fork-status --fetch --cached-forks --verify-fork-branches` after
`d019be2` matched 63/63 fork default tips and 120/120 live branch tips.
`MOREmbedded/main` `d495c4d` remains in `main`; `upstream/main` is
`75df990`, one commit after the marked synchronization point `0bb1b315`.

The SDK coverage audit now follows the existing typed `ReadSchPinProp` and
`SchGetExtra` branches only for their guarded object types. Before this
correction, the report and `sdk-generate --object-type pin` counted working
pin fields such as `ShowName`, `DefaultValue`, and `HiddenNetName` as missing.
The corrected report reads 713/2176 reachable declarations (previously
677/2176); this is a measurement correction, not 36 new runtime properties.
The generator's candidate list now excludes those already handled fields.

Script `.184` extends the child's SDK probe to `ISch_Pin` and exposes 14
live-qualified pin reads through `obj_query`, including
`DescriptionString`, `IdentifierString`, UI/error flags, text-position
margins, and the object's SDK handle. On a disposable copy of
`Z:\sinara\eem_fmc_carrier\PCB\I2C.SchDoc`, every candidate answered
for IC44-1; a later `ePin` `obj_query` read the new fields with zero
unknown, failed or unreadable properties. `CompilationMasked` was not
included because its pin read has not been qualified. The copy was closed
without saving. Corrected SDK coverage is 727/2176 declarations (33.4%).

All eleven current `morembedded` remote refs, including the direct child's
`main`, `feature/company-profiles`, four `pr*` branches, and three `claude/*`
branches, passed `git merge-base --is-ancestor <ref> main`. The exact marked
upstream synchronization commit and current merge base are both
`0bb1b3154cca6e58a517b23edee3d7a108f1c232`; `upstream/main` is one
commit later. Thus the child's branch commits are all represented in our
history, while the wider behavior audit of other forks remains open.

A full suite run on `38f71fc` produced 9,811 passes, 165 skips, one expected
failure and two failures: a source guard matched a comment mentioning the
excluded compile-mask property, and the generated tool reference had a stale
`pcb_get_vias` description. The comment and reference were corrected; both
failed tests then passed (2/2). The entire suite was not rerun after these
documentation-only corrections.
