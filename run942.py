import json
import os
import sys

# Ensure we're running from backend dir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.mt_mx_converter import MT2MXConverter

converter = MT2MXConverter()
mt942_str = """{1:F01BANKUS33AXXX0000000000}
{2:I942BANKDEFFXXXXN}
{4:
:20:REF123456789
:25:ACC89347589
:28C:1/1
:34F:USD1234,56
:13D:202611091530+0000
:61:2611090626C1234,56NRFNREF1234
-}"""

result = converter.validate_and_convert(mt942_str, "MT942")

with open("out942.json", "w") as f:
    json.dump(result, f, indent=2)
