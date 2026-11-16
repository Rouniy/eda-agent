# Board quality rules

Companion ruleset for the eda-agent design harness. It governs the
**physical quality bar** of the finished board: whether a person can
build it, assemble it, debug it, and read it, and whether it looks like
an engineer drew it rather than a script.

Normative language: **MUST** / **MUST NOT** are hard; **SHOULD** admits a
documented exception; **MAY** is a permitted option.

---

## 0. Scope, and what this does not own

The server owns sequencing. `design_next_action` decides which of the 13
stages runs next and when it is done; `design_get_discipline` owns the
schematic planner's rules; `design_visual_review` owns the render → look →
critique loop. **This document adds no stages, re-orders nothing, and
overrides none of those.**

What it adds is the layer none of them cover: the numeric intent that
must exist before `rules_stackup` can synthesize anything, and the
geometric and documentation standards that make `placement`, `routing`,
`pours_tuning` and `outputs` produce a board someone would sign off on.

Each section below binds to the stage named in its heading. Apply a
section's rules while that stage is open; check them again at
`verification`.

### Precedence

When two rules collide, resolve in this order:

1. Safety and manufacturability: the board can be fabricated, assembled,
   and powered without damage
2. Electrical correctness: netlist parity, impedance, return paths,
   power integrity
3. Serviceability: testable, reworkable, readable
4. Visual quality: alignment, consistency, tidiness

Never buy a lower item at the cost of a higher one. But when the higher
items are unaffected, **item 4 is a requirement, not a nicety**: on a
finished board there is almost always slack, and "it routes" is not the
bar.

---

## 1. Board intent: stage `requirement`, `architecture`

`design_validate_requirement` captures the functional requirement.
`design_load_fab_profile` captures the fab's limits. Between them sits a
set of physical facts neither one holds, and `rules_stackup` cannot
synthesize correct rules without them.

Fill `board-intent.template.md` before leaving `architecture`. Every
field is either **stated by the user**, or **derived with a cited
calculation**. A field that is neither MUST become an `open_question` and
block the stage.

| Field | Why it gates later stages |
|---|---|
| Board outline, origin, and its source | `placement` cannot start without it |
| Mounting holes: position, diameter, keepout radius | Fixed geometry must be placed and locked first |
| Enclosure / mating constraints | Connector placement is not free |
| Highest frequency **and** fastest edge rate | Decides whether §8 applies at all |
| Impedance-controlled nets, target Z, single-ended or differential | Feeds `pcb_calc_impedance` and diff-pair rules |
| Highest-current nets and their current | Feeds `pcb_calc_trace_width_for_current` |
| Operating temperature range | Derating, and thermal copper budget |
| Assembly style: single-side reflow / double-side / hand-soldered parts | Decides bottom-side placement rules |
| Surface finish | Affects pad finish and fine-pitch practice |
| Panelization and rails needed? | Reserves board-edge space |
| Test strategy: bed-of-nails, probe points, none | Decides test-point rules in §6 |

**Do not substitute a typical value for a missing one.** "Assuming a
4-layer 1.6 mm FR-4 stack" is the single most expensive sentence in this
workflow: every width, clearance, impedance and stitching pitch computed
downstream inherits the guess, and none of them are re-derived when the
real stack arrives.

The fab profile has the same discipline already, `FabProfile.source`
exists so the numbers trace to a capability page with a date. Honor it:
transcribe, cite, never recall from memory.

---

## 2. Rules before geometry: stage `rules_stackup`

**No track, via, or pour may be placed before the design rules exist in
the editor.** A constraint that lives only in the conversation is
forgotten within a few turns; a constraint in a design rule is enforced
by `pcb_run_drc` on every check thereafter. This is the difference
between a board that converges and one that gets re-routed.

Prefer `design_synthesize_rules(profile=...)`, it derives each value
from a profile field or a verified calculator and hands back
`pcb_create_design_rule` / `pcb_modify_layer` dicts to dispatch verbatim.
Hand-authoring rules is the exception, and each hand-authored value MUST
carry a one-line justification.

The rule set MUST cover, at minimum:

- **Clearance**, banded per net class, signal, power, high-voltage, RF ,
  not one global value
