import os

path = r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\app\services\mt_mx_converter.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines[-50:]):
    line_no = len(lines) - 50 + i + 1
    print(f"{line_no}: {repr(line)}")
