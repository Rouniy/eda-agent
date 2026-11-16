"""Write README.pypi.md: README.md with every repository link made absolute.

PyPI shows the page without the repository around it, so a relative link or
picture there leads nowhere. The front page keeps relative links (they work
on GitHub and are checked against the tree); the package ships this copy.

    python scripts/gen_pypi_readme.py           # rewrite the file
    python scripts/gen_pypi_readme.py --check   # exit 1 if it is stale
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://github.com/Rouniy/eda-agent/blob/main/"
RAW = "https://raw.githubusercontent.com/Rouniy/eda-agent/main/"
HEAD = ("<!-- Generated from README.md by scripts/gen_pypi_readme.py: the same "
        "page with absolute links, for PyPI. -->\n")


def build() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    def link(m: re.Match) -> str:
        target = m.group(1)
        if re.match(r"(https?:|mailto:|#)", target):
            return m.group(0)
        return "](" + BASE + target + ")"

    def picture(m: re.Match) -> str:
        target = m.group(1)
        return m.group(0) if re.match(r"https?:", target) else 'src="' + RAW + target + '"'

    text = re.sub(r"\]\(([^)\s]+)\)", link, text)
    return HEAD + re.sub(r'src="([^"]+)"', picture, text)


def main() -> int:
    out = ROOT / "README.pypi.md"
    want = build()
    if "--check" in sys.argv:
        have = out.read_text(encoding="utf-8") if out.exists() else ""
        if have != want:
            print("README.pypi.md is stale: run python scripts/gen_pypi_readme.py")
            return 1
        return 0
    out.write_text(want, encoding="utf-8", newline="\n")
    print(f"wrote {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
