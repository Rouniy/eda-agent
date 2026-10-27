# PCB quality ruleset

A companion ruleset for the eda-agent design harness, covering the
**physical quality bar** of a finished board: manufacturability,
assembly, serviceability, and whether the layout reads as engineered
rather than generated.

Added by this fork; not part of upstream eda-agent.
Originally contributed in `tisn1678065900-dot/eda-agent` branch
`boardquality` (`21f0412`), under the repository's Apache-2.0 license.

## Files

| File | What it is |
|---|---|
| [rules.en.md](rules.en.md) | The ruleset. Canonical version. |
| [rules.zh.md](rules.zh.md) | 中文版。与英文版同步维护。 |
| [board-intent.template.md](board-intent.template.md) | Per-board physical intent. Fill during `requirement` / `architecture`. |
| [fab-profile.template.json](fab-profile.template.json) | `FabProfile` shape for `design_load_fab_profile`. Every number is a placeholder. |
| [../../skills/boardquality/SKILL.md](../../skills/boardquality/SKILL.md) | The client skill that applies it. |

## Why it exists separately from the harness

The server already owns a great deal: `design_next_action` sequences the
13 stages, `design_get_discipline` bounds the schematic planner,
`design_synthesize_rules` derives design rules from a fab profile, and
`design_visual_review` runs a render → look → critique loop against a
rubric.

Two gaps remain, and they are the ones that decide whether a board is
usable:

1. **Missing numeric intent.** `design_synthesize_rules` derives rules
   from a `FabProfile` — but stackup choice, impedance targets, peak
   currents, edge rates, enclosure constraints and test strategy are not
   in that profile and are not in the functional requirement either. When
   they are absent, they get assumed, and every value computed downstream
   inherits the assumption. `board-intent.template.md` makes them a gate
   instead.

2. **Geometric and documentation standards.** The visual rubric catches
   off-grid parts, acute angles and colliding designators. It does not
   say which grid, that rotations are 90° multiples, that like parts sit
   at uniform pitch, that polarized parts face one way, that pours are
   stitched across their area rather than fenced, or that silkscreen has
   to be readable by whoever assembles the board.

The ruleset fills those two gaps and defers to the server everywhere
else. It adds no stages and overrides nothing.

## Using it

**Claude Code** — copy the skill into your project:

```bash
mkdir -p .claude/skills/boardquality
cp skills/boardquality/SKILL.md .claude/skills/boardquality/SKILL.md
```

`/boardquality` is then available in that project, and applies alongside
`/autodesign`.

**Other clients** — point the model at `rules.en.md` (or `rules.zh.md`)
as context for the design session. The ruleset is written to be read
directly; nothing in it depends on the skill wrapper.

**Either way**, start by filling `board-intent.template.md` and a real
fab profile. The ruleset's first and most important clause is that
missing physical parameters block the stage instead of being guessed.

## Scope

Backend-agnostic in intent, but the tool names cited are the Altium
surface, which is the most complete. On KiCad the design harness is not
registered at all, so use the ruleset as review criteria rather than as a
workflow.