- **Width**, per net class, with `value` (min), `favored_value` (the
  router's default), and `max_value` all set
- **Via** sizes derived as `min_drill + 2 × min_annular_ring`, never
  tighter than the profile allows
- **Board-edge clearance** for all copper
- **Hole-to-hole** and **hole-to-copper**
- **Component clearance**, so assembly does not collide
- **Silk-to-mask** and **silk-to-pad**, so no designator lands on a pad
- **Solder-mask and paste-mask expansion**, uniform; any per-pad
  exception documented
- **Differential-pair gap and length matching**, when §8 applies
- **Polygon connect style**, plane and thermal pads use **direct
  connect**, not thermal relief. Thermal relief on a ground plane costs
  inductance and thermal path for no benefit on a reflow-assembled
  board. Hand-soldered parts MAY use relief; note which and why.

**Never design to the fab's exact minimum.** Leave one step of margin ,
if the profile allows 3.5 mil track, design at 5 mil unless density
genuinely forbids it. Boards that sit on the limit yield worse and cost
more, and there is nowhere to retreat when a spin needs a wider trace.

Changing an existing rule requires reporting **what, why, old → new**
before the change.

---

## 3. Placement: stage `placement`

`pcb_plan_placement` optimizes HPWL and keeps groups together. These
rules constrain what it is allowed to produce.

### 3.1 Order

1. Place and **lock** everything mechanically fixed first: connectors,
   mounting holes, indicators, anything the enclosure or a mating part
   determines. Locked objects MUST NOT move afterwards; if one must,
   report and ask.
2. Then place functional blocks.
3. Then place the parts inside each block.

Optimizing before the fixed geometry is locked produces a placement that
must be undone.

### 3.2 Electrical placement

- Parts in one functional block MUST be physically grouped. A block whose
  parts are scattered across the board is a defect regardless of net
  length.
- Signal flow SHOULD run one way across the board, input to output,
  left-to-right or bottom-to-top, without doubling back.
- Decoupling capacitors MUST sit at the pin they decouple, on the
  shortest cap → pin → via loop available. Distance to the IC is the
  wrong metric; **loop area** is the metric. A cap that is close but
  vias out the far side is worse than one slightly further with a via at
  its pad.
- Crystals and oscillators: adjacent to their IC, shortest possible
  traces, no other signal routed underneath or alongside.
- Sensitive analog, ADC references, op-amp inputs, high-impedance nodes
 , kept away from switching regulators, high-di/dt loops, and
  connectors.
- Switching-regulator hot loops (switch node, input cap, diode/FET) are
  placed for **minimum loop area** before anything else in that block.
- Heat-dissipating parts spread out, never clustered; copper area and
  thermal vias budgeted at placement time, not discovered at routing.
- Connectors face the board edge with room for the mating part, the
  cable's bend radius, and a hand to reach them.

### 3.3 Geometry: this is what makes a board look designed

- Every component origin MUST land on a **single declared placement
  grid** (0.5 mm metric, or 25 mil imperial). Confirm with
  `audit_find_off_grid_components`. A coordinate like `X = 12.3847 mm`
  is a defect, not a rounding detail.
- Rotation MUST be a multiple of 90°. Any other angle requires a stated
  reason, RF matching structures and mechanically-constrained parts
  qualify; "the router preferred it" does not.
- Like parts in a group, resistor arrays, a decoupling bank, LED rows,
  test points, MUST be aligned in rows or columns with **uniform
  pitch**. Uniform, not merely tidy: 2.0 mm between every pair, not
  1.8 / 2.1 / 1.95.
- **Polarized parts face the same way** within a block: diodes,
  electrolytics, and IC pin 1 all consistently oriented. This is what
  makes assembly errors visible and inspection fast.
- Spacing MUST be visually consistent. Dense here and empty there reads
  as unfinished even when it is electrically fine.
- Distribute mass over the board. Where a functional constraint forces
  asymmetry, balance it with pour and silkscreen rather than leaving a
  bare quadrant.

### 3.4 Prohibited

- Moving a locked object.
- Pushing a part outside its functional block to make routing easier.
- **Inventing a footprint.** If the library lacks one, stop and say so. A
  footprint created without the datasheet land pattern in hand MUST be
  marked `UNVERIFIED` and listed in the report, never silently emitted.
  `library_readiness` exists to prevent exactly this; do not route
  around it.

---

## 4. Routing: stage `routing`

- **No 90° corners. No acute angles.** Corners are 45° or arcs. Confirm
  with `audit_find_acute_angles`.
- Width is constant along a net. Where a change is unavoidable, taper;
  never step.
- Parallel runs keep uniform spacing and read as a bus. Route groups
  together, not one net at a time with the rest fitted around them.
- Adjacent layers SHOULD route predominantly orthogonally.
- No stubs, no loops, no isolated copper, no acute copper slivers.
  Confirm stubs with `audit_find_via_antennas`.
- Minimize layer changes: ≤ 2 vias per signal net by default; more
  requires a reason.
- **Every trace MUST have a continuous reference plane beneath it.**
  Crossing a plane split is prohibited. If a crossing is unavoidable, add
  a stitching capacitor at the crossing and report it, the return
  current takes the long way around otherwise, and that loop is the
  antenna.
- High-current nets get widths from `pcb_calc_trace_width_for_current`
  (IPC-2221), never from habit. Where the computed width does not fit,
  parallel across layers with a via array, and say so.
- Sensitive analog does not run parallel to digital or switching nets for
  any appreciable length. Cross orthogonally where crossing is needed.
- Differential pairs: same layer, uniform gap end to end, symmetric
  routing, changing layers together. **Match length within the pair at
  the source of the skew**, not by serpentining one leg at the far end.

---

## 5. Copper and ground: stage `pours_tuning`

- Keep reference planes **whole**. Every plane cut is a detour for return
  current. Where a cut is unavoidable, trace the return path explicitly
  and confirm it is not forced to go around.
- **Pours MUST be via-stitched across their area, not merely fenced along
  the trace edges.** A fence of vias beside a trace leaves the copper
  between fences free to resonate as a patch; on thin laminate at high
  frequency that patch is exactly the structure that couples between
  blocks. Use `pcb_place_stitching_vias` over the pour region.
- Derive the stitching pitch; do not adopt a habit:

  ```
  λ_g = c / (f · √εr)          pitch ≤ λ_g / 20   (strict)
                               pitch ≤ λ_g / 10   (general)
  ```

  Use the highest frequency of concern from §1, for digital, the
  bandwidth implied by the edge rate (`f_knee ≈ 0.35 / t_r`), not the
  clock. **Show the substitution and the result**; a bare "1.5 mm" is not
  auditable.
- Every signal via that changes reference layer needs a return via
  nearby, within ~1.5 mm by default, tighter under §8.
- Ground pads connect to the plane with a via at or immediately beside
  the pad. A pad that reaches ground through a length of trace is not
  grounded at frequency.
- After every repour: remove isolated islands and copper slivers, then
  **re-run `pcb_run_drc`**. A repour is a geometry change; treating it as
  cosmetic is how clean boards become dirty ones.

---

## 6. Silkscreen and documentation: stages `placement`, `outputs`

Silkscreen is read by a human holding the board with a soldering iron.
Judge it by that standard.

- Uniform text height and stroke width board-wide. Default 0.8-1.0 mm
  height, 0.15 mm stroke; never below the profile's
  `min_silk_width_mils`.
- **Designator rotation is 0° or 90° only**, read left-to-right and
  bottom-to-top. Confirm with `audit_find_mirrored_pcb_text`.
- No silk over pads, vias, or fiducials. No designator ambiguous about
  which part it labels. Confirm with `audit_find_designator_collisions`.
- Mark, always: **pin 1**, polarity, connector pinouts, and any
  orientation that could be reversed at assembly.
- The board carries its own identity: board name, revision, date, and any
  compliance marks.
- Three asymmetric fiducials for SMT assembly.
- Test points: uniform footprint, on the grid, grouped and accessible
  from one side, labeled, covering every supply rail and every signal
  worth probing. Match the test strategy declared in §1.

Self-check: **could someone who has never seen this board assemble it
correctly from the silkscreen alone?** If not, it is not finished.

---

## 7. Manufacturability and assembly

- Every geometry sits inside the fab profile with margin (§2).
- Board-edge: keep components clear of the edge, 5 mm by default, more
  where rails or V-scoring are used. Reserve rail width when §1 says the
  board is panelized.
- Footprints follow IPC-7351 land patterns. Do not scale a footprint to
  make a part fit.
- **One passive size series per board** where practical. Mixing 0402 /
  0603 / 0805 without cause costs feeder slots and invites the wrong part
  in the wrong place.
- Mask slivers between fine-pitch pads must exceed the profile's
  `min_mask_sliver_mils`; below it, specify how the mask is handled.
- Double-side reflow: bottom side carries small passives only; heavy or
  tall parts go top.
- Hand-soldered parts get clearance for an iron at a working angle.
- BOM: every line procurable, with a real manufacturer part number.
  Prefer parts already in inventory, per the planner's discipline.

---

## 8. High-speed and RF: conditional

**Applies when any of these is true**: highest frequency > 100 MHz; edge
rate < 1 ns; any impedance-controlled net exists. If any holds, the whole
section is mandatory.

- Impedance-controlled widths come from `pcb_calc_impedance` against the
  actual stackup, or from the fab's impedance table. **A width chosen
  from experience is not acceptable**, and the derivation goes in the
  report.
- A controlled-impedance trace references one continuous plane along its
  entire length. Where it changes layer, the reference must remain
  continuous and a ground via accompanies the transition.
- RF corners are arcs or mitered, never square.
- Keepout beside RF traces: ≥ 3× trace width, no other copper inside it.
- Termination and matching components sit at the point they act on.
- Divider, combiner, and any branched structure: hold branch lengths and
  phase equal within the declared tolerance, and encode that tolerance as
  a length-matching design rule so DRC checks it.
- Where a trace must change width at a component pad, taper.
- Under a shield can: no silkscreen, no tall parts inside the footprint,
  and a continuously stitched ground ring under the can wall.
- Stitching pitch per §5, computed at the highest frequency of concern.

---

## 9. Agent conduct

These constrain *how you work*. They are violated more often than the
technical clauses, and cost more when they are.

1. **Read before writing.** Establish the current state and report it
   before modifying anything. `design_review_snapshot` bundles the reads.
2. **Checkpoint before risk.** `app_checkpoint` before `sch_to_pcb`,
   `routing`, `pours_tuning`, and before any bulk edit.
3. **Small steps.** ≤ 20 objects per operation by default; state the scope
   and get confirmation before a larger sweep.
4. **Never assume a parameter.** Missing input becomes an `open_question`
   and blocks the stage. Writing "I'll assume 4 layers" is itself the
   violation.
5. **Never silently lower a standard.** A constraint you cannot meet is
   reported as unmet. Reporting "done" over a quiet compromise is the
   worst failure mode available here, because it is the one nobody
   catches.
6. **Traceable changes.** Each round reports what changed, why, and which
   nets it touched.
7. **Paste the evidence.** Finish with `pcb_run_drc`, `design_lint_report`
   and `obj_crossref_net`, and include their actual output. "Checks
   passed" without the output is not a check.
8. **DRC violations mean not finished.** Harmless-looking ones are listed
   individually with their disposition, not waived in bulk.

---

## 10. Extended visual-review rubric

`design_visual_review` ships a PCB rubric, off-grid parts, acute angles,
courtyard collisions, mirrored text, edge clearance, missing decoupling.
Walk these additional items in the same loop, and cross-check with the
audits named:

| Look for | Cross-check |
|---|---|
| Like parts not aligned, or pitch not uniform within a group | visual |
| Polarized parts in a block facing inconsistent directions | visual |
| Designators rotated to angles other than 0°/90° | `audit_find_mirrored_pcb_text` |
| Pour present but not stitched across its area | `pcb_get_vias` |
| Trace crossing a plane split or plane gap | visual, then check the reference layer |
| Isolated copper islands or slivers after repour | `pcb_run_drc` |
| Density visibly uneven across the board | visual |
| Silk unreadable, ambiguous, or missing pin-1 / polarity marks | `audit_find_designator_collisions` |
| Connector clearance insufficient for the mating part or cable | visual + 3D |

---

## 11. Sign-off checklist: stage `verification`

Not complete until every line is checked, with output shown:

- [ ] `obj_crossref_net` / `proj_compare_sch_pcb`: schematic and PCB in sync
- [ ] `pcb_run_drc`: zero violations, or each waiver justified individually
- [ ] `proj_run_erc`: clean
- [ ] `design_lint_report`: all checks pass or explained
- [ ] All components on the declared grid; all rotations 90° multiples
- [ ] No 90° corners, acute angles, stubs, or isolated copper
- [ ] Pours stitched, with the pitch calculation shown
- [ ] Every trace has a continuous reference plane; no split crossings
- [ ] Impedance-controlled widths traced to a calculation or fab table
- [ ] High-current widths traced to `pcb_calc_trace_width_for_current`
- [ ] Silkscreen: no pad overlap, uniform orientation, pin-1 and polarity
      present
- [ ] Board name, revision, and date on the board
- [ ] No `UNVERIFIED` footprints remain
- [ ] 3D check: no interference, no height violation
- [ ] Fab package complete: Gerbers, drill, IPC-356 netlist, BOM,
      pick-and-place, assembly drawing
