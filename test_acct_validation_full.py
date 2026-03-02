"""
Full integration tests for the enhanced IBAN / BBAN / Mutual-Exclusivity /
SEPA-rule / Amount validation logic added in Step 4.8.

Each test creates a minimal ISO 20022 XML snippet and calls
_validate_account_identifiers_in_xml() directly.
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# --- Minimal stub so we don't need the full server stack -----
from services.models import ValidationReport, ValidationIssue

class FakeValidator:
    """Thin stub that only provides the helpers the method expects."""
    pass

# Monkey-patch only the method under test
from services.validator import ISOValidator
stub = object.__new__(ISOValidator)

def _run(xml: str):
    report = ValidationReport("TEST-001", "pacs.008", "Full 1-3")
    stub._validate_account_identifiers_in_xml(xml, report)
    return report.issues

PASS = "\u2705"
FAIL = "\u274c"
all_ok = True
results = []

def check(label, issues, expect_codes, expect_none=False):
    global all_ok
    codes = [i['code'] for i in issues]
    if expect_none:
        ok = len(issues) == 0
        results.append((ok, label, f"codes={codes}"))
    else:
        ok = all(c in codes for c in expect_codes)
        results.append((ok, label, f"codes={codes}"))
    if not ok:
        all_ok = False

# ─── IBAN Tests ───────────────────────────────────────────────────────────────

# 1. Valid IBAN — no errors
xml_valid_iban = """<root>
  <DbtrAcct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id></DbtrAcct>
</root>"""
check("Valid GB IBAN – no errors", _run(xml_valid_iban), [], expect_none=True)

# 2. Too short (< 15 chars)
xml_short = """<root>
  <DbtrAcct><Id><IBAN>GB29NWBK</IBAN></Id></DbtrAcct>
</root>"""
check("IBAN too short (< 15)", _run(xml_short), ["IBAN_VALIDATION_ERROR"])

# 3. Too long (> 34 chars)
xml_long = """<root>
  <DbtrAcct><Id><IBAN>GB29NWBK6016133192681900000000000000000</IBAN></Id></DbtrAcct>
</root>"""
check("IBAN too long (> 34)", _run(xml_long), ["IBAN_VALIDATION_ERROR"])

# 4. Lowercase letters
xml_lower = """<root>
  <DbtrAcct><Id><IBAN>gb29nwbk60161331926819</IBAN></Id></DbtrAcct>
</root>"""
check("IBAN lowercase – pattern fail", _run(xml_lower), ["IBAN_VALIDATION_ERROR"])

# 5. Unknown country code
xml_xx = """<root>
  <DbtrAcct><Id><IBAN>XX12ABCD12345678901234</IBAN></Id></DbtrAcct>
</root>"""
check("IBAN unknown country XX", _run(xml_xx), ["IBAN_VALIDATION_ERROR"])

# 6. Wrong length for country (DE = 22, we give 21)
xml_de_short = """<root>
  <DbtrAcct><Id><IBAN>DE8937040044053201300</IBAN></Id></DbtrAcct>
</root>"""
check("IBAN DE wrong length (21 instead of 22)", _run(xml_de_short), ["IBAN_VALIDATION_ERROR"])

# 7. MOD-97 fails
xml_mod97 = """<root>
  <DbtrAcct><Id><IBAN>DE00370400440532013000</IBAN></Id></DbtrAcct>
</root>"""
check("IBAN MOD-97 fail (check digits 00)", _run(xml_mod97), ["IBAN_VALIDATION_ERROR"])

# 8. Valid with spaces (stripped before check) — should pass
xml_spaces = """<root>
  <DbtrAcct><Id><IBAN>GB29 NWBK 6016 1331 9268 19</IBAN></Id></DbtrAcct>
</root>"""
check("IBAN with spaces (auto-stripped) – no error", _run(xml_spaces), [], expect_none=True)

# ─── Mutual Exclusivity ───────────────────────────────────────────────────────

# 9. Both IBAN and Othr present
xml_both = """<root>
  <DbtrAcct>
    <Id>
      <IBAN>GB29NWBK60161331926819</IBAN>
      <Othr><Id>12345678</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </DbtrAcct>
</root>"""
check("Both IBAN and Othr present", _run(xml_both), ["ACCT_MUTUAL_EXCLUSIVITY"])

# 10. Neither IBAN nor Othr
xml_empty_id = """<root>
  <DbtrAcct><Id></Id></DbtrAcct>
