import requests
from bs4 import BeautifulSoup
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
WORDS = ["scherenschnitte", "Feldenkrais", "apple"]
lines = []
for word in WORDS:
    url = f"https://encyclopedia.thefreedictionary.com/{word}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "lxml")
    lines.append(f"=== {word} ===")
    lines.append(f"title: {(soup.title.string or '')[:120]}")
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        lines.append(f"meta: {(meta.get('content') or '')[:250]}")
    for sel in ["#Definition", "#MainTxt", "#wtn", "article", ".ds-list", "#content"]:
        el = soup.select_one(sel)
        if el:
            t = el.get_text(" ", strip=True)
            if len(t) > 30:
                lines.append(f"{sel}: {t[:500]}")
    lines.append("")
Path(__file__).resolve().parent.joinpath("probe_enc_out.txt").write_text("\n".join(lines), encoding="utf-8")
print("done")
