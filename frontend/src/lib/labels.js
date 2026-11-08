// Human labels for backend enums (mirrors backend/dadi/taxonomy.py and tactics.py).

export const SCAM_TYPE_LABELS = {
  digital_arrest: "Digital arrest (fake police/CBI)",
  courier_parcel: "Courier / parcel (fake customs)",
  kyc_bank_block: "KYC / bank account block",
  electricity_bill: "Electricity disconnection",
  lottery_prize: "Lottery / KBC prize",
  job_task: "Job / task scam",
  investment: "Investment / trading scam",
  other: "Not yet clear",
};

export const RED_FLAG_LABELS = {
  impersonates_authority: "Claims to be police / CBI / bank / government",
  threat_of_arrest: "Threatens arrest or legal action",
  demands_secrecy: "Tells the victim to keep it secret",
  remote_access_app: "Asks to install a remote-access app",
  safe_account_transfer: "Asks to move money to a 'safe account'",
  urgency_pressure: "Creates panic and urgency",
  asks_otp_pin: "Asks for OTP / PIN / CVV",
  asks_personal_ids: "Asks for Aadhaar / PAN / card details",
};

export const TACTIC_LABELS = {
  glasses: "Lost her glasses",
  door_bell: "Doorbell",
  pressure_cooker: "Pressure cooker whistle",
  mishear: "Mishears on purpose",
  repeat_please: "Asks to repeat",
  slow_digits: "Reads fake digits slowly",
  battery_low: "Battery low",
  grandson: "Asks the grandson",
  health_tangent: "Health story",
  tv_serial: "TV serial distraction",
  wrong_button: "Pressed the wrong button",
  neighbour: "Neighbour story",
  ask_upi: "Extracting: UPI ID",
  ask_account_ifsc: "Extracting: bank account + IFSC",
  ask_name_badge: "Extracting: name + badge no.",
  ask_whatsapp: "Extracting: WhatsApp number",
  ask_police_station: "Extracting: office / station",
};

export const INTEL_FIELDS = [
  ["upi_ids", "UPI IDs"],
  ["accounts", "Bank accounts"],
  ["ifsc", "IFSC"],
  ["phones", "Phone / WhatsApp"],
  ["apps", "Remote-access apps"],
  ["urls", "Links"],
  ["names", "Names given"],
  ["agencies_claimed", "Claimed agency"],
  ["amounts", "Amounts demanded"],
];

export const MIX_LABEL = { "hi-IN": "Hinglish", "ta-IN": "Tanglish", "bn-IN": "Benglish", "kn-IN": "Kanglish", "te-IN": "Tenglish" };
export const PERSONA_HUE = { dadi: 330, paati: 200, thakuma: 35, ajji: 140, ammamma: 270 };

export const DISCLAIMER = "Simulated scam call: scammer played by an actor or our AI";

export const mmss = (sec) => {
  const s = Math.max(0, Math.round(Number(sec) || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

export const identifierCount = (intel = {}) =>
  ["upi_ids", "accounts", "phones", "ifsc"].reduce((n, k) => n + (intel[k]?.length || 0), 0);
