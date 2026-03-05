"""
Comprehensive UETR UUID v4 validation test.
Covers: correct format, wrong length, uppercase, wrong version,
        wrong variant, bad chars, too long (user's XML value), missing hyphens.
"""
import re

UUID_V4 = re.compile(
    r'^[0-9a-f]{8}-'       # 8 hex
    r'[0-9a-f]{4}-'        # 4 hex
    r'4[0-9a-f]{3}-'       # version 4 + 3 hex
    r'[89ab][0-9a-f]{3}-'  # variant [89ab] + 3 hex
    r'[0-9a-f]{12}$'       # 12 hex
)

def classify(val):
    """Return the same hint logic used in _validate_uetr_in_xml."""
    if len(val) != 36:
        return f"FAIL — wrong length ({len(val)} chars, need 36)"
    if val != val.lower():
        return "FAIL — must be lowercase"
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', val.lower()):
        return "FAIL — bad 8-4-4-4-12 structure"
    if val[14] != '4':
        return f"FAIL — version digit must be '4', got '{val[14]}'"
    return f"FAIL — variant nibble must be 8/9/a/b, got '{val[19]}'"

test_cases = [
    # (value, expect_valid, description)
    ("550e8400-e29b-41d4-a716-446655440000",                       True,  "Valid UUID v4"),
    ("f47ac10b-58cc-4372-a567-0e02b2c3d479",                       True,  "Valid UUID v4 #2"),
    ("a3bb189e-8bf9-3888-9f80-f4f1e7614b34",                       False, "Version = 3 (not v4)"),
    ("550e8400-e29b-41d4-c716-446655440000",                       False, "Variant 'c' invalid"),
    ("550E8400-E29B-41D4-A716-446655440000",                       False, "Uppercase hex"),
    ("550e8400-e29b-41d4-a716-4466554400008899870970970970970970",  False, "Too long (from user XML)"),
    ("550e8400e29b41d4a716446655440000",                            False, "No hyphens (32 chars)"),
    ("550e8400-e29b-41d4-a716-44665544000",                        False, "Too short (35 chars)"),
    ("550e8400-e29b-41d4-a716-4466554400001",                      False, "Too long (37 chars)"),
    ("gggggggg-gggg-4ggg-aggg-gggggggggggg",                       False, "Invalid hex chars 'g'"),
    ("550e8400-e29b-41d4-a716-446655440000",                       True,  "Valid UUID v4 repeated check"),
]

print(f"{'VALUE':<55}  {'EXPECTED':<8}  {'GOT':<8}  {'STATUS'}")
print("-" * 100)

all_ok = True
for val, expect_valid, desc in test_cases:
    got_valid = bool(UUID_V4.match(val))
    ok = got_valid == expect_valid
    if not ok:
        all_ok = False
    mark   = "✅" if ok else "❌ FAIL"
    result = "PASS  " if got_valid else classify(val)
    short  = val if len(val) <= 50 else val[:47] + "..."
    print(f"{short:<55}  {'VALID' if expect_valid else 'INVALID':<8}  {'VALID' if got_valid else 'INVALID':<8}  {mark}  {desc}")
    if not ok:
        print(f"{'':>100}  ↑ mismatch!")

print()
print("ALL TESTS PASSED ✅" if all_ok else "❌ SOME TESTS FAILED")
