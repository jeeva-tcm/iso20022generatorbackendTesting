import os
import sys
import asyncio

# Ensure app is in python path
THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(THIS, ".."))
sys.path.insert(0, ROOT)

from app.services.bulk_generator import generate_single_xml
from app.services.validator import ISOValidator

async def main():
    print("Generating and validating pacs.002.001.10 XML messages...")
    v = ISOValidator()
    
    # Selected blocks for pacs.002
    test_cases = [
        [],
        ["instructing_agent", "instructed_agent"],
        ["debtor", "creditor"],
        ["instructing_agent", "instructed_agent", "debtor", "creditor"]
    ]
    
    for idx, selected in enumerate(test_cases):
        print(f"\n--- Test Case {idx}: {selected} ---")
        try:
            xml = generate_single_xml("pacs.002.001.10", selected, idx)
            print("Generated XML (part):")
            lines = xml.split("\n")
            tx_inf_lines = []
            capture = False
            for line in lines:
                if "<TxInfAndSts>" in line:
                    capture = True
                if capture:
                    tx_inf_lines.append(line)
                if "</TxInfAndSts>" in line:
                    capture = False
            print("\n".join(tx_inf_lines[:40]))
            if len(tx_inf_lines) > 40:
                print("...")
                print("\n".join(tx_inf_lines[-10:]))
            
            report = await v.validate(xml, message_type="pacs.002.001.10")
            res = report.to_dict()
            print(f"Validation status: {res.get('status')}")
            if res.get("status") == "FAIL":
                for issue in res.get("details", []):
                    print(f" - [{issue.get('severity')}] {issue.get('code')}: {issue.get('message')} at {issue.get('path')}")
            else:
                print("SUCCESS!")
        except Exception as e:
            print(f"Exception occurred: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
