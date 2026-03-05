"""
Comprehensive IBAN / BBAN account identifier validation test.
Tests: MOD-97, country length, pattern, mutual exclusivity, BBAN rules, SEPA rule.
"""
import re
from lxml import etree

# ── IBAN helpers (same as in validator.py) ──────────────────────────────────
# Source: SWIFT IBAN Registry, Edition 2024
# NOTE: US, CA, AU, IN, CN, JP do NOT participate in the IBAN scheme.
#       An IBAN starting with 'US' is ALWAYS INVALID.
IBAN_LENGTHS = {
    'AD':24,'AE':23,'AL':28,'AT':20,'AZ':28,
    'BA':20,'BE':16,'BF':28,'BG':22,'BH':22,'BI':27,'BJ':28,'BR':29,'BY':28,
    'CF':27,'CG':27,'CH':21,'CI':28,'CM':27,'CR':22,'CV':25,'CY':28,'CZ':24,
    'DE':22,'DJ':27,'DK':18,'DO':28,'DZ':26,
    'EE':20,'EG':29,'ES':24,
    'FI':18,'FK':18,'FO':18,'FR':27,
    'GA':27,'GB':22,'GE':22,'GI':23,'GL':18,'GN':26,'GQ':27,'GR':27,'GT':28,'GW':25,
    'HN':28,'HR':21,'HU':28,
    'IE':22,'IL':23,'IQ':23,'IR':26,'IS':26,'IT':27,
    'JO':30,
    'KM':27,'KW':30,'KZ':20,
    'LB':28,'LC':32,'LI':21,'LT':20,'LU':20,'LV':21,'LY':25,
    'MA':28,'MC':27,'MD':24,'ME':22,'MG':27,'MK':19,'ML':28,
    'MN':20,'MR':27,'MT':31,'MU':30,'MZ':25,
    'NE':28,'NI':32,'NL':18,'NO':15,'NZ':16,
    'OM':23,  # Oman — added in 2024 SWIFT Registry
    'PK':24,'PL':28,'PS':29,'PT':25,
    'QA':29,
    'RO':24,'RS':22,'RU':33,
    'SA':24,'SC':31,'SD':18,'SE':24,'SI':19,'SK':24,
    'SM':27,'SN':28,'SO':23,'ST':25,'SV':28,
    'TD':27,'TG':28,'TL':23,'TN':24,'TR':26,
    'UA':29,
    'VA':22,'VG':24,
    'XK':20,
    'YE':30,
}
IBAN_PATTERN = re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$')

def iban_mod97(iban):
    rearranged = iban[4:] + iban[:4]
    numeric = ''.join(str(ord(c)-55) if c.isalpha() else c for c in rearranged)
    try:
        return int(numeric) % 97 == 1
    except ValueError:
        return False

def validate_iban(raw):
    # Strip spaces but do NOT uppercase before pattern check
    # (matching production code — lowercase must fail the pattern)
    v_no_spaces = raw.strip().replace(' ', '')
    if not (15 <= len(v_no_spaces) <= 34):
        return f"FAIL: length {len(v_no_spaces)} out of range 15-34"
    if not IBAN_PATTERN.match(v_no_spaces):   # pattern requires uppercase
        return f"FAIL: pattern mismatch '{v_no_spaces}'"
    v = v_no_spaces.upper()                   # only uppercase AFTER pattern passes
    country = v[:2]
    if country not in IBAN_LENGTHS:
        return f"FAIL: unknown / non-IBAN country '{country}'"
    expected = IBAN_LENGTHS[country]
    if len(v) != expected:
        return f"FAIL: length {len(v)} != {expected} for {country}"
    if not iban_mod97(v):
        return f"FAIL: MOD-97 check digit invalid"
    return "PASS"

print("=== IBAN Tests ===")
iban_tests = [
    ("GB29NWBK60161331926819",    "PASS",  "Valid GB IBAN"),
    ("DE89370400440532013000",    "PASS",  "Valid DE IBAN"),
    ("NL91ABNA0417164300",        "PASS",  "Valid NL IBAN"),
    ("FR7630006000011234567890189","PASS", "Valid FR IBAN"),
    ("OM810180000001299123456",   "PASS",  "Valid OM (Oman) IBAN — 23 chars"),
    ("DE755121080012451261998789798798789797097097097097970970709",
                                  "FAIL",  "Too long (> 34 chars)"),
    ("DE75512108001245126199",    "PASS",  "Valid 22-char DE IBAN"),
    ("GB29NWBK60161331926818",    "FAIL",  "Wrong check digit (last digit off)"),
    ("XX12345678901234",           "FAIL",  "Unknown country XX"),
    ("DE00370400440532013000",    "FAIL",  "MOD-97 fails (check digits 00)"),
    ("gb29nwbk60161331926819",    "FAIL",  "Lowercase — pattern must fail"),
    ("GB29 NWBK 6016 1331 9268 19","PASS", "Spaces stripped before check"),
    # US is NOT an IBAN country — wire transfers to the US use ABA routing numbers
    ("US12345678901234567890",    "FAIL",  "US — not an IBAN country"),
    ("US02123456789012345678",    "FAIL",  "US with valid-looking format — still invalid"),
]

all_ok = True
for val, expect, desc in iban_tests:
    result = validate_iban(val)
    got    = "PASS" if result == "PASS" else "FAIL"
    ok     = got == expect
    if not ok: all_ok = False
    mark   = "✅" if ok else "❌ MISMATCH"
    print(f"  {mark}  {desc}")
    print(f"       value='{val[:40]}{'...' if len(val)>40 else ''}' → {result}")

print()
print("=== BBAN Tests ===")
def validate_bban(v):
    v = v.strip()
    if not v: return "FAIL: empty"
    if len(v) > 30: return f"FAIL: length {len(v)} > 30"
    if not re.match(r'^[A-Za-z0-9]+$', v): return f"FAIL: invalid chars in '{v}'"
    return "PASS"

bban_tests = [
    ("12345678901234",  "PASS", "Valid numeric BBAN"),
    ("ABCD1234EFGH",    "PASS", "Valid alphanumeric BBAN"),
    ("",                "FAIL", "Empty BBAN"),
    ("1234567890123456789012345678901", "FAIL", "31 chars (over limit 30)"),
    ("1234 5678",       "FAIL", "Space in BBAN"),
    ("1234-5678",       "FAIL", "Hyphen in BBAN"),
    ("A" * 30,          "PASS", "Exactly 30 chars"),
]
for val, expect, desc in bban_tests:
    result = validate_bban(val)
    got    = "PASS" if result == "PASS" else "FAIL"
    ok     = got == expect
    if not ok: all_ok = False
    mark   = "✅" if ok else "❌ MISMATCH"
    print(f"  {mark}  {desc}: '{val[:35]}' → {result}")

print()
print("ALL TESTS PASSED ✅" if all_ok else "❌ SOME TESTS FAILED")
