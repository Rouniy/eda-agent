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

- **An app icon.** The Altium status window, the web dashboard's browser tab
  and the desktop shortcut now show one eda-agent icon instead of Windows'
  blank default: a gold "A" drawn as two PCB traces ending in via pads,
  with a blue spark, on the dashboard's dark tile. The 16 to 32 px sizes are
  drawn on their own pixel grid so the taskbar button stays sharp. Sources
  are in `assets/icon`; `python scripts/build_icons.py` rebuilds the favicon,
  the `.ico` and the status window's `Icon.Data`. Scripts 2026.11.14.1.
- **Signal integrity: the whole board.** New job kind `board-si` and tool
  `si_board_check`: every high-speed net and pair, chosen by name or Altium
  net class, checked against its own limits (impedance, loss, return loss,
  skew, stub resonance, eye). Each failure is placed on the board: an
  impedance fault where the TDR sees it, walked along the route at each
  section's own delay; a stub at its tee. Results go to a self-contained
  `report.html`, `findings.json` and `summary.csv`, and the failing nets are
  highlighted in Altium (with optional marker text). Trace loss follows the
  copper temperature, uniform or from a thermal analysis' map. Jobs record
  the snapshot and jobs their inputs came from; the Simulation page shows
  that graph and marks results stale once the board is saved.
- **Signal integrity: delay matching.** A board-check target takes
  `delay_match_ps`: its nets and pairs are held to the slowest of them
  (a bus, a byte lane, a clock with its data). A net too far ahead is a
  finding at its driving pin, with how far ahead it is and about how much
  trace matches it.
