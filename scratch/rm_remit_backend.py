import os
import re

file_path = r'c:\Users\HP\Desktop\iso final\iso20022generatorbackend\app\services\mt_mx_converter.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the line `if mt_type == "103" and b2_subtype == "REMIT": return "103 REMIT"`
content = re.sub(r'\s*if mt_type == "103" and b2_subtype == "REMIT": return "103 REMIT"\n', '\n', content)

# Remove the line `if sub_type == "REMIT": return "103 REMIT"`
content = re.sub(r'\s*if sub_type == "REMIT": return "103 REMIT"\n', '\n', content)

# Also remove `"103REMIT"` from the heal list
content = content.replace('"103", "103+", "103REMIT"', '"103", "103+"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Removed MT103 REMIT detection logic.")

# Optionally remove the mapping file
mapping_file = r'c:\Users\HP\Desktop\iso final\iso20022generatorbackend\app\mappings\MT103 REMIT.json'
if os.path.exists(mapping_file):
    os.remove(mapping_file)
    print("Deleted MT103 REMIT mapping file.")
