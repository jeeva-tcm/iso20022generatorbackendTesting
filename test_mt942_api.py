import urllib.request
import json
import os

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

data = json.dumps({'mt_message': mt942_str, 'target_mt_type': 'MT942'}).encode('utf-8')
try:
    req = urllib.request.Request('http://127.0.0.1:8001/convert-mt-to-mx', data=data, headers={'content-type': 'application/json'})
    response = urllib.request.urlopen(req, timeout=10)
    result = response.read().decode('utf-8')
    with open(os.path.abspath(r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\api_debug_out_942.json"), "w") as f:
        f.write(result)
except Exception as e:
    with open(os.path.abspath(r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\api_debug_out_942.json"), "w") as f:
        f.write(str(e))
        if hasattr(e, 'read'):
            f.write("\n\n")
            f.write(e.read().decode('utf-8'))
