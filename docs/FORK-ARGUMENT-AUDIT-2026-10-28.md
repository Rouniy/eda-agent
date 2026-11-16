# Fork tool-argument audit, 2026-10-28

Scope: the 14 donor-only `(function, argument)` pairs left after the
geometry, multipart and temperature-rise ports. This checks callable
capability, not whether an old call string works unchanged. The relevant
fork refs are cached locally. The direct child `MOREmbedded/main` was
fetched at `032fb4b2088d9cfa8d95daad9572c9f1f49f3d41`.

| Donor spelling | Current route | Decision |
| --- | --- | --- |
| `lib_render_footprint(path)` | `lib_render_footprint(output_path)` | Same caller-chosen SVG destination. |
| `lib_rotate_footprint(save)` | `lib_rotate_footprint`, then `app_save_document` on the exact PcbLib | Keep save separate from a geometry edit and its readback. |
| `obj_zoom(x, y, radius)` with `action="point"` | `obj_zoom_to_xy(x, y, radius)` | Same native `generic.zoom_to_xy` action, exposed directly; this audit extended its Python arguments to fractional mils. |
| `pcb_check_stackup(vendor, stackup)` | `pcb_check_vendor_stackup(vendor, stackup)` | Preserves the vendor-specific comparison alongside the other stack check. |
| `pcb_apply_stackup_template(vendor, stackup)` | `pcb_apply_vendor_stackup_template(vendor, stackup)` | Preserves the vendor-specific dry-run/apply route. |
| `lib_delete_component(name)` | `lib_delete_component(component_name)` | Same symbol selector; current tool also accepts an index. |
| `pcb_build_stack(pcbdoc_path)` | `pcb_build_stack(board_path)` | Same exact PcbDoc and layer-plan input. |
| `pcb_grow_pour(name)` | `pcb_grow_pour(board_path, index, expected_name, expected_layer, ...)` | Current selector guards a specific board and polygon before editing. |
| `pcb_physical_stack(style)` | `pcb_physical_stack(board_path)` plus `pcb_set_stack_style(board_path, style)` | Separate exact-board read and verified style write. |
| Nested `run(batch)` in donor `pcb_build_stack` | Current nested `run(ops)` | Internal helper, not an MCP argument. |

The first five rows account for nine pairs on `MOREmbedded/main`; the
last five account for five pairs in other fork branches. An AST inventory
of all 994 `@mcp.tool()` function names under `MOREmbedded/main`'s
`src/eda_agent/tools` found no name absent from the corresponding current
modules (which expose 1093 tool names). This proves name coverage for
that tree, not full semantic equivalence. The fork's two Python test paths
absent by name, `test_sdk_found_tools.py` and `test_update_command.py`,
were exercised/adapted separately in the upstream sync record.

Verification used fresh `git fetch upstream main` and `git fetch
morembedded main`, `git ls-tree` for source/test paths, Python AST parsing
of decorated tool functions, and focused `git show` reads of donor and
current implementations. `upstream/main` remained
`ee7589c9fc543d0b99bb142dc8ca12b618fffeab`, exactly
`git merge-base main upstream/main`, with zero commits in
`main..upstream/main` at this audit.

After the fractional-mil Python zoom change, seven related tests passed.
The restarted MCP exposed `x`, `y` and `radius` as numeric arguments;
Altium 26.11 returned `x=1234.5678`, `y=-25.125` for a real board zoom.
That board was closed without saving.
