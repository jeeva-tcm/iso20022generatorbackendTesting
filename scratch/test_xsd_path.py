import os
import sys

xsd_path = r'c:\Users\HP\Desktop\iso final\iso20022generatorbackend\xsds\extracted'

message_type = 'camt.053.001.08'
exact_xsd = f"{message_type}.xsd"
exact_path = os.path.join(xsd_path, exact_xsd)
if os.path.exists(exact_path):
    print("Exact path:", exact_path)
else:
    parts = message_type.split('.')
    family_short = parts[0] + "." + parts[1] if len(parts) >= 2 else message_type
    print("Family short:", family_short)
    
    available_xsds = [f for f in os.listdir(xsd_path) if f.startswith(family_short) and f.endswith(".xsd")]
    if available_xsds:
        available_xsds.sort(reverse=True)
        print("Fallback path:", os.path.join(xsd_path, available_xsds[0]))
