# Changelog

This file did not exist before this entry (no changelog convention was
established in the repository's history; releases were tracked only by
git tag and PyPI description). Added here using the common
[Keep a Changelog](https://keepachangelog.com/) format as a reasonable
default - adjust or drop if the project prefers a different convention.

Where an entry says UNVERIFIED, it means the code is covered by tests
but has not been watched working against a live Altium session or a real
Nexar account. Each such tool says so in its own docstring too; the
generated [`docs/TOOL_REFERENCE.md`](docs/TOOL_REFERENCE.md) carries a
maturity classification for every tool.

## [Unreleased]

### Added

- **Token usage of the EDA tools, counted.** Every MCP tool call is
  measured as the server sends it: the arguments the AI wrote and the
  result it reads back, turned into an estimated token count (about 4
  characters a token, images by their size as the model shrinks them),
  with the time taken. Kept per workspace in `.eda-agent/usage/` (which
  ignores itself for git), summed per tool, day, session and profile.
  Shown on a new **Stats** tab in the status window in Altium and a new
  **Usage** view in the dashboard (key 9). A setting, `usage_stats`
  (default on): **Token stats** on the Config tab, or per profile in the
  dashboard's Workspace view; `EDA_AGENT_USAGE_OFF=1` also turns it off.
  See [`docs/TOKEN_USAGE.md`](docs/TOKEN_USAGE.md).

- **`eda-agent start` brings one design workspace up in one command.**
  Each workspace keeps its own settings in `.eda-agent/workspace.json`
  (profile, dashboard port, the Altium 365 workspaces the tools may use)
  and its dashboard log in `.eda-agent/logs/`, so two workspaces share
  nothing and no client detail lands in this repository. Secrets stay in
  the user environment; the file refuses keys that look like one. Only an
  eda-agent process is stopped to free the dashboard port.

- **An offline copy of an Altium 365 managed library, kept in the profile.**
  `altium365_scan_library` reads every component, symbol, footprint and
  folder into `<profile>/library/<workspace host>/` as JSON and CSV, past
  the 10,000-row `totalCount` cap, with several readers on row ranges and
  pages halved when they time out; an interrupted scan continues.
  `altium365_update_library` rereads all but the bulk block at the end of
  the list and probes the row past it. `altium365_search_library` searches
  it offline and `lib_search` folds it in as `source: "altium365"`.
  `altium365_library_report` lists gaps and, given design folders, joins
  placements from `.SchDoc` files on the item id and flags older
  revisions. CLI: `altium365-scan-library`, `altium365-update-library`.
  Live-checked on 2026-11-10 against a 22,561-component workspace: the
  scan and the counts matched an independent scan, the refresh took
  1m49s. `profile.json` names the workspace in `altium365_workspaces`.
- **`altium365_scan_3d_models`** reads the library's 3D model items from
  Altium's Explorer panel, which the GraphQL API cannot list. UNVERIFIED:
  the live run was stopped before it finished.

- **Project stages in the dashboard.** The Workspace view's Settings card
  has a switch for the NPI gates (off by default; it writes the profile's
  `phase_gates.json`, as `phases-enable` does). With it on, a *Project
  stages* card shows each tracked `.PrjPcb` as a stepper from Feasibility
  to Production, passed, current, ahead or not run, and each stage opens
  its gate's checklist to mark Met, Unmet, Waived or Open with the
  evidence. Projects are tracked by path, or picked from those open in
  Altium; each has a revision, and changing it reopens the gates. The list
  and the answers live in `<workspace>/phase_gates/`, never in a
  repository, and the ledger is the one the `design_phase_*` tools write
  (`product` = the project's file name). See docs/NPI_PHASE_GATES.md.
- **A Research stage** between Feasibility and Prototype, with five
  checks: the architecture chosen, risks ranked and owned, the top risks
  retired on an eval kit or in simulation, reference designs read, and
  every requirement mapped to a block. 47 checks across six stages.
- **Per-profile settings.** A profile may carry `preferences.json` with the
  Altium panel's Config-tab keys (component value format, keep in view,
  dialogs, and the edits/deleting/closing/UI-automation safety switches)
  and `default_mode`, the design mode a run starts in. The profile wins
  over the panel's one-per-machine file for the value format and workflow
  settings; for the safety switches the stricter of the two wins, so a
  profile can add a restriction but never lift one. `default_mode` sits
  between `EDA_AGENT_MODE` and `eda-agent mode-use`. Refusals and the
  value-format tool name the profile file when it decided.
  `profile-validate` checks the file. See docs/PROFILES.md.
- **Settings card in the dashboard's Workspace mode (key 8).** Shows each
  of those settings, the value in effect and where it comes from (this
  profile, the Altium panel, the environment, `mode-use` or the default),
  and sets or clears it in the profile's `preferences.json`. The panel's
  own file is read, never written. The Altium panel itself still shows
  only its own choice; UNVERIFIED on a live Altium.

- **Dashboard Workspace mode.** A top-bar chip names the profile in
  effect and where it comes from; mode 8 shows the resolution order, a
  button per central profile to switch to it, the design-rule targets and
  the rules they produce, rulesets, ERC sets, fab limits, templates and
  conventions, each file viewable read-only, plus compare, preview and
  apply against what is open in Altium. See docs/PROFILES.md. The
  compare/apply buttons call the existing `profile_diff_all` and
  `profile_apply_all`; UNVERIFIED from the page against a live Altium.
- `profile-validate` now names why a ruleset is invalid, not only that it
  is. The check itself moved to `profile.validate_profile`, which the
  dashboard uses too.

### Merged from upstream

- **27 commits, `214f5d3..5e126f6`.** Fifteen files conflicted. Four
  resolutions were not a choice of side:

  - `KnownPCBPropertyList` was unioned. The file's own comment warns that
    a list lagging the reader tells a caller a property does not exist
    when it does, so both sides' names are in it.
  - In `PCB_PlaceTracks`, upstream's block was a SECOND `Result`
    assignment after ours. Taking it would have dropped
    `skipped_existing`, `nets_not_found` and `connectivity_rebuilt`; ours
    is kept and upstream's current-layer report lifted into it.
  - `Gen_BatchDelete` took upstream's rewrite whole: our side had become a
    stale duplicate of the same logic under different variable names.
  - `proj_sync_pcb` moved onto upstream's `send_answering`, and pad-net
    checking folded into `_after_sync`, which reports mismatched pads as
    well as unbound ones. Our `verify_pad_nets` knob and `_verify_pad_nets`
    helper were deleted rather than left as a second way to say the same
    thing.

### Fixed

- **`proj_run_erc` and `proj_get_erc_violations` stopped the bridge**
  (`SCRIPT_VERSION` `2026.11.10.1`). `Gen_GetErcViolations` built each
  violation with `IntToStr(ErrorLevel)` and `SuppressedText`, neither
  declared anywhere, so Altium 26.11.1.5 halted with "Undeclared
  identifier" on the first violation. `error_level` now carries the
  numeric level and the duplicate `suppressed` key is gone. The same scan
  found `FindPadNetByName`, whose definition a merge on 2026-10-10
  dropped while the `pcb.place_via` and `pcb.place_track` commands (given
  a net) and `pcb_rebind_copper_to_pad_nets` kept calling it; it is
  restored. A new
  lint rule, `undeclared-read`, fails the build on any bare identifier no
  unit declares and `scripts/altium/lint_external_names.txt` does not
  list. UNVERIFIED live: checked by the linter and tests, not yet run in
  Altium.

- **app_list_panels, app_open_panel and app_read_panel on AD 26.11.** They
  ran on the event loop thread without COM, and 26.11 has no
  TPopupPanelButton for a docked panel, so they saw 0 panels. They now run
  on a thread of their own and also find a panel by its caption; live on
  26.11 they list Projects, Properties and a floating Explorer, and read
  the Projects grid.
- **Altium 365 settings set with `setx` work without a restart**: the
  user's saved environment fills in what the process lacks.
  `EDA_AGENT_ALTIUM365_TIMEOUT_S` sets the request timeout.

- **Nexar sign-in works with a portal app.** `eda-agent altium365-login`
  sent the client id and PKCE verifier but no client secret, so an app made
  in the Nexar portal (a confidential client) was turned down with HTTP 400.
  `EDA_AGENT_NEXAR_CLIENT_SECRET`, when set, now goes with the code exchange
  and with each refresh. It is kept out of the config's printed form and
  masked if a reply echoes it. A refused token request now says what Nexar
  said (`invalid_client`, `invalid_grant`, ...) with a likely fix, instead
  of only the status. Checked live on 2026-11-09: the login succeeded with
  a portal app and its secret, and listed the account's workspaces.

- **The login says which workspaces it reaches.** After signing in,
  `eda-agent altium365-login` lists every Altium 365 workspace the account
  can reach, marks any that `EDA_AGENT_ALTIUM365_WORKSPACES` leaves out, and
  says how to keep the tools to some of them. The docs no longer send
  readers to an Admin > Developer token page that many plans lack; there,
  Nexar is the way in.

- **What the 2026-11-08 live verification found** (`SCRIPT_VERSION`
  `2026.11.08.5`). Each was seen on a live Altium 26.11.1.5 against
  scratch files:
  - `app_open_document` and `app_reload_document` could not open a
    harness wiring diagram: `.wirdoc` had no kind, so a reload closed the
    diagram and failed to reopen it, and `kind=HARNESS` reported success
    for a document `sch_get_harness` could not see. A .WirDoc now opens
    through the workspace manager, and the reply's `kind` is what Altium
    gave the document.
  - A harness wire, splice or cable answered `Name` with nothing, so
    `obj_delete filter="Name=W2"` matched nothing. It now answers the
    name its description carries, the same one `sch_get_harness` shows.
  - `profile_apply_all` wrote the ERC matrix of whichever project had
    focus, which with a free board in front was Altium's "Free
    Documents". Writing it now needs `project_path`, "Free Documents" is
    refused by the diff, preview and apply and by `proj_erc_apply`, and
    the dashboard's Workspace view passes the project its Compare read.
  - A dry run listed its sections under `applied`; they are under
    `would_apply` now. `design_list_modes` flags a selected mode that
    does not exist. `obj_modify` answers `modified:false` when every
    property it asked for was refused.

- **The merged pad-net check read only the first 500 pads.**
  `pcb.get_pad_properties` windows at 500 and reports `truncated`;
  `_after_sync` called it once with no paging and ignored that, so on any
  real board it would have reported a fraction of the unbound pads as if
  it were the whole board. That is the bug the check was written to catch,
  reappearing in a new place. It now goes through `_fetch_all_pads`, and
  its two sweep counters are named `pads_swept` and `sweep_complete`
  because `verify_eco` already answers `complete` and `pads_checked` with
  different meanings.

- **`proj_sync_pcb`'s `wait_seconds` had become a dead parameter.** The
  rewrite onto `send_answering` left it in the signature, and so in the
  tool's schema, with nothing reading it. It is passed as the waiter's
  timeout again.

- **The sync tests were environment-dependent.** `driver` returns a dialog
  presser only when Dialogs Automatic is on AND Altium's process can be
  named, so the tests took one path on a machine with Altium open and
  another in CI. They force it off now, and the fake bridge implements the
  `expecting` contract `send_answering` requires.

### Added

- Optional direct Altium 365 workspace API route alongside Nexar, with
  workspace token authentication and live schema introspection. Request
  construction is tested; live workspace acceptance remains pending.

- Optional cross-check against a locally installed `pcb-toolkit` executable
  gives a second numerical result for supported calculators. The built-in
  calculation remains available without that executable.

- Library file helpers can inspect PcbLib and LibPkg data, extract STEP
  references, compare and preview footprints, and make explicit backups
  before library edits.

- Offline vendor stackup templates, laminate data, and fab capability checks
  are exposed through CLI and MCP. Native layer changes remain explicit
  editor operations and require version-matched Altium acceptance.

- Ten offline engineering calculators are available through CLI and MCP:
  conductor spacing, fusing current, via parasitics, spiral inductance,
  reactance, resonance, wavelength, PDN target impedance, padstack geometry,
  and wire gauge. Each result states whether it is exact, published, or an
  estimate, and refuses physically invalid inputs.

- `part_find_replacements` evaluates candidate parts using explicit
  parameter directions, units, lifecycle and stock evidence. It reports
  unreviewed attributes and missing datasheet, PCN, and pad-geometry checks;
  a result is not an equivalence or drop-in approval.

- `rotation_audit`, an advisory check in `pcb_layout_audit`: each
  two-pad part on either side is tried at 0/90/180/270 degrees about its
  origin, scored by net airline (minimum spanning tree) for routable
  nets and by distance to the nearest return pad for plane nets, and
  reported when another rotation beats the current one by 25 mils.
  The idea comes from coffeenmusic/altium-mcp's `check_orientation`,
  reimplemented on the LayoutBoard model. The bottom-side rotation sign
  was measured on four flipped parts in Altium 26.11.1.5. Scoring remains
  a geometric advisory and is covered by synthetic-board tests.

#### Owner profiles

A per-workspace house style, so one machine can work for several
companies without re-stating their conventions on every call. See
[`docs/PROFILES.md`](docs/PROFILES.md).

- A profile directory carries naming conventions, design rules,
  fab/stackup profiles, footprint-authoring defaults, footprint-policy
  pins, schematic unit/grid settings, and project templates. Formats
  that already existed (`naming.json`, rulesets, fab profiles) are
  reused rather than reinvented.
- Found from `EDA_AGENT_PROFILE_DIR`, then a project-local
  `.eda-agent/profile/` discovered by walking up from the working
  directory, then the centrally active profile. **The project-local path
  is cwd-relative**, so it reaches the CLI but usually not the MCP
  server, whose client launches it from elsewhere; an MCP setup wants
  the central profile or the environment variable.
- CLI: `profile-init`, `profile-list`, `profile-use`, `profile-show`,
  `profile-validate`, `profile-new-project`.
- Tools: `profile_show`, `profile_list`, `eng_list_rulesets`,
  `eng_load_ruleset`, `eng_profile_fab_profile`,
  `profile_apply_document_settings`.
- `profile_new_document`: create a schematic or board from one of the
  profile's `templates/documents/` files and open it. Altium's own New
  Document makes a blank sheet and so does the bridge's
  `create_document`; there is no API that applies a template, so this
  copies the file, which is what applying one amounts to on disk. The
  template's own extension wins over the destination's, an existing
  file is refused unless `overwrite=True`, and a copy that Altium then
  declines to open still reports the path it wrote. Altium
  **preferences** stay out of reach (no scripting API at all) and
  **Draftsman** is unsupported, both stated plainly in
  [`docs/PROFILES.md`](docs/PROFILES.md) rather than left to be
  discovered.
- `lib_add_footprint_pad` / `lib_create_standard_footprint` /
  `lib_add_footprint_pads` take their pad corner radius from the active
  profile instead of a hardcoded 25%, and
  `lib_audit_footprint_policies` uses the profile's footprint policy
  when none is passed.

#### Board artwork, offline library reads, part labels and datasheets

- `pcb_place_image`: raster artwork (silkscreen logo, QR code) as PCB
  region primitives. Decomposed into non-overlapping rectangles rather
  than traced outlines, so nothing is approximated away from the source
  art and holes need no special handling. Plans by default
  (`dry_run=True`) and reports the primitive count first, with a
  `max_regions` cap. Verified on a live board: an asymmetric test glyph
  placed at a known origin and read back with `pcb_query_region`
  confirmed the scale, the bottom-left origin corner, the layer, and
  that the art is neither mirrored nor flipped.
- `lib_read_pcblib_headers`: a `.PcbLib`'s footprint names, pad counts,
  heights and descriptions with Altium closed, for library hygiene in
  CI. Reads the ASCII streams only; pad geometry lives in the binary
  region and stays a live read through `lib_get_pad_geometry`.
- `part_parse_lcsc_label`: decodes the QR payload on an LCSC reel or
  bag. Only `pc`, `pm` and `qty` have a documented meaning, so the
  remaining keys are returned verbatim rather than given invented names.
- `part_cache_datasheet` / `part_list_cached_datasheets`: keep the PDF
  on disk with its URL, SHA-256 and fetch time. The host allowlist is
  deny-by-default from `EDA_AGENT_DATASHEET_HOSTS`, and the payload is
  verified to be a PDF by magic bytes rather than by `Content-Type`.

#### Altium Booster 3.2.0 feature integration

- IPC-7351B footprint validation against a live SchLib/PcbLib pair
  (`eng_validate_library_live`), plus a CSV/HTML report writer
  (`eng_write_library_validation_report`) and standalone IPC-name
  parsing (`eng_parse_ipc_footprint_name`).
- Pre-ECO schematic/PCB diff, both offline (`eng_eco_preview`) and fed
  from live Altium reads (`eng_eco_preview_live`).
- LTspice batch runs no longer flash a window on Windows.
- Nexar Supply search (`NexarProvider`) now returns pricing, stock,
  lifecycle status and similar parts, not just identity and datasheet.
- Altium 365 additions: `update_parameters`/`entity`/`workspace_infos`/
  `library_components_params` on the Nexar client, and three new write
  tools (`eng_a365_publish_model`, `eng_a365_release_component`,
  `eng_a365_update_parameters`), each off unless `confirm=True`.
  **UNVERIFIED against a real Nexar account**: covered by a test double
  only.
- Rotating, size-capped, secret-redacting activity log
  (`activity_log.py`), alongside the existing stderr logging.
- `Lib_GetFootprintPads` (DelphiScript) extended to also return track
  coordinates (for courtyard/silkscreen checks) and a 3D-body flag.
  Verified against a live Altium session.
- **Experimental, UNVERIFIED**: `eda-agent eco-execute`, a CLI command
  that auto-presses Altium's Engineering Change Order dialog via the
  existing reactive dialog driver. Off unless `--confirm`.

### Fixed

- `pcb_modify_layer` accepts fractional copper and dielectric thicknesses
  through the MCP schema, preserving decimal mil values sent to Altium.

- Reading an owner profile no longer raises. It is read during server
  startup and on the pad-authoring path, where a malformed JSON file
  took the whole MCP server down and broke `lib_add_footprint_pad`, and
  a non-numeric corner radius was forwarded to Altium verbatim by one
  tool while raising `TypeError` in another. A present-but-unusable file
  now degrades to its default; `profile-validate` is where such problems
  are reported, and it applies the same checks the consuming tools do.
