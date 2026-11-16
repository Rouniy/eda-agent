# SPDX-License-Identifier: Apache-2.0
"""Classify amplifier pin names into functional units."""
import re as _re

_AMP_WORDS = _re.compile(
    r"op[\s\-_]?amp|operational amplifier|comparator|current[\s\-_]?sense|"
    r"current[\s\-_]?shunt|instrumentation amplifier|difference amplifier|"
    r"differential amplifier|in[\s\-_]?amp\b|amplifier", _re.I)

# Role patterns are matched against the pin NAME with an optional unit
# letter or number (A/B/C/D or 1-4) before or after, e.g. "+INA", "INA+",
# "IN1-", "OUTB", "VOUT_A".
_IN_POS = _re.compile(r"^(?:\+IN|IN\+|INP|IN_?P|VIN\+|\+VIN|NONINV|NI|\+)$",
                      _re.I)
_IN_NEG = _re.compile(r"^(?:-IN|IN-|INN|IN_?N|VIN-|-VIN|INV|-)$", _re.I)
_OUT = _re.compile(r"^(?:V?OUT|VO|O|OUTPUT)$", _re.I)
_SUPPLY_POS = _re.compile(
    r"^(?:V\+|\+V|VCC\+?|VDD|AVDD|VS\+?|\+VS|VPOS|V_?POS|VCC|VS|PWR)$", _re.I)
_SUPPLY_NEG = _re.compile(
    r"^(?:V-|-V|VEE|VSS|AVSS|VS-|-VS|VNEG|V_?NEG|GND|AGND|DGND|PGND)$", _re.I)
_UNIT = _re.compile(r"^(?P<a>[A-D1-4])?(?P<core>.+?)(?P<b>[A-D1-4])?$", _re.I)


def _norm(name: str) -> str:
    return str(name).strip().replace(" ", "").replace("_", "").upper()


def _role(name: str) -> tuple[str | None, str]:
    """(role, unit) for one pin name; role None when it is not an amp pin."""
    n = _norm(name)
    for pattern, role in ((_SUPPLY_POS, "v+"), (_SUPPLY_NEG, "v-")):
        if pattern.match(n):
            return role, ""
    for pattern, role in ((_IN_POS, "in+"), (_IN_NEG, "in-"), (_OUT, "out")):
        if pattern.match(n):
            return role, ""
    # Unit suffix or prefix: OUTA, INA+, +INA, IN1-, OUT2, A_OUT ...
    for core, unit in ((n[:-1], n[-1]), (n[1:], n[0])):
        if unit in "ABCD1234" and core:
            core = core.rstrip("_")
            for pattern, role in ((_IN_POS, "in+"), (_IN_NEG, "in-"),
                                  (_OUT, "out")):
                if pattern.match(core):
                    return role, unit
    # "+INA" style: sign first, unit last.
    m = _re.match(r"^([+-])IN([A-D1-4])$", n)
    if m:
        return ("in+" if m.group(1) == "+" else "in-"), m.group(2)
    m = _re.match(r"^IN([A-D1-4])([+-])$", n)
    if m:
        return ("in+" if m.group(2) == "+" else "in-"), m.group(1)
    return None, ""


def classify_amplifier_pins(pins: list[dict]) -> dict | None:
    """Group pins into amplifier units, or None when they do not form one.

    Returns ``{"units": [{"unit", "in+", "in-", "out", "extra": [...]}],
    "v+": [...], "v-": [...], "extra": [...]}``. A unit needs both inputs
    and an output. Pins that fit no role go to ``extra``: on a single
    amplifier they join the left side under the inputs; on a multi-unit
    part they go on the power part.
    """
    units: dict[str, dict] = {}
    supply_pos: list[dict] = []
    supply_neg: list[dict] = []
    extra: list[dict] = []
    for p in pins:
        role, unit = _role(p.get("name", ""))
        if role == "v+":
            supply_pos.append(p)
        elif role == "v-":
            supply_neg.append(p)
        elif role in ("in+", "in-", "out"):
            u = units.setdefault(unit, {"unit": unit})
            if role in u:
                extra.append(p)          # a second OUT etc. is not a unit role
            else:
                u[role] = p
        else:
            extra.append(p)
    whole = [u for u in units.values()
             if all(r in u for r in ("in+", "in-", "out"))]
    if not whole:
        return None
    for u in units.values():
        if u not in whole:
            extra.extend(u[r] for r in ("in+", "in-", "out") if r in u)
    whole.sort(key=lambda u: u["unit"])
    for u in whole:
        u["extra"] = []
    return {"units": whole, "v+": supply_pos, "v-": supply_neg,
            "extra": extra}


def looks_like_amplifier(pins: list[dict], description: str = "") -> bool:
    """True when the description names an amplifier/comparator, or when the
    pin names form at least one complete IN+/IN-/OUT unit."""
    if description and _AMP_WORDS.search(description):
        return classify_amplifier_pins(pins) is not None
    return classify_amplifier_pins(pins) is not None
