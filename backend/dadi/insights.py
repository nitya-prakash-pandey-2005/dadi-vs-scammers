"""Scam intelligence board + freeze list: what an insights portal for banks, telcos and police would show."""

from __future__ import annotations

import csv
import io
import re
from collections import Counter

from .numwords import words_to_digits

PSP_BANK = {
    "okaxis": "Axis Bank (Google Pay)", "oksbi": "SBI (Google Pay)", "okhdfcbank": "HDFC Bank (Google Pay)",
    "okicici": "ICICI Bank (Google Pay)", "ybl": "Yes Bank (PhonePe)", "ibl": "IndusInd Bank (PhonePe)",
    "axl": "Axis Bank (PhonePe)", "apl": "Axis Bank (Amazon Pay)", "upi": "BHIM (NPCI)", "paytm": "Paytm",
    "ptyes": "Yes Bank (Paytm)", "ptaxis": "Axis Bank (Paytm)", "pthdfc": "HDFC Bank (Paytm)", "ptsbi": "SBI (Paytm)",
    "sbi": "SBI", "icici": "ICICI Bank", "hdfcbank": "HDFC Bank", "axisbank": "Axis Bank", "kotak": "Kotak Mahindra Bank",
}
AGENCIES = {
    "CBI": ("cbi", "सीबीआई"), "ED": ("enforcement directorate", " ed ", "ईडी"), "RBI": ("rbi", "reserve bank", "आरबीआई"),
    "TRAI": ("trai", "ट्राई"), "Customs": ("customs", "कस्टम"), "Narcotics": ("narcotics", "ncb", "नारकोटिक्स"),
    "Police": ("police", "पुलिस", "காவல்"), "SBI": ("sbi", "state bank", "एसबीआई"), "HDFC": ("hdfc",), "ICICI": ("icici",),
    "FedEx": ("fedex", "फेडेक्स"), "DHL": ("dhl",), "Electricity board": ("electricity", "bijli", "बिजली"),
    "KBC": ("kbc", "kaun banega"), "Income Tax": ("income tax", "आयकर"),
}
_UNITS = {"lakh": 100_000, "lac": 100_000, "लाख": 100_000, "crore": 10_000_000, "करोड़": 10_000_000, "करोड": 10_000_000,
          "thousand": 1000, "hazaar": 1000, "hazar": 1000, "हजार": 1000, "हज़ार": 1000}


def rupees(text: str) -> int | None:
    t = words_to_digits(str(text)).lower()
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", t)
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    unit = next((v for k, v in _UNITS.items() if k in t[m.end():]), 1)
    return int(n * unit)


def agency_key(name: str) -> str:
    low = f" {name.lower()} "
    return next((k for k, keys in AGENCIES.items() if any(x in low for x in keys)), name.strip())


def _ids(intel: dict) -> list[tuple[str, str]]:
    return [(kind, str(v).lower()) for field, kind in (("upi_ids", "UPI"), ("phones", "phone"), ("accounts", "account"))
            for v in intel.get(field, [])]


def _bank(kind: str, value: str) -> str:
    return PSP_BANK.get(value.split("@")[-1], "") if kind == "UPI" else ""


def insights(calls: list[dict]) -> dict:
    agencies, types, flags, handles = Counter(), Counter(), Counter(), Counter()
    rupees_total, upis = 0, set()
    for c in calls:
        intel = c.get("intel") or {}
        agencies.update({agency_key(a) for a in intel.get("agencies_claimed", [])})
        if intel.get("scam_type") and intel["scam_type"] != "other":
            types[intel["scam_type"]] += 1
        flags.update({f["flag"] for f in intel.get("red_flags", [])})
        rupees_total += sum(rupees(a) or 0 for a in intel.get("amounts", []))
        upis.update(v for k, v in _ids(intel) if k == "UPI")
    handles.update(u.split("@")[-1] for u in upis)
    return {
        "calls": len(calls),
        "minutes_wasted": round(sum(float(c.get("wasted_seconds") or 0) for c in calls) / 60, 1),
        "rupees_demanded": rupees_total,
        "agencies": [{"name": k, "calls": n} for k, n in agencies.most_common(8)],
        "scam_types": [{"type": k, "calls": n} for k, n in types.most_common()],
        "red_flags": [{"flag": k, "calls": n} for k, n in flags.most_common(6)],
        "handles": [{"handle": h, "bank": PSP_BANK.get(h, ""), "ids": n} for h, n in handles.most_common()],
    }


def freeze_list(calls: list[dict], rings: dict) -> list[dict]:
    """One row per mule ID: which bank to alert, which calls and ring it came from, when it was first seen."""
    ring_of = {cid: n for n, r in enumerate(rings.get("rings", []), 1) for cid in r["calls"]}
    rows: dict[tuple[str, str], dict] = {}
    for c in sorted(calls, key=lambda c: c.get("started_at") or 0):
        intel = c.get("intel") or {}
        for kind, value in _ids(intel):
            row = rows.setdefault((kind, value), {"kind": kind, "id": value, "bank": _bank(kind, value), "calls": [],
                                                  "ring": None, "names": [], "first_seen": c.get("started_at")})
            row["calls"].append(c["id"])
            row["ring"] = row["ring"] or ring_of.get(c["id"])
            row["names"] = sorted(set(row["names"]) | set(intel.get("names", [])))
    return sorted(rows.values(), key=lambda r: (r["ring"] is None, -len(r["calls"]), r["kind"], r["id"]))


def freeze_csv(rows: list[dict]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["kind", "id", "bank", "ring", "calls", "names_used", "first_seen_unix"])
    for r in rows:
        w.writerow([r["kind"], r["id"], r["bank"], r["ring"] or "", " ".join(r["calls"]), "; ".join(r["names"]), r["first_seen"]])
    return out.getvalue()