- **Signal integrity: the eye at a bit error rate.** `si_channel_eye` and
  a board-check target take `ber` (default 1e-12), `noise_rms_mv`,
  `rj_rms_ps` and `dj_pp_ps`, and give the statistical eye:
  `eye_height_at_ber_mv`, `eye_width_at_ber_ps` / `_ui` and
  `bit_error_rate`, with the limits `eye_at_ber_min_mv` and
  `eye_at_ber_min_ui`. Every pattern is counted with its probability, so
  a long channel whose worst-case eye is closed is judged at the rate it
  has to meet. Down to 1e-18. See
  [The eye at a bit error rate](docs/SI_TIME.md#the-eye-at-a-bit-error-rate).
- **Signal integrity: the equaliser chosen for you.** `tx_ffe: "auto"`
  works out the transmitter taps that leave the largest worst-case eye
  (`tx_ffe_pre`, `tx_ffe_post` set how many), as the exact solution of a
  linear programme; `ctle_db: "auto"` picks the boost, up to
  `ctle_max_db`. A clean channel gets none. `ffe_main_tap`, `ctle_db` and
  the notes say what was chosen. See
  [Equalisation](docs/SI_TIME.md#equalisation).
- **Signal integrity: PAM4 eyes.** `modulation: "pam4"` in
  `si_channel_eye` and in a board-check target runs the eye on four
  levels, two bits a symbol: the three eyes of the pattern
  (`eye_height_lower_mv`, `_middle_`, `_upper_`), the worst case, the eye
  at a bit error rate and the equalisers, chosen ones included. See
  [PAM4](docs/SI_TIME.md#pam4).
- **Signal integrity: ground copper in the gap shields.** A ground pour
  flooded between a net and its neighbour, or a guard track, now counts
  in the crosstalk of a net channel and the board check: the coupling is
  solved with that copper in the cross-section, held at the reference,
  and the aggressor's row says how much was found (`guard_mils`). A net
  that has pours and no tracks is now among the quiet nets.
- **Update: a reinstall that did not take is caught.** `eda-agent update`
  reinstalls the package when `pyproject.toml` changed. pip could end
  that with the old install removed and the new one not written, leaving
  a Python that no longer finds eda-agent, and the update said nothing.
  The install is now asked for from a new Python; if it is not there it is
  installed once more, and if it still is not the step is reported as
  failed with the command to run.
- **Signal integrity: DFE error propagation.** With `dfe_taps` and the eye
  at a bit error rate, `bit_error_rate` now counts the errors a wrong
  decision of the DFE brings after it: the decisions of the last taps are
  a Markov chain, solved for the length of the burst (`dfe_burst_errors`;
  1 is no propagation). The contour still takes decisions as right.
- **Signal integrity: sinusoidal jitter.** `sj_pp_ps` in `si_channel_eye`
  and in a board-check target adds sinusoidal jitter to the eye at a bit
  error rate, with the density of a sine (not two points), together with
  the random and deterministic parts.
- **Signal integrity: PAM4 limits at the symbol rate.** A routed net, a
  pair and a board-check target with `modulation: "pam4"` are now checked
  at half the data rate: the loss at Nyquist, the stub limit and the
  default skew limit follow the symbol, as the eye already did.
- **Signal integrity: the cursors of the worst case.** `main_cursor_mv`
  and `isi_mv` are now read at the sampling phase where the worst-case eye
  is tallest, not at the pulse's peak, so the reported eye is exactly
  twice their difference. They move a little where reflections put the
  best phase off the peak; the eye itself does not change.
- **Signal integrity: the eye pattern quick on long sweeps.** The bit
  pattern of `si_channel_eye` is now convolved with the pulse one sample
  phase at a time instead of through a pattern padded with zeros: the
  same waveform to rounding, several times quicker where the sweep is
  long and fine.
- **Simulation jobs: a running job is not shown as queued.** On Windows a
  status file read in the instant its run was rewriting it was refused
  and taken for missing, so a poll could show `queued` for a job already
  running. The read is now tried again for a moment.
- **Signal integrity: the return path.** A net channel and the board check
  now look at the reference copper under each route (split planes, pours
  and regions, with their holes) and report every place where it stops:
  a split between two plane nets, a slot, a missing pour. Each is a
  finding placed where the route crosses it (check `return path`,
  `return_gaps`, `return_gap_mils`); a stripline with its other plane
  whole there is a warning.
- **Signal integrity: a crosstalk failure says its fix.** A net channel
  and the board check now end a failed crosstalk check with the gap at
  which the worst neighbour brings the total within the limit ("AGG at
  7.8 mil or more brings it within 5 %"), every other neighbour left where
  it is; on a facing signal layer it is the offset to the side. When the
  other neighbours alone are over the limit the detail says so. The
  figures are in `crosstalk.json` under `fix`.
- **Signal integrity: crosstalk across the board.** A net channel and the
  board check now search the board for the copper that runs beside each
  net: other nets' tracks on the same layer, within reach, with the length
  they share. Each neighbour's capacitive and inductive coupling comes from
  the field solver at its gap, and gives the near-end and far-end
  crosstalk for the net's edge (`crosstalk_next_pct`, `crosstalk_fext_pct`).
  A pair counts as the difference of its sides, as victim and as
  aggressor; grounds and supply rails are left out. The new check
  `crosstalk` (limit `xtalk_max_pct`, default 5 % of the aggressors' swing)
  is placed on the board at the coupled stretch, with the aggressor, the
  length and the gap. Against the coupled line solved in full the near end
  is within 5 %. In a board check with eyes, crosstalk times the
  neighbours' swing (`xtalk_swing_mv`) is noise on both rails of the eye,
  and the eye limit is held against what is left; `si_channel_eye` takes
  such noise from any source as `noise_mv`. `si_net_channel` lists the
  aggressors in its reply (`crosstalk`).
- **Signal integrity: neighbours with their own edge and swing.**
  `xtalk_aggressors` gives nets an edge and a swing of their own by name
  (`{"match": "CLK*", "rise_ps": 300, "swing_mv": 3300}`), in a net channel
  and in the board check. A slower neighbour couples less at the far end
  and over a short run. With every swing known, crosstalk is also given in
  millivolts on the net (`crosstalk_noise_mv`), each neighbour at its own
  swing, and `xtalk_max_mv` holds it to a limit (the check `crosstalk
  noise`): the figure that matters where 3.3 V logic runs beside a
  low-swing pair. The eye of the board check takes each neighbour's noise
  at its own swing.
- **Signal integrity: eyes and SPICE models.** New job kind `channel-eye`
  and engine `spice`. The `eda-agent` engine convolves a channel's pulse
  response with a PRBS pattern and adds the worst-case eye by peak
  distortion analysis; the `spice` engine fits the channel as a passive
  rational macromodel (relaxed vector fitting, passivity enforcement),
  writes it as a subcircuit of linear elements with an LTspice symbol, and
  runs the same pattern in ngspice or LTspice, reporting how far the two
  routes differ. Drivers and receivers come from IBIS files or explicit
  values and are the same circuit in both routes. New tools
  `si_channel_eye`, `si_spice_model` and `si_ibis_models`. See
  [Eyes and SPICE models](docs/SI_TIME.md).
- **Signal integrity: the edge at the receiver.** The eye job and the
  board check now also give what one edge does where it arrives:
  overshoot, ringback, the deepest fall on the way up (a reflection inside
  the edge, which a clock input can see twice) and the settling time, with
  the driver and receiver given (resistances, capacitances or IBIS).
  `overshoot_max_pct`, `ringback_max_pct` and `edge_reversal_max_pct` hold
  them to limits; the board check places a failure at the receiving pin.
  A failed overshoot names the series resistor at the driver that cures
  it (`series_r_ohms`), or says that none does. The level a step settles
  to is worked out from the S-matrix at 0 Hz and the terminations, so it
  is right behind a weak driver too.
- **Signal integrity: equalisation in the eye.** `si_channel_eye` and a
  board-check target take a transmitter FFE (`tx_ffe`, taps one unit
  interval apart, scaled to the driver's peak swing), a receiver CTLE
  (`ctle_db`, `ctle_peak_ghz`) and a receiver DFE (`dfe_taps`, `dfe_max`).
  The eye, the worst-case eye and the cursors are then those the receiver
  decides on, so a long channel whose plain eye is closed can be judged as
  the link runs it. `dfe_tap1_mv` and the notes give the taps. All off by
  default; convolution engine only. See
  [Equalisation](docs/SI_TIME.md#equalisation).
- **Signal integrity: routed nets and pairs.** A routed net or differential
  pair is modelled from pin to pin: its path is found in the board's copper
  (tees, stubs and layer changes included), every trace section uses the RLGC
  of its own cross-section, vias are coaxial barrels with stubs, pad
  capacitance and the return-via loop when the reference changes, and the
  blocks are cascaded as exact chain matrices. New job kind `net-channel`;
  new tools `si_board_snapshot` (the board and stackup read once, content
  named, stale once the board is saved) and `si_net_channel` (S-parameters,
  TDR, delay, loss at Nyquist, skew, mode conversion, checks against limits,
  and the width, gap, uncoupled-length and length rules, written to Altium
  when asked). The length rule spends the loss headroom at the lines' own
  loss per mil, with vias and stubs as a fixed cost, and a stub whose notch
  falls within twice Nyquist fails its own check. See
  [Routed nets and pairs](docs/SI_NETS.md).
- **Signal integrity: transmission lines and a stackup planner.** New
  package `eda_agent.si`. A 2D eddy-current solver gives R(f) and L(f)
  of traces and their reference planes with skin and proximity effect
  from DC up; the field solver gives C(f) and G(f) with causal
  Djordjevic-Sarkar dielectrics (mask included); Huray, Hammerstad or
  Groisse roughness; exact modal S-parameters of coupled lines with
  mixed mode and crosstalk. New job kinds `line-model` (also on
  scikit-rf, as a closed-form check of a single microstrip) and
  `stackup-plan`; new tools `si_line_model` and `si_stackup_plan` (widths
  and pair gaps per layer for target impedances, compared with or written
  as Altium impedance profiles); a Transmission line form, plots and
  result files on the dashboard's Simulation page. See
  [docs/SI_LINES.md](docs/SI_LINES.md).
- **Thermal analysis.** `sim_thermal_analysis` solves a board's steady
  temperature field in three dimensions from the power each part
  dissipates: the real copper of every layer (pours, planes with their
  antipads, tracks and pads with their exact areas), every plated hole,
  the laminate's anisotropic conduction, natural or forced convection
  and radiation from both faces, the edges and part cases. It reports
  the peak, hotspots with the nearest part, each powered part's pad,
  junction and case temperature against `tj_max_c`, the hottest
  unpowered parts, a heat balance and, with `refine`, a grid-convergence
  error estimate, and writes a heat map per layer. It takes the Joule
  heat map of an IR-drop run as an extra source. Checked against exact
  solutions (series slab, Bessel fin, Fourier spreading series,
  convection and radiation balance, via arrays). Copper that does not
  touch is kept apart inside a grid cell (a pad and the pour round it, a
  via in another net's pour), so the answer does not depend on the cell
  size resolving the clearances. Each run also writes a picture of the
  copper as it was solved. See [`docs/THERMAL.md`](docs/THERMAL.md).
  Run live on one populated six-layer board read from Altium.

- **Features and dependencies, and a one-command installer.** One
  registry (`eda_agent.features`) describes every optional part: the pip
  extras, the Rust wheels built from this repository, the programs some
  tools drive (openEMS, LTspice, ngspice, KiCad, FreeCAD, pcb-toolkit)
  and the simulation engines, each with its license and what it offers.
  `eda-agent features` shows what is installed with versions;
  `eda-agent install-deps --all` (or named features) installs the rest
  after showing its plan, one pip call per feature, GPL engines in their
  own environment, and prints the steps for programs. The same in the
  dashboard's new **Features** page (install buttons with live output,
  engine switches) and the `app_features` / `app_install_features` tools.
  New extra `si` (scikit-rf). New settings `EDA_AGENT_ENGINES_DIR`,
  `EDA_AGENT_FEATURES_FILE`.
- **Simulation engines and jobs.** Every simulator is an engine behind
  one job model (`eda_agent.simulation`): a job is a folder named by a
  hash of the problem, each engine writes normalised results beside its
  own files, and `sim_job_compare` sets the answers side by side. Engines
  today: this project's solvers (S-parameter quality checks, the 2D
  field solver), scikit-rf, and openEMS (run as its own process, as
  before). Job kinds: `touchstone-check`, `xsection-2d`, `em-3d`. Tools
  `sim_engines`, `sim_job_run`, `sim_job_status`, `sim_job_compare`,
  `sim_jobs`; the dashboard's new **Simulation** page. Other packages add
  engines and features through the `eda_agent.engines` and
  `eda_agent.features` entry points. New setting `EDA_AGENT_SIM_JOBS`.
  First step of the signal-integrity work (docs/SIMULATION.md).

- **Euan Mutch's router as an opt-in autorouter engine.** `eda-agent
  router-use euan` (or `EDA_AGENT_ROUTER=euan`) routes `pcb_autoroute`
  jobs with the router from his fork (TechAUmNu/eda-agent, Apache-2.0);
  `eda-agent router-show` says which engine is in force and why. The
  default engine stays the default; what this work found wrong in it is
  under Fixed. Both engines' results go through the same verdict and our
  gloss, and the default router's via guards were ported into his.
  Where his router took for a join what the verdict does not
  (`join_existing`, `reuse_vias` through a blind via, or a plane pad
  "served" by a via that stands outside the plane), or let any via
  share a pad's solder mask opening under `pad_vias="centre"`, it no
  longer does. A narrow `neck_pads` branch keeps its width after the
  pour stage and in the attempt after a plane is given back (it was laid
  at the net's full width, into another net's clearance), and his coarser
  grid pitches route clean (see Fixed: a pad smaller than a cell). A
  setting that cannot be used routes with the default engine, and his
  router's own job parameters are range-checked before anything runs.
  `python -m eda_agent.layout.bench_run --fixtures DIR --router euan`
  benchmarks it on your own boards, and `scripts/bench_router_engines.py`
  compares both engines on synthetic ones. See
  [Autorouter engines](docs/ROUTER_ENGINES.md).

- **PCB toolkit: 44 calculators, a Calculators tab and `pcb_calc
  kind=toolkit`.** Controlled impedance (microstrip, embedded
  microstrip, symmetric and offset stripline, dual stripline, coplanar)
  and differential pairs (edge-coupled, broadside, coplanar) come from a
  new 2D field solver with solder mask, trapezoidal traces, mixed
  dielectrics, causal Er(f), dispersion, and conductor loss with
  roughness; it agrees with the exact conformal-mapping results within
  0.1 %. Trace and via current come from a thermal model of the board
  (planes, laminate, convection, radiation) in place of a chart. Also
  crosstalk, plane-pair capacitance and cavity impedance, PDN target,
  timing, junction temperature, Ohm's law and passives, padstacks, BGA
  lands and conversions. The dashboard tab (key 0) fills inputs from the
  open board's layer stack. See [`docs/PCB_TOOLKIT.md`](docs/PCB_TOOLKIT.md).

- **PDN analysis.** `sim_pdn_ir_drop` solves a power net and its return
  as a sparse resistor network of the board's real copper (pours and
  planes on a grid, tracks and arcs as exact resistors, via barrels from
  the stackup; pads met at their real edge and barrels at their hole
  wall, so the answer does not move with the grid) and reports the worst
  pins of every load, current density, loss per layer, overloaded tracks
  and vias, and a grid-convergence error estimate. `sim_pdn_impedance`
  finds a rail's decoupling capacitors (MLCC, polymer, tantalum and
  electrolytic defaults; the value from the comment, else from the
  part's parameters), works out each pin's mounting inductance from
  the copper that joins it to the planes, solves the power/ground plane
  pair as a field cavity on its real, perforated shape (FDFD, exact
  skin-effect surface impedance, Djordjevic-Sarkar laminate) and reports
  where |Z| at the load exceeds the target. Both are checked against
  closed-form references, and the IR-drop run writes its Joule heat map.
  Both ran live, read-only, on one six-layer board, with the capacitor
  values read from the parts' parameters. See [`docs/PDN.md`](docs/PDN.md).
- **SPICE model library and LTspice round trip.** `sim_scan_models`
  indexes vendor model files and LTspice symbols (including LTspice's own
  library, encrypted models through their symbols) into the design
  workspace; `sim_find_models` and `sim_find_schematic_models` find models
  by MPN; `sim_get_pin_map` and `sim_set_pin_map` match symbol pins to
  model nodes by name, never silently by pin number; and
  `sim_attach_library_model` links a model only after its pins check out.
  `eng_ltspice_deck_from_schematic` now emits subcircuits with the model's
  name and node order and includes their files (it used the Comment and
  pin-number order before, and dropped parts that had SpicePrefix but no
  SIM link). `eng_ltspice_run` copies model files into the run folder,
  `eng_ltspice_export` writes a deck with its models for the LTspice GUI,
  and `eng_ltspice_compare_schematic` checks an LTspice `.asc`/`.net`
  against the Altium schematic (parts, values, wiring). See
  [`docs/SPICE_MODELS.md`](docs/SPICE_MODELS.md). Checked live against
  LTspice XVII; UNVERIFIED against live Altium.

- **Symbol and footprint preview before placing a part.** The
  dashboard's Library pane has a "Look up a part" view: search the
  profile's scanned Altium 365 library offline (name, value,
  description, MPN), pick a part, and see its symbol and footprint as
  they are in the library, with pin and pad counts and where each comes
  from; a multi-part symbol shows one part at a time. A part from a
  .SchLib can be previewed by path and name (an .IntLib through its
  extracted .SchLib, never opened in Altium). New script read
  `library.get_symbol_geometry` loads the symbol the way placement does
  (`SchServer.LoadComponent` for a Workspace part, the open SchLib
  otherwise), answers its graphics, pins and models, and destroys a
  loaded part again, so nothing reaches a sheet. New tool `lib_preview_part` writes
  both drawings as SVG. A footprint link that names no file (the usual
  "any library" link) is resolved by reading the .PcbLibs beside the
  symbol's library from disk. Checked live on a Workspace part and a
  .SchLib part: symbols read in under a second (SchLib: 6 to 9 s, it is
  opened), nothing opened, closed, placed or marked modified. A
  Workspace part must be asked for with its revision (CMP-00000010-3).
  Not done yet: a Workspace part's footprint, which has no file to read;
  the preview says so and shows the symbol.

- **Fab and IPC class floors on a board's design rules, on demand.**
  New `pcb_rules_fab_floors` tool holds the board's existing rules up
  against one fab build's published minimums (the cited fab rules
  database) and, with `ipc_class`, the profile's IPC class floors
  (`std-floors`), and says rule by rule which ones sit below the floor
  and why, with the fab quote or IPC clause behind each floor. It reports
  by default; with `apply=True` it raises board-wide rules that are below
  the floor and nothing else. Rules already stricter are never loosened,
  scoped rules below the floor are left for the user to name, rules DRC
  does not check and kinds with no writer (annular ring) are reported,
  and nothing is created or deleted. Writes go into the board's rule log.
  Never runs on its own. UNVERIFIED against a live board.

- **EMI/EMC pre-scan and openEMS field solving.** `sim_emc_prescan`
  checks a routed board's fast nets with no external program. It finds
  tracks that cross a split or slot in their reference plane or have no
  plane beside them, fast tracks near the board edge, and layer changes
  with no return via. It also estimates differential-mode radiated
  emission per net (Ott's small-loop formula) against CISPR 32 or
  FCC Part 15 limit lines. `sim_em_build_model`, `sim_em_run` and
  `sim_em_results` cut a few nets with their return copper and the real
  stackup out of the board and solve them in openEMS, which runs as a
  separate process. Results come back as a Touchstone file and a summary:
  return loss, S21, and for antennas directivity, efficiency and pattern.
  `sim_read_touchstone` summarises any `.sNp` file. Checked against
  openEMS 0.37 on Windows: a 50 ohm microstrip's effective permittivity
  from two line lengths is within 1 % of Hammerstad-Jensen, |S21| 0.986,
  |S11| -33 dB (`tests/emc/test_openems_real_solver.py`, skipped where
  openEMS is not set up). The live board read is UNVERIFIED.
  See [`docs/EMC_RF.md`](docs/EMC_RF.md).

- **Fab design-rule database for thirteen PCB fabs.** JLCPCB, PCBWay,
  Technoservice, Satland, Eurocircuits, Würth Elektronik, Multi Circuit
  Boards, AISLER, Beta LAYOUT, NextPCB, PCBCart, OSH Park and Advanced
  Circuits, each with its published pages registered as a connector.
  Twelve have rules stored, every figure with the fab's quote, page and
  date; Würth Elektronik is pending (its site refuses scripts).
  New `fab-list`, `fab-rules`, `fab-compare` and `fab-refresh` commands
  and `design_list_fabs`, `design_fab_rules`, `design_fab_compare`
  tools give every rule of one build (board edge, V-score, mask,
  silkscreen, tolerances, aspect ratio and more, not only the seven
  minimums a fab profile carries). `fab-refresh` re-reads a fab's pages,
  obeying robots.txt, snapshots them outside the repository and checks
  every stored quote is still there; it never rewrites a figure. IPC
  class 2/3 floors come from the active profile (IPC values are
  licensed and never ship in the repository) and are refused without them.
  See [`docs/FAB_AND_CALCULATORS.md`](docs/FAB_AND_CALCULATORS.md).

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
- **Optional Rust compute (`--compute rust|auto|python`,
  `EDA_AGENT_COMPUTE`, `eda-agent compute-status`).** The routing
  planner's grid A* has a compiled port in a separate wheel,
  `rust/eda_agent_compute` (PyO3, Apache-2.0). On the 1090-pad board from
  `tests/route/test_scale.py`, a whole run takes 11 s instead of 184 s at
  a 10 mil grid, and 2.2 s instead of 32.5 s at 25 mil, with
  byte-identical output. Python stays the default. `rust` refuses to start
  without a matching wheel, and every routing result names its
  implementation in `summary.compute`. `tests/route/test_compute_parity.py`
  holds the two implementations to the same paths, verdicts and expansion
  counts. A new CI job builds the Windows wheel and uploads it. See
  `docs/RUST_COMPUTE.md`.

### Changed

- **Signal integrity: eye findings sit at the receiving pin.** A board
  check placed a failed eye at the driving pin; it is judged at the
  receiver, where the edge findings already are.
- **Signal integrity: the eye at a bit error rate is quick on long
  sweeps.** Cursors far below a voltage step now go through the series of
  ln cos together instead of one by one: a response of 1000 bits takes a
  fifth of the time, and they are no longer taken at their worst. With
  noise given, only the part of the spectrum the noise leaves is worked
  out: 0.1 s where it took 3 s.
- **Signal integrity: the eye settles to the right level.** The pulse
  response took the first frequency point as DC. The step then sloped
  over its window, every bit left a small offset behind, and the offsets
  added up as ISI that was not there (8 mV instead of 3 mV on a matched
  4 inch line at 800 mV); behind a weak driver into an open end the slope
  was steep enough for the eye to be refused as "still ringing". The level
  is now worked out from the S-matrix read back to 0 Hz and the
  terminations. Eye heights rise slightly; worst-case eyes rise more.
  The read-back uses magnitudes, which do not turn with the delay, so the
  level also holds on a long channel swept in coarse steps.
- **Signal integrity: dual striplines.** Two signal layers between a pair
  of planes are now modelled as they are built. A trace there is referenced
  to the planes on either side, past the other signal layer (which used to
  be taken as a solid reference, and gave too low an impedance); the result
  names the layer passed over. Crosstalk now also searches the facing signal
  layer: a track that runs over or under the net with no plane between
  couples through the dielectric between the two layers, worked out by the
  field solver from both traces at their own heights and the offset to the
  side. Each such aggressor is reported with its layer (`aggressor_layer`),
  its offset (`offset_mils`) and the dielectric between; the board check
  places it like any other. The near end agrees with the coupled line
  solved in full within 5 %. See
  [docs/SI_NETS.md](docs/SI_NETS.md#crosstalk).
- **The placer's annealing polish scores each move incrementally.** It
  used to re-score the whole board (every net's pins, every courtyard
  pair, the whole congestion grid) on every move; it now re-scores only
  the nets and parts the move touched. Same seed, same placement: every
  term is re-summed in the original order, so the score is bit-identical,
  and tests check that term by term over thousands of random moves.
  `construct_placement` on a 45-part board went from 37 s to 2.8 s, a
  124-part board from 82 s to 15 s (cloud Linux).
  `ConstructOptions(incremental_score=False)` restores full re-scoring.

- **The routing solution check rejects far-apart pairs by their bounding
  boxes before measuring.** Same violations, same order, same `checked`
  count. A box gap is never larger than the true distance, so no reported
  pair is skipped. The Python path on the 10 mil benchmark went from 184 s
  to 160 s.

- **The router sets up its jobs faster on boards with planes or excluded
  layers.** Each net's via guards worked out every item on those layers
  again: its clearance to the net's via and the grid cells it bars. Both
  are now worked out once and kept for the next net, and the barred cells
  are merged through one index per cell. Same cells for every net and via
  style, in the same order (checked on 792 jobs with both engines, and
  against a direct reckoning in the tests). On a board with 1,500 vias of
  other nets and two planes, setting up went from 26 s to 6.7 s.

### Removed

- **Upstream's sponsor note is gone from this fork** (`SCRIPT_VERSION`
  `2026.11.08.3`). The upstream merge in #20 brought in a "Finding
  eda-agent useful?" strip with a Sponsor button under the status
  window's log, a heart button above it, a "Support the project" section
  in the README, and upstream's GitHub Sponsors and Buy Me a Coffee
  handles in `.github/FUNDING.yml`. All four asked for money for
  upstream on this fork's behalf, which this fork had already undone
  once for FUNDING.yml (see the 2026-11-03 entry below). The note, the
  heart and their handlers are removed and the log hint gets back the
  width the heart took; FUNDING.yml is the blank template again. The
  update icon that came in the same upstream commit stays.
  `test_status_window_update_icon` and
  `test_fork_identity_points_at_morembedded` keep both from coming back
  at the next merge.

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

- **A board edited by script reads modified.** After a stack edit
  (`pcb_set_dielectric`), and on other scripted edits, Altium's own
  modified flag read false while its title showed
  `BoosterTest.PcbDoc * - Altium Designer`. So `app_get_active_document`
  and `app_list_documents` called an edited board clean, and
  `app_close_document` let it through to Altium's modal save prompt. The
  title of the document in front is now read as well (`ui/title_state.py`):
  a `*` there reports `modified: true` with `modified_from: "window title"`,
  and a close without `discard_changes` is refused before it reaches
  Altium. The title only adds a modified the API missed; it never clears
  one, and it answers only for the document in front.
- **The dashboard's background threads can be stopped.** `create_app`
  started a log tailer, a sentinel watcher and a heartbeat that ran until
  the process ended; `eda_agent.web.dashboard.stop_background()` now ends
  them, and the test run calls it after every module. The tailer waits on
  its stop event instead of sleeping, so it ends at once. Before, each
  test module that built an app left three threads polling in its xdist
  worker, and a test that patched `time.sleep` counted the tailer's sleeps
  as its own (592 where it expected 2).
- **eda-agent installs on Python 3.15 again.** pyamg 5.4 has no wheel for
  3.15 yet, so pip built it from source and, without a C++ toolchain, the
  whole `pip install` failed. pyamg is now required only below 3.15. The
  thermal solver already falls back to a direct solve without it (and says
  so in its notes); that is slower on fine grids. `pip install pyamg` adds
  it back by hand once a 3.15 wheel exists.
- **UI automation lost by a process that started beside another.** The
  first process in a venv that needs oleacc's or UI Automation's comtypes
  wrapper generates it into `comtypes/gen`. Two processes doing that at
  the same moment read each other's half-written file, and the one that
  lost ran without menu walking, dialog reading or control access for its
  whole life (`_AVAILABLE = False`, no error shown). The generation now
  runs under a lock file, one process at a time, and is tried again after
  a failure (`eda_agent.ui.comgen`). In a test of 4 processes starting
  together on a fresh wrapper, 8 rounds each, the old code lost one or more
  processes in 4 rounds and the new code in none. This was also the cause
  of the 8 menu tests that failed on one worker in the first `pytest -n 4`
  run of every new venv.
- **Signal integrity in Altium, from a run on real copper.** The stackup
  the SI tools read now takes the dielectric from Altium's separate
  dielectric layers where the copper layers carry none (the line model and
  stackup planner reported "no dielectric" on such boards). Marker text is
  refused when the board was edited since the snapshot but not saved yet,
  or when another document is in front; a second marking run replaces the
  earlier markers; and each stretch of a route outside the impedance band
  gets its own placed finding, not only the worst.

- **A simulation job's kept answer is tied to the code that made it.** The
  same job asked again after an update returned the older code's results
  unless forced; it is now solved again.

- **Crosstalk sees curved routes.** A neighbour's arcs were not searched,
  and a neighbour beside a curved stretch was dropped because each chord
  of the curve is shorter than the 10 mil a run had to be. Arcs now count,
  and it is a net's whole shared length that must reach 10 mil.

- **A net between free pads can be modelled.** A net with fewer than two
  component pins (a bare test board, edge fingers, a test point at one
  end) was refused as having no pins. Its free pads now count as pins, with
  a note.

- **An eye is never wider than its unit interval.** An eye open at every
  sample of the interval read 33 / 32 UI (1.031 UI in a board check). It
  now reads one sample short of the interval: the crossing lies between
  two samples.

- **IBIS buffers as vendors write them.** A driver's output resistance was
  read from the two table points either side of 0 V, which on a real file
  is the clamp diode below the rail: a 50 ohm driver came out as 0.18 ohm.
  It is now read on the transistor's side of the table. A pull-up that
  barely conducts near its rail is not averaged in, an input is refused as
  a driver, and a receiver's on-die termination is taken from its clamp
  tables.

- **An eye from a sweep too coarse for the bit is refused.** A slow bit on
  a wide sweep (a 10 ns bit on a 50 MHz step) wrapped round onto itself and
  gave an eye larger than the supply. The job now says which step it needs,
  and a board check gives such a net more points.

- **Fan-out vias keep off copper the router does not see.** A BGA's
  fan-out and the plane fan-out laid their vias outside the search, so
  they skipped its hole-to-hole and hidden-copper guards: a fan-out via
  could land on another net's copper on an excluded layer or a plane
  layer (a short), or too near a drilled hole. Both now check what the
  search checks. That check also got faster: it looks only at what lies
  near the via, so with 3,200 items on a layer no route uses, a clear
  spot takes 0.05 ms to check instead of 18 ms.
- **New vias stay out of keep-outs on layers no route uses.** The router
  draws a keep-out only on the layers it routes (and the Keep-Out
  layer's on all of them), but a via passes the others too: one could
  stand in a keep-out drawn on an excluded layer or a pour taken as a
  plane. The search and both fan-outs now keep out of those.
- **A via in a pad is checked where it is laid.** The search lays a via
  in a pad at the pad's centre, but checked the hole gap, hidden copper
  and mask web at the centre of the nearest grid cell, up to half a
  cell's diagonal away (3 mil on a 4.2 mil grid). It is now checked at
  the pad's centre as well.
- **New vias keep the mask web on an excluded outer layer.** The router's
  vias go through every copper layer, but its mask guard counted only
  the openings on the layers it routes: with the bottom layer excluded,
  a new via could stand 4 mil of mask from a via opening there where the
  sliver rule asks for 10. Both outer layers' openings now count.
- **A `pad_vias` the router does not know fails the routing job.** A
  misspelt value was routed as `"bga"` without a word; any case, and the
  spelling `"center"`, are now taken as meant, given as a dict or as a
  `StageOptions` object. `"centre"`, which only Euan's router takes, is
  routed as `"bga"` by the default engine, and the job's notes say so,
  and say when its fallback widened that to IC pins.
- **A new via's mask opening runs together only with its own net's.**
  Where a pad may take a via (a BGA's ball by default), the mask guard
  let a new via's opening merge into that pad's opening whatever the
  pad's net: on a 0.8 mm BGA a dog-bone via stood 7.3 mil from three
  other nets' balls, its opening one with theirs, no solder dam between
  them, and the verdict passed it. Openings that already meet count as
  one, and a new via's may merge only into one whose every pad and via
  is of its net, each pad one that may take a via, and never where it
  would join two nets' openings: next to another net's via whose opening
  ran into that net's pad, a new via shared the pad's opening too. Any
  other opening keeps the board's mask web.
- **Stage numbers are range-checked before routing.** A negative
  `lane_cost` gave the shortest path search negative weights, and the
  server process ran out of memory and aborted, with no job error; a
  `lane_depth` of 1e7 mil held a job worker for hours. `lane_cost`,
  `lane_depth`, `pair_skew`, `pair_width`, `pair_gap`, `fine_pitch` and
  `bus_min` out of range, or not numbers, now fail the job at once, and
  so does a number too large to compute with (a 400-digit `lane_cost`
  passed the check and overflowed mid-job); the engines get each as a
  plain float.
- **A differential pair's skew bump can no longer loop for ever.** When
  a bump had to be cut to its run, rounding could leave it a hair too
  long, and the same height came back on every pass: the job never
  returned (seen with a tight `pair_skew`).
- **A pad smaller than a grid cell is entered from a cell the router
  keeps clear.** When no cell centre falls in a pad, the track ends at
  the nearest cell's centre, outside the pad; that cell was taken as
  all pad copper and left out of the router's own clearance map, so
  another net could come within clearance of the track end. At Euan's
  coarser pitches 43 of 1,155 random small-pad boards broke a
  clearance; none do now. The two cells nearest two such pads of
  different nets are judged by the tracks that end on them, without the
  margin a diagonal step needs, and an escape stub from a pad by its own
  copper rather than a disc round each cell it crosses: random boards of
  0201 parts at pitch 15 and 20 route 100% and 97.5%, where the first
  version of this fix left 75% and 52% (and the router before it 89%
  and 82%, with clearance violations on 12 of 160 boards).
- **A blind via is no way into a plane or pour beyond its span.** A pad
  wired to a via that stops short of its net's plane layer was taken as
  already in the plane, and a pad on a blind via as joined to a pour on
  a layer the via never reaches: the pad was never routed, and the
  verdict found the net open. A via now counts only on the layers it
  passes, in the plane fan-out's count of pads already joined too, and
  the routing attempt after a plane is given back routes again a pad
  whose only way in was through that plane.
- **The DRC verdict joins a plane layer only through vias that reach
  it.** It took every via of an internal plane layer's net as joined to
  the plane, so a pad wired to a blind via that stops short of the
  plane counted as in it while no copper reached it, and a board left
  that way was reported complete.
- **The gloss keeps out of every keep-out.** It honoured keep-outs on the
  routed layer only and missed arcs, so it could straighten a route
  through a keep-out drawn as Keep-Out layer tracks (which bar every
  copper layer) or as a ring of arc round a mounting hole.
- **The `eng_ltspice_*` tools now find LTspice XVII.** They looked for
  LTspice 24 only, while the `sim_*` tools found either; a wrong
  `EDA_AGENT_LTSPICE_EXE` is now reported instead of being ignored.
- **`.MEAS` results with a lower-case `at`/`from`/`to`** (as LTspice XVII
  writes them) are read; they were dropped from `measurements`.
- **`rotation_audit` no longer lets a part on the other side block a
  turn.** A turned part's courtyard was checked against every other
  part's, so a bottom-side part under a top-side part was never offered
  a turn (and the other way round), though courtyards on opposite sides
  never meet. It now checks the same side only, the rule
  `placement_audit` already uses. Checked live on 2026-11-12 (Altium
  26.11.1.5) on a copy of BoosterTest: a backwards bottom-side
  WE-PMI 1008 under the same footprint on top got turn 180, saving
  173.2 mils; applied and read back, the pads swapped as predicted and
  the connection shortened by exactly 173.2 mils. Main suggested nothing
  there. With both parts on the bottom, every turn is still blocked.

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
