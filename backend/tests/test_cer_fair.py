"""The arena's error rate must measure what Prisma got wrong, not spelling choices it got right."""

from dadi.arena import cer


def test_number_words_and_digits_count_as_the_same():
    # live arena, 10 Nov: Prisma wrote the digits as words; that is not an error
    assert cer("मैंने 2035 नहीं, OTP माँगा है", "मैंने दो शून्य तीन पांच नहीं, OTP मांगा है") < 0.05


def test_nukta_and_chandrabindu_variants_are_not_errors():
    assert cer("ज़रा ज़ोर से बोलिए, माँ", "जरा जोर से बोलिए, मां") == 0.0


def test_currency_symbols_are_ignored():
    assert cer("बस ₹980 का हिसाब", "बस 980 का हिसाब") == 0.0


def test_romanised_hindi_heard_in_devanagari_gets_no_score():
    # the AI scammer sometimes writes Hindi in Roman letters; Prisma rightly answers in Devanagari
    assert cer("Main Rahul bol raha hu, aapka account block hone wala hai", "मैं राहुल बोल रहा हूँ, आपका account block होने वाला है") is None


def test_real_errors_still_count():
    assert cer("UPI ID likhiye: rathore.cbi@okaxis", "UPI ID likhiye: rathod.cbi@okaxis") > 0.0
    assert cer("abcd", "abxd") == 0.25 and cer("Hello, World!", "hello world") == 0.0
