# SPDX-License-Identifier: Apache-2.0
"""Calls whose argument count differs from the routine's declaration, across the script units.

DelphiScript reports these only when Altium compiles the script project, as "Comma expected" or
"')' expected" in a dialog that names no file. A routine one unit changed and a caller another unit
kept is how they arise, so this runs with the lint, before a deploy.

  python lint_arity.py            exit code 1 when any call does not match
"""
import bisect
import os
import re
import sys
from pathlib import Path

from lint import PAS_FILES

def blank(text: str) -> str:
    """Comments and string contents replaced by spaces, newlines kept."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "'":
            j = i + 1
            while j < n:
                if text[j] == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            out.append("'" + "".join("\n" if ch == "\n" else "s" for ch in text[i + 1:j]) + "'")
            i = j + 1
        elif c == "{":
            j = text.find("}", i)
            j = n - 1 if j < 0 else j
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j + 1]))
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("(*", i):
            j = text.find("*)", i)
            j = n - 2 if j < 0 else j
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j + 2]))
            i = j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def close_paren(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] in "([":
            depth += 1
        elif text[i] in ")]":
            depth -= 1
            if depth == 0:
                return i
    return -1


def count_args(inner: str) -> int:
    if not inner.strip():
        return 0
    depth, count = 0, 1
    for ch in inner:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
    return count


def main(argv=None) -> int:
    root = Path(os.path.dirname(os.path.abspath(__file__)))
    return check(root)


def check(root: Path) -> int:
    texts = {f: blank((root / f).read_text(encoding="utf-8-sig", errors="replace"))
             for f in PAS_FILES if (root / f).exists()}
    decl = {}
    HEAD = re.compile(r"^[ \t]*(?:procedure|function)[ \t]+([A-Za-z_]\w*)[ \t]*(\()?", re.I | re.M)
    for f, text in texts.items():
        for m in HEAD.finditer(text):
            name = m.group(1).lower()
            if m.group(2):
                end = close_paren(text, m.end() - 1)
                params = text[m.end():end]
                n = 0
                for group in params.split(";"):
                    names = group.split(":")[0]
                    names = re.sub(r"\b(var|const|out)\b", " ", names, flags=re.I)
                    n += len([x for x in names.split(",") if x.strip()])
            else:
                n = 0
            decl.setdefault(name, set()).add(n)
    problems = 0
    CALL = re.compile(r"(?<![\w.])([A-Za-z_]\w*)[ \t]*\(")
    for f, text in texts.items():
        line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                line_starts.append(i + 1)
        for m in CALL.finditer(text):
            name = m.group(1).lower()
            if name not in decl:
                continue
            # skip the declaration itself
            prefix = text[text.rfind("\n", 0, m.start()) + 1:m.start()]
            if re.match(r"[ \t]*(procedure|function)[ \t]+$", prefix, re.I):
                continue
            end = close_paren(text, m.end() - 1)
            if end < 0:
                continue
            n = count_args(text[m.end():end])
            if n not in decl[name]:
                line = bisect.bisect_right(line_starts, m.start())
                problems += 1
                print(f"{f}:{line}: {m.group(1)} called with {n} argument(s), declared with {sorted(decl[name])}")
    print(f"arity: {problems} call(s) do not match their declaration")
    return problems


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
