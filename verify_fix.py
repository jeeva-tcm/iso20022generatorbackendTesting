
import re

def test_logic(msg):
    # Mocking elem_name
    def elem_name(default="A field"):
        m = re.search(r"Element '([^']+)'", msg)
        if not m: return default
        raw = m.group(1)
        return raw.split('}')[-1] if '}' in raw else raw

    # Mocking bad_value with the NEW logic
    def bad_value(default=""):
        m = re.search(r"[Vv]alue\s+'([^']*)'|The\s+value\s+'([^']*)'", msg)
        if m: return m.group(1) or m.group(2) or ""
        quotes = re.findall(r"'([^']*)'", msg)
        if quotes:
            keywords = {'facet', 'enumeration', 'maxLength', 'minLength', 'pattern', 'base', 'type', 'atomic', 'element', 'attribute'}
            tn_m = re.search(r"Element '([^']+)'", msg)
            tag_name = tn_m.group(1).split('}')[-1] if tn_m else ""
            for q in quotes:
                clean_q = q.split('}')[-1] if '}' in q else q
                if clean_q not in keywords and clean_q != tag_name:
                    return q
        m = re.search(r":\s*'([^']*)'", msg)
        if m: return m.group(1)
        return default

    raw_val = bad_value(default="___NOT_EMPTY___")
    is_truly_empty = (
        raw_val == "" or 
        "The value ''" in msg or 
        'The value ""' in msg or 
        "value '' is not accepted" in msg or
        "value is ''" in msg
    )
    
    if is_truly_empty:
        name = elem_name("Cd")
        return f"EMPTY ERROR: {name}"

    if "enumeration" in msg.lower() or "is not an element of the set" in msg.lower():
        ev = bad_value()
        name = elem_name()
        if name == "Cd":
            return f"VALIDATION ERROR: {name} -> {ev}"
            
    return f"OTHER ERROR: {raw_val}"

# Test with a typical enumeration message
msg1 = "Element 'Cd': [facet 'enumeration'] The value 'Passport' is not an element of the set {'BICFI', 'IBAN'}"
print(f"Msg 1: {test_logic(msg1)}")

# Test with a truly empty message
msg2 = "Element 'Cd': [facet 'minLength'] The value '' has a length of '0'..."
print(f"Msg 2: {test_logic(msg2)}")

# Test with atomic type error (no 'value' keyword)
msg3 = "Element 'Cd': 'Passport' is not a valid value of the atomic type 'Max4Text'."
print(f"Msg 3: {test_logic(msg3)}")
