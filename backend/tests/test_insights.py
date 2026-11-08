from dadi.insights import agency_key, freeze_list, freeze_csv, insights, rupees

CALLS = [
    {"id": "c1", "started_at": 100.0, "wasted_seconds": 120, "intel": {
        "upi_ids": ["rathore.cbi@okaxis"], "agencies_claimed": ["CBI Mumbai", "CBI मुंबई"], "names": ["Vijay Rathore"],
        "amounts": ["₹25,000", "5 lakh"], "scam_type": "digital_arrest",
        "red_flags": [{"flag": "threat_of_arrest", "quote": "x", "t": 1}]}},
    {"id": "c2", "started_at": 200.0, "wasted_seconds": 60, "intel": {
        "upi_ids": ["RATHORE.CBI@okaxis"], "phones": ["9876543210"], "agencies_claimed": ["SBI head office"],
        "amounts": ["980 रुपये"], "scam_type": "kyc_bank_block"}},
    {"id": "c3", "started_at": 300.0, "wasted_seconds": 0, "intel": {}},
]
RINGS = {"rings": [{"calls": ["c1", "c2"]}]}


def test_rupees_understands_indian_formats():
    assert rupees("₹25,000") == 25_000 and rupees("5 lakh") == 500_000 and rupees("2 crore") == 20_000_000
    assert rupees("980 रुपये") == 980 and rupees("Rs. 1,50,000") == 150_000 and rupees("lots") is None


def test_agency_key_merges_spellings():
    assert agency_key("CBI Mumbai") == agency_key("CBI मुंबई") == agency_key("सीबीआई") == "CBI"
    assert agency_key("Mumbai Cyber Police") == "Police" and agency_key("Acme Corp") == "Acme Corp"


def test_insights_aggregates_calls():
    i = insights(CALLS)
    assert i["calls"] == 3 and i["minutes_wasted"] == 3.0
    assert i["rupees_demanded"] == 25_000 + 500_000 + 980
    assert i["agencies"][0] == {"name": "CBI", "calls": 1} and {"name": "SBI", "calls": 1} in i["agencies"]
    assert i["scam_types"][0]["calls"] == 1 and i["red_flags"][0] == {"flag": "threat_of_arrest", "calls": 1}
    assert i["handles"] == [{"handle": "okaxis", "bank": "Axis Bank (Google Pay)", "ids": 1}]


def test_freeze_list_merges_ids_across_calls_and_rings():
    rows = freeze_list(CALLS, RINGS)
    upi = next(r for r in rows if r["kind"] == "UPI")
    assert upi["id"] == "rathore.cbi@okaxis" and upi["calls"] == ["c1", "c2"] and upi["ring"] == 1
    assert upi["bank"] == "Axis Bank (Google Pay)" and upi["first_seen"] == 100.0
    assert next(r for r in rows if r["kind"] == "phone")["calls"] == ["c2"]
    csv = freeze_csv(rows)
    assert csv.splitlines()[0].startswith("kind,id,bank") and "rathore.cbi@okaxis" in csv
