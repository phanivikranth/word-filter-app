"""Fix feature templates after split: root wrapper, orphan closing div, ngFor display."""
from pathlib import Path

FEATURES = Path(__file__).resolve().parents[1] / "src" / "app" / "features"

WRAPPERS = {
    "word-check": '<div class="flex flex-col gap-6 animate-fade-in">\n',
    "filters": '<div class="clay-card p-6 flex flex-col gap-6 animate-fade-in">\n',
    "puzzles": '<div class="clay-card p-6 flex flex-col gap-6 animate-fade-in">\n',
    "games": '<div class="clay-card p-6 flex flex-col gap-6 animate-fade-in">\n',
    "admin": '<div class="clay-card p-6 flex flex-col gap-6 animate-fade-in">\n',
    "performance": '<div class="clay-card p-6 flex flex-col gap-6 animate-fade-in">\n',
    "profile": '<div class="clay-card p-6 flex flex-col gap-6 animate-fade-in">\n',
}


def main() -> None:
    for name, open_tag in WRAPPERS.items():
        path = FEATURES / name / f"{name}.component.html"
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        # drop comment header lines at start
        while lines and (lines[0].strip().startswith("<!--") or not lines[0].strip()):
            lines.pop(0)
        text = "\n".join(lines).strip()
        # remove one orphan closing div at end (from removed *ngIf wrapper)
        if text.endswith("</div>"):
            text = text[: text.rfind("</div>")].rstrip()
        text = open_tag + text + "\n</div>\n"
        text = text.replace('[formGroup]="filterForm"', '[formGroup]="vm.filterForm"')
        text = text.replace("{{ vm.word }}", "{{ word }}")
        text = text.replace("*ngFor=\"let word of words\"", "*ngFor=\"let word of vm.words\"")
        text = text.replace("*ngFor=\"let word of interactiveWords\"", "*ngFor=\"let word of vm.interactiveWords\"")
        path.write_text(text, encoding="utf-8")
        print("fixed", path.name)


if __name__ == "__main__":
    main()
