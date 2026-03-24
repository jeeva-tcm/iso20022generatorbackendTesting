import sys
import os
sys.path.insert(0, r"c:\Users\HP\Documents\ISO Stub Validator\iso20022generatorbackend")

from app.services.mt_mx_converter import MT2MXConverter
from app.services.validator import ISOValidator

mt_msg = """
:20:REF123
:21:REL456
:32A:240324USD1000,
:52A:BANKUS33
:58A:BANKGB22
:50K:/12345
NAME1
ADDR1
:59:/67890
NAME2
ADDR2
"""
converter = MT2MXConverter()
result = converter.validate_and_convert(mt_msg, forced_mt_type="202COV")
mx = result.get("mx_message", "")
print("---- XML START ----")
print(mx)
print("---- XML END ----")

validator = ISOValidator()
detected = validator._detect_message_type(mx)
print(f"Detected Type: '{detected}'")
