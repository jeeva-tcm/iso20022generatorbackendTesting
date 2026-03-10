import sys
import os
sys.path.append(os.path.abspath(r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend"))
from app.services.mt_mx_converter import MTtoMXConverter

mt199_str = """{1:F01BANKUS33AXXX0000000000}
{2:I199BANKDEFFXXXXN}
{4:
:20:REF123456789
:21:REL987654321
:79:PLEASE CONFIRM STATUS OF PAYMENT
SENT ON 09 MARCH 2026.
-}"""

converter = MTtoMXConverter()
result = converter.convert(mt199_str)
print("status:", result["status"])
if "errors" in result:
    for e in result["errors"]:
        print("ERROR:", e)
print("XML:")
print(result["mx_message"])
print("LOGS:", result["logs"])
