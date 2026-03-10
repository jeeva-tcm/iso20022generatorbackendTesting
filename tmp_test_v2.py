import sys
import os
import json

# Add backend/app to sys.path
sys.path.append(os.path.join(os.getcwd(), "app"))

from services.mt_mx_converter import MT2MXConverter

mt103 = """{1:F01BANKBEBBAXXX0000000000}{2:I103BANKDEFFXXXXN}{4:
:20:SENDER-REF-123
:23B:CRED
:32A:240115USD1000,50
:50K:/12345678
JOHN DOE
ADDRESS LINE 1
:59:/87654321
JANE DOE
ADDRESS LINE 2
:71A:SHA
-}"""

converter = MT2MXConverter()
result = converter.validate_and_convert(mt103)

if result["status"] == "success":
    print("SUCCESS")
    print("Detected Type:", result["detected_type"])
    print("MX Message:")
    print(result["mx_message"])
else:
    print("FAILED")
    print("Errors:", json.dumps(result.get("errors", []), indent=2))
    print("Logs:", json.dumps(result.get("logs", []), indent=2))
