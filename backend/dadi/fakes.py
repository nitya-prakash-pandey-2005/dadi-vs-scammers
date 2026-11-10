"""Fake personal data Dadi may read out. Every card number fails the Luhn check and every
Aadhaar number starts with 0 or 1 (real ones never do) AND fails the Verhoeff checksum,
so nothing Dadi says can ever match a real person's card or Aadhaar. Her deliberate first-read
mistake ("slip") is precomputed too and fails the same checks, so a slip can never land on a valid number."""

from __future__ import annotations

import random

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def luhn_valid(num: str) -> bool:
    if not num.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(num)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _luhn_check_digit(partial: str) -> int:
    for d in range(10):
        if luhn_valid(partial + str(d)):
            return d
    raise AssertionError("unreachable")


def verhoeff_valid(num: str) -> bool:
    if not num.isdigit():
        return False
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def _verhoeff_check_digit(partial: str) -> int:
    c = 0
    for i, ch in enumerate(reversed(partial)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return _INV[c]


def fake_card(seed) -> str:
    rng = random.Random(f"card-{seed}")
    body = "4" + "".join(str(rng.randint(0, 9)) for _ in range(14))
    good = _luhn_check_digit(body)
    bad = (good + rng.randint(1, 9)) % 10
    return body + str(bad)


def fake_aadhaar(seed) -> str:
    rng = random.Random(f"aadhaar-{seed}")
    body = rng.choice("01") + "".join(str(rng.randint(0, 9)) for _ in range(10))
    good = _verhoeff_check_digit(body)
    bad = (good + rng.randint(1, 9)) % 10
    return body + str(bad)


def fake_otp(seed) -> str:
    rng = random.Random(f"otp-{seed}")
    return "".join(str(rng.randint(0, 9)) for _ in range(6))


def slip(num: str, seed, still_invalid=lambda n: True) -> str:
    """Dadi's deliberate first-read mistake: one digit (never the first) changed, chosen so the result is
    still invalid. A free-form 'get one digit wrong' turned 1 in 9 fake cards into Luhn-valid numbers."""
    rng = random.Random(f"slip-{num}-{seed}")
    options = [num[:i] + d + num[i + 1:] for i in range(1, len(num)) for d in "0123456789" if d != num[i]]
    return rng.choice([n for n in options if still_invalid(n)])


def fake_wallet(seed) -> dict[str, str]:
    rng = random.Random(f"wallet-{seed}")
    w = {
        "card": fake_card(seed),
        "aadhaar": fake_aadhaar(seed),
        "otp": fake_otp(seed),
        "account": "0000" + "".join(str(rng.randint(0, 9)) for _ in range(7)),
        "bank": "State Bank, Civil Lines branch",
        "balance": "₹2,40,000",
    }
    w["card_slip"] = slip(w["card"], seed, lambda n: not luhn_valid(n))
    w["aadhaar_slip"] = slip(w["aadhaar"], seed, lambda n: not verhoeff_valid(n))  # first digit stays 0/1
    w["otp_slip"] = slip(w["otp"], seed)
    w["account_slip"] = slip(w["account"], seed)
    return w