</root>"""
check("Neither IBAN nor Othr", _run(xml_empty_id), ["ACCT_MISSING_ID"])

# ─── BBAN Tests ───────────────────────────────────────────────────────────────

# 11. Valid BBAN
xml_valid_bban = """<root>
  <DbtrAcct>
    <Id>
      <Othr><Id>12345678901234</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </DbtrAcct>
</root>"""
check("Valid generic BBAN – no errors", _run(xml_valid_bban), [], expect_none=True)

# 12. Empty BBAN
xml_empty_bban = """<root>
  <DbtrAcct>
    <Id>
      <Othr><Id></Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </DbtrAcct>
</root>"""
check("Empty BBAN", _run(xml_empty_bban), ["BBAN_VALIDATION_ERROR"])

# 13. BBAN > 30 chars
xml_bban_long = """<root>
  <DbtrAcct>
    <Id>
      <Othr><Id>1234567890123456789012345678901</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </DbtrAcct>
</root>"""
check("BBAN > 30 chars", _run(xml_bban_long), ["BBAN_VALIDATION_ERROR"])

# 14. BBAN with special chars (no country struct)
xml_bban_special = """<root>
  <DbtrAcct>
    <Id>
      <Othr><Id>1234-5678</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </DbtrAcct>
</root>"""
check("BBAN with hyphens – invalid chars", _run(xml_bban_special), ["BBAN_VALIDATION_ERROR"])

# ─── SEPA rule ───────────────────────────────────────────────────────────────

# 15. SEPA payment with BBAN → rejected
xml_sepa_bban = """<root>
  <PmtTpInf><SvcLvl><Cd>SEPA</Cd></SvcLvl></PmtTpInf>
  <DbtrAcct>
    <Id>
      <Othr><Id>12345678901234</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </DbtrAcct>
</root>"""
check("SEPA payment with BBAN – rejected", _run(xml_sepa_bban), ["SEPA_BBAN_NOT_ALLOWED"])

# ─── BBAN structure: GB ──────────────────────────────────────────────────────
# GB BBAN structure: 4a + 6n + 8n = 18 chars
# E.g. NWBK601613319268

# 16. Valid GB BBAN with GB creditor country
xml_gb_bban_valid = """<root>
  <Cdtr><PstlAdr><Ctry>GB</Ctry></PstlAdr></Cdtr>
  <CdtrAcct>
    <Id>
      <Othr><Id>NWBK60161331926819</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </CdtrAcct>
</root>"""
check("Valid GB BBAN (4a+6n+8n) – no error", _run(xml_gb_bban_valid), [], expect_none=True)

# 17. Invalid GB BBAN – numeric where alpha required
xml_gb_bban_bad = """<root>
  <Cdtr><PstlAdr><Ctry>GB</Ctry></PstlAdr></Cdtr>
  <CdtrAcct>
    <Id>
      <Othr><Id>123460161331926819</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </CdtrAcct>
</root>"""
check("Invalid GB BBAN (numeric where alpha needed)", _run(xml_gb_bban_bad), ["BBAN_VALIDATION_ERROR"])

# ─── Multiple accounts ───────────────────────────────────────────────────────

# 18. Two accounts, one valid IBAN, one bad BBAN — collect all errors
xml_multi = """<root>
  <DbtrAcct>
    <Id><IBAN>DE00370400440532013000</IBAN></Id>
  </DbtrAcct>
  <CdtrAcct>
    <Id>
      <Othr><Id>BAD BBAN!</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr>
    </Id>
  </CdtrAcct>
</root>"""
issues_multi = _run(xml_multi)
check("Multiple errors from multiple accounts collected",
      issues_multi, ["IBAN_VALIDATION_ERROR", "BBAN_VALIDATION_ERROR"])

# ─── Print Results ────────────────────────────────────────────────────────────
print("\n=== IBAN / BBAN / Mutual-Exclusivity / SEPA / Multi-Account Tests ===\n")
for ok, label, detail in results:
    mark = PASS if ok else FAIL
    print(f"  {mark}  {label}")
    if not ok:
        print(f"       {detail}")

print()
print("ALL TESTS PASSED ✅" if all_ok else "❌  SOME TESTS FAILED — see above")
