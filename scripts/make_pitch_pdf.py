"""PITCH.md -> PITCH.pdf: one A4 page, logo on top, every link clickable.

Run from the repo root (re-run after putting the live demo / video links into PITCH.md):

    uv run --no-project --with markdown --with pypdf python scripts/make_pitch_pdf.py

Bare URLs (https://...) pasted into PITCH.md become links too. If the text no longer fits on one page, the font
shrinks in 0.2 pt steps until it does (the script says which size it used). Needs Google Chrome.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "PITCH.md", ROOT / "PITCH.pdf"
LOGO = ROOT / "docs" / "brand" / "logo.svg"
CHROME_CANDIDATES = [
    os.environ.get("CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
    shutil.which("chrome") or "",
]

CSS = """
@page { size: A4; margin: 11mm 13mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font-family: "Segoe UI", "Nirmala UI", "Noto Sans", "Noto Sans Devanagari", Arial, sans-serif;
       font-size: __PT__pt; line-height: 1.36; color: #1d1b2e; }
header { display: flex; align-items: center; gap: 10px; padding-bottom: 6px; margin-bottom: 6px;
         border-bottom: 2px solid #e9e1fb; }
header svg { width: 40px; height: 40px; flex: none; }
h1 { font-size: 1.62em; line-height: 1.15; margin: 0; letter-spacing: -0.01em; }
h1 small { display: block; font-size: .5em; font-weight: 600; letter-spacing: .14em; text-transform: uppercase;
           color: #c0306f; margin-bottom: 2px; }
h2 { font-size: 1.14em; margin: .7em 0 .25em; padding-left: 7px; border-left: 3px solid #d6337f; color: #2a1f4a; }
p { margin: .28em 0; }
strong { color: #14112a; }
a { color: #5b35c4; text-decoration: none; border-bottom: 1px solid #cdbdf3; }
em { color: #4a4560; }
p:first-of-type, p:nth-of-type(2) { background: #f7f3ff; padding: 4px 7px; border-radius: 5px; }
"""


def chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    sys.exit("Google Chrome not found; set CHROME=<path to chrome>")


def build_html(md_text: str, pt: float) -> str:
    # bare URLs -> autolinks (skip URLs already inside a markdown link or <...>)
    md_text = re.sub(r"(?<![(<\[\"'])\b(https?://[^\s)<>\]]+[^\s)<>\].,;:])", r"<\1>", md_text)
    lines = md_text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("# ") else "Pitch"
    body = markdown.markdown("\n".join(lines[1:]), extensions=["extra", "sane_lists"])
    body = body.replace("<a href=", '<a target="_blank" href=')
    logo = LOGO.read_text(encoding="utf-8")
    logo = re.sub(r"<title[^>]*>.*?</title>", "", logo, flags=re.S)
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
        f"<style>{CSS.replace('__PT__', f'{pt:.1f}')}</style></head><body>"
        f"<header>{logo}<h1><small>Dadi vs Scammers · Pukaar · Apni Awaaz</small>{title}</h1></header>"
        f"{body}</body></html>"
    )


def render(html: str, tmp: Path) -> int:
    page = tmp / "pitch.html"
    page.write_text(html, encoding="utf-8")
    pdf = tmp / "pitch.pdf"
    subprocess.run(
        [chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
         page.as_uri()],
        check=True, capture_output=True, timeout=120,
    )
    shutil.copyfile(pdf, OUT)
    shutil.copyfile(page, tmp / "last.html")
    return len(PdfReader(str(OUT)).pages)


def main() -> None:
    md_text = SRC.read_text(encoding="utf-8")
    pt = float(os.environ.get("PITCH_PT", "9.6"))
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        while True:
            pages = render(build_html(md_text, pt), tmp)
            if pages == 1 or pt <= 7.0:
                break
            pt = round(pt - 0.2, 1)
        if os.environ.get("PITCH_KEEP_HTML"):
            shutil.copyfile(tmp / "last.html", Path(os.environ["PITCH_KEEP_HTML"]))
    print(f"{OUT}: {pages} page(s) at {pt:.1f} pt")
    if pages != 1:
        sys.exit("PITCH.pdf is more than one page even at 7 pt: shorten PITCH.md")


if __name__ == "__main__":
    main()
