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
