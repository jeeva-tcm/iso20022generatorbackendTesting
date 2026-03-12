
import re

def bad_value(msg, tag_name="", default=""):
    # 1. Standard lxml: "... value 'xxx' ..."
    # Specifically looking for the data value
    m = re.search(r"(?:[Vv]alue|The\s+value)\s+'([^']*)'", msg)
    if m: 
        val = m.group(1)
        # If the matched value is a small digit and there are other quotes, maybe we picked the wrong one
        if not (val.isdigit() and len(val) < 4):
             return val

    # 2. Smart quote extraction
    quotes = re.findall(r"'([^']*)'", msg)
    if quotes:
        keywords = {'facet', 'enumeration', 'maxLength', 'minLength', 'pattern', 'base', 'type', 'atomic', 'element', 'attribute'}
        
        filtered = []
        for q in quotes:
            clean_q = q.split('}')[-1] if '}' in q else q
            # Ignore keywords, tag names, and small numeric strings in quotes (usually facets)
            if clean_q not in keywords and clean_q != tag_name and not (clean_q.isdigit() and len(clean_q) < 4):
                filtered.append(q)
        
        if filtered:
            # Prefer the longest one if multiple remain (e.g. 'Passport' vs 'Max4Text')
            return max(filtered, key=len)
            
        # Fallback to any non-keyword, non-tag
        for q in quotes:
            clean_q = q.split('}')[-1] if '}' in q else q
            if clean_q not in keywords and clean_q != tag_name:
                return q
    
    # 3. Fallback: quote after colon
    m = re.search(r":\s*'([^']*)'", msg)
    if m: return m.group(1)
    
    return default

# Simulated lxml messages
msgs = [
    "Element 'Cd': [facet 'maxLength'] The value 'Passport' has a length of '8'; this exceeds the allowed maximum of '4'.",
    "Element 'Cd': 'Passport' is not a valid value of the atomic type 'Max4Text'.",
    "Element '{urn:iso}Cd': [facet 'enumeration'] The value 'Passport' is not an element of the set {'BICFI', 'IBAN'}",
    "Element 'Cd': The length '8' is invalid for value 'Passport'."
]

for m in msgs:
    print(f"MSG: {m}")
    print(f"RESULT: {bad_value(m, 'Cd')}")
    print("-" * 20)
