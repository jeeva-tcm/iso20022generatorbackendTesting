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

if "mx_message" in result:
    with open("debug_xml_out.xml", "w", encoding="utf-8") as f:
        f.write(result["mx_message"])
    print("XML written to debug_xml_out.xml")
    
    # Check for PstlAdr string explicitly
    if "<PstlAdr>" in result["mx_message"]:
        print("YES! FOUND <PstlAdr> exactly.")
    elif "PstlAdr" in result["mx_message"]:
        print("FOUND PstlAdr but maybe with prefix or different attrs.")
        print("Snippet:", result["mx_message"][result["mx_message"].find("PstlAdr")-10:result["mx_message"].find("PstlAdr")+50])
    else:
        print("COMPLETELY MISSING PstlAdr")
else:
    print("Conversion failed")
    print(json.dumps(result.get("errors", []), indent=2))
