import json
import sys
import os

filepath = r"c:/Users/DELL/iso-validator/iso20022generatorbackend/bics/entities.ftm.json"

if not os.path.exists(filepath):
    print("File not found.")
    sys.exit(1)

errors = 0
with open(filepath, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            print(f"Error at line {i}: {e}")
            print(f"Line content: {line[:100]}...")
            errors += 1
            if errors > 10:
                print("Too many errors. Stopping.")
                break

print(f"Scan completed. Total errors: {errors}")
