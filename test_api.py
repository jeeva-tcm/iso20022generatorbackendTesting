import re
import urllib.request
import json
import traceback

with open("test_output.txt", "w") as f:
    f.write("Starting test...\\n")

    try:
        mt_msg = "{1:F01BBBBUS33AXXX0000000000}{2:I#CCCCGB2LXXXXN}\\n:20:REF17\\n:32A:261231USD1500,00\\n:50K:/US\\nSENDER\\n:59:/GB\\nREC\\n:71A:SHA\\n-}"
        data = json.dumps({'mt_message': mt_msg, 'target_mt_type': 'MT103'}).encode('utf-8')
        req = urllib.request.Request('http://127.0.0.1:8001/convert-mt-to-mx', data=data, headers={'content-type': 'application/json'})
        response = urllib.request.urlopen(req, timeout=5)
        f.write("Success:\\n")
        f.write(response.read().decode('utf-8'))
    except Exception as e:
        f.write("ERROR:\\n")
        f.write(str(e) + "\\n")
        if hasattr(e, 'read'):
            f.write(e.read().decode('utf-8') + "\\n")
        f.write(traceback.format_exc())
