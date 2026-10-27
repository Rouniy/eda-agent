# Board intent — <project name>

Physical intent for one board. Fill this during the `requirement` /
`architecture` stages, before `rules_stackup` synthesizes anything.

Rules for filling it in:

- Every value is **stated by the user** or **derived with a shown
  calculation**. Write the derivation next to the value.
- A field you cannot fill becomes an `open_question` that blocks the
  stage. Leave it as `UNKNOWN — blocking`.
- `n/a` is a legitimate answer, but only as a decision, not as a way to
  skip a question. Write why.

---

## Mechanical

| Field | Value | Source / derivation |
|---|---|---|
| Board outline | | file, drawing, or dimensions |
| Origin / datum | | |
| Board thickness | | |
| Mounting holes: position, Ø, keepout | | |
| Enclosure / mating constraints | | what fixes connector positions |
| Max component height, top / bottom | | |
| Keepout regions | | |

## Stackup and fab

| Field | Value | Source / derivation |
|---|---|---|
| Fab and capability page | | URL + date transcribed |
| Copper layer count | | |
| Stackup: layer, material, εr, thickness, copper weight | | fab stackup table |
| Surface finish | | |
| Panelized? rails needed? | | |

Fab limits go in the `FabProfile` JSON, not here — see
`fab-profile.template.json`.

## Electrical

| Field | Value | Source / derivation |
|---|---|---|
| Supply rails: voltage, current, tolerance | | |
| Highest-current nets and their current | | feeds `pcb_calc_trace_width_for_current` |
| Highest operating frequency | | |
| Fastest edge rate `t_r` | | decides whether the RF/high-speed section applies |
| Impedance-controlled nets: target Z, SE / diff | | feeds `pcb_calc_impedance` |
| Length-matched groups and tolerance | | becomes a design rule |
| Isolation / creepage requirements | | |

## Thermal and environment

| Field | Value | Source / derivation |
|---|---|---|
| Operating temperature range | | |
| Known dissipating parts and their power | | |
| Cooling: convection / conduction / forced | | |

## Assembly and test

| Field | Value | Source / derivation |
|---|---|---|
| Assembly: single-side reflow / double-side / hand-soldered parts | | |
| Bottom-side placement permitted? | | |
| Test strategy: bed-of-nails / probe points / none | | decides test-point rules |
| Programming / debug access needed | | |
| Fiducials required | | 3 asymmetric for SMT |

## Conventions for this board

| Field | Value |
|---|---|
| Placement grid | e.g. 0.5 mm |
| Routing grid | |
| Units | metric / imperial |
| Passive size series | e.g. 0402 throughout |
| Silk text height / stroke | e.g. 0.8 mm / 0.15 mm |
| Board-edge component keepout | e.g. 5 mm |

## Open questions

Anything above marked `UNKNOWN — blocking`, restated here with who needs
to answer it.

1.
