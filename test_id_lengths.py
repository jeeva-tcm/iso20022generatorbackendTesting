"""
Test ID field max-length validation using the exact values from the user's XML message.
"""
import re

ID_MAX_LENGTHS = {
    "InstrId":    35,
    "EndToEndId": 35,
    "BizMsgIdr":  35,
    "MsgId":      35,
    "TxId":       35,
    "UETR":       36,
}

# Values taken directly from the user's XML message
test_fields = [
    # (tag, value)
    ("BizMsgIdr",  "MSG-2026-B-0018587585858758758758759"),          # 35 chars → PASS
    ("MsgId",      "MSG-2026-B-00189798709709709709"),               # 31 chars → PASS
    ("InstrId",    "INSTR-ID-9998997097070970"),                     # 25 chars → PASS
    ("EndToEndId", "E2E-REF-77798y98y98y089y08y08y08y"),            # 33 chars → PASS
    ("TxId",       "TX-ID-5559009870970970970970907809"),            # 34 chars → PASS  (borderline)
    ("UETR",       "550e8400-e29b-41d4-a716-4466554400008899870970970970970970"),  # too long → FAIL
    # Extra test cases
    ("MsgId",      "A" * 36),                                        # 36 chars → FAIL (over limit)
    ("UETR",       "550e8400-e29b-41d4-a716-446655440000"),         # 36 chars → PASS (exact limit)
    ("UETR",       "550e8400-e29b-41d4-a716-4466554400001"),        # 37 chars → FAIL
]

print(f"{'TAG':<14} {'LEN':>4}  {'MAX':>4}  {'RESULT'}")
print("-" * 50)
errors = 0
for tag, val in test_fields:
    max_len = ID_MAX_LENGTHS[tag]
    actual  = len(val)
    ok      = actual <= max_len
    if not ok:
        errors += 1
    status = "✅ OK  " if ok else f"❌ FAIL  → exceeds by {actual - max_len}"
    print(f"{tag:<14} {actual:>4}  {max_len:>4}  {status}")

print()
print(f"Total errors: {errors}")
