"""Split app.component.html into feature template fragments."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app"
HTML = ROOT / "app.component.html"
FEATURES = ROOT / "features"

MARKERS = [
    ("word-check", "VIEW 1: BASIC WORD CHECK", "VIEW 2: ADVANCED FILTER"),
    ("filters", "VIEW 2: ADVANCED FILTER", "VIEW 3: PUZZLE SOLVER"),
    ("puzzles", "VIEW 3: PUZZLE SOLVER", "VIEW 4: GAMES ZONE"),
    ("games", "VIEW 4: GAMES ZONE", "VIEW 5: DICTIONARY ADMIN"),
    ("admin", "VIEW 5: DICTIONARY ADMIN", "VIEW 6: TELEMETRY"),
    ("performance", "VIEW 6: TELEMETRY", "VIEW 7: USER PROFILE"),
    ("profile", "VIEW 7: USER PROFILE", "RIGHT COLUMN"),
]


def extract(text: str, start: str, end: str) -> str:
    i = text.index(f"<!-- {start}")
    j = text.index(f"<!-- {end}", i)
    block = text[i:j]
    # drop outer ngIf wrapper line if present
    lines = block.splitlines()
    out = []
    for line in lines:
        if "searchMode ===" in line and "*ngIf" in line:
            continue
        if line.strip() == "</div>" and not out:
            continue
        out.append(line)
    # remove trailing closing div for ngIf
    while out and out[-1].strip() == "</div>":
        out.pop()
    return "\n".join(out).strip() + "\n"


def main() -> None:
    text = HTML.read_text(encoding="utf-8")
    for name, start, end in MARKERS:
        body = extract(text, start, end)
        body = body.replace("searchMode === 'basic'", "true")
        body = body.replace("(click)=\"setSearchMode(", "(click)=\"vm.setSearchMode(")
        # router-based: exploreWord already in facade
        dir_path = FEATURES / name
        dir_path.mkdir(parents=True, exist_ok=True)
        tpl = dir_path / f"{name}.component.html"
        tpl.write_text(body, encoding="utf-8")
        print("wrote", tpl.relative_to(ROOT.parent.parent))


if __name__ == "__main__":
    main()
