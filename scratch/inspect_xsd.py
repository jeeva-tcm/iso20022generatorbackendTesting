import re
import os

def inspect_file(path, type_pattern):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"\n====== Inspecting {os.path.basename(path)} for pattern: {type_pattern} ======")
    # Find complexTypes containing pattern
    for match in re.finditer(r'<xs:complexType name="([^"]*' + type_pattern + r'[^"]*)">.*?</xs:complexType>', content, re.DOTALL):
        print(f"\nFound ComplexType: {match.group(1)}")
        print(match.group(0))

import sys

if len(sys.argv) > 2:
    inspect_file(sys.argv[1], sys.argv[2])
else:
    inspect_file("xsds/extracted/pacs.010.001.03.xsd", "CreditInstruction")
    inspect_file("xsds/extracted/pain.002.001.10.xsd", "OriginalGroupInformation")
    inspect_file("xsds/extracted/pain.008.001.08.xsd", "PaymentInstruction")
