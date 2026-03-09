from app.services.mt_mx_converter import MT2MXConverter

converter = MT2MXConverter(mappings_dir="app/mappings")
msg = """{1:F01BBBBUS33AXXX0000000000}{2:I103CCCCGB2LXXXXN}{3:{121:550e8400-e29b-41d4-a716-446655440000}}{4:
:20:REF20261231001
:23B:CRED
:32A:261231USD1500,00
:50K:/US33XXX12345678901234
JOHN DOE CORP
123 MAIN STREET
NEW YORK US
:52A:BBBBUS33XXX
:53A:BBBBUS33XXX
:57A:CCCCGB2LXXX
:59:/GB29NWBK60161331926819
JANE SMITH LTD
ddddddddddddddddddddd
ddddddddddddddddd
dddddddddddddddddd
ddddddddddddddd
ddddddddddddddddddd
dddddddddddddddddd
ddddddddddddddddddddddd
dddddddddddddddddddddd
ddddddddddddddddddd
dddddddddddddddddddddddddddddddddd
456 HIGH STREET
LONDON GB
:70:PAYMENT FOR INVOICE 12345
asdfsdvvvnervjvenv
:71A:SHA
-}"""

result = converter.validate_and_convert(msg)
print("Status:", result.get("status"))
if "errors" in result:
    for e in result["errors"]:
        print("Error:", e)
else:
    print("Success! MX generated.")
