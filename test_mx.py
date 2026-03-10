import json
import xml.dom.minidom 
from app.services.mt_mx_converter import MT2MXConverter
c = MT2MXConverter('app/mappings')
msg = '{1:F01BANKBEBBAXXX0000000000}{2:I103BANKDEFFXXXXN}{4:\n:20:REF123\n:32A:240115USD1000,\n:50K:/123456\nJOHN DOE\nLONDON\n:59:/987654\nJANE DOE\nPARIS\n:71A:SHA\n-}'
res = c.validate_and_convert(msg)
print(json.dumps(res, indent=2))
with open('test_mt103.xml', 'w') as f:
    f.write(res.get('mx_message', 'NO MESSAGE'))
