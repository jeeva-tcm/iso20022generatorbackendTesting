<<<<<<< HEAD
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
=======
import asyncio
import os
import sys
import traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

with open('python_logs.txt', 'w', encoding='utf-8') as flog:
    sys.stdout = flog
    sys.stderr = flog

    from app.services.validator import ISOValidator

    async def run():
        validator = ISOValidator()
        print("Testing latest.xml")
        
        with open('latest.xml', 'r', encoding='utf-8') as f:
            xml = f.read()
        
        report = await validator.validate(xml, "Full 1-3", "Auto-detect", "latest.xml")
        for i in report.issues:
            print(f"ISSUE [{i['layer']}] {i['severity']} {i['message']} {i['code']}")

    if __name__ == "__main__":
        try:
            asyncio.run(run())
        except Exception as e:
            traceback.print_exc()
>>>>>>> 96741fe0d295ef0ab1d8e27573fb6b0661647cef
