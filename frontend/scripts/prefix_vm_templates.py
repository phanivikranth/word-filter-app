"""Prefix TerseAppFacade bindings in feature templates with vm."""
import re
from pathlib import Path

FEATURES = Path(__file__).resolve().parents[1] / "src" / "app" / "features"

# Methods/properties that live on the facade (first segment before . or | or )
SKIP_PREFIX = {"true", "false", "null", "vm", "_", "let", "item", "i", "index", "rIdx", "col", "cell", "row", "key", "char", "w", "syn", "ant", "rhyme", "def", "ex", "pron", "link", "form", "opt", "log", "nameInput", "sugg", "res", "err", "detail", "status", "method", "path", "action", "time", "ip"}

PROP_RE = re.compile(
    r"(\*ngIf|\*ngFor|\[ngClass\]|\[ngModel\]|\(click\)|\(input\)|\(change\)|\(keyup\.enter\)|{{|\|)\s*=?[\"']?\(?([a-zA-Z_][\w]*)"
)


def prefix_expr(expr: str) -> str:
    """Add vm. to facade members in a short expression."""
    if expr.strip().startswith("vm."):
        return expr

    def repl(m: re.Match) -> str:
        word = m.group(0)
        if word in SKIP_PREFIX:
            return word
        if word in ("titlecase", "uppercase", "slice", "number", "json"):
            return word
        return f"vm.{word}"

    # property access at start
    parts = re.split(r"(\|\s*\w+)", expr)
    out = []
    for part in parts:
        if part.startswith("|"):
            out.append(part)
            continue
        tokens = re.findall(r"[a-zA-Z_][\w]*|\S+", part)
        rebuilt = []
        for tok in tokens:
            if re.match(r"^[a-zA-Z_]\w*$", tok) and tok not in SKIP_PREFIX and tok not in (
                "Math",
                "String",
                "Number",
                "Array",
            ):
                if not rebuilt or rebuilt[-1] != "vm.":
                    rebuilt.append(f"vm.{tok}")
                else:
                    rebuilt.append(tok)
            else:
                rebuilt.append(tok)
        out.append("".join(rebuilt) if rebuilt else part)
    return "".join(out)


def process_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # ngModel
    text = re.sub(
        r'\[\(ngModel\)\]="([^"]+)"',
        lambda m: f'[(ngModel)]="vm.{m.group(1).split(".")[0]}"' if not m.group(1).startswith("vm.") else m.group(0),
        text,
    )
    text = re.sub(
        r'\[ngModel\]="([^"]+)"',
        lambda m: f'[ngModel]="vm.{m.group(1)}"' if not m.group(1).startswith("vm.") else m.group(0),
        text,
    )
    # *ngIf="foo"
    def ngif_repl(m):
        cond = m.group(1).strip()
        if cond.startswith("vm.") or cond.startswith("!vm."):
            return m.group(0)
        if cond.startswith("!"):
            return f'*ngIf="!vm.{cond[1:]}"'
        return f'*ngIf="vm.{cond}"'

    text = re.sub(r'\*ngIf="([^"]+)"', ngif_repl, text)
    # (click)="method(
    text = re.sub(
        r'\(click\)="([a-zA-Z]\w*)',
        lambda m: m.group(0) if m.group(1).startswith("vm.") else f'(click)="vm.{m.group(1)}',
        text,
    )
    text = re.sub(
        r'\(keyup\.enter\)="([a-zA-Z]\w*)',
        lambda m: m.group(0) if m.group(1).startswith("vm.") else f'(keyup.enter)="vm.{m.group(1)}',
        text,
    )
    text = re.sub(
        r'\(input\)="([a-zA-Z]\w*)',
        lambda m: m.group(0) if m.group(1).startswith("vm.") else f'(input)="vm.{m.group(1)}',
        text,
    )
    text = re.sub(
        r'\(change\)="([a-zA-Z]\w*)',
        lambda m: m.group(0) if m.group(1).startswith("vm.") else f'(change)="vm.{m.group(1)}',
        text,
    )
    # {{ expr }}
    def mustache(m):
        inner = m.group(1).strip()
        if inner.startswith("vm.") or "|" in inner and "vm." in inner:
            return m.group(0)
        first = inner.split("|")[0].strip().split(".")[0]
        if first in SKIP_PREFIX or first[0].isupper():
            return m.group(0)
        return "{{ vm." + inner + " }}"

    text = re.sub(r"\{\{\s*([^}]+)\s*\}\}", mustache, text)
    # [disabled]="isSearching"
    text = re.sub(
        r'\[disabled\]="([a-zA-Z]\w*)"',
        lambda m: f'[disabled]="vm.{m.group(1)}"' if not m.group(1).startswith("vm.") else m.group(0),
        text,
    )
    path.write_text(text, encoding="utf-8")


def main():
    for html in FEATURES.glob("*/*.component.html"):
        process_file(html)
        print("patched", html.name)


if __name__ == "__main__":
    main()
