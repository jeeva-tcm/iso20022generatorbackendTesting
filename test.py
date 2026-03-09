import urllib.request
import json

data = json.dumps({'mt_message': '{1:F01BBBBUS33AXXX0000000000}{2:I#CCCCGB2LXXXXN}\\n:20:REF17\\n:32A:261231USD1500,00\\n:50K:/US\\nSENDER\\n:59:/GB\\nREC\\n:71A:SHA\\n-}', 'target_mt_type': 'MT103'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8001/convert-mt-to-mx', data=data, headers={'content-type': 'application/json'})

try:
    print(urllib.request.urlopen(req).read().decode('utf-8'))
except Exception as e:
    print('ERROR:', e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
