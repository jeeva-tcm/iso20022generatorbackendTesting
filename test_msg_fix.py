
import os
import sys

# Mocking the environment for Layer2Mixin
class MockValidator:
    def __init__(self):
        self.codelists = {
            "schme_nm": {
                "schmeNm_validation": {
                    "valid_cd_codes": [
                        {"code": "LEI"}, {"code": "CUST"}, {"code": "BANK"}
                    ],
                    "invalid_cd_codes": [
                        {"code": "Passport", "reason": "Used for individuals, not organizations"}
                    ]
                }
            }
        }
    
    def _camel_to_words(self, text):
        return text

# Inject MockValidator into Layer2Mixin inheritance if needed, 
# or just test the logic from the file by importing.

import re

# Copying the logic from layer2_validator.py to test it
def test_simplification(msg):
    # Mocking bad_value
    def bad_value(default=""):
        m = re.search(r"[Vv]alue\s+'([^']*)'", msg)
        if m: return m.group(1)
        m = re.search(r"Element\s+'[^']+':\s*'([^']*)'", msg)
        return m.group(1) if m else default

    # Mocking elem_name
    def elem_name(default="A field"):
        m = re.search(r"Element '([^']+)'", msg)
        if not m: return default
        raw = m.group(1)
        return raw.split('}')[-1] if '}' in raw else raw

    # The Logic we just implemented
    raw_val = bad_value(default="___NOT_EMPTY___")
    if raw_val == "" or (raw_val == "___NOT_EMPTY___" and ("''" in msg or '""' in msg)):
        name = elem_name("Cd")
        if name == "Cd" and ("SchmeNm" in msg):
             return (f"❌ Missing or empty...", f"For this tag data is required. It can have the valid data such as 'LEI', 'CUST'...")

    if "enumeration" in msg.lower() or "is not an element of the set" in msg.lower():
        ev = bad_value()
        name = elem_name()
        if name == "Cd" and "SchmeNm" in msg:
            valid_codes = ["LEI", "CUST", "BANK"] # Mocked
            codes_str = ", ".join(valid_codes)
            return (
                f"❌ Invalid scheme code '{ev}' for {name}.",
                f"For this tag data '{ev}' is invalid. It can have the valid data such as: {codes_str}."
            )
    return "No match"

msg = "Element '{urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08}Cd': [facet 'enumeration'] The value 'Passport' is not an element of the set {'BICFI', 'IBAN'}"
print(f"INPUT: {msg}")
print(f"OUTPUT: {test_simplification(msg)}")
