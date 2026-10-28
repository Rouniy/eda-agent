# Fork behavior checkpoint, 2026-10-28

`main` / `origin/main` were `52d3b8c8126109e12d2f08e0bc0a18d837874409`
at this check. The exact `upstream/main` merge base and remote tip were
`ee7589c9fc543d0b99bb142dc8ca12b618fffeab`; no upstream commits were
pending. The upstream tip is recorded as the second parent of merge
`338f615`, so the synchronization point is Git ancestry, not a guessed
date. `MOREmbedded/main` was `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.

`eda-agent fork-status --fetch --cached-forks --verify-fork-branches --json`
matched all 118 live branch tips to cached refs. Fifty-four cached refs
are not ancestors of `main`; that count measures divergent commits, not
missing functionality. No new branch tip appeared since the previous
118-branch check.

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
script project. This is a possible compatibility gap, not a proved missing
runtime feature: the current AD26.11 script responds, but no AD25 host is
available for a compile check. Review the stub and project wiring before
claiming AD25 parity.

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

The direct child fork's `test_update_command.py` was run unchanged against
the current source in a temporary test file: 38 passed and 12 failed. The
current `eda-agent update --status --from <remote-or-folder> --json` already
reports the checkout, installed package, deployed scripts and compiled
Altium version. `eda-agent update --yes` separately updates the primary
checkout. The donor failures include its older exact action text, its
single-command `run_update` interface and a different `--check` exit-code
contract. The distinct deploy-from-folder operation is now available as
`eda-agent install-scripts --from <checkout> --force`: it validates the
source before copying into the existing Altium destination, and treats a
source that is already the destination as a no-op. This does not create a
second runtime script project. Focused install/update checks passed 35/35.
No claim of full CLI contract parity is made.

The status command now follows the donor's distinction between an unknown
Altium state and a step that needs action: unknown remains visible in the
report but exits 0; a real action exits 1. Two focused regression cases
cover both outcomes, and the update/status slice passed 26/26.

`git merge-tree --write-tree HEAD morembedded/main` was also checked without
touching the worktree. It reports 62 conflicts (45 content, 15 add/add,
2 modify/delete). The child fork's 33 unique commits therefore have no
zero-conflict merge into the current tree. Its public commands and major
behavior groups have been reconciled above, but making its tip a second
parent still requires a deliberate merge resolution and regression check.
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
