
import re

msg = "Element 'Cd': [facet 'maxLength'] The value 'Passport' has a length of '8'; this exceeds the allowed maximum of '4'."

def test_extraction(msg):
    name = "Cd"
    # Current logic in bad_value
    quotes = re.findall(r"'([^']*)'", msg)
    print(f"Standard findall: {quotes}")
    
    # Logic in Rule 13 fallback
    # re.findall(r"'(?!\d')(.*?)'", msg)
    best_guess = re.findall(r"'(?!\d')(.*?)'", msg)
    print(f"Rule 13 fallback (problematic): {best_guess}")
    
    # Better logic:
    # We want quotes that contain text, and we want to exclude keywords.
    technical = {'facet', 'enumeration', 'maxLength', 'minLength', 'pattern', 'base', 'type', 
                 'atomic', 'element', 'attribute', 'length', 'exceeds', 'allowed', 
                 'maximum', 'Identifier', 'value', name}
    
    real_quotes = re.findall(r"'([^']*)'", msg)
    candidates = [q for q in real_quotes if q not in technical and q.lower() not in technical]
    # Filter out small numbers
    candidates = [c for c in candidates if not (c.isdigit() and len(c) < 4)]
    
    if candidates:
        # Prefer the one with most alpha chars
        lv = max(candidates, key=lambda x: sum(c.isalpha() for c in x))
        print(f"Fixed extraction: {lv}")
    else:
        print("Fixed extraction: NOT FOUND")

test_extraction(msg)
