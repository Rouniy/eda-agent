# Altium field notes for AI agents

These behaviors were verified against Altium Designer 26.8.1 while driving it
through this MCP server. Treat them as operating constraints.

## Symbols, models, and footprints

1. A schematic symbol, its footprint model, and its placed PCB component are
   separate objects. Matching designators alone does not synchronize them.
2. Before assigning either model, verify the manufacturer datasheet: package,
   pin count/names, exposed-pad numbering, pitch, and recommended land pattern.
3. Set both the schematic footprint parameter and its implementation/model link.
   A visible `Footprint` parameter does not prove ECO can resolve the model.
4. Verify the exact footprint exists in an installed or explicitly referenced
   `.PcbLib`, then call `library.get_pad_geometry`. A footprint record may exist
   with zero serialized pads and fail only during ECO validation.
5. Pad designators must exactly match schematic pin designators. Common traps:
   diode `A/K` versus `1/2`, named crystal pins versus numeric pads, connector
   `MP` pins, and exposed pads named `0`, `EP`, or the next package pin number.
6. Never infer connectivity from PNG/SVG. Use the compiled netlist and verify
   each `(designator, pin, net)` against the actual PCB pad name.

## Headless schematic-to-PCB assignment

`pcb.place_components` needs geometry (`footprint`, `library_path`), identity
(`designator`, `lib_reference`, `comment`), connectivity (`pad_nets`), and the
correct PCB `SourceUniqueId` (`unique_id`). In hierarchical projects the latter
is normally not the short schematic component ID. It has this form:

```text
\SHEET_UNIQUE_ID\COMPONENT_UNIQUE_ID
```

Derive the prefix from a known matched PCB component on the same sheet
(`pcb.get_components` returns `source_unique_id`) or compiled project mapping.
After placement, save, force a recompile, and require all of the following:

```text
matched_components == schematic component count
extra_in_schematic == []
extra_in_pcb == []
in_sync == true
```

Equal counts are insufficient: the same designator can be unmatched on both
sides when its source ID is wrong.

## Multiple open PCB documents

Altium may retain a different internal current PCB than the visible document.
`app_set_active_document` is not a reliable PCB selector. Before PCB reads or
writes call `pcb.focus_board` with the absolute `.PcbDoc` path and verify the
returned path. Pass `board_path` directly where supported. An unexpected
component count is a stop condition.

## ECO safety and direction

ECO is modal and is not reliably headless. With the target PCB focused, the
verified schematic-to-PCB comparison is:

```text
WorkspaceManager:Compare
ObjectKind=Project|Action=UpdateMe
```

`UpdateOther` is focus-dependent and can reverse the direction into PCB-to-
schematic. Always click **Validate Changes** first, then enable **Only Show
Errors** and require an empty list. Never execute while any footprint operation
is red/unavailable or has dependent pin/net failures. Proposed net changes are
not themselves validation errors; the error-only view is the gate.

## Library serialization quirk

Adding a pad only to a footprint group can look correct in memory but fail to
serialize. This server registers new pads with both the footprint and PcbLib
board and broadcasts registration to both. Always save, reload, and re-read pad
geometry; reject zero pads or unexpected duplicates.

## Restarting the MCP polling script

Use scripts from this checkout only. Do not mix them with the legacy
`C:\Users\Alex\EDA Agent\scripts` copy.

1. If a script-error dialog is visible, capture it, press `OK`, then send
   `Ctrl+F3`. Do not close the MCP form first.
2. Otherwise close the exact `EDA Agent MCP` form, then send `Ctrl+F3` to the
   Altium main window.
3. Launch this checkout through COM:

```powershell
$project = 'D:\msys64\home\Alex\src\22\eda-agent\scripts\altium\Altium_API.PrjScr'
$uri = "dxpprocess://ScriptingSystem:RunScript?ProjectName=$project|ProcName=Dispatcher.pas>StartMCPServer"
$shell = New-Object -ComObject Shell.Application
$shell.ShellExecute($uri, '', '', 'open', 0)
```

4. Require `application.ping` with the expected script version and zero cast
   errors. The status form should remain minimized (typically an off-screen
   rectangle near `-25600,-25600`).

Closing an ECO whose initiating IPC client was killed may stop the polling loop.
Ping after every modal workflow and run the safe reload sequence if it fails.

## Verification gates

- Back up/checkpoint the exact target document before structural edits.
- Re-read every mutation; do not trust a successful write response alone.
- Save, force recompile, and compare schematic/PCB mappings.
- Validate ECO without execution whenever model resolution is in question.
- Run DRC/connectivity audits after an applied PCB change.
- Stop on an unknown dialog, wrong document, missing reference net, zero-pad or
  duplicate-pad footprint, version mismatch, or mapping regression.
