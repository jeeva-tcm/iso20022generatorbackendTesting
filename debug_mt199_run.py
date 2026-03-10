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
with open(os.path.abspath(r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\debug_mt199_out.txt"), "w") as f:
    f.write("XML:\n")
    f.write(result.get("mx_message", ""))
    f.write("\nLOGS:\n")
    f.write(str(result.get("logs", "")))
