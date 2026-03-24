import sys
import os
import asyncio

# Redirect stdout to a file
output_file = open("debug_output.txt", "w", encoding="utf-8")
sys.stdout = output_file

sys.path.insert(0, r"c:\Users\HP\Documents\ISO Stub Validator\iso20022generatorbackend")

from app.services.mt_mx_converter import MT2MXConverter
from app.services.validator import ISOValidator

mt_msg = "{1:F01BANKBEBBAXXX0000000000}{2:I103BANKDEFFXXXXN}{4:\n:20:REF123\n:21:REL456\n:32A:240324USD1000,\n:52A:BANKUS33\n:58A:BANKGB22\n:50K:/12345\nNAME1\nADDR1\n:59:/67890\nNAME2\nADDR2\n-}"
converter = MT2MXConverter()
result = converter.validate_and_convert(mt_msg, forced_mt_type="202COV")
mx = result.get("mx_message", "")
if not mx:
    print("CONVERSION FAILED!")
    print(f"Errors: {result.get('errors')}")
    print(f"Logs: {result.get('logs')}")

print("---- XML START ----")
print(mx)
print("---- XML END ----")

if mx:
    validator = ISOValidator()
    detected = validator._detect_message_type(mx)
    print(f"Detected Type: '{detected}'")
    report = asyncio.run(validator.validate(mx))
    print("\n--- Validation Report ---")
    print(f"Status: {report.status}")
    print(f"Errors: {report.errors}, Warnings: {report.warnings}")
    for issue in report.issues:
        print(f"[{issue.get('severity')}] {issue.get('code')} @ {issue.get('path')}: {issue.get('message')}")

output_file.close()
