import ast
import sys

path = r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\app\services\mt_mx_converter.py"
try:
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    ast.parse(source)
    print("SYNTAX OK - no errors found")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    print(f"Text: {e.text!r}")
