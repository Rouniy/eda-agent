# Project phase gates

A board passes stages on its way to production: feasibility, research,
prototype, engineering validation (EVT), design validation (DVT) and
production validation (PVT). Each stage has a list of checks; a stage is
clear when every check is answered for the board's current revision.

Three tools read and write that record. They are part of the default tool
surface and need no running Altium:

| Tool | What it does |
|---|---|
| `design_phase_standing` | Where the product stands: the first stage that is not clear, and what is open in it |
| `design_phase_gate` | One stage in full: each check, why it is asked at this stage, what counts as done and which tools answer it |
| `design_phase_answer` | Record the outcome of one check: met, unmet or waived, with the detail and the board revision |

The tools never run a check themselves. The client runs the tools a check
names and records the outcome, so a stage can be reviewed with Altium
closed and every answer shows how old it is.

Three rules make a stage hard to pass by accident:

- an answer expires after the time its check allows;
- an answer belongs to one revision of the board and stops counting for
  another;
- a waiver without a reason is refused.

The current stage is the first one that does not clear: a board whose
feasibility never closed is at feasibility however much layout is done.
