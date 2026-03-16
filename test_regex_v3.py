
import re

msg = "Element 'Cd': [facet 'maxLength'] The value 'Passport' has a length of '8'; this exceeds the allowed maximum of '4'."

def bad_value(msg):
    # 1. Standard lxml: "... value 'xxx' ..."
    m = re.search(r"(?:[Vv]alue|The\s+value)\s+'([^']*)'", msg)
    if m: 
        return f"FIRST_CHECK: {m.group(1)}"
    
    # 2. Smart quote extraction (Aggressive filtering)
    quotes = re.findall(r"'([^']*)'", msg)
    return f"QUOTES: {quotes}"

print(bad_value(msg))

msg2 = "Element 'Cd': [facet 'maxLength'] The length '8' is invalid for value 'Passport'."
print(bad_value(msg2))
