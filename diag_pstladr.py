import sys
import os
import json
import xml.etree.ElementTree as ET

# Add backend/app to sys.path
sys.path.append(os.path.join(os.getcwd(), "app"))

from services.mt_mx_converter import MT2MXConverter

mt103 = """{1:F01BANKBEBBAXXX0000000000}{2:I103BANKDEFFXXXXN}{4:
:20:SENDER-REF-123
:23B:CRED
:32A:240115USD1000,50
:50K:/12345678
JOHN DOE
:59:/87654321
JANE DOE
:71A:SHA
-}"""

converter = MT2MXConverter()
result = converter.validate_and_convert(mt103)

print("Status:", result["status"])
if "errors" in result:
    print("Errors:", json.dumps(result["errors"], indent=2))

if "mx_message" in result:
    print("--- Generated XML ---")
    print(result["mx_message"])
    
    # Check for PstlAdr
    if "<PstlAdr>" in result["mx_message"]:
        print("FOUND <PstlAdr> in XML")
    else:
        print("MISSING <PstlAdr> in XML")
