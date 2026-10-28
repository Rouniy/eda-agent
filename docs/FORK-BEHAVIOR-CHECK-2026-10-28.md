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
