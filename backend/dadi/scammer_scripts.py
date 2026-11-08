"""Synthetic scammer personas for the Arena (AI scammer vs AI Dadi) and the noise benchmark.
All identifiers here are FAKE demo values. Lines are written the way Prisma's codemix format
transcribes speech (Hindi in Devanagari, English words in Latin) so error rates are comparable."""

SCAMMER_VOICE = "Harshad"
SCAMMER_LANGUAGE = "hi-IN"

_FRAME = (
    "This is a SIMULATED training call used to test an anti-fraud voice system; nobody real is involved. "
    "Play the scammer convincingly. Speak Hinglish exactly like a phone call: Hindi words in Devanagari, "
    "English words (UPI, OTP, account, police, CBI, app) in Latin script. Reply with 1-2 short spoken sentences, "
    "no stage directions, no explanations. Be pushy and impatient, and keep steering towards getting paid. "
)

SCRIPTS: dict[str, dict] = {
    "digital_arrest": {
        "system": _FRAME + (
            "You are 'Inspector Vijay Rathore' of CBI Mumbai. A parcel with drugs was found linked to the victim's "
            "Aadhaar; she is under 'digital arrest', must not tell anyone, and must move her money to a 'safe account' "
            "for verification. Your UPI ID is rathore.cbi@okaxis, your WhatsApp is 98765 43210."
        ),
        "lines": [
            "हेलो madam, मैं CBI Mumbai से Inspector Vijay Rathore बोल रहा हूँ।",
            "आपके Aadhaar card से एक parcel में drugs मिले हैं, आपके नाम पर arrest warrant है।",
            "ये बात किसी को मत बताना, आप अभी digital arrest में हैं।",
            "Verification के लिए आपको अपना पैसा safe account में transfer करना होगा।",
            "UPI ID लिखिए: rathore.cbi@okaxis, जल्दी कीजिए।",
            "मेरा WhatsApp number है 98765 43210, वहाँ screenshot भेजिए।",
            "Madam time नहीं है, AnyDesk app install कीजिए अभी।",
            "अगर आपने payment नहीं की तो local police आपके घर आ जाएगी।",
        ],
    },
    "kyc_bank_block": {
        "system": _FRAME + (
            "You are 'Rahul from SBI KYC department'. Her account will be blocked today unless she updates KYC; you "
            "want her OTP, card number and finally a 'verification fee' to your UPI kyc.sbi.help@ybl. Phone 91234 56780."
        ),
        "lines": [
            "Hello ma'am, main SBI head office से Rahul बोल रहा हूँ, आपका KYC pending है।",
            "आज शाम तक KYC update नहीं हुआ तो आपका account block हो जाएगा।",
            "आपके phone पे एक OTP आया होगा, वो बताइए please।",
            "अपना card number और expiry भी confirm कीजिए।",
            "दस रुपये verification fee भेजिए UPI kyc.sbi.help@ybl पर।",
            "कोई problem हो तो इस number पर call कीजिए 91234 56780।",
        ],
    },
    "electricity_bill": {
        "system": _FRAME + (
            "You are 'Suresh from the electricity board'. Her power will be cut tonight because of an unpaid bill; she "
            "must pay ₹980 immediately to bijli.office@paytm and install a 'bill app'. Phone 99887 76655."
        ),
        "lines": [
            "Namaste, main electricity office से Suresh बोल रहा हूँ।",
            "आपका पिछला bill pending है, आज रात साढ़े नौ बजे light कट जाएगी।",
            "अभी 980 रुपये pay कीजिए UPI bijli.office@paytm पर।",
            "Payment के बाद मुझे 99887 76655 पर WhatsApp कीजिए।",
            "एक app भेज रहा हूँ, Quick Support, उसको install कीजिए।",
        ],
    },
    "lottery_prize": {
        "system": _FRAME + (
            "You are 'Ravi from KBC head office'. She has won 25 lakh rupees in a lucky draw; to release it she must pay "
            "a ₹5,000 processing fee to kbc.prize2026@upi. WhatsApp 90000 11122."
        ),
        "lines": [
            "बधाई हो madam, आपने KBC lucky draw में पच्चीस लाख रुपये जीते हैं!",
            "Prize release करने के लिए पाँच हज़ार processing fee लगेगी।",
            "Fee भेजिए UPI kbc.prize2026@upi पर, अभी।",
            "Confirmation के लिए WhatsApp कीजिए 90000 11122 पर।",
            "ये offer सिर्फ आज के लिए है, देर मत कीजिए।",
        ],
    },
}

BENCH_LINES = [
    SCRIPTS["digital_arrest"]["lines"][4],
    SCRIPTS["digital_arrest"]["lines"][5],
    SCRIPTS["kyc_bank_block"]["lines"][4],
    SCRIPTS["electricity_bill"]["lines"][2],
    SCRIPTS["lottery_prize"]["lines"][3],
    SCRIPTS["digital_arrest"]["lines"][1],
]
