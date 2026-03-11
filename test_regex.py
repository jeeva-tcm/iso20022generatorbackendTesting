import json
import re

j_str = '{"selector": ".*\\\\.Ctry$"}'
j = json.loads(j_str)
selector = j["selector"]
regex = re.compile(selector)

key = "Document.FIToFICstmrCdtTrf.CdtTrfTxInf.Dbtr.PstlAdr.Ctry"
print(f"Selector: {selector}")
print(f"Match: {bool(regex.match(key))}")
