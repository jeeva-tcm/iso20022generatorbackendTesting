import asyncio
import sys

sys.path.append(r'c:\Users\HP\Desktop\iso final\iso20022generatorbackend')
from app.services import mt_mx_converter

sample_mt940 = """{1:F01BANKDEFFAXXX0000000000}{2:I940BANKDEFFXXXXN}{4:
:20:123456
:25:ACC123
:28C:1/1
:60F:C260302USD1000,
:62F:C260302USD1000,
-}"""

res = mt_mx_converter.validate_and_convert(sample_mt940)
print(res.get("mx_message"))
