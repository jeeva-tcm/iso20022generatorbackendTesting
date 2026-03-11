import json
import re

codelists = {
    "country": {
        "codes": ["US", "GB"]
    }
}
data = {
    "Document.FIToFICstmrCdtTrf.CdtTrfTxInf.Dbtr.PstlAdr.Ctry": "ZZ",
    "AppHdr.Fr.FIId.FinInstnId.Othr.Ctry": "XYZ"
}

selector = ".*\\.Ctry$"
regex = re.compile(selector)
matching_keys = [k for k in data.keys() if regex.match(k)]

print("matching_keys:", matching_keys)

list_name = "country"
cl_data = codelists[list_name]
valid_codes = cl_data.get("codes", [])

for key in matching_keys:
    value = data[key]
    if value not in valid_codes:
        field_name = key.split('.')[-1]
        msg = f"Invalid country code '{value}' in field '{field_name}'."
        print("Issue added:", msg)
