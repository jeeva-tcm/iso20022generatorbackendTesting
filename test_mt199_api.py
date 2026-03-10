import urllib.request
import json
import os

mt199_str = """{1:F01BANKUS33AXXX0000000000}
{2:I199BANKDEFFXXXXN}
{4:
:20:REF123456789
:21:REL987654321
:79:PLEASE CONFIRM STATUS OF PAYMENT
SENT ON 09 MARCH 2026.
-}"""

data = json.dumps({'mt_message': mt199_str, 'target_mt_type': 'MT199'}).encode('utf-8')
try:
    req = urllib.request.Request('http://127.0.0.1:8001/convert-mt-to-mx', data=data, headers={'content-type': 'application/json'})
    response = urllib.request.urlopen(req, timeout=10)
    result = response.read().decode('utf-8')
    with open(os.path.abspath(r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\api_debug_out.json"), "w") as f:
        f.write(result)
except Exception as e:
    with open(os.path.abspath(r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\api_debug_out.json"), "w") as f:
        f.write(str(e))
        if hasattr(e, 'read'):
            f.write("\n\n")
            f.write(e.read().decode('utf-8'))
