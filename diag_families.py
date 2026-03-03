import os
import collections

xsd_dir = r'c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\xsds\extracted'
if not os.path.exists(xsd_dir):
    print("XSD directory not found")
else:
    files = [f for f in os.listdir(xsd_dir) if f.endswith('.xsd')]
    print(f"Total XSDs: {len(files)}")
    
    families = collections.defaultdict(int)
    for f in files:
        family = f.split('.')[0]
        families[family] += 1
    
    for family, count in sorted(families.items()):
        print(f"{family}: {count}")
