from lxml import etree
import re

def friendly_error(msg):
    def elem_name(default="A field"):
        m = re.search(r"Element '([^']+)'", msg)
        return m.group(1).split('}')[-1] if m else default

    def bad_value(default=""):
        m = re.search(r"[Vv]alue '([^']*)'", msg)
        if m: return m.group(1)
        m = re.search(r"Element '[^']+': '([^']*)'", msg)
        if m: return m.group(1)
        m = re.search(r": '([^']*)'", msg)
        return m.group(1) if m else default

    val = bad_value(default="___NONE___")
    print(f"Extracted Value: '{val}'")
    
    if val == "" or "''" in msg or '""' in msg:
        name = elem_name()
        return f"❌ Empty elements found in '{name}'"
    return "FAILED TO CATCH"

# Simulated LXML error for <MsgId></MsgId>
msg1 = "Element 'MsgId': '' is not a valid value of the atomic type 'Max35Text'."
msg2 = "Element '{urn:iso:std:iso:20022:tech:xsd:head.001.001.01}MsgId': [facet 'minLength'] The value '' has a length of 0; this underruns the allowed minimum length of 1."

print(f"Test 1: {friendly_error(msg1)}")
print(f"Test 2: {friendly_error(msg2)}")
