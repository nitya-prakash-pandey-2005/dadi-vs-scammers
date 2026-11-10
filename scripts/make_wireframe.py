"""Draws docs/design/wireframe.svg: a low-fidelity wireframe of Dadi's main screens and the user flow between them.

Run: uv run --no-project python scripts/make_wireframe.py
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

W, H = 1600, 1200
INK, MUTED, LINE, FILL, CARD, BG = "#232336", "#6b6b80", "#9a9aae", "#e6e6ee", "#ffffff", "#f6f6fa"
ACCENT, ACCENT2 = "#d6337f", "#7c4ddb"
FONT = "'Segoe UI', Inter, 'Helvetica Neue', Arial, sans-serif"
MONO = "'Cascadia Mono', Consolas, 'JetBrains Mono', monospace"

out: list[str] = []


def t(x, y, s, size=12, weight=400, fill=INK, anchor="start", font=FONT, italic=False):
    style = ' font-style="italic"' if italic else ""
    out.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{style}>{escape(s)}</text>')


def r(x, y, w, h, fill=FILL, stroke="none", rx=6, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def lines(x, y, w, n, gap=9, h=4):
    """Grey placeholder text lines."""
    for i in range(n):
        ww = w if i < n - 1 else w * 0.6
        r(x, y + i * gap, ww, h, fill="#d3d3de", rx=2)


def card(x, y, w, h, title, sub=None):
    r(x, y, w, h, fill=CARD, stroke=LINE, rx=8)
    t(x + 10, y + 18, title, 11.5, 600)
    if sub:
        t(x + w - 10, y + 18, sub, 10, 400, MUTED, "end")


def chip(x, y, s, fill="#f1e4ff", ink=ACCENT2, w=None):
    w = w or (len(s) * 6.2 + 14)
    r(x, y, w, 17, fill=fill, rx=8.5)
    t(x + w / 2, y + 12.5, s, 9.5, 500, ink, "middle")
    return w


def button(x, y, w, s, primary=False):
    r(x, y, w, 24, fill=ACCENT if primary else CARD, stroke="none" if primary else LINE, rx=7)
    t(x + w / 2, y + 16, s, 10.5, 600, "#fff" if primary else INK, "middle")


def frame(x, y, w, h, n, title, note):
    r(x, y, w, h, fill=CARD, stroke=INK, rx=12, sw=1.5)
    r(x, y, w, 26, fill="#ececf3", rx=12)
    r(x, y + 14, w, 12, fill="#ececf3", rx=0)
    for i, c in enumerate(("#ff6b6b", "#ffc145", "#3ecf8e")):
        out.append(f'<circle cx="{x + 14 + i * 13}" cy="{y + 13}" r="4" fill="{c}"/>')
    t(x + 58, y + 17.5, f"{n} · {title}", 12, 700)
    t(x + w - 12, y + 17.5, note, 10, 400, MUTED, "end")


def sidebar(x, y, h, active):
    r(x, y, 104, h, fill="#f3f3f8", rx=0)
    out.append(f'<circle cx="{x + 16}" cy="{y + 18}" r="8" fill="url(#lg)"/>')
    t(x + 30, y + 22, "Dadi vs Scammers", 9.5, 700)
    items = ["Live call", "Check a message", "Calls & reports", "Scam intelligence", "Scam ring radar", "AI-vs-AI arena"]
    for i, s in enumerate(items):
        yy = y + 46 + i * 22
        if s == active:
            r(x + 6, yy - 12, 92, 18, fill="#e4dcf7", rx=5)
        t(x + 14, yy, s, 9.5, 600 if s == active else 400, INK if s == active else MUTED)


def arrow(points, label=None, lx=None, ly=None, color=ACCENT, dash=None, anchor="middle"):
    d = "M" + " L".join(f"{px} {py}" for px, py in points)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    mk = "url(#ah)" if color == ACCENT else "url(#ahg)"
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{da} marker-end="{mk}" stroke-linejoin="round"/>')
    if label:
        lw = len(label) * 6.1 + 14
        bx = lx - lw / 2 if anchor == "middle" else lx - 7
        r(bx, ly - 13, lw, 19, fill=BG, stroke=color, rx=9.5, sw=1)
        t(bx + lw / 2, ly + 1, label, 10.5, 600, color, "middle")


# ---------------------------------------------------------------- canvas
out.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
t(40, 42, "Dadi vs Scammers: wireframe of the main screens and the user flow", 20, 700)
t(40, 64, "Low fidelity. Boxes are cards, grey bars are text. Desktop has a sidebar, phones get bottom tabs; every screen is reachable from both.", 12, 400, MUTED)
# legend
arrow([(1236, 40), (1286, 40)])
t(1294, 44, "flow of a call / its data", 11, 400, INK)
arrow([(1236, 62), (1286, 62)], color=LINE, dash="5 4")
t(1294, 66, "same screen at 390 px", 11, 400, INK)

# ---------------------------------------------------------------- 1 · Live call (desktop)
AX, AY, AW, AH = 40, 110, 800, 480
frame(AX, AY, AW, AH, 1, "Live call", "/#/app · desktop 1440 px")
sidebar(AX, AY + 26, AH - 26, "Live call")
cx = AX + 116
r(cx, AY + 34, AW - 128, 22, fill="#f3f3f8", rx=5)
t(cx + 8, AY + 49, "Live scam line", 10.5, 700)
chip(AX + AW - 112, AY + 37, "● Gnani live", "#dcf7ea", "#0f8a5f", 96)
t(cx, AY + 76, "Don't block scammers. Route them to Dadi.", 13, 700)
lines(cx, AY + 84, 360, 2)
# phone panel
px, py, pw, ph = cx, AY + 108, 220, 360
r(px, py, pw, ph, fill=CARD, stroke=ACCENT, rx=10, sw=1.4)
t(px + 10, py + 17, "PHONE PANEL", 9.5, 700, ACCENT, font=MONO)
chip(px + pw - 72, py + 6, "Line idle", "#eeeef3", MUTED, 62)
out.append(f'<circle cx="{px + pw / 2}" cy="{py + 66}" r="30" fill="url(#lg)"/>')
t(px + pw / 2, py + 71, "KD", 15, 700, "#fff", "middle")
t(px + pw / 2, py + 116, "Kamla Devi", 12.5, 700, INK, "middle")
t(px + pw / 2, py + 131, "Kanpur · Hinglish · auto language", 9.5, 400, MUTED, "middle")
button(px + 12, py + 142, pw - 24, "Call Dadi (mic) / replay", True)
t(px + 12, py + 186, "Dadi's mission", 10, 600)
for i, s in enumerate(["Free play", "UPI", "Account", "WhatsApp", "Name+badge"]):
    r(px + 12 + (i % 3) * 66, py + 193 + (i // 3) * 21, 62, 17, fill="#e4dcf7" if i == 1 else "#f1f1f6", rx=5)
    t(px + 43 + (i % 3) * 66, py + 205 + (i // 3) * 21, s, 9, 500, INK, "middle")
t(px + 12, py + 254, "Who picks up", 10, 600)
for i, s in enumerate(["Auto", "Dadi", "Paati", "Thakuma", "Ajji", "Ammamma"]):
    r(px + 12 + (i % 3) * 66, py + 261 + (i // 3) * 21, 62, 17, fill="#e4dcf7" if i == 0 else "#f1f1f6", rx=5)
    t(px + 43 + (i % 3) * 66, py + 273 + (i // 3) * 21, s, 9, 500, INK, "middle")
t(px + 12, py + 322, "Line: earphones / speaker · 8 kHz", 9.5, 400, MUTED)
t(px + 12, py + 338, "Hang up → report", 9.5, 600, ACCENT)
# war room
wx = px + pw + 12
ww = AX + AW - 12 - wx
t(wx, py - 4, "WAR ROOM (updates live)", 9.5, 700, ACCENT2, font=MONO)
c1 = (ww - 8) / 2
card(wx, py, c1, 82, "Scammer ka time barbaad")
t(wx + 10, py + 60, "0:00", 30, 700, ACCENT)
lines(wx + 92, py + 44, c1 - 104, 2)
card(wx + c1 + 8, py, c1, 82, "Scam type", "confidence")
chip(wx + c1 + 18, py + 30, "Digital arrest 98%", "#ffe0ec", ACCENT, 120)
r(wx + c1 + 18, py + 60, c1 - 20, 6, fill="#ececf3", rx=3)
r(wx + c1 + 18, py + 60, (c1 - 20) * 0.9, 6, fill=ACCENT2, rx=3)
card(wx, py + 92, c1, 160, "Live transcript", "Prisma")
for i in range(5):
    right = i % 2 == 1
    bw = c1 * (0.55 if right else 0.62)
    bx = wx + c1 - 10 - bw if right else wx + 10
    r(bx, py + 122 + i * 25, bw, 19, fill="#efe6fb" if right else "#f1f1f6", rx=6)
t(wx + 10, py + 247, "scammer left · Dadi right", 9, 400, MUTED)
card(wx + c1 + 8, py + 92, c1, 96, "Intel captured", "regex + LLM")
chip(wx + c1 + 18, py + 116, "UPI rathore.cbi@okaxis ✓", "#ffe0ec", ACCENT, 150)
chip(wx + c1 + 18, py + 138, "phone 98765 43210", "#ffe0ec", ACCENT, 112)
chip(wx + c1 + 136, py + 138, "AnyDesk", "#ffe0ec", ACCENT, 56)
chip(wx + c1 + 18, py + 160, "CBI · Vijay Rathore", "#eeeef3", INK, 116)
card(wx + c1 + 8, py + 196, c1, 56, "Mission: UPI", "complete ✓")
lines(wx + c1 + 18, py + 32 + 196, c1 - 30, 2)
card(wx, py + 262, c1, 98, "Red flags (with quotes)", "4")
for i in range(3):
    t(wx + 10, py + 296 + i * 21, f"0:{8 + i * 13:02d}", 9, 400, MUTED, font=MONO)
    r(wx + 40, py + 289 + i * 21, c1 - 52, 5, fill="#d3d3de", rx=2)
    r(wx + 40, py + 297 + i * 21, (c1 - 52) * 0.6, 4, fill="#e3e3ea", rx=2)
r(wx + c1 + 8, py + 262, c1, 98, fill="#fff3f8", stroke=ACCENT, rx=8, sw=1.3)
t(wx + c1 + 18, py + 280, "Repeat caller! same voice 0.956", 11, 700, ACCENT)
t(wx + c1 + 18, py + 298, "Gnani voice-clone fingerprint", 9.5, 400, MUTED)
t(wx + c1 + 18, py + 312, "matched an earlier call", 9.5, 400, MUTED)
button(wx + c1 + 18, py + 324, 108, "Open earlier call")

# ---------------------------------------------------------------- 1m · Live call on a phone
BX, BY, BW, BH = 872, 110, 214, 480
r(BX, BY, BW, BH, fill=CARD, stroke=INK, rx=26, sw=1.5)
r(BX + 78, BY + 8, 58, 8, fill="#d9d9e3", rx=4)
t(BX + BW / 2, BY + BH + 20, "1 · Live call at 390 px", 12, 700, INK, "middle")
out.append(f'<circle cx="{BX + 22}" cy="{BY + 34}" r="9" fill="url(#lg)"/>')
t(BX + 38, BY + 38, "Live scam line", 10.5, 700)
chip(BX + BW - 64, BY + 26, "Demo", "#dcf7ea", "#0f8a5f", 52)
lines(BX + 14, BY + 56, BW - 28, 3)
r(BX + 14, BY + 90, (BW - 28) / 2, 22, fill="#e4dcf7", rx=6)
t(BX + 14 + (BW - 28) / 4, BY + 105, "Phone", 10, 700, INK, "middle")
t(BX + 14 + 3 * (BW - 28) / 4, BY + 105, "War room", 10, 500, MUTED, "middle")
r(BX + 14, BY + 120, BW - 28, 290, fill=CARD, stroke=ACCENT, rx=10, sw=1.2)
out.append(f'<circle cx="{BX + BW / 2}" cy="{BY + 170}" r="28" fill="url(#lg)"/>')
t(BX + BW / 2, BY + 222, "Kamla Devi", 12, 700, INK, "middle")
button(BX + 26, BY + 236, BW - 52, "Call Dadi", True)
for i in range(4):
    r(BX + 26, BY + 276 + i * 24, BW - 52, 16, fill="#f1f1f6", rx=5)
r(BX, BY + BH - 56, BW, 56, fill="#f3f3f8", rx=0)
r(BX, BY + BH - 30, BW, 30, fill="#f3f3f8", rx=26)
for i, s in enumerate(["Call", "Check", "Intel", "Rings", "Arena"]):
    t(BX + 22 + i * 42.5, BY + BH - 22, s, 9, 700 if i == 0 else 400, ACCENT if i == 0 else MUTED, "middle")
    r(BX + 15 + i * 42.5, BY + BH - 46, 14, 12, fill=ACCENT if i == 0 else "#c9c9d6", rx=3)
arrow([(AX + AW, AY + 240), (BX - 2, AY + 240)], color=LINE, dash="5 4")

# ---------------------------------------------------------------- 2 · Report
CX, CY, CW, CH = 1124, 110, 436, 480
frame(CX, CY, CW, CH, 2, "Report (complaint draft)", "/#/app/report/<id>")
x0, w0 = CX + 12, CW - 24
t(x0, CY + 46, "Suspected scam call: complaint draft", 12.5, 700)
button(CX + CW - 236, CY + 54, 60, "Calls")
button(CX + CW - 170, CY + 54, 82, "Evidence pack")
button(CX + CW - 82, CY + 54, 70, "Print/PDF", True)
t(x0, CY + 70, "Call 2c57… · Kamla Devi answered", 9.5, 400, MUTED)
r(x0, CY + 86, w0, 22, fill="#fff8e1", stroke="#e0b84a", rx=6)
t(x0 + 8, CY + 101, "Simulated scam call · review before filing", 9.5, 500, "#8a6a10")
card(x0, CY + 116, w0, 48, "Summary")
lines(x0 + 10, CY + 140, w0 - 20, 2)
card(x0, CY + 172, w0, 62, "Call recording (evidence)", "SHA-256 SEALED")
r(x0 + 10, CY + 192, w0 - 20, 16, fill="#f1f1f6", rx=8)
for i in range(40):
    hh = 3 + (i * 7 % 9)
    r(x0 + 30 + i * 9, CY + 200 - hh / 2, 4, hh, fill=ACCENT2, rx=1)
t(x0 + 10, CY + 224, "6f63b4d7b6a9c2d5…  left = caller, right = Dadi", 9, 400, MUTED, font=MONO)
card(x0, CY + 242, w0 / 2 - 4, 70, "Incident")
lines(x0 + 10, CY + 266, w0 / 2 - 24, 4)
card(x0 + w0 / 2 + 4, CY + 242, w0 / 2 - 4, 70, "Claimed identity")
lines(x0 + w0 / 2 + 14, CY + 266, w0 / 2 - 24, 3)
card(x0, CY + 320, w0, 54, "Suspect identifiers")
chip(x0 + 10, CY + 346, "rathore.cbi@okaxis", "#ffe0ec", ACCENT, 118)
chip(x0 + 134, CY + 346, "9876543210", "#ffe0ec", ACCENT, 80)
chip(x0 + 220, CY + 346, "AnyDesk", "#ffe0ec", ACCENT, 60)
card(x0, CY + 382, w0 / 2 - 4, 86, "Red flags + timeline")
lines(x0 + 10, CY + 406, w0 / 2 - 24, 6)
card(x0 + w0 / 2 + 4, CY + 382, w0 / 2 - 4, 86, "Where to report")
for i, s in enumerate(["cybercrime.gov.in", "Helpline 1930", "Sanchar Saathi Chakshu"]):
    t(x0 + w0 / 2 + 14, CY + 418 + i * 17, s, 10, 600, "#1f7fb8")

# ---------------------------------------------------------------- 3 · Scam ring radar
DX, DY, DW, DH = 40, 690, 470, 470
frame(DX, DY, DW, DH, 3, "Scam ring radar", "/#/app/rings")
x0, w0 = DX + 12, DW - 24
t(x0, DY + 46, "Same mule ID or same voice = same gang", 12, 700)
button(DX + DW - 132, DY + 34, 120, "Mule-ID feed (CSV)")
for i, (n, s) in enumerate([("5", "scam calls"), ("1", "ring found"), ("3", "calls linked"), ("4/5", "known AI voice")]):
    t(x0 + i * 112, DY + 86, n, 18, 700, ACCENT if i == 1 else INK)
    t(x0 + i * 112, DY + 101, s, 9.5, 400, MUTED)
card(x0, DY + 112, w0, 190, "Who is behind the calls", "— mule ID   - - voice")
nodes = [(DX + DW / 2, DY + 160, "Call 3 · KBC prize"), (DX + DW / 2 - 90, DY + 248, "Vijay Rathore · CBI"), (DX + DW / 2 + 90, DY + 248, "Rahul · SBI")]
for (ax, ay, _), (bx, by, _) in [(nodes[0], nodes[1]), (nodes[0], nodes[2]), (nodes[1], nodes[2])]:
    out.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="#22a6c8" stroke-width="2" stroke-dasharray="6 4"/>')
t(DX + DW / 2, DY + 262, "same voice 0.96", 9.5, 600, "#1d8fae", "middle")
for nx, ny, s in nodes:
    out.append(f'<circle cx="{nx}" cy="{ny}" r="13" fill="{ACCENT}"/>')
    t(nx, ny + 28, s, 9.5, 600, INK, "middle")
out.append(f'<circle cx="{DX + 60}" cy="{DY + 186}" r="10" fill="#fff" stroke="{LINE}" stroke-width="2"/>')
t(DX + 60, DY + 210, "Suresh (no link)", 9.5, 400, MUTED, "middle")
card(x0, DY + 312, w0, 146, "Ring 1: 3 calls")
t(x0 + 10, DY + 344, "Names used", 9, 400, MUTED)
chip(x0 + 10, DY + 350, "Rahul", "#fff1cc", "#8a6a10", 46)
chip(x0 + 62, DY + 350, "Vijay Rathore", "#fff1cc", "#8a6a10", 86)
t(x0 + 10, DY + 384, "Mule IDs to freeze", 9, 400, MUTED)
chip(x0 + 10, DY + 390, "9000011112", "#ffe0ec", ACCENT, 76)
chip(x0 + 92, DY + 390, "kbc.price2026@upi", "#ffe0ec", ACCENT, 112)
t(x0 + 10, DY + 424, "Scripts", 9, 400, MUTED)
chip(x0 + 10, DY + 430, "Digital arrest", "#eeeef3", INK, 84)
chip(x0 + 100, DY + 430, "KYC block", "#eeeef3", INK, 66)
button(x0 + w0 - 196, DY + 426, 60, "Report")
button(x0 + w0 - 130, DY + 426, 60, "Report")
button(x0 + w0 - 64, DY + 426, 58, "Report")

# ---------------------------------------------------------------- 4 · Arena
EX, EY, EW, EH = 550, 690, 470, 470
frame(EX, EY, EW, EH, 4, "AI-vs-AI arena", "/#/app/arena · testing")
x0, w0 = EX + 12, EW - 24
t(x0, EY + 46, "AI scammer (Timbre voice) calls AI Dadi", 12, 700)
card(x0, EY + 58, w0, 92, "Match setup")
for i, s in enumerate(["Scam script", "Scammer voice", "Noise: 10 dB babble", "Mission", "Grandmother", "Turns"]):
    xx, yy = x0 + 10 + (i % 3) * 146, EY + 82 + (i // 3) * 30
    r(xx, yy, 138, 22, fill="#f1f1f6", stroke="#d3d3de", rx=5)
    t(xx + 8, yy + 15, s + " ▾", 9.5, 500, INK)
button(x0, EY + 158, 150, "Start match", True)
t(x0 + 162, EY + 174, "8 kHz phone band · Prisma transcribes every line", 9.5, 400, MUTED)
card(x0, EY + 192, w0 * 0.62, 208, "Call transcript", "CER per line")
for i in range(6):
    right = i % 2 == 1
    bw = w0 * 0.62 * 0.62
    bx = x0 + w0 * 0.62 - 10 - bw if right else x0 + 10
    r(bx, EY + 220 + i * 29, bw, 22, fill="#efe6fb" if right else "#f1f1f6", rx=6)
    if not right:
        t(bx + bw + 6, EY + 235 + i * 29, f"CER .{10 + i * 3}", 8.5, 400, MUTED, font=MONO)
mx = x0 + w0 * 0.62 + 8
mw = w0 - w0 * 0.62 - 8
card(mx, EY + 192, mw, 150, "Scores")
for i, (n, s) in enumerate([("0", "persona breaks"), ("0", "'I am a bot' admissions"), ("125–260 ms", "Prisma per line"), ("0.13", "CER (8 Nov)")]):
    t(mx + 10, EY + 226 + i * 30, n, 12.5, 700, ACCENT if i < 2 else INK)
    t(mx + 10, EY + 239 + i * 30, s, 8.5, 400, MUTED)
r(mx, EY + 350, mw, 50, fill="#fff3f8", stroke=ACCENT, rx=8, sw=1.3)
t(mx + 10, EY + 368, "Voice match 0.956", 11, 700, ACCENT)
t(mx + 10, EY + 385, "Dadi teases him in character", 9, 400, MUTED)
card(x0, EY + 410, w0, 48, "Noise benchmark", "clean · 20 · 10 · 0 dB")
lines(x0 + 10, EY + 434, w0 - 20, 2)

# ---------------------------------------------------------------- 5 · Check a message
FX, FY, FW, FH = 1060, 690, 240, 470
frame(FX, FY, FW, FH, 5, "Check a message", "")
x0, w0 = FX + 12, FW - 24
t(x0, FY + 46, "Paste an SMS / WhatsApp", 11.5, 700)
r(x0, FY + 56, w0, 78, fill="#fbfbfd", stroke="#c9c9d6", rx=6)
lines(x0 + 8, FY + 68, w0 - 16, 4)
chip(x0, FY + 142, "Sample: digital arrest", "#eeeef3", INK, 130)
button(x0, FY + 166, w0, "Check", True)
r(x0, FY + 200, w0, 46, fill="#ffe0ec", stroke=ACCENT, rx=8)
t(x0 + 10, FY + 218, "Verdict: SCAM", 12, 700, ACCENT)
t(x0 + 10, FY + 236, "Electricity bill disconnection", 9.5, 500, INK)
card(x0, FY + 254, w0, 58, "Red flags")
lines(x0 + 10, FY + 278, w0 - 20, 3)
card(x0, FY + 320, w0, 44, "IDs found")
chip(x0 + 10, FY + 340, "UPI", "#ffe0ec", ACCENT, 36)
chip(x0 + 52, FY + 340, "link", "#ffe0ec", ACCENT, 38)
card(x0, FY + 372, w0, 40, "The true fact")
lines(x0 + 10, FY + 394, w0 - 20, 1)
card(x0, FY + 420, w0, 40, "Dadi's reply (copy)")
lines(x0 + 10, FY + 442, w0 - 20, 1)

# ---------------------------------------------------------------- 6 · Intelligence
GX, GY, GW, GH = 1320, 690, 240, 470
frame(GX, GY, GW, GH, 6, "Intelligence", "")
x0, w0 = GX + 12, GW - 24
t(x0, GY + 46, "What scammers do", 11.5, 700)
for i, (n, s) in enumerate([("5", "calls"), ("7", "mule IDs")]):
    t(x0 + i * 100, GY + 74, n, 17, 700, INK)
    t(x0 + i * 100, GY + 88, s, 9.5, 400, MUTED)
card(x0, GY + 98, w0, 110, "Who they pretend to be")
for i, f in enumerate([0.9, 0.6, 0.45, 0.3]):
    r(x0 + 10, GY + 124 + i * 20, (w0 - 20) * f, 10, fill=ACCENT2 if i == 0 else "#c7b6ef", rx=3)
card(x0, GY + 216, w0, 70, "Scripts + pressure tactics")
lines(x0 + 10, GY + 240, w0 - 20, 4)
card(x0, GY + 294, w0, 164, "Freeze list for banks")
for i in range(5):
    r(x0 + 10, GY + 324 + i * 18, w0 - 20, 14, fill="#f1f1f6" if i else "#e4dcf7", rx=3)
button(x0 + 10, GY + 422, 60, "CSV")
button(x0 + 76, GY + 422, 60, "JSON")

# ---------------------------------------------------------------- flow arrows
# 1 → 2: hang up → report (top lane)
arrow([(AX + 640, AY), (AX + 640, 90), (CX + 300, 90), (CX + 300, CY - 2)], "hang up → complaint draft + sealed recording", 780, 94)
# 1 → 3: links calls
arrow([(AX + 220, AY + AH), (AX + 220, DY - 2)], "mule ID or voice fingerprint links calls", AX + 220, 640)
# 4 → 3
arrow([(EX, EY + 250), (DX + DW + 2, DY + 250)])
t((EX + DX + DW) / 2, EY + 238, "arena", 10.5, 600, ACCENT, "middle")
t((EX + DX + DW) / 2, EY + 268, "calls", 10.5, 600, ACCENT, "middle")
# 4 → 2: every call has a report
arrow([(EX + 380, EY), (EX + 380, 650), (CX + 120, 650), (CX + 120, CY + CH + 2)], "every call, live or arena, gets a report", EX + 600, 654)
# 2 → 6: reports feed intelligence
arrow([(CX + 380, CY + CH), (CX + 380, GY - 2)], "IDs → freeze list", CX + 380, 628)

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="wt">'
    '<title id="wt">Dadi vs Scammers wireframe: live call, report, scam ring radar, arena, message checker, intelligence</title>'
    '<defs>'
    '<linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff5aa5"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient>'
    f'<marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{ACCENT}"/></marker>'
    f'<marker id="ahg" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{LINE}"/></marker>'
    '</defs>' + "\n".join(out) + "</svg>\n"
)
dest = Path(__file__).resolve().parents[1] / "docs" / "design" / "wireframe.svg"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(svg, encoding="utf-8")
print(dest)
