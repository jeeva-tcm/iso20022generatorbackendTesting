
from lxml import etree
import re

# Mocking the msg from lxml for a length violation
# Common lxml length error message:
# Element 'Cd': [facet 'maxLength'] The value 'Passport' has a length of '8'; this exceeds the allowed maximum of '4'.

def bad_value(msg, default=""):
    # 1. Standard lxml: "... value 'xxx' ..."
    # Improved regex with better grouping
    m = re.search(r"(?:[Vv]alue|The\s+value)\s+'([^']*)'", msg)
    if m: return m.group(1)
    
    # 2. Smart quote extraction
    quotes = re.findall(r"'([^']*)'", msg)
    if quotes:
        keywords = {'facet', 'enumeration', 'maxLength', 'minLength', 'pattern', 'base', 'type', 'atomic', 'element', 'attribute'}
        tn_m = re.search(r"Element '([^']+)'", msg)
        tag_name = tn_m.group(1).split('}')[-1] if tn_m else ""

        filtered = []
        for q in quotes:
            clean_q = q.split('}')[-1] if '}' in q else q
            if clean_q not in keywords and clean_q != tag_name and not (clean_q.isdigit() and len(clean_q) < 4):
                filtered.append(q)
        
        if filtered:
            return filtered[0]
        # Fallback
        for q in quotes:
            clean_q = q.split('}')[-1] if '}' in q else q
            if clean_q not in keywords and clean_q != tag_name:
                return q
    
    # 3. Fallback: quote after colon
    m = re.search(r":\s*'([^']*)'", msg)
    if m: return m.group(1)
    
    return default

test_msg = "Element 'Cd': [facet 'maxLength'] The value 'Passport' has a length of '8'; this exceeds the allowed maximum of '4'."
print(f"MSG: {test_msg}")
print(f"RESULT: {bad_value(test_msg)}")

test_msg_alt = "Element 'Cd': 'Passport' is not a valid value of the atomic type 'Max4Text'."
print(f"MSG: {test_msg_alt}")
print(f"RESULT: {bad_value(test_msg_alt)}")
