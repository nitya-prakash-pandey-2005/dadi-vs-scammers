"""Scam types, red flags and Prisma keyterms."""

SCAM_TYPES = [
    "digital_arrest", "courier_parcel", "kyc_bank_block", "electricity_bill",
    "lottery_prize", "job_task", "investment", "other",
]

SCAM_TYPE_LABELS = {
    "digital_arrest": "Digital arrest (fake police/CBI)",
    "courier_parcel": "Courier / parcel (fake customs)",
    "kyc_bank_block": "KYC / bank account block",
    "electricity_bill": "Electricity disconnection",
    "lottery_prize": "Lottery / KBC prize",
    "job_task": "Job / task scam",
    "investment": "Investment / trading scam",
    "other": "Other",
}

RED_FLAGS = {
    "impersonates_authority", "threat_of_arrest", "demands_secrecy", "remote_access_app",
    "safe_account_transfer", "urgency_pressure", "asks_otp_pin", "asks_personal_ids",
}

RED_FLAG_LABELS = {
    "impersonates_authority": "Claims to be police / CBI / bank / government",
    "threat_of_arrest": "Threatens arrest or legal action",
    "demands_secrecy": "Tells the victim to keep it secret",
    "remote_access_app": "Asks to install a remote-access app",
    "safe_account_transfer": "Asks to move money to a 'safe account'",
    "urgency_pressure": "Creates panic and urgency",
    "asks_otp_pin": "Asks for OTP / PIN / CVV",
    "asks_personal_ids": "Asks for Aadhaar / PAN / card details",
}

SCAM_KEYTERMS = [
    "CBI", "ED", "RBI", "TRAI", "SEBI", "FedEx", "DHL", "customs", "narcotics", "drugs",
    "money laundering", "arrest warrant", "digital arrest", "Aadhaar", "PAN", "KYC", "UPI",
    "OTP", "PIN", "CVV", "IFSC", "AnyDesk", "TeamViewer", "safe account", "Skype", "video call",
    "electricity", "bijli", "lottery", "KBC", "Paytm", "PhonePe", "Google Pay", "SBI", "HDFC",
    "ICICI", "cyber crime", "police", "inspector", "parcel",
]
