---
name: boardquality
description: Hold a PCB to an engineering quality bar — grid-aligned placement, 45-degree routing, stitched pours, readable silkscreen, fab margin, and machine-enforced design rules. Apply alongside autodesign, or on any board work where the user asks for a layout that is manufacturable, reviewable, or simply looks professionally drawn. Complements the design harness; it does not replace design_next_action.
---

# Board quality bar (eda-agent)

The design harness gets a board built. This skill decides whether the
board is any good: whether a fab can make it, an operator can assemble
it, an engineer can debug it, and a reviewer can look at it without
wincing.

Full ruleset: [../../docs/pcb-quality/rules.en.md](../../docs/pcb-quality/rules.en.md)
(中文: [rules.zh.md](../../docs/pcb-quality/rules.zh.md))

## What this skill does not do

It adds no stages and re-orders nothing. `design_next_action` still owns
sequencing, `design_get_discipline` still owns the schematic planner, and
`design_visual_review` still owns the render → look → critique loop. This
skill supplies the numeric intent those need as input, and the geometric
standard they are silent on.

Use it with `/autodesign`, or on its own when editing a board by hand.

## The three rules that matter most

Everything else in the ruleset is detail. These three are where boards
actually go wrong:

1. **Never assume a physical parameter.** Stackup, fab limits, impedance
   targets, currents, edge rates. A missing one becomes an
   `open_question` that blocks the stage — never a "typical value".
   Every number computed downstream inherits the guess, and none of them
   get re-derived when the real value arrives.

2. **Rules into the editor before geometry.** No track, via, or pour
   until `design_synthesize_rules` (or `pcb_create_design_rule`) has put
   the constraints where `pcb_run_drc` enforces them. A constraint that
   lives only in the conversation is gone in a few turns.

3. **Report what actually happened.** Paste real `pcb_run_drc` /
   `design_lint_report` output. A quiet compromise reported as "done" is
   the one failure nobody catches.

## Before the board: board intent

Fill [board-intent.template.md](../../docs/pcb-quality/board-intent.template.md)
during `requirement` / `architecture`. It captures what
`design_validate_requirement` and `FabProfile` between them do not: board
outline and its source, mounting holes, enclosure constraints, highest
frequency *and* edge rate, impedance-controlled nets, peak currents,
temperature range, assembly style, panelization, test strategy.

`rules_stackup` cannot synthesize correct rules without these, and
[fab-profile.template.json](../../docs/pcb-quality/fab-profile.template.json)
is the shape `design_load_fab_profile` wants — transcribed from the fab's
capability page and cited in `source`, never recalled from memory.

## During `placement`

Fixed geometry first — connectors, mounting holes, anything the enclosure
determines — placed and **locked**, then blocks, then parts within
blocks.

Geometry that reads as designed: every origin on one declared grid
(`audit_find_off_grid_components`), rotations in 90° multiples, like
parts aligned at uniform pitch, polarized parts consistently oriented,
even density across the board.

Electrical placement that survives review: decoupling judged by **loop
area**, not distance; switching hot loops minimized first; sensitive
analog away from switchers and connectors; heat spread out.

## During `routing`

45° or arcs, never square corners, never acute
(`audit_find_acute_angles`). Constant width per net, taper where it must
change. Groups routed together so parallel runs read as a bus. Continuous
reference plane under every trace — crossing a plane split is prohibited;
if unavoidable, add a stitching cap and report it. Widths for current
from `pcb_calc_trace_width_for_current`, not from habit.

## During `pours_tuning`

Pours are **stitched across their area**, not fenced along trace edges —
a via fence leaves the copper between fences free to resonate as a patch.
Use `pcb_place_stitching_vias` over the region, and derive the pitch:

```
λ_g = c / (f · √εr)      pitch ≤ λ_g/20 (strict), λ_g/10 (general)
```

For digital use the edge-rate bandwidth (`f_knee ≈ 0.35 / t_r`), not the
clock. Show the substitution. Return via beside every layer-changing
signal via. Re-run `pcb_run_drc` after every repour — a repour is a
geometry change, not a cosmetic one.

## Silkscreen

Judged by one question: could someone who has never seen this board
assemble it correctly from the silk alone? Uniform height and stroke,
designators at 0°/90° only, nothing over pads, pin 1 and polarity always
marked, board name / revision / date present.

## Finishing

Walk §10's extra rubric items in the `design_visual_review` loop, then
the §11 sign-off checklist at `verification`. DRC violations mean not
finished — list each one with its disposition rather than waiving in
bulk.
