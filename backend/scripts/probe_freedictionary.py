import requests
from bs4 import BeautifulSoup
from pathlib import Path

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

WORDS = ["apple", "scherenschnitte", "Feldenkrais", "knaidel", "cymotrichous", "xyzzynotfound"]
OUT = "scripts/probe_out.txt"

lines = []
for word in WORDS:
    r = requests.get(f"https://www.thefreedictionary.com/{word}", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "lxml")
    lines.append(f"=== {word} {r.status_code} ===")
    lines.append(f"title: {(soup.title.string or '')[:100]}")
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        lines.append(f"meta: {(meta.get('content') or '')[:200]}")

    definition = soup.select_one("#Definition")
    if definition:
        text = definition.get_text(" ", strip=True)
        lines.append(f"#Definition: {text[:400]}")

    for sel in ["#MainTxt", "#wtn", ".encyc", "#Encyclopedia", "#trans"]:
        el = soup.select_one(sel)
        if el:
            t = el.get_text(" ", strip=True)
            if t:
                lines.append(f"{sel}: {t[:250]}")
    lines.append("")

Path(__file__).resolve().parent.joinpath("probe_out.txt").write_text("\n".join(lines), encoding="utf-8")
print("written probe_out.txt")
